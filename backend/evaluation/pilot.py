"""Step 13 human-review eligibility and group-separated pilot inventory.

This reuses the Step 12 contract. It never annotates from predictions or infers
that a synthetic fixture/public sample form was an actual issued document.
"""
import argparse
import os
from .schema import Dataset,CATEGORIES,dataset_group
from .vault import read_json,save_json

REQUIRED_FIELDS={'documentType','deadlines','amounts','primaryDeadline','primaryAmount',
                 'extractionStatus','missingFields','uncertainFields','englishInterpretation','pilotReview'}
REVIEW_FLAGS={'independentOfPrediction','categoryReviewed','deadlinesAndMeaningsReviewed',
              'amountsAndLabelsReviewed','paidAndUnpaidReviewed','multipleDatesAndAmountsReviewed',
              'missingAndAmbiguousReviewed','japaneseEvidenceReviewed','englishInterpretationReviewed'}


def review_gaps(item):
    gaps=[];truth=item['groundTruth'];verification=truth.get('verification',{})
    if item['provenance']=='synthetic':gaps.append('synthetic_not_real_pilot')
    if not item.get('authorizationConfirmed'):gaps.append('authorization_not_confirmed')
    if item['category'] is None:gaps.append('category_unreviewed')
    if not truth.get('complete') or verification.get('status')!='verified' or verification.get('method')!='independent_human':gaps.append('complete_independent_human_truth_missing')
    if not REQUIRED_FIELDS<=truth.keys():gaps.append('required_review_fields_missing')
    if not truth.get('englishInterpretation'):gaps.append('english_interpretation_missing')
    review=truth.get('pilotReview') or {}
    if any(review.get(flag) is not True for flag in REVIEW_FLAGS):gaps.append('human_review_checklist_incomplete')
    if not review.get('reviewerId') or review.get('reviewerId')!=verification.get('reviewerId'):gaps.append('reviewer_binding_missing')
    return gaps


def inventory(dataset):
    rows=[]
    for document in dataset.documents:
        item=document.model_dump(exclude_unset=True)
        gaps=review_gaps(item)
        rows.append({'id':document.id,'datasetGroup':dataset_group(document.provenance),
            'category':document.category or 'unassigned','pilotEligible':not gaps,'reviewGaps':gaps})
    groups={}
    for name in ['issued_documents','public_sample_forms','synthetic_fixtures']:
        selected=[r for r in rows if r['datasetGroup']==name]
        groups[name]={'samples':len(selected),'pilotEligible':sum(r['pilotEligible'] for r in selected),
            'categoryCoverage':{c:sum(r['category']==c for r in selected) for c in sorted(CATEGORIES|{'unassigned'})}}
    return {'targetIssuedDocuments':40,'groups':groups,'samples':rows,
        'realAccuracyEstablished':False,'publicProductionReady':False,
        'policy':'review_independently_before_ocr_keep_public_forms_separate_from_issued_documents'}


if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);parser.add_argument('--annotation-key-file');parser.add_argument('--output',required=True);args=parser.parse_args()
    try:
        dataset=Dataset.model_validate(read_json(args.manifest,args.annotation_key_file))
        result=inventory(dataset);save_json(args.output,result)
        print('Pilot review inventory recorded; unavailable human review was not inferred.')
    except Exception:
        print('Pilot inventory failed validation; private inputs and errors are suppressed.')
        raise SystemExit(1) from None
