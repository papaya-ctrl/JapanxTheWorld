"""End-to-end accuracy with explicit denominators and failures retained."""
from collections import Counter
from math import ceil
import statistics
from .metrics import normalized_text, score_result

EMPTY={'deadlines':[],'amounts':[],'evidence':[],'documentType':None,
       'primaryDeadline':None,'primaryAmount':None,'extractionStatus':None}


def ratio(numerator,denominator):
    return {'numerator':numerator,'denominator':denominator,
            'value':numerator/denominator if denominator else None}


def _page_and_evidence(prediction,expected,result):
    evidence=expected.get('evidence')
    if not evidence:return None
    sources=[e for e in result.get('evidence',[]) if e['id'] in prediction.get('evidenceIds',[])]
    return all(normalized_text(item['text']) in normalized_text(''.join(e['text'] for e in sources if e['page']==item['page'])) for item in evidence)


def score_document(result,truth,*,outcome='ok'):
    reviewed=truth.get('verification',{}).get('status')!='unreviewed'
    if not reviewed or outcome.startswith('NOT_EXECUTED'):
        return {'scorable':False,'annotationReviewed':reviewed,'processingSucceeded':outcome=='ok' and result is not None,
            'pendingKnownDeadlines':len(truth.get('deadlines',[])), 'pendingKnownAmounts':len(truth.get('amounts',[]))}
    delivered=outcome=='ok' and result is not None
    result=result if delivered else EMPTY
    score=score_result(result,truth)
    score.update(scorable=True,annotationReviewed=True,complete=truth.get('complete',False),processingSucceeded=delivered)
    for field,key in [('deadlines','date'),('amounts','value')]:
        metric=score[field]
        if not delivered and metric['exact'] is not None:metric['exact']=False
        verified=[p for p in result[field] if p['status']=='verified']
        labeled=[e for e in truth.get(field,[]) if 'label' in e]
        metric['labelExpected']=len(labeled)
        metric['labelCorrect']=sum(any(p['kind']==e['kind'] and p[key]==e[key] and p['label']==e['label'] and _page_and_evidence(p,e,result) is not False for p in verified) for e in labeled)
        evidenced=[e for e in truth.get(field,[]) if e.get('evidence')]
        metric['evidenceExpected']=len(evidenced)
        metric['evidenceCorrect']=sum(any(p['kind']==e['kind'] and p[key]==e[key] and _page_and_evidence(p,e,result) is True for p in verified) for e in evidenced)
        metric['duplicateVerifiedEntries']=len(verified)-len({(p['kind'],p[key]) for p in verified})
    for key in ('documentType','primaryDeadline','primaryAmount','extractionStatus'):
        if key in truth and (key!='extractionStatus' or truth[key] is not None):
            score[key+'Correct']=delivered and result[key]==truth[key]
    checks=[]
    for check in truth.get('uncertainFields',[]):
        field=check['field'];key='date' if field=='deadlines' else 'value'
        value=check.get(key)
        candidates=[p for p in result[field] if p['kind']==check['kind'] and (value is None or p[key]==value)]
        safe=any(p['status']=='unverified' and _page_and_evidence(p,check,result) is not False for p in candidates)
        safe=safe and not any(p['status']=='verified' for p in candidates)
        if check.get('mustNotBePrimary',True):safe=safe and result['primaryDeadline' if field=='deadlines' else 'primaryAmount'] is None
        checks.append(delivered and safe)
    score['uncertainty']={'correct':sum(checks),'scored':len(checks)}
    missing=[delivered and (result[key]==[] if key in {'deadlines','amounts'} else result[key] is None) for key in truth.get('missingFields',[])]
    score['missingFields']={'correct':sum(missing),'scored':len(missing)}
    era=[]
    evidence={e['id']:e for e in result.get('evidence',[])}
    for check in truth.get('eraChecks',[]):
        candidates=[p for p in result['deadlines'] if p['kind']==check['kind'] and any(evidence[i]['page']==check['page'] for i in p.get('evidenceIds',[]) if i in evidence)]
        literal=normalized_text(check['literal'])
        candidates=[p for p in candidates if literal in normalized_text(''.join(evidence[i]['text'] for i in p.get('evidenceIds',[]) if i in evidence and evidence[i]['page']==check['page']))]
        if check['expectedDate'] is None:
            correct=bool(candidates) and all(p['status']=='unverified' for p in candidates)
        else:correct=any(p['date']==check['expectedDate'] and p['status']=='verified' for p in candidates)
        era.append(delivered and correct)
    score['eraConversion']={'correct':sum(era),'scored':len(era)}
    repeats=[]
    for check in truth.get('repeatedAmounts',[]):
        candidates=[p for p in result['amounts'] if p['kind']==check['kind'] and p['value']==check['value'] and p['status']=='verified']
        repeats.append(delivered and len(candidates)==1 and candidates[0].get('occurrences')==check['occurrences'])
    score['deduplication']={'correct':sum(repeats),'scored':len(repeats)}
    return score


def summarize_quality(rows):
    scored=[r['accuracy'] for r in rows if r['accuracy'].get('scorable')]
    complete=[s for s in scored if s['complete']]
    partial=[s for s in scored if not s['complete']]
    result={'samples':len(rows),'successful':sum(r['outcome']=='ok' for r in rows),
        'failedOrNotExecuted':sum(r['outcome']!='ok' for r in rows),'scorableSamples':len(scored),
        'completeAnnotations':len(complete),'partialAnnotations':len(partial),
        'unreviewedAnnotations':sum(not r['accuracy'].get('annotationReviewed',True) for r in rows),
        'notExecuted':sum(r['outcome'].startswith('NOT_EXECUTED') for r in rows),
        'pendingKnownDeadlines':sum(r['accuracy'].get('pendingKnownDeadlines',0) for r in rows),
        'pendingKnownAmounts':sum(r['accuracy'].get('pendingKnownAmounts',0) for r in rows),
        'outcomes':dict(Counter(r['outcome'] for r in rows))}
    for field in ('deadlines','amounts'):
        metrics=[s[field] for s in complete];known=[s[field] for s in scored]
        tp=sum(m['matched'] for m in metrics);fp=sum(m['falsePositive'] for m in metrics);fn=sum(m['missed'] for m in metrics)
        result[field]={'truePositive':tp,'falsePositive':fp if metrics else None,'falseNegative':fn,
            'precision':ratio(tp,tp+fp),'recall':ratio(tp,tp+fn),
            'exactMatch':ratio(sum(m['exact'] is True for m in metrics),len(metrics)),
            'falsePositiveDocumentRate':ratio(sum(m['falsePositive']>0 for m in metrics),len(metrics)),
            'knownFieldRecall':ratio(sum(m['matched'] for m in known),sum(m['expected'] for m in known)),
            'knownFalseNegatives':sum(m['missed'] for m in known),
            'labelAssociation':ratio(sum(m['labelCorrect'] for m in known),sum(m['labelExpected'] for m in known)),
            'supportingEvidence':ratio(sum(m['evidenceCorrect'] for m in known),sum(m['evidenceExpected'] for m in known)),
            'unverifiedPredictions':sum(m['unverified'] for m in known),
            'duplicateVerifiedEntries':sum(m['duplicateVerifiedEntries'] for m in known)}
    for name in ('documentType','primaryDeadline','primaryAmount','extractionStatus'):
        values=[s[name+'Correct'] for s in scored if s.get(name+'Correct') is not None]
        result[name]=ratio(sum(values),len(values))
    for name in ('uncertainty','missingFields','eraConversion','deduplication'):
        result[name]=ratio(sum(s[name]['correct'] for s in scored),sum(s[name]['scored'] for s in scored))
    transcribed=[s for s in scored if s.get('characterEdits') is not None]
    result['transcriptionSamples']=len(transcribed)
    result['characterErrorRate']=ratio(sum(s['characterEdits'] for s in transcribed),sum(s['characters'] for s in transcribed))
    samples=[r.get('resources',{}) for r in rows]
    latency=[s['elapsedSeconds'] for s in samples if s.get('elapsedSeconds') is not None]
    peaks=[s['peakRssBytes']/1024**2 for s in samples if s.get('peakRssBytes') is not None]
    result['resources']={'latencySamples':len(latency),'medianSeconds':statistics.median(latency) if latency else None,
        'p95Seconds':sorted(latency)[ceil(.95*len(latency))-1] if latency else None,
        'maximumSeconds':max(latency) if latency else None,'rssSamples':len(peaks),'peakRssMiB':max(peaks) if peaks else None}
    for name,key,predicate in [('warmLatency','elapsedSeconds',lambda s:s.get('modelInitSeconds')==0),
                               ('initialization','modelInitSeconds',lambda s:s.get('modelInitSeconds') is not None and s['modelInitSeconds']>0),
                               ('sampledCpu','sampledCpuPercent',lambda s:s.get('sampledCpuPercent') is not None)]:
        values=[s[key] for s in samples if predicate(s)]
        result['resources'][name]={'samples':len(values),'median':statistics.median(values) if values else None,'maximum':max(values) if values else None}
    result['limitations']=['convenience_sample_not_population_accuracy','variants_are_not_independent_samples',
        'partial_ground_truth_excluded_from_precision_and_exact_denominators',
        'processing_failures_remain_in_complete_accuracy_denominators',
        'character_edit_error_includes_reading_order_and_is_not_an_automatic_root_cause_label',
        'false_positive_rate_means_documents_with_any_false_verified_field_per_complete_document',
        'unverified_candidates_are_retained_and_do_not_count_as_verified_positives']
    return result
