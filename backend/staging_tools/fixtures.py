"""Small explicitly synthetic documents; never personal or issuer records."""
from io import BytesIO
from pathlib import Path


def font_path(value=None):
    paths=[value,'/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']
    return next((str(Path(p)) for p in paths if p and Path(p).is_file()),None)


def image(variant='partial',font=None):
    from PIL import Image,ImageDraw,ImageFont
    selected=font_path(font)
    if not selected:raise ValueError('Provide an installed Japanese-capable font.')
    lines=['国民健康保険税','納期限 令和13年6月30日','利用期限 2032年6月30日','納付額 5,000円','合計金額 不明'] if variant=='partial' else ['お知らせ','資料を保管してください']
    output=BytesIO()
    with Image.new('RGB',(480,640 if variant=='partial' else 320),'white') as generated:
        draw=ImageDraw.Draw(generated);typeface=ImageFont.truetype(selected,27)
        draw.text((20,10),'SYNTHETIC TEST',font=ImageFont.truetype(selected,13),fill='gray')
        for index,line in enumerate(lines):draw.text((24,60+index*100),line,font=typeface,fill='black')
        generated.save(output,format='PNG')
    return output.getvalue()


def scanned_pdf(data,pages=2):
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    output=BytesIO();document=canvas.Canvas(output,pagesize=(230,307))
    for _ in range(pages):document.drawImage(ImageReader(BytesIO(data)),0,0,230,307);document.showPage()
    document.save();return output.getvalue()


def verify_partial(result):
    assert result['source']=='deterministic' and result['extractionStatus']=='partial'
    assert result['primaryDeadline']=='2031-06-30' and result['primaryAmount'] is None
    assert any(d['kind']=='payment' and d['date']=='2031-06-30' and d['status']=='verified' for d in result['deadlines'])
    assert any(d['kind']=='usage_expiration' and d['date']=='2032-06-30' and d['status']=='verified' for d in result['deadlines'])
    assert any(a['kind']=='payment' and a['value']==5000 and a['status']=='verified' for a in result['amounts'])
    public={k:v for k,v in result.items() if k!='evidence'}
    import json
    assert not any('\u3040'<=character<='\u9fff' for character in json.dumps(public,ensure_ascii=False))
    assert any(any('\u3040'<=character<='\u9fff' for character in e['text']) for e in result['evidence'])
