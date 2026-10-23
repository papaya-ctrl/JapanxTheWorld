"""A bounded local PDF/size suite, derived only from generated synthetic images."""
from copy import deepcopy
import json
from pathlib import Path


def make_load_dataset(dataset_directory):
    from PIL import Image
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    root=Path(dataset_directory).expanduser().resolve()
    if root.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("Keep evaluation inputs and annotations outside the workspace.")
    source_manifest=json.loads((root/"manifest.json").read_text())
    source=next(d for d in source_manifest["documents"] if d["id"]=="S001" and d["provenance"]=="synthetic")
    destination=root/"load";destination.mkdir(exist_ok=True,mode=0o700)
    target=destination/"manifest.json"
    if target.exists():raise FileExistsError("Existing load annotations will not be overwritten.")
    documents=[]
    def add(path,variant,truth=None,error=None):
        gt=deepcopy(truth if truth is not None else source["groundTruth"])
        if error:gt={"expectedError":error}
        documents.append({"id":f"L{len(documents)+1:03d}","path":str(path),"category":source["category"],
                          "provenance":"synthetic","variant":variant,"groundTruth":gt})
    for pages in (1,3):
        path=destination/f"scanned-{pages}.pdf"
        document=canvas.Canvas(str(path),pagesize=(528,720))
        for _ in range(pages):
            document.drawImage(ImageReader(source["path"]),0,0,528,720)
            document.showPage()
        document.save()
        truth=deepcopy(source["groundTruth"]);truth["transcription"]*=pages
        add(path,f"scanned_pdf_{pages}_pages",truth)
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    path=destination/"embedded.pdf"
    document=canvas.Canvas(str(path),pagesize=(528,720));document.setFont("HeiseiMin-W3",16)
    # Known content of this synthetic fixture, not a real document transcription.
    lines=["国民健康保険税 納付書","発行日 2027年1月10日","納期限 令和9年4月15日",
           "利用期限 令和10年4月15日","納付額 26,400円","納付額 26,400円"]
    for index,line in enumerate(lines):document.drawString(30,650-index*70,line)
    document.showPage();document.save();add(path,"embedded_text_pdf")
    path=destination/"large.png"
    with Image.open(source["path"]) as image:
        with image.resize((3300,4500),Image.Resampling.LANCZOS) as enlarged:enlarged.save(path)
    add(path,"large_image_14_85_megapixels")
    data=Path(source["path"]).read_bytes()
    path=destination/"near-limit.png";path.write_bytes(data+b"\0"*(10*1024**2-64-len(data)))
    add(path,"near_10_mib_upload")
    path=destination/"corrupt.png";path.write_bytes(b"\x89PNG\r\n\x1a\nbroken")
    add(path,"corrupted_image",error="INVALID_DOCUMENT")
    path=destination/"oversize.png";path.write_bytes(data+b"\0"*(10*1024**2+1-len(data)))
    add(path,"over_10_mib_upload",error="DOCUMENT_LIMIT_EXCEEDED")
    path=destination/"six-pages.pdf";document=canvas.Canvas(str(path))
    for _ in range(6):document.showPage()
    document.save();add(path,"over_page_limit",error="DOCUMENT_LIMIT_EXCEEDED")
    target.write_text(json.dumps({"schemaVersion":1,"datasetId":"bounded-synthetic-load","documents":documents},ensure_ascii=False,indent=2))
    target.chmod(0o600)
    return target


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("directory",type=Path)
    make_load_dataset(parser.parse_args().directory)
    print("Created a bounded synthetic PDF/size suite outside the workspace.")
