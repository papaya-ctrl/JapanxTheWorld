"""Bounded stage ablation on the two authorized Step 12 synthetic fixtures only.

Oracle crops and label counterfactuals are diagnostics, never application output.
No recognition repair, alternate model, download or runtime rule is installed.
"""
import argparse
import base64
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import time

from .vault import save_json


def _coverage(box,truth):
    overlap=max(0,min(box[2],truth[2])-max(box[0],truth[0]))*max(0,min(box[3],truth[3])-max(box[1],truth[1]))
    return overlap/((truth[2]-truth[0])*(truth[3]-truth[1]))


def _target(connection,limits,model_root):
    with open(os.devnull,'w') as sink:os.dup2(sink.fileno(),1);os.dup2(sink.fileno(),2)
    from services.ocr.lease import exclusive_worker_lease
    from services.ocr.paddle_extractor import create_paddle_ocr
    from services.documentAnalysis.analyzer import analyze_ocr_document
    import numpy as np
    from PIL import Image
    try:
        with exclusive_worker_lease():
            model=None
            for _ in range(2):
                data,kind=connection.recv();payload=json.loads(data)
                if model is None:
                    start=time.perf_counter();model=create_paddle_ocr(model_root);init=time.perf_counter()-start
                else:init=0.
                with Image.open(BytesIO(base64.b64decode(payload['png']))) as image:
                    if image.format!='PNG' or image.size!=(640,640):raise ValueError()
                    with image.convert('RGB') as rgb:pixels=np.frombuffer(rgb.tobytes('raw','BGR'),dtype=np.uint8).reshape(640,640,3)
                start=time.perf_counter();raw=list(model.predict(pixels))[0];native=time.perf_counter()-start
                record={'page_index':0,'rec_texts':list(raw['rec_texts']),
                    'rec_scores':[float(s) for s in raw['rec_scores']],
                    'rec_boxes':[[float(v) for v in box] for box in raw['rec_boxes']]}
                analysis=analyze_ocr_document([record]);pipeline=model.paddlex_pipeline
                observations=[]
                for rect in payload['oracleRects']:
                    candidate=max(range(len(record['rec_boxes'])),key=lambda i:_coverage(record['rec_boxes'][i],rect))
                    detected=list(pipeline._crop_by_polys(pixels,[raw['rec_polys'][candidate]]))[0]
                    direct=list(pipeline.text_rec_model([detected],return_word_box=False))[0]
                    x1,y1,x2,y2=[int(v) for v in rect]
                    oracle=pixels[max(0,y1-6):min(640,y2+6),max(0,x1-6):min(640,x2+6)].copy()
                    oracle_result=list(pipeline.text_rec_model([oracle],return_word_box=False))[0]
                    observations.append({'detectedText':record['rec_texts'][candidate],
                        'detectedConfidence':record['rec_scores'][candidate],
                        'sourceInkCoverage':_coverage(record['rec_boxes'][candidate],rect),
                        'directDetectedCropText':str(direct['rec_text']),
                        'directDetectedCropConfidence':float(direct['rec_score']),
                        'oracleCropText':str(oracle_result['rec_text']),
                        'oracleCropConfidence':float(oracle_result['rec_score'])})
                corrected=deepcopy(record)
                # The only counterfactual changes the known generated label;
                # date/amount digits and all geometry/confidence stay untouched.
                corrected['rec_texts']=[text.replace('納付额','納付額') for text in corrected['rec_texts']]
                counterfactual=analyze_ocr_document([corrected])
                result={'modelInitSeconds':init,'fullImageInferenceSeconds':native,
                    'observations':observations,'rawRecords':record,
                    'originalPrimaryAmount':analysis['primaryAmount'],
                    'originalAmountKinds':[a['kind'] for a in analysis['amounts']],
                    'originalAmountStatuses':[a['status'] for a in analysis['amounts']],
                    'counterfactualPrimaryAmount':counterfactual['primaryAmount'],
                    'counterfactualAmountKinds':[a['kind'] for a in counterfactual['amounts']],
                    'counterfactualAmountStatuses':[a['status'] for a in counterfactual['amounts']]}
                connection.send(('ok',result))
    except Exception:
        try:connection.send(('error','DOCUMENT_UNREADABLE'))
        except (OSError,EOFError):pass
    finally:connection.close()


def run(manifest,output,key):
    from .accuracy import documents
    from services.ocr.resources import available_memory_bytes
    from services.ocr.worker import LocalDocumentWorker
    from services.ocr.limits import DocumentLimits
    from PIL import ImageDraw,ImageFont,Image
    if available_memory_bytes()<3*1024**3:raise RuntimeError('Insufficient synthetic-only headroom.')
    samples={d['id']:d for d in documents(manifest)}
    selected=[samples[identifier] for identifier in ['S101','S111']]
    if any(d['provenance']!='synthetic' for d in selected):raise ValueError('Only generated synthetic fixtures are accepted.')
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',27)
    with Image.new('RGB',(640,640)) as canvas:
        draw=ImageDraw.Draw(canvas);rects=[list(draw.textbbox((24,y),'納付額 5,000円',font=font)) for y in [355,450]]
    worker=LocalDocumentWorker(DocumentLimits(min_host_available_bytes=768*1024**2),target=_target)
    results=[]
    try:
        for item in selected:
            payload={'png':base64.b64encode(Path(item['path']).read_bytes()).decode(),'oracleRects':rects}
            result=worker.analyze(json.dumps(payload).encode(),'png')
            result.update(id=item['id'],sampledPeakRssMiB=worker.last_peak_rss_bytes/1024**2)
            results.append(result)
    finally:worker.close()
    result={'mode':'synthetic_stage_ablation','results':results,'workerClosed':worker._process is None,
        'productionCorrectionEnabled':False,'recognitionModelChanged':False}
    save_json(output,result,key)
    return result


if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);parser.add_argument('--output',required=True);parser.add_argument('--key-file',required=True);args=parser.parse_args()
    try:
        report=run(args.manifest,args.output,args.key_file)
        print(json.dumps({'syntheticSamples':len(report['results']),'workerClosed':report['workerClosed']}))
    except Exception:
        print('Synthetic stage probe failed safely; private input and exception details are suppressed.')
        raise SystemExit(1) from None
