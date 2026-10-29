"""Step 12 CLI: independent datasets, guarded native runs and frozen OCR replay."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import threading
import time
import psutil

from .quality import score_document,summarize_quality
from .schema import Dataset,truth_dict,CATEGORIES,PROVENANCES,ISSUED_PROVENANCES
from .vault import private_path,read_json,save_json,write_private


def initialize(inputs,output,*,provenance='real_private',authorized=False,key=None):
    paths=[Path(p).expanduser().resolve() for p in inputs]
    if any(not p.is_file() or p.suffix.lower() not in {'.png','.jpg','.jpeg','.webp','.pdf'} for p in paths):raise ValueError('Supply existing supported authorized inputs.')
    if any(p.stat().st_size>10*1024**2 for p in paths):raise ValueError('Inputs must respect the production upload limit.')
    dataset=Dataset.model_validate({'schemaVersion':2,'targetRealDocuments':40,'documents':[
        {'id':f"{'P' if provenance=='public_sample_form' else 'R'}{i+1:03d}",'path':str(path),'inputSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'provenance':provenance,'category':None,
         'authorizationConfirmed':authorized,'groundTruth':{'complete':False,'verification':{'status':'unreviewed','method':'pending'}}}
        for i,path in enumerate(paths)]})
    # exclude_unset prevents unknown optional facts from becoming null assertions.
    save_json(output,dataset.model_dump(exclude_unset=True),key)
    return len(paths)


def documents(path,*,legacy=False,key=None):
    raw=read_json(path,key)
    if raw.get('schemaVersion')==2:
        dataset=Dataset.model_validate(raw)
        result=[]
        for d in dataset.documents:
            if not d.authorizationConfirmed:raise ValueError('Confirm authorization for every supplied input.')
            path=Path(d.path).expanduser().resolve()
            if path.stat().st_size>10*1024**2 or hashlib.sha256(path.read_bytes()).hexdigest()!=d.inputSha256:raise ValueError('Document bytes changed; independent annotations require re-review.')
            item=d.model_dump();item['groundTruth']=truth_dict(d);result.append(item)
        return result
    if not legacy:raise ValueError('Legacy known facts require explicit --legacy-known-facts acknowledgement.')
    from .runner import validate_manifest
    result=validate_manifest(raw)['documents']
    if not 1<=len(result)<=50:raise ValueError('Use one to fifty documents.')
    for item in result:
        if not item['groundTruth'].get('complete') and not (item['groundTruth'].get('deadlines') or item['groundTruth'].get('amounts')):
            item['groundTruth']['verification']={'status':'unreviewed','method':'pending'}
    return result


def _row(item,result,outcome,resources=None):
    from .review import digest
    return {'id':item['id'],'category':item['category'] or 'unassigned','provenance':item['provenance'],
        'outcome':outcome,'accuracy':score_document(result,item['groundTruth'],outcome=outcome),
        'inputSha256':item.get('inputSha256'),'groundTruthSha256':digest(item['groundTruth']),
        'resources':resources or {}}


def report(rows,mode,*,environment=None):
    groups={}
    for provenance in PROVENANCES:
        selected=[r for r in rows if r['provenance']==provenance]
        if selected:groups[provenance]={'summary':summarize_quality(selected),
            'categories':{category:summarize_quality([r for r in selected if r['category']==category]) for category in sorted({r['category'] for r in selected})}}
    backend=Path(__file__).resolve().parents[1]
    fingerprints={name:hashlib.sha256((backend/name).read_bytes()).hexdigest() for name in [
        'services/documentAnalysis/fields/engine.py','services/documentAnalysis/fields/dates.py',
        'services/documentAnalysis/fields/layout.py','evaluation/quality.py','evaluation/schema.py']}
    return {'schemaVersion':2,'mode':mode,'environment':environment,'targetRealDocuments':40,
        'implementationSha256':fingerprints,
        'groups':groups,'rows':rows,
        'missingRealCategories':sorted(CATEGORIES-{r['category'] for r in rows if r['provenance'] in ISSUED_PROVENANCES}),
        'groundTruthPolicy':'independent_annotations_only_no_prediction_promotion',
        'linuxRuntimeVerified':False,'publicProductionReady':False}


def replay(manifest,archive,*,legacy=False,profile='medium-side1600',annotation_key=None,output=None,key=None):
    from .profiles import PROFILES
    from services.ocr.records import OCRBox
    from services.documentAnalysis.fields.engine import extract_fields
    if profile not in PROFILES:raise ValueError('Unsupported archived profile.')
    archive=private_path(archive);old=read_json(archive/'metrics.json')
    historical={r['documentId']:r for r in old['profiles'][profile]['rows'] if r['repeat']==0}
    rows=[]
    for item in documents(manifest,legacy=legacy,key=annotation_key):
        previous=historical.get(item['id']);path=archive/f"{profile}-{item['id']}-0-private.json"
        resources=previous['resources'] if previous else {}
        result=None;outcome=previous['resources']['outcome'] if previous else 'ARCHIVE_RESULT_MISSING'
        if outcome=='ok' and path.is_file():
            original=read_json(path)
            boxes=[OCRBox(e['id'],e['text'],e['confidence'],tuple(e['bbox']),e['page'],e['originalIndex'],tuple(tuple(p) for p in e['polygon']) if e.get('polygon') else None) for e in original['evidence']]
            result=extract_fields(boxes)
        elif outcome=='ok':outcome='ARCHIVE_RESULT_MISSING'
        # Resource counters belong to the historical run, not today's replay.
        allowed={k:resources[k] for k in ['elapsedSeconds','peakRssBytes','modelInitSeconds','inferenceSeconds'] if k in resources}
        rows.append(_row(item,result,outcome,allowed))
        if key and result is not None:save_json(Path(output)/(item['id']+'.result.fernet'),result,key)
    result=report(rows,'frozen_step9_ocr_current_engine_replay',environment=old.get('environment'))
    result['timingOrigin']='historical_ocr_not_new_native_measurements'
    result['archivePairingLimitation']='legacy_archive_identifies_inputs_by_id_without_saved_input_hash_binding'
    return result


class Observation:
    def __init__(self,worker):self.worker=worker;self.samples=[];self.stop=threading.Event();self.pressure=False;self.swap=psutil.swap_memory().used
    def __enter__(self):
        def monitor():
            while not self.stop.wait(.05):
                try:
                    process=self.worker._process
                    if process:
                        child=psutil.Process(process.pid);cpu=child.cpu_times()
                        self.samples.append((child.pid,child.memory_info().rss,cpu.user+cpu.system))
                    if psutil.swap_memory().used-self.swap>512*1024**2:
                        self.pressure=True
                        if process and process.is_alive():process.terminate()
                        return
                except (psutil.NoSuchProcess,psutil.AccessDenied,ValueError):pass
        self.thread=threading.Thread(target=monitor,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join(timeout=1)


def native(manifest,output,*,legacy=False,small=False,key=None,annotation_key=None,model_root=None,require_pilot_review=False):
    from middleware.file_validator import detect_document_kind
    from services.ocr.configuration import OCRConfiguration
    from services.ocr.errors import DocumentProcessingError
    from services.ocr.limits import DocumentLimits
    from services.ocr.resources import available_memory_bytes,cgroup_memory
    from services.ocr.worker import LocalDocumentWorker
    inputs=documents(manifest,legacy=legacy,key=annotation_key)
    if require_pilot_review:
        from .pilot import review_gaps
        if legacy or any(review_gaps(item) for item in inputs):raise ValueError('Formal pilot requires complete independent human review for every sample.')
    if key:
        from .vault import key_bytes
        from cryptography.fernet import Fernet
        Fernet(key_bytes(key,output))
    if small:
        from PIL import Image
        for item in inputs:
            if item['provenance']!='synthetic':raise ValueError('The smaller memory allowance is only for bounded synthetic PNGs.')
            with Image.open(item['path']) as image:
                if image.format!='PNG' or max(image.size)>640:raise ValueError('Small mode requires PNG inputs no larger than 640x640.')
    worker=LocalDocumentWorker(DocumentLimits(min_host_available_bytes=768*1024**2),
        model_root or os.environ.get('DOCUMENT_OCR_MODEL_ROOT'),config=OCRConfiguration())
    rows=[];halted=None;first=True
    try:
        for item in inputs:
            minimum=(3 if small else 5)*1024**3
            if halted or first and available_memory_bytes()<minimum:
                halted=halted or 'NOT_EXECUTED_START_MEMORY_GUARD'
                rows.append(_row(item,None,halted));continue
            path=Path(item['path']).expanduser().resolve();size=path.stat().st_size
            if size>worker.limits.max_file_bytes:
                rows.append(_row(item,None,'DOCUMENT_LIMIT_EXCEEDED'));continue
            data=path.read_bytes();before=hashlib.sha256(data).digest();result=None;started=time.perf_counter();outcome='ok'
            with Observation(worker) as observed:
                try:result=worker.analyze(data,detect_document_kind(data))
                except DocumentProcessingError as error:outcome=error.code
            elapsed=time.perf_counter()-started;first=False
            if observed.pressure:outcome='HOST_SWAP_GUARD';halted='NOT_EXECUTED_AFTER_HOST_GUARD';result=None
            if outcome=='ANALYSIS_MEMORY_LIMIT':halted='NOT_EXECUTED_AFTER_MEMORY_GUARD'
            if hashlib.sha256(path.read_bytes()).digest()!=before:raise ValueError('An input changed during evaluation.')
            cpu_by_pid={}
            for pid,rss,cpu in observed.samples:cpu_by_pid.setdefault(pid,[]).append(cpu)
            cpu=max((v[-1]-v[0] for v in cpu_by_pid.values() if len(v)>1),default=None)
            resources={'elapsedSeconds':elapsed,'peakRssBytes':worker.last_peak_rss_bytes,
                'modelInitSeconds':worker.last_metrics.get('modelInitSeconds'),
                'inferenceSeconds':worker.last_metrics.get('inferenceSeconds'),
                'rssAfterBytes':worker.last_metrics.get('rssAfterBytes'),
                'sampledCpuPercent':cpu/elapsed*100 if cpu is not None else None,
                'cgroup':cgroup_memory()}
            rows.append(_row(item,result,outcome,resources))
            if key and result is not None:save_json(Path(output)/(item['id']+'.result.fernet'),result,key)
            print(json.dumps({'id':item['id'],'outcome':outcome}),flush=True)
            result=data=None
    finally:worker.close()
    import importlib.metadata
    env={'os':platform.system(),'machine':platform.machine(),'python':platform.python_version(),
        'versions':{p:importlib.metadata.version(p) for p in ['paddleocr','paddlepaddle','paddlex','Pillow']},
        'configuration':asdict(OCRConfiguration()),'workerRssCapGiB':5,'samplingSeconds':.05,
        'availableBeforeNextRunGiB':round(available_memory_bytes()/1024**3,2),
        'containerExecution':Path('/.dockerenv').exists()}
    result=report(rows,'fresh_native_small_synthetic' if small else 'fresh_native',environment=env)
    result['workerClosed']=worker._process is None;result['rawEvidencePersisted']=bool(key)
    return result


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    init=sub.add_parser('init');init.add_argument('inputs',nargs='+',type=Path);init.add_argument('--authorized',action='store_true');init.add_argument('--provenance',choices=['real_private','anonymized_real','public_sample_form'],default='real_private');init.add_argument('--output',type=Path,required=True);init.add_argument('--key-file',type=Path)
    keygen=sub.add_parser('keygen');keygen.add_argument('--output',type=Path,required=True)
    for action in ['encrypt','decrypt']:
        command=sub.add_parser(action);command.add_argument('--input',type=Path,required=True);command.add_argument('--output',type=Path,required=True);command.add_argument('--key-file',type=Path,required=True)
    for action in ['run','replay']:
        command=sub.add_parser(action);command.add_argument('--manifest',type=Path,required=True);command.add_argument('--output',type=Path,required=True);command.add_argument('--legacy-known-facts',action='store_true');command.add_argument('--annotation-key-file',type=Path)
        command.add_argument('--key-file',type=Path)
        if action=='run':command.add_argument('--small-synthetic',action='store_true');command.add_argument('--model-root',type=Path);command.add_argument('--require-pilot-review',action='store_true')
        else:command.add_argument('--archive',type=Path,required=True)
    args=parser.parse_args();os.umask(0o077)
    if args.action=='init':initialize(args.inputs,args.output,provenance=args.provenance,authorized=args.authorized,key=args.key_file);print('Private unreviewed annotation dataset created; no facts were inferred.');return
    if args.action=='keygen':
        from cryptography.fernet import Fernet
        write_private(args.output,Fernet.generate_key()+b'\n');print('Private recovery key generated; keep it separate from results.');return
    if args.action in {'encrypt','decrypt'}:
        value=read_json(args.input,args.key_file if args.action=='decrypt' else None)
        save_json(args.output,value,args.key_file if args.action=='encrypt' else None)
        print('Private JSON artifact written without overwriting any existing file.');return
    output=private_path(args.output)
    if output.exists():raise FileExistsError('Use a new output directory; prior results are never overwritten.')
    output.mkdir(parents=True,mode=0o700)
    result=native(args.manifest,output,legacy=args.legacy_known_facts,small=args.small_synthetic,key=args.key_file,annotation_key=args.annotation_key_file,model_root=args.model_root,require_pilot_review=args.require_pilot_review) if args.action=='run' else replay(args.manifest,args.archive,legacy=args.legacy_known_facts,annotation_key=args.annotation_key_file,output=output,key=args.key_file)
    save_json(output/'metrics.json',result)
    print(json.dumps({'mode':result['mode'],'samples':len(result['rows']),'outcomes':dict(Counter(r['outcome'] for r in result['rows']))}))


if __name__=='__main__':
    try:main()
    except Exception:
        print('Evaluation failed. Inspect private inputs/configuration; no source text or exception details are published.',file=sys.stderr)
        raise SystemExit(1) from None
