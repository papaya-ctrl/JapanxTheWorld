"""Explicit error-stage review for encrypted Step 12 predictions; no inferred causes."""
import argparse
import re
from .review import digest,STAGES,CATEGORIES
from .vault import read_json,save_json,private_path


def template(metrics,predictions,key):
    reviews=[]
    for row in metrics['rows']:
        if row['outcome']!='ok':continue
        if not re.fullmatch(r'[RS]\d{3}',row['id']):raise ValueError('Use anonymous sample IDs.')
        prediction=read_json(private_path(predictions)/(row['id']+'.result.fernet'),key)
        reviews.append({'id':row['id'],'predictionSha256':digest(prediction),
            'groundTruthSha256':row['groundTruthSha256'],'reviewed':False,'reviewerKind':None,'errors':[]})
    return {'schemaVersion':2,'reviews':reviews}


def apply(metrics,predictions,key,reviews):
    from copy import deepcopy
    if reviews.get('schemaVersion')!=2:raise ValueError('Expected version 2 reviews.')
    result=deepcopy(metrics);rows={row['id']:row for row in result['rows']};seen=set()
    for review in reviews['reviews']:
        identifier=review['id']
        if not isinstance(identifier,str) or not re.fullmatch(r'[RS]\d{3}',identifier) or identifier in seen or identifier not in rows:raise ValueError('Invalid or duplicated sample identity.')
        seen.add(identifier);row=rows[identifier]
        prediction=read_json(private_path(predictions)/(identifier+'.result.fernet'),key)
        if review['predictionSha256']!=digest(prediction) or review['groundTruthSha256']!=row['groundTruthSha256']:raise ValueError('Prediction or ground truth changed; repeat the review.')
        if type(review.get('reviewed')) is not bool or not isinstance(review.get('errors'),list):raise ValueError('Explicit review status/errors are required.')
        kind=review.get('reviewerKind')
        if review['reviewed']:
            if kind not in {'independent_human','controlled_synthetic_investigation'}:raise ValueError('Declare review provenance.')
            if row['provenance']!='synthetic' and kind!='independent_human':raise ValueError('Real error causes require independent human review.')
        elif review['errors'] or kind is not None:raise ValueError('Unreviewed entries cannot assert causes.')
        counts={stage:0 for stage in STAGES}
        for error in review['errors']:
            if not isinstance(error,dict) or set(error)!={'stage','category'} or type(error['stage']) is not str or type(error['category']) is not str or error['stage'] not in STAGES or error['category'] not in CATEGORIES:raise ValueError('Only allowlisted stages/categories; never copy sensitive notes.')
            counts[error['stage']]+=1
        row['manualErrorReview']={'reviewed':review['reviewed'],'counts':counts if review['reviewed'] else None}
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['template','apply']);parser.add_argument('--metrics',required=True);parser.add_argument('--predictions',required=True);parser.add_argument('--key-file',required=True);parser.add_argument('--reviews');parser.add_argument('--output',required=True);args=parser.parse_args()
    metrics=read_json(args.metrics)
    result=template(metrics,args.predictions,args.key_file) if args.action=='template' else apply(metrics,args.predictions,args.key_file,read_json(args.reviews))
    save_json(args.output,result);print('Private review artifact written; unreviewed error stages remain unscored.')


if __name__=='__main__':
    try:main()
    except Exception:
        print('Review failed validation; private text and exception details are suppressed.')
        raise SystemExit(1) from None
