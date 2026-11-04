"""Linux-only native smoke. All input is generated here; raw OCR is never saved."""
import argparse
from dataclasses import asdict
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import threading
import time

import psutil
from services.ocr.configuration import OCRConfiguration
from services.ocr.errors import DocumentProcessingError
from services.ocr.limits import DocumentLimits
from services.ocr.worker import LocalDocumentWorker
from staging_tools.fixtures import image


class VerificationError(Exception):
    pass


def import_probe(connection, limits, model_root):
    """Run native imports inside the same supervised, RSS-limited worker boundary."""
    with open(os.devnull, 'w') as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    try:
        connection.recv()
        import paddle
        from paddleocr import PaddleOCR  # noqa: F401
        connection.send(('ok', {'cpuOnly': not paddle.is_compiled_with_cuda()}))
    except Exception:
        connection.send(('ok', {'importFailed': True}))
    finally:
        connection.close()


def verify_result(result):
    """Independent known fixture expectations; never fill in missing OCR fields."""
    from models.schemas import DocumentUploadResultSchema
    from staging_tools.fixtures import verify_partial
    public = DocumentUploadResultSchema.model_validate({
        **result, 'source': 'deterministic', 'deadline': result['primaryDeadline'],
        'urgency': None, 'relatedGuide': None,
        'officialWarning': ' '.join(result['warnings']) or None,
    }).model_dump(mode='json')
    verify_partial(public)
    checks = {
        'documentType': public['documentType'] == 'National Health Insurance Tax',
        'paymentDeadline': any(d['kind'] == 'payment' and d['date'] == '2031-06-30'
            and d['status'] == 'verified' and d['label'] == 'Payment deadline' for d in public['deadlines']),
        'separateExpiration': any(d['kind'] == 'usage_expiration' and d['date'] == '2032-06-30'
            and d['status'] == 'verified' for d in public['deadlines']),
        'verifiedPaymentAmount': any(a['kind'] == 'payment' and a['value'] == 5000
            and a['status'] == 'verified' for a in public['amounts']),
        'nullPrimaryAmount': public['primaryAmount'] is None,
        'partialStatus': public['extractionStatus'] == 'partial',
    }
    text = ''.join(e['text'] for e in public['evidence'])
    checks['japaneseRecognition'] = all(label in text for label in ('納期限', '利用期限', '納付額'))
    ids = {e['id'] for e in public['evidence']}
    fields = public['deadlines'] + public['amounts']
    checks['evidenceRetention'] = bool(ids) and all(
        field['evidenceIds'] and set(field['evidenceIds']) <= ids
        for field in fields if field['status'] == 'verified')
    without_evidence = {key: value for key, value in public.items() if key != 'evidence'}
    checks['englishPublicOutput'] = not any('\u3040' <= c <= '\u9fff'
        for c in json.dumps(without_evidence, ensure_ascii=False))
    if not all(checks.values()):
        raise VerificationError('SYNTHETIC_EXPECTATIONS_FAILED')
    return checks


def cgroup_sample():
    # Imported only when invoked from repository root with both source roots on PYTHONPATH.
    from ci.linux_ocr import cgroups
    rows = cgroups()
    current = [r['currentBytes'] for r in rows if r['currentBytes'] is not None]
    peak = [r['kernelPeakBytes'] for r in rows if r['kernelPeakBytes'] is not None]
    return {'currentBytes': max(current) if current else None,
            'kernelLifetimePeakBytes': max(peak) if peak else None}


def run(state, mode):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise VerificationError('LINUX_X86_64_REQUIRED')
    config, limits = OCRConfiguration(), DocumentLimits()
    worker = LocalDocumentWorker(limits, state / 'models', config=config,
        lock_path=state / 'ocr-worker.lock', **({'target': import_probe} if mode == 'import' else {}))
    output = {'status': 'failed', 'failureCode': None, 'configuration': asdict(config),
              'workerRssLimitBytes': limits.max_worker_rss_bytes,
              'samplingSeconds': .05, 'rows': [], 'workerClosed': False,
              'versions': {name: importlib.metadata.version(name) for name in
                           ('paddlepaddle', 'paddleocr', 'paddlex', 'Pillow', 'pypdfium2', 'psutil')}}
    samples = []
    stopped = threading.Event()
    def monitor():
        while not stopped.wait(.05):
            samples.append(cgroup_sample())
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    previous_pid = None
    last_process = None
    try:
        data = b'probe' if mode == 'import' else image('partial', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
        for index in range(1 if mode == 'import' else 3):
            from services.ocr.resources import available_memory_bytes
            if available_memory_bytes() < 3 * 1024**3:
                raise VerificationError('INSUFFICIENT_RUNTIME_MEMORY')
            if mode != 'import':
                import shutil
                if shutil.disk_usage(state).free < 2 * 1024**3:
                    raise VerificationError('INSUFFICIENT_RUNTIME_DISK')
            start = time.monotonic()
            result = worker.analyze(data, 'png')
            elapsed = time.monotonic() - start
            last_process = psutil.Process(worker._process.pid)
            if mode == 'import':
                if result.get('importFailed') or result.get('cpuOnly') is not True:
                    raise VerificationError('CPU_IMPORT_FAILED')
                output['cpuOnly'] = True
                checks = {'nativeCpuImport': True}
            else:
                checks = verify_result(result)
                if index == 0 and worker.last_metrics.get('modelInitSeconds', 0) <= 0:
                    raise VerificationError('MODEL_INITIALIZATION_NOT_OBSERVED')
                if index and (previous_pid != worker._process.pid or worker.last_metrics.get('modelInitSeconds') != 0):
                    raise VerificationError('WARM_WORKER_NOT_REUSED')
                if worker.last_metrics.get('inferenceCalls', 0) < 1:
                    raise VerificationError('NATIVE_INFERENCE_NOT_OBSERVED')
            output['rows'].append({'request': index + 1, 'seconds': round(elapsed, 4),
                'modelInitSeconds': worker.last_metrics.get('modelInitSeconds'),
                'inferenceSeconds': worker.last_metrics.get('inferenceSeconds'),
                'inferenceCalls': worker.last_metrics.get('inferenceCalls'),
                'peakWorkerRssBytes': worker.last_peak_rss_bytes,
                'workerReused': previous_pid == worker._process.pid if index else False,
                'checks': checks})
            previous_pid = worker._process.pid
            result = None  # Never serialize or print raw predictions/evidence.
        output['status'] = 'passed'
    except (DocumentProcessingError, VerificationError) as error:
        output['failureCode'] = error.code if isinstance(error, DocumentProcessingError) else str(error)
    except Exception:
        output['failureCode'] = 'NATIVE_VERIFICATION_FAILED'
    finally:
        worker.close()
        stopped.set()
        monitor_thread.join(timeout=2)
        output['workerClosed'] = worker._process is None and (last_process is None or not last_process.is_running())
        if not output['workerClosed']:
            output.update(status='failed', failureCode='WORKER_CLEANUP_FAILED')
        sampled = [s['currentBytes'] for s in samples if s['currentBytes'] is not None]
        lifetime = [s['kernelLifetimePeakBytes'] for s in samples if s['kernelLifetimePeakBytes'] is not None]
        output['peakSampledCgroupBytes'] = max(sampled) if sampled else None
        output['kernelCgroupLifetimePeakBytes'] = max(lifetime) if lifetime else None
        output['cgroupScopeNote'] = 'Shared/ancestor counters may include other job processes; kernel peak is lifetime, not reset.'
        output['temporaryImageFilesCreated'] = 0  # Fixture is rendered into BytesIO only.
        output['peakWorkerRssBytes'] = max([r['peakWorkerRssBytes'] for r in output['rows']] + [worker.last_peak_rss_bytes])
        if mode != 'import':
            output['coldStartSeconds'] = output['rows'][0]['seconds'] if output['rows'] else None
            output['medianWarmSeconds'] = statistics.median([r['seconds'] for r in output['rows'][1:]]) if len(output['rows']) > 1 else None
            output['modelInitializationObserved'] = any(
                r['modelInitSeconds'] is not None and r['modelInitSeconds'] > 0 for r in output['rows']) or worker.last_metrics.get('modelInitSeconds', 0) > 0
            output['nativeInferenceObserved'] = any(
                r['inferenceCalls'] is not None and r['inferenceCalls'] > 0 for r in output['rows']) or worker.last_metrics.get('inferenceCalls', 0) > 0
            output['models'] = []
            for name in ('PP-OCRv6_medium_det', 'PP-OCRv6_medium_rec'):
                manifest = state / 'models' / name / 'installation.json'
                if manifest.is_file():
                    info = json.loads(manifest.read_text())
                    output['models'].append({'name': name, 'revision': info['revision'], 'sha256': info['sha256']})
        from ci.linux_ocr import write_json
        write_json(state / ('import-probe.json' if mode == 'import' else 'inference.json'), output)
        print(mode, output['status'], output['failureCode'] or '')
    return output['status'] == 'passed'


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['import', 'inference'])
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    from ci.linux_ocr import GateError, state_path, write_json
    try:
        state = state_path(args.state)
    except GateError as error:
        print(str(error), file=sys.stderr)
        return 1
    try:
        return 0 if run(state, args.mode) else 1
    except VerificationError as error:
        # Architecture rejection happens before any worker/model is created.
        # Still leave an explicit failed gate for the always-run summary.
        write_json(state / ('import-probe.json' if args.mode == 'import' else 'inference.json'),
                   {'status': 'failed', 'failureCode': str(error), 'workerStarted': False})
        print(args.mode, 'failed', str(error))
        return 1


if __name__ == '__main__':
    sys.exit(main())
