"""Small, explicitly synthetic image corpus with independent source specifications."""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
from .schema import Dataset
from .vault import private_path,save_json


def make_dataset(directory,font=None):
    from PIL import Image,ImageDraw,ImageFont,ImageFilter
    directory=private_path(directory)
    if directory.exists():raise FileExistsError('Use a new synthetic dataset directory.')
    directory.mkdir(parents=True,mode=0o700)
    candidates=[font,'/System/Library/Fonts/Supplemental/Arial Unicode.ttf','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    path=next((Path(p) for p in candidates if p and Path(p).is_file()),None)
    if not path:raise ValueError('Supply an installed Japanese-capable font.')
    regular=ImageFont.truetype(str(path),27);vertical=ImageFont.truetype(str(path),24)
    def ev(text):return [{'text':text,'page':1}]
    def deadline(kind,value,label,text):return {'kind':kind,'date':value,'label':label,'evidence':ev(text)}
    def amount(kind,value,label,text):return {'kind':kind,'value':value,'label':label,'evidence':ev(text)}
    payment=deadline('payment','2031-06-30','Payment deadline','納期限 令和13年6月30日')
    money=amount('payment',5000,'Payment amount','納付額 5,000円')
    def truth(dtype,dates=(),amounts=(),primary_date=None,primary_amount=None,status='verified',**extra):
        return {'verification':{'status':'verified','method':'synthetic_specification'},'complete':True,
            'documentType':dtype,'deadlines':list(dates),'amounts':list(amounts),
            'primaryDeadline':primary_date,'primaryAmount':primary_amount,'extractionStatus':status,**extra}
    health=truth('National Health Insurance Tax',[payment,deadline('usage_expiration','2032-06-30','Usage expiration date','利用期限 2032年6月30日')],[money],'2031-06-30',5000,
        eraChecks=[{'literal':'令和13年6月30日','expectedDate':'2031-06-30','kind':'payment','page':1}],repeatedAmounts=[{'kind':'payment','value':5000,'occurrences':2}])
    health_lines=['国民健康保険税 納付書','納期限 令和13年6月30日','利用期限 2032年6月30日','納付額 5,000円','納付額 5,000円']
    cases=[
        ('national_health_insurance','repeated',health_lines,health),
        ('residence_tax','roles',['住民税 納付書','納期限 令和13年6月30日','納付額 5,000円','延滞金 300円','支払済金額 1,000円'],truth('Residence Tax',[payment],[money,amount('late_fee',300,'Late fee','延滞金 300円'),amount('paid',1000,'Already-paid amount','支払済金額 1,000円')],'2031-06-30',5000)),
        ('national_pension','clean',['国民年金のお知らせ','納付期限 2031年6月30日','納付金額 17,000円'],truth('National Pension Notice',[deadline('payment','2031-06-30','Payment deadline','納付期限 2031年6月30日')],[amount('payment',17000,'Payment amount','納付金額 17,000円')],'2031-06-30',17000)),
        ('utility','clean',['電気料金のお知らせ','支払期日 2031年6月30日','請求金額 6,800円'],truth('Electricity Notice',[deadline('payment','2031-06-30','Payment due date','支払期日 2031年6月30日')],[amount('billed',6800,'Billed amount','請求金額 6,800円')],'2031-06-30',6800)),
        ('school','multiple',['学校通知','提出期限 2031年6月30日','申請期限 2031年7月10日','合計金額 1,200円'],truth('School Notice',[deadline('submission','2031-06-30','Submission deadline','提出期限 2031年6月30日'),deadline('application','2031-07-10','Application deadline','申請期限 2031年7月10日')],[amount('total',1200,'Total amount','合計金額 1,200円')],primary_amount=1200)),
        ('employment','salary',['雇用条件通知書','基本給 280,000円'],truth('Employment Conditions Notice',status='partial',uncertainFields=[{'field':'amounts','kind':'unknown','value':280000,'evidence':ev('基本給 280,000円'),'reason':'source_ambiguous'}])),
        ('municipal','submission',['市役所からのお知らせ','提出期限 2031年6月30日'],truth('Municipal Notice',[deadline('submission','2031-06-30','Submission deadline','提出期限 2031年6月30日')],primary_date='2031-06-30',missingFields=['amounts','primaryAmount'])),
        ('unknown','missing',['お知らせ','資料を保管してください'],truth(None,status='no_fields',missingFields=['deadlines','amounts','documentType','primaryDeadline','primaryAmount'])),
        ('unknown','illustrative',['参考資料','記入例 納期限 2031年6月30日','見本 納付額 5,000円'],truth(None,status='unverified',uncertainFields=[{'field':'deadlines','kind':'payment','date':'2031-06-30','evidence':ev('記入例 納期限 2031年6月30日'),'reason':'illustrative'},{'field':'amounts','kind':'payment','value':5000,'evidence':ev('見本 納付額 5,000円'),'reason':'illustrative'}])),
        ('unknown','kanji_era',['納付書','納期限 令和十三年六月三十日','納付額 5,000円'],truth('Payment Slip',[deadline('payment','2031-06-30','Payment deadline','納期限 令和十三年六月三十日')],[money],'2031-06-30',5000,eraChecks=[{'literal':'令和十三年六月三十日','expectedDate':'2031-06-30','kind':'payment','page':1}])),
        ('national_health_insurance','blurred',health_lines,deepcopy(health)),
        ('national_health_insurance','vertical',['国民健康保険税','納期限令和13年6月30日','納付額5,000円'],truth('National Health Insurance Tax',[deadline('payment','2031-06-30','Payment deadline','納期限令和13年6月30日')],[amount('payment',5000,'Payment amount','納付額5,000円')],'2031-06-30',5000)),
        ('residence_tax','table',['住民税','納付額','延滞金','5,000円','300円'],truth('Residence Tax',amounts=[amount('payment',5000,'Payment amount','5,000円'),amount('late_fee',300,'Late fee','300円')],primary_amount=5000)),
        ('unknown','paid',['納付額 5,000円','納付済'],truth(None,amounts=[money])),
        ('unknown','unreadable_values',['納期限 不明','納付額 不明'],truth(None,status='unverified',uncertainFields=[{'field':'deadlines','kind':'payment','evidence':ev('納期限 不明'),'reason':'source_unreadable'},{'field':'amounts','kind':'payment','evidence':ev('納付額 不明'),'reason':'source_unreadable'}])),
        ('unknown','issue_only',['発行日 2031年6月1日','請求期間 2031年5月1日〜2031年5月31日'],truth(None,status='no_fields',missingFields=['deadlines','amounts','primaryDeadline','primaryAmount'])),
    ]
    documents=[]
    for index,(category,variant,lines,gt) in enumerate(cases,101):
        path=directory/f'S{index:03d}.png'
        with Image.new('RGB',(640,640),'white') as image:
            draw=ImageDraw.Draw(image)
            draw.text((20,8),'SYNTHETIC TEST',font=regular,fill='gray')
            if variant=='vertical':
                for column,line in enumerate(lines):
                    for row,char in enumerate(line):draw.text((560-column*160,65+row*28),char,font=vertical,fill='black')
            elif variant=='table':
                for text,xy in zip(lines,[(24,70),(24,180),(350,180),(24,235),(350,235)]):draw.text(xy,text,font=regular,fill='black')
            else:
                for row,line in enumerate(lines):draw.text((24,70+row*95),line,font=regular,fill='black')
            if variant=='blurred':
                with image.filter(ImageFilter.GaussianBlur(1.6)) as blurred:blurred.save(path)
            else:image.save(path)
        path.chmod(0o600)
        # Transcription is authored from the generator specification, not OCR.
        # Vertical reading order is intentionally left unscored as full CER.
        if variant!='vertical':gt['transcription']='SYNTHETIC TEST'+''.join(lines)
        documents.append({'id':f'S{index:03d}','path':str(path),'inputSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'category':category,'provenance':'synthetic','variant':variant,'authorizationConfirmed':True,'groundTruth':gt})
    dataset=Dataset.model_validate({'schemaVersion':2,'targetRealDocuments':40,'documents':documents})
    save_json(directory/'manifest.json',dataset.model_dump(exclude_unset=True))
    return directory/'manifest.json'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--font',type=Path);args=parser.parse_args()
    make_dataset(args.directory,args.font);print('Created 16 explicitly synthetic bounded images and independent annotations.')
