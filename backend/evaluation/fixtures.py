"""Generate explicitly synthetic documents; never impersonate real issuers."""
import argparse
import json
from pathlib import Path


def make_dataset(directory, *, private_sample=None, font_path=None):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    directory = Path(directory).expanduser().resolve()
    project = Path(__file__).resolve().parents[2]
    if directory.is_relative_to(project):
        raise ValueError("Evaluation data and annotations must stay outside the workspace.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest_path = directory/"manifest.json"
    if manifest_path.exists():
        raise FileExistsError("Existing annotations will not be overwritten.")
    font_path = Path(font_path) if font_path else Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
    if not font_path.is_file():
        raise FileNotFoundError("Supply an installed Japanese font for synthetic rendering on this platform.")
    font = ImageFont.truetype(str(font_path), 38)
    # These are generated examples, not historical, real, or issuing-organization records.
    cases = [
        ("national_health_insurance", ["国民健康保険税 納付書", "発行日 2027年1月10日", "納期限 令和9年4月15日", "利用期限 令和10年4月15日", "納付額 26,400円", "納付額 26,400円"],
         "National Health Insurance Tax", [("payment", "2027-04-15"), ("usage_expiration", "2028-04-15")], [("payment",26400)], "2027-04-15",26400),
        ("residence_tax", ["住民税 納付書", "納期限 令和9年5月31日", "納付額 19,000円", "延滞金 700円", "支払済金額 3,000円"],
         "Residence Tax", [("payment","2027-05-31")], [("payment",19000),("late_fee",700),("paid",3000)],"2027-05-31",19000),
        ("national_pension", ["国民年金のお知らせ", "発行日 2027年1月9日", "納付期限 2027年6月30日", "納付金額 17,000円"],
         "National Pension Notice", [("payment","2027-06-30")], [("payment",17000)], "2027-06-30",17000),
        ("utility", ["電気料金のお知らせ", "請求期間 2027年4月1日〜2027年4月30日", "支払期日 2027年5月20日", "請求金額 6,800円"],
         "Electricity Notice", [("payment","2027-05-20")],[("billed",6800)],"2027-05-20",6800),
        ("school", ["学校通知", "提出期限 2027年5月10日", "申請期限 2027年5月20日", "合計金額 1,200円"],
         "School Notice",[("submission","2027-05-10"),("application","2027-05-20")],[("total",1200)],None,1200),
        ("employment", ["雇用条件通知書", "発行日 2027年2月2日", "基本給 280,000円", "領収日 2027年2月10日"],
         "Employment Conditions Notice",[],[],None,None),
        ("municipal", ["市役所からのお知らせ", "提出期限 2027年8月21日", "資料を確認してください"],
         "Municipal Notice",[("submission","2027-08-21")],[],"2027-08-21",None),
        ("unknown", ["お知らせ", "資料を大切に保管してください", "発行日 2027年10月1日"],None,[],[],None,None),
    ]
    documents = []
    for index, (category, lines, doctype, dates, amounts, primary_date, primary_amount) in enumerate(cases):
        variants = ["clean"]
        if index == 0: variants += ["vertical"]
        if index == 3: variants += ["blurred"]
        if index == 4: variants += ["rotated"]
        for variant in variants:
            identifier = f"S{len(documents)+1:03d}"
            image = Image.new("RGB", (1100,1500), "white")
            draw = ImageDraw.Draw(image)
            if variant == "vertical":
                for column, line in enumerate(lines):
                    for row, char in enumerate(line.replace(" ", "")):
                        draw.text((1010-column*150,70+row*42),char,font=font,fill="black")
            else:
                for row, line in enumerate(lines):
                    draw.text((55,80+row*140),line,font=font,fill="black")
            if variant == "blurred": image = image.filter(ImageFilter.GaussianBlur(.8))
            if variant == "rotated": image = image.rotate(2, resample=Image.Resampling.BICUBIC, fillcolor="white")
            path = directory/(identifier+".png")
            image.save(path)
            image.close()
            date_labels = {"payment":"Payment deadline", "usage_expiration":"Usage expiration date",
                           "submission":"Submission deadline", "application":"Application deadline"}
            if category == "utility":
                date_labels["payment"] = "Payment due date"
            amount_labels = {"payment":"Payment amount", "billed":"Billed amount", "total":"Total amount",
                             "late_fee":"Late fee", "paid":"Already-paid amount"}
            truth = {"complete":True,"documentType":doctype,
                     "deadlines":[{"kind":kind,"date":value,"label":date_labels[kind]} for kind,value in dates],
                     "amounts":[{"kind":kind,"value":value,"label":amount_labels[kind]} for kind,value in amounts],
                     "primaryDeadline":primary_date,"primaryAmount":primary_amount,
                     "transcription":"".join(lines)}
            documents.append({"id":identifier,"path":str(path),"provenance":"synthetic",
                              "category":category,"variant":variant,"groundTruth":truth})
    if private_sample and Path(private_sample).is_file():
        # Add annotations manually in the private manifest. Never publish the
        # real sample's facts here or derive truth from the analyzer's output.
        documents.append({"id":"R001","path":str(Path(private_sample).resolve()),"provenance":"real_private",
            "category":"national_health_insurance","variant":"phone_photo",
            "groundTruth":{"complete":False,"annotationSource":"Unannotated: enter independently reviewed facts privately.",
                           "deadlines":[],"amounts":[]}})
    manifest={"schemaVersion":1,"datasetId":"local-private-and-synthetic","documents":documents}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    manifest_path.chmod(0o600)
    return manifest_path


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("directory",type=Path)
    parser.add_argument("--private-sample",type=Path)
    parser.add_argument("--font",type=Path,help="Installed font with Japanese glyph coverage.")
    args=parser.parse_args()
    path=make_dataset(args.directory,private_sample=args.private_sample,font_path=args.font)
    print("Created private synthetic evaluation dataset and manifest.")
