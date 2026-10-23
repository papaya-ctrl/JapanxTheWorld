"""One-model, bounded benchmark. Reports actual OS and null unavailable counters."""
import argparse
from dataclasses import replace
from io import BytesIO
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import threading
import time

import psutil
from services.ocr.configuration import OCRConfiguration
from services.ocr.limits import DocumentLimits
from services.ocr.resources import available_memory_bytes,cgroup_memory
from services.ocr.worker import LocalDocumentWorker


def fixture(font_path=None):
    from PIL import Image,ImageDraw,ImageFont
    candidates=[font_path,'/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']
    path=next((Path(p) for p in candidates if p and Path(p).is_file()),None)
    if path is None:raise ValueError('Provide an installed Japanese-capable --font.')
    font=ImageFont.truetype(str(path),27);output=BytesIO()
    with Image.new('RGB',(480,480),'white') as image:
        draw=ImageDraw.Draw(image)
        for i,line in enumerate(['住民税 納付書','納期限 2031年6月30日','納付額 5,000円']):draw.text((24,40+i*110),line,font=font,fill='black')
        image.save(output,format='PNG')
    return output.getvalue()


def verify(result):
    assert result['documentType']=='Residence Tax'
    assert result['primaryDeadline']=='2031-06-30' and result['primaryAmount']==5000
    assert any(d['kind']=='payment' and d['status']=='verified' and d['date']=='2031-06-30' for d in result['deadlines'])
    assert any(a['kind']=='payment' and a['status']=='verified' and a['value']==5000 for a in result['amounts'])


def run(data,*,model_root=None,repeat=3,recycle=False,lock_path=None,synthetic=True):
    if not 2<=repeat<=5:raise ValueError('Use two to five bounded requests.')
    if available_memory_bytes()<(3 if synthetic else 5)*1024**3:raise RuntimeError('Insufficient available memory for this bounded benchmark.')
    from middleware.file_validator import detect_document_kind
    if len(data)>DocumentLimits().max_file_bytes:raise ValueError('Input exceeds the production upload limit.')
    kind=detect_document_kind(data)
    limits=DocumentLimits(max_worker_requests=2 if recycle else 64)
    worker=LocalDocumentWorker(limits,model_root,config=OCRConfiguration(),lock_path=lock_path)
    stopped=threading.Event();samples=[];rows=[];last_pid=None
    def monitor():
        process=psutil.Process()
        while not stopped.wait(.05):
            try:
                children=process.children(recursive=True)
                infos=[(child.pid,child.memory_info().rss,child.cpu_times()) for child in children if child.is_running()]
                samples.append({'rss':max((r[1] for r in infos),default=0),'cgroup':cgroup_memory(),
                                'cpuByPid':{r[0]:r[2].user+r[2].system for r in infos}})
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    try:
        for index in range(repeat):
            start=time.perf_counter();begin=len(samples)
            result=worker.analyze(data,kind)
            if synthetic:verify(result)
            result=None
            elapsed=time.perf_counter()-start
            pid=worker._process.pid
            observed=samples[begin:]
            cpu_values=[s['cpuByPid'][pid] for s in observed if pid in s['cpuByPid']]
            current=cgroup_memory()
            rows.append({'request':index+1,'seconds':round(elapsed,4),
                'modelInitSeconds':round(worker.last_metrics.get('modelInitSeconds',0),4),
                'inferenceSeconds':round(worker.last_metrics.get('inferenceSeconds',0),4),
                'peakRssMiB':round(worker.last_peak_rss_bytes/1024**2,2),
                'rssAfterMiB':round(worker.last_metrics.get('rssAfterBytes',0)/1024**2,2),
                'cpuUtilizationPercent':round(max(0,(cpu_values[-1]-cpu_values[0]))/elapsed*100,1) if len(cpu_values)>1 else None,
                'containerCurrentMiB':round(current['currentBytes']/1024**2,2) if current['currentBytes'] is not None else None,
                'containerPeakSampleMiB':round(max(s['cgroup']['currentBytes'] for s in observed if s['cgroup']['currentBytes'] is not None)/1024**2,2) if any(s['cgroup']['currentBytes'] is not None for s in observed) else None,
                'workerReused':last_pid==pid if last_pid is not None else False,'workerRecycled':last_pid!=pid if last_pid is not None else False,'knownSyntheticFieldsCorrect':True if synthetic else None})
            last_pid=pid
    finally:
        worker.close();stopped.set();thread.join(timeout=1)
    warm=[r['seconds'] for r in rows if r['modelInitSeconds']==0]
    return {'environment':{'os':platform.system(),'machine':platform.machine(),'python':platform.python_version(),
            'logicalCpus':psutil.cpu_count(),'hostRamGiB':round(psutil.virtual_memory().total/1024**3,2),
            'cgroupMemoryLimitMiB':round(cgroup_memory()['limitBytes']/1024**2,2) if cgroup_memory()['limitBytes'] is not None else None,
            'versions':{name:importlib.metadata.version(name) for name in ['paddleocr','paddlepaddle','paddlex','Pillow']},
            'samplingSeconds':.05,'platformRequested':os.environ.get('STAGING_PLATFORM'),
            'declaredHostMachine':os.environ.get('STAGING_HOST_MACHINE'),'declaredHostOS':os.environ.get('STAGING_HOST_OS'),
            'containerExecution':Path('/.dockerenv').exists()},
            'workload':'explicitly_synthetic_480x480_japanese' if synthetic else 'private_input_unscored','configuration':{'models':'Medium/Medium','batch':1,'cpuThreads':4,'detectorSide':1600,'rssCapGiB':5},
            'rows':rows,'coldSeconds':rows[0]['seconds'],
            'medianWarmSeconds':round(statistics.median(warm),4) if warm else None,
            'estimatedSerialDocumentsPerMinute':round(60/statistics.median(warm),2) if warm else None,
            'endRssGrowthMiB':round(rows[-1]['rssAfterMiB']-rows[0]['rssAfterMiB'],2),
            'workerClosed':worker._process is None,'recycleMode':recycle,
            'memoryGrowthLimitation':'Only bounded requests; not a leak or sustained-throughput proof.'}


def main(argv=None):
    parser=argparse.ArgumentParser();inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--small-synthetic',action='store_true');inputs.add_argument('--private-input',type=Path)
    parser.add_argument('--repeat',type=int,default=3);parser.add_argument('--verify-recycling',action='store_true');parser.add_argument('--font',type=Path)
    parser.add_argument('--output',type=Path);args=parser.parse_args(argv)
    root=os.environ.get('DOCUMENT_OCR_MODEL_ROOT') or str(Path.home()/'.paddlex/official_models')
    # Share the same lease as the production app. If that cached worker is alive,
    # the benchmark fails busy instead of loading a duplicate model.
    lock=Path(os.environ.get('DJANGO_STATE_DIR','/var/lib/japanxtheworld'))/'ocr-worker.lock' if Path('/.dockerenv').exists() else None
    if args.private_input:
        path=args.private_input.expanduser().resolve()
        if path.is_relative_to(Path(__file__).resolve().parents[2]):raise ValueError('Use private input outside the checkout.')
        if path.stat().st_size>DocumentLimits().max_file_bytes:raise ValueError('Input exceeds the production upload limit.')
        data=path.read_bytes()
    else:data=fixture(args.font)
    report=run(data,model_root=root,repeat=args.repeat,recycle=args.verify_recycling,lock_path=lock,synthetic=args.small_synthetic)
    if args.verify_recycling and not any(r['workerRecycled'] for r in report['rows']):raise ValueError('Use at least three requests to observe request-count recycling.')
    if args.output:
        path=args.output.expanduser().resolve()
        if path.is_relative_to(Path(__file__).resolve().parents[2]):raise ValueError('Keep benchmark artifacts outside the checkout.')
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);path.write_text(json.dumps(report,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps(report))


if __name__=='__main__':main()
