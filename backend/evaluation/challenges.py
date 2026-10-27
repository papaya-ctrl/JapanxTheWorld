"""Independent synthetic specifications for layout/interpretation stress cases.

These are controlled OCR inputs, not real documents or native OCR measurements.
"""
from services.documentAnalysis.analyzer import analyze_ocr_document


def _truth(*,deadlines=(),amounts=(),primary_date=None,primary_amount=None,status='verified',document_type=None,**extra):
    return {'complete':True,'documentType':document_type,
        'deadlines':[{'kind':k,'date':d,'label':l} for k,d,l in deadlines],
        'amounts':[{'kind':k,'value':v,'label':l} for k,v,l in amounts],
        'primaryDeadline':primary_date,'primaryAmount':primary_amount,'extractionStatus':status,**extra}


def cases():
    payment=('payment','2031-06-30','Payment deadline')
    amount=('payment',5000,'Payment amount')
    specs=[
        ('illustrative_deadline',[('記入例 納期限 2031年6月30日',0,0,450,25)],_truth(status='unverified',uncertainFields=[{'field':'deadlines','kind':'payment','date':'2031-06-30','reason':'illustrative'}])),
        ('illustrative_amount',[('見本 納付額 5,000円',0,0,350,25)],_truth(status='unverified',uncertainFields=[{'field':'amounts','kind':'payment','value':5000,'reason':'illustrative'}])),
        ('illustrative_type',[('記入例 国民健康保険税 納付書',0,0,450,25)],_truth(status='no_fields')),
        ('illustrative_paid_stamp',[('納付額 5,000円',0,0,280,25),('見本 納付済',0,100,250,125)],_truth(amounts=[amount],primary_amount=5000)),
        ('kanji_era',[('納期限 令和十三年六月三十日',0,0,450,25)],_truth(deadlines=[payment],primary_date='2031-06-30',eraChecks=[{'literal':'令和十三年六月三十日','expectedDate':'2031-06-30','kind':'payment','page':1}])),
        ('split_date',[('納期限',0,0,70,25),('令和',90,0,140,25),('13年',145,0,195,25),('6月',200,0,240,25),('30日',245,0,300,25)],_truth(deadlines=[payment],primary_date='2031-06-30',eraChecks=[{'literal':'令和13年6月30日','expectedDate':'2031-06-30','kind':'payment','page':1}])),
        ('separate_expiration',[('納期限 2031年6月30日',0,0,420,25),('利用期限 2032年6月30日',0,100,420,125)],_truth(deadlines=[payment,('usage_expiration','2032-06-30','Usage expiration date')],primary_date='2031-06-30')),
        ('multiple_deadlines',[('納期限 2031年6月30日',0,0,420,25),('提出期限 2031年7月10日',0,100,420,125)],_truth(deadlines=[payment,('submission','2031-07-10','Submission deadline')])),
        ('payment_late_paid',[('納付額 5,000円',0,0,300,25),('延滞金 300円',0,90,300,115),('支払済金額 1,000円',0,180,350,205)],_truth(amounts=[amount,('late_fee',300,'Late fee'),('paid',1000,'Already-paid amount')],primary_amount=5000)),
        ('repeated_sections',[('納付額 5,000円',0,y,300,y+25) for y in (0,100,200)],_truth(amounts=[amount],primary_amount=5000,repeatedAmounts=[{'kind':'payment','value':5000,'occurrences':3}])),
        ('low_confidence',[('納付額 5,000円',0,0,300,25,.4)],_truth(amounts=[amount],status='unverified',uncertainFields=[{'field':'amounts','kind':'payment','value':5000,'reason':'low_confidence_input'}])),
        ('partial_result',[('納付額 5,000円',0,0,300,25),('合計金額 不明',0,100,300,125)],_truth(amounts=[amount],status='partial',uncertainFields=[{'field':'amounts','kind':'total','reason':'source_unreadable'}])),
        ('similar_character_date',[('納期限 令和B年6月30日',0,0,420,25)],_truth(status='unverified',uncertainFields=[{'field':'deadlines','kind':'payment','reason':'invalid_literal'}])),
        ('blurry_unreadable',[('納期限 不明',0,0,300,25,.3),('納付額 不明',0,100,300,125,.3)],_truth(status='unverified',uncertainFields=[{'field':'deadlines','kind':'payment','reason':'source_unreadable'},{'field':'amounts','kind':'payment','reason':'source_unreadable'}])),
        ('table_columns',[('納付額',0,0,100,25),('延滞金',300,0,400,25),('5,000円',0,35,110,60),('300円',300,35,400,60)],_truth(amounts=[amount,('late_fee',300,'Late fee')],primary_amount=5000)),
        ('vertical_date',[('納期限',400,0,425,90),('令和13年6月30日',400,110,425,420)],_truth(deadlines=[payment],primary_date='2031-06-30')),
        ('already_paid',[('納付額 5,000円',0,0,300,25),('納付済',0,100,100,125)],_truth(amounts=[amount])),
        ('era_boundary',[('納期限 平成31年5月1日',0,0,420,25)],_truth(status='unverified',eraChecks=[{'literal':'平成31年5月1日','expectedDate':None,'kind':'payment','page':1}],uncertainFields=[{'field':'deadlines','kind':'payment','reason':'invalid_literal'}])),
        ('unknown_missing',[('お知らせ 資料',0,0,300,25)],_truth(status='no_fields',missingFields=['deadlines','amounts','documentType','primaryDeadline','primaryAmount'])),
        ('same_amount_different_roles',[('納付額 5,000円',0,0,300,25),('支払済金額 5,000円',0,100,350,125)],_truth(amounts=[amount,('paid',5000,'Already-paid amount')],primary_amount=5000)),
    ]
    return [{'id':f'S{index+201:03d}','category':'unknown','provenance':'synthetic','variant':name,'items':items,'groundTruth':truth} for index,(name,items,truth) in enumerate(specs)]


def analyze_case(case):
    items=case['items']
    return analyze_ocr_document([{'page_index':0,'rec_texts':[i[0] for i in items],
        'rec_boxes':[list(i[1:5]) for i in items],'rec_scores':[i[5] if len(i)>5 else .99 for i in items]}])


if __name__=='__main__':
    import argparse
    from .accuracy import _row,report
    from .vault import save_json
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    rows=[_row(case,analyze_case(case),'ok') for case in cases()]
    save_json(args.output,report(rows,'controlled_ocr'))
    print('Measured twenty controlled synthetic OCR cases; numeric results saved privately.')
