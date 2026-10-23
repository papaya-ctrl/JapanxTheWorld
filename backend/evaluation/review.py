"""Manual, prediction-bound error review. Never infer root cause from a missed field."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
import re
from pathlib import Path

STAGES={'ocr_recognition','field_extraction','interpretation','unresolved'}
CATEGORIES={'missing_text','wrong_characters','split_or_order','wrong_date','wrong_amount',
            'wrong_label_association','false_deadline','false_amount','document_type',
            'primary_selection','uncertainty_status','unsupported_instruction','needs_investigation'}


def row_key(profile,identifier,repeat):
    from .profiles import PROFILES
    if type(profile) is not str or profile not in PROFILES or type(identifier) is not str or not re.fullmatch(r'[A-Z]\d{3}',identifier) or type(repeat) is not int or not 0<=repeat<=4:
        raise ValueError('Use known profile names, anonymized IDs and bounded repeats.')
    return profile,identifier,repeat


def digest(prediction):
    return hashlib.sha256(json.dumps(prediction,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def private_path(path):
    path=Path(path).expanduser().resolve()
    if path.is_relative_to(Path(__file__).resolve().parents[2]):raise ValueError('Keep manual reviews and predictions outside the checkout.')
    return path


def template(metrics,predictions):
    reviews=[]
    for profile,data in metrics['profiles'].items():
        for row in data['rows']:
            if row['resources']['outcome']!='ok':continue
            row_key(profile,row['documentId'],row['repeat'])
            name=f"{profile}-{row['documentId']}-{row['repeat']}-private.json"
            path=private_path(predictions)/name
            prediction=json.loads(path.read_text())
            reviews.append({'profile':profile,'documentId':row['documentId'],'repeat':row['repeat'],
                'predictionSha256':digest(prediction),'reviewed':False,'errors':[]})
    return {'schemaVersion':1,'reviews':reviews}


def apply_reviews(metrics,predictions,reviews):
    if reviews.get('schemaVersion')!=1 or not isinstance(reviews.get('reviews'),list):raise ValueError('Unsupported review schema.')
    result=deepcopy(metrics);lookup={}
    for profile,data in result['profiles'].items():
        for row in data['rows']:lookup[row_key(profile,row['documentId'],row['repeat'])]=row
    seen=set()
    for review in reviews['reviews']:
        key=row_key(review['profile'],review['documentId'],review['repeat'])
        if key in seen or key not in lookup:raise ValueError('Review identity is duplicated or not in this run.')
        seen.add(key);row=lookup[key]
        if row['resources']['outcome']!='ok':raise ValueError('Field-stage review requires a successful saved prediction.')
        expected=private_path(predictions)/f'{key[0]}-{key[1]}-{key[2]}-private.json'
        prediction=json.loads(expected.read_text())
        if digest(prediction)!=review.get('predictionSha256'):raise ValueError('Prediction changed; review must be repeated.')
        if type(review.get('reviewed')) is not bool:raise ValueError('Explicitly mark each manual review as true/false.')
        if not isinstance(review.get('errors'),list):raise ValueError('Use an explicit error list.')
        counts={stage:0 for stage in STAGES}
        for error in review['errors']:
            if not isinstance(error,dict) or set(error)!={'stage','category'} or type(error['stage']) is not str or type(error['category']) is not str or error['stage'] not in STAGES or error['category'] not in CATEGORIES:
                raise ValueError('Only allowlisted manual stages/categories are accepted; no free-text notes.')
            counts[error['stage']]+=1
        if not review['reviewed'] and review['errors']:raise ValueError('Unreviewed entries cannot assert a cause.')
        row['manualErrorReview']={'reviewed':review['reviewed'],'counts':counts if review['reviewed'] else None}
    # Unreviewed rows stay unscored, never implied to have zero errors.
    return result


def summary(rows):
    reviewed=[r['manualErrorReview'] for r in rows if r.get('manualErrorReview',{}).get('reviewed') is True]
    return {'reviewedRequests':len(reviewed),**{stage:sum(r['counts'][stage] for r in reviewed) if reviewed else None for stage in sorted(STAGES)}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['template','apply']);parser.add_argument('--metrics',type=Path,required=True);parser.add_argument('--predictions',type=Path,required=True);parser.add_argument('--reviews',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    metrics=json.loads(private_path(args.metrics).read_text())
    result=template(metrics,args.predictions) if args.action=='template' else apply_reviews(metrics,args.predictions,json.loads(private_path(args.reviews).read_text()))
    output=private_path(args.output);output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as file:json.dump(result,file,ensure_ascii=False,indent=2);file.write('\n')
    output.chmod(0o600)
    print('Private review artifact created. Only reviewed allowlisted stage counts may be published.')


if __name__=='__main__':main()
