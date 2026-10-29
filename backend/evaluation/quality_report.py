"""Publish only allowlisted anonymous IDs, numeric counters and fixed categories."""
import argparse
import json
from math import isfinite
from pathlib import Path
import re
from .quality import summarize_quality
from .review import summary as review_summary,STAGES
from .schema import CATEGORIES,PROVENANCES,dataset_group
from .vault import read_json

MODES={'fresh_native','fresh_native_small_synthetic','frozen_step9_ocr_current_engine_replay','controlled_ocr'}
OUTCOMES={'ok','DOCUMENT_UNREADABLE','INVALID_DOCUMENT','DOCUMENT_LIMIT_EXCEEDED','ANALYSIS_TIMEOUT',
    'ANALYSIS_MEMORY_LIMIT','ANALYSIS_BUSY','OCR_UNAVAILABLE','HOST_SWAP_GUARD','ARCHIVE_RESULT_MISSING',
    'NOT_EXECUTED_START_MEMORY_GUARD','NOT_EXECUTED_AFTER_HOST_GUARD','NOT_EXECUTED_AFTER_MEMORY_GUARD'}
COUNTERS={'expected','verified','matched','missed','falsePositive','unscoredPredictions','exact','knownFieldsRecovered',
    'labelMatches','labelScored','unverified','labelExpected','labelCorrect','evidenceExpected','evidenceCorrect','duplicateVerifiedEntries'}
SCALARS={'scorable','annotationReviewed','complete','processingSucceeded','pendingKnownDeadlines','pendingKnownAmounts',
    'documentTypeCorrect','primaryDeadlineCorrect','primaryAmountCorrect','extractionStatusCorrect','characterEdits','characters'}
CHECKS={'uncertainty','missingFields','eraConversion','deduplication'}
RESOURCES={'elapsedSeconds','peakRssBytes','modelInitSeconds','inferenceSeconds','rssAfterBytes','sampledCpuPercent'}


def numeric(value):
    if value is not None and (type(value) not in {int,float,bool} or not isfinite(value) or value<0):raise ValueError('Only finite nonnegative numeric counters are publishable.')
    return value


def public_report(metrics):
    mode=metrics['mode']
    if mode not in MODES:raise ValueError('Unrecognized execution mode.')
    rows=[];seen=set()
    for row in metrics['rows']:
        identifier=row['id'];category=row['category'];provenance=row['provenance'];outcome=row['outcome']
        if not isinstance(identifier,str) or not re.fullmatch(r'[RSP]\d{3}',identifier) or identifier in seen:raise ValueError('Use distinct anonymous sample IDs.')
        seen.add(identifier)
        if category not in CATEGORIES|{'unassigned'} or provenance not in PROVENANCES or outcome not in OUTCOMES:raise ValueError('Unrecognized public metadata.')
        prefix='S' if provenance=='synthetic' else 'P' if provenance=='public_sample_form' else 'R'
        if not identifier.startswith(prefix):raise ValueError('Sample ID and dataset group disagree.')
        original=row['accuracy'];accuracy={k:numeric(original[k]) for k in SCALARS if k in original}
        for field in ['deadlines','amounts']:
            if field in original:accuracy[field]={k:numeric(original[field][k]) for k in COUNTERS if k in original[field]}
        for field in CHECKS:
            if field in original:accuracy[field]={k:numeric(original[field][k]) for k in ['correct','scored']}
        cleaned={'id':identifier,'category':category,'provenance':provenance,'outcome':outcome,'accuracy':accuracy,
            'resources':{k:numeric(row['resources'][k]) for k in RESOURCES if k in row.get('resources',{})}}
        review=row.get('manualErrorReview')
        if review:
            if type(review['reviewed']) is not bool:raise ValueError('Invalid review status.')
            cleaned['manualErrorReview']={'reviewed':review['reviewed'],'counts':{stage:numeric(review['counts'][stage]) for stage in STAGES} if review['reviewed'] else None}
        rows.append(cleaned)
    groups={}
    for provenance in PROVENANCES:
        selected=[r for r in rows if r['provenance']==provenance]
        if selected:groups[provenance]={'summary':summarize_quality(selected),'errorStages':review_summary(selected),
            'categoryCoverage':{category:sum(r['category']==category for r in selected) for category in sorted(CATEGORIES|{'unassigned'})}}
    public_rows=[]
    for row in rows:
        accuracy=row['accuracy']
        item={k:row[k] for k in ['id','category','provenance','outcome']}
        for field in ['deadlines','amounts']:
            metric=accuracy.get(field)
            if metric:item[field]={k:metric[k] for k in ['matched','missed','falsePositive','unverified','exact']}
        item['resultChecks']={k:accuracy[k] for k in ['documentTypeCorrect','primaryDeadlineCorrect','primaryAmountCorrect','extractionStatusCorrect'] if k in accuracy}
        item['resources']={k:v for k,v in row['resources'].items() if k in {'elapsedSeconds','peakRssBytes'}}
        public_rows.append(item)
    return {'schemaVersion':2,'mode':mode,'groups':groups,'rows':public_rows,
        'datasetGroupCounts':{group:sum(dataset_group(r['provenance'])==group for r in rows) for group in ['issued_documents','public_sample_forms','synthetic_fixtures']},
        'timingOrigin':'historical_ocr' if mode.startswith('frozen') else 'no_native_ocr' if mode=='controlled_ocr' else 'fresh_native',
        'publicProductionReady':False}


def publish(inputs,output):
    reports=[public_report(read_json(path)) for path in inputs]
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as file:json.dump({'schemaVersion':2,'runs':reports},file,indent=2,allow_nan=False);file.write('\n')
    return reports


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('inputs',nargs='+');parser.add_argument('--output',required=True);args=parser.parse_args()
    try:publish(args.inputs,args.output);print('Published allowlisted numeric accuracy reports; no document facts copied.')
    except Exception:
        print('Publication failed validation; no private exception details are printed.')
        raise SystemExit(1) from None
