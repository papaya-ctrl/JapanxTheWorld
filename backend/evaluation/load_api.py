"""Two concurrent local uploads and one follow-up: bounded overload verification."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from threading import Barrier

from .metrics import score_result
from .runner import load_manifest


def run(manifest_path,output):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings")
    os.environ["OPENAI_API_KEY"]=""
    import django
    django.setup()
    from django.test import override_settings
    from django.core.cache import cache
    from django.core.files.uploadedfile import SimpleUploadedFile
    from rest_framework.test import APIClient
    from services.ocr.worker import get_document_worker
    entries=[d for d in load_manifest(manifest_path)["documents"] if d["provenance"]=="synthetic" and d["variant"]=="clean"][:2]
    if len(entries)!=2:raise ValueError("Two annotated synthetic inputs are required.")
    output=Path(output).expanduser().resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[2]):raise ValueError("Keep load artifacts outside the workspace.")
    barrier=Barrier(2)
    def submit(entry,synchronize=False):
        if synchronize:barrier.wait(timeout=10)
        response=APIClient().post("/api/documents/analyze",{
            "file":SimpleUploadedFile("document",Path(entry["path"]).read_bytes(),content_type="application/octet-stream")},format="multipart")
        result={"documentId":entry["id"],"httpStatus":response.status_code}
        if response.status_code==200:
            metrics=score_result(response.json(),entry["groundTruth"])
            result["knownFactsCorrect"]=all(metrics[k]["knownFieldsRecovered"] for k in ("deadlines","amounts"))
        else:result["errorCode"]=response.json().get("code")
        return result
    try:
        with override_settings(ALLOWED_HOSTS=["testserver"],DOCUMENT_ANALYSIS_RATE="100/min"):
            cache.clear()
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures=[executor.submit(submit,entry,True) for entry in entries]
                responses=[f.result(timeout=130) for f in futures]
            assert sorted(r["httpStatus"] for r in responses)==[200,503],"Overlapping work was not bounded safely."
            assert all(r.get("knownFactsCorrect",True) for r in responses),"A result was associated with the wrong request."
            assert next(r for r in responses if r["httpStatus"]==503)["errorCode"]=="ANALYSIS_BUSY"
            followup=submit(entries[1])
            assert followup["httpStatus"]==200 and followup["knownFactsCorrect"]
            result={"concurrentRequests":responses,"followup":followup,"peakWorkerMiB":round(get_document_worker().last_peak_rss_bytes/1024**2),
                    "automaticRetries":0,"concurrentHeavyJobs":1}
        output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        output.write_text(json.dumps(result,indent=2)+"\n");output.chmod(0o600)
        print(json.dumps(result))
    finally:get_document_worker().close()


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("manifest",type=Path);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();run(args.manifest,args.output)
