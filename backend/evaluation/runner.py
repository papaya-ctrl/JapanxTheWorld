"""Sequential, privacy-safe benchmarks with time/RSS/host-pressure cancellation."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
from pathlib import Path
import platform
import re
import statistics
import sys
import time

import psutil
from services.ocr.limits import DocumentLimits
from .metrics import score_result
from .profiles import PROFILES

CATEGORIES = {"national_health_insurance", "residence_tax", "national_pension", "utility", "school", "employment", "municipal", "unknown"}


def _child(connection, profile_name, model_root):
    with open(os.devnull,"w") as sink:
        os.dup2(sink.fileno(),1); os.dup2(sink.fileno(),2)
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    from services.ocr.document_adapter import analyze_document_bytes
    from services.ocr.errors import DocumentProcessingError
    model = None
    process = psutil.Process()
    connection.send(("ready", {}))
    try:
        while True:
            data, kind = connection.recv()
            metrics = {"modelInitSeconds":0., "inferenceSeconds":0., "inferenceCalls":0,
                       "rssBeforeBytes":process.memory_info().rss}
            started = time.perf_counter()
            def predict(image):
                nonlocal model
                if model is None:
                    begin = time.perf_counter()
                    connection.send(("phase", {"name":"model_initialization","rssBytes":process.memory_info().rss}))
                    model = PROFILES[profile_name].create(model_root)
                    metrics["modelInitSeconds"] = time.perf_counter()-begin
                    metrics["rssAfterModelInitBytes"] = process.memory_info().rss
                    pipeline = model.paddlex_pipeline
                    metrics["detectionPredictor"] = type(pipeline.text_det_model).__name__
                    metrics["recognitionPredictor"] = type(pipeline.text_rec_model).__name__
                    metrics["detectionBackend"] = type(pipeline.text_det_model.runner).__name__
                    metrics["recognitionBackend"] = type(pipeline.text_rec_model.runner).__name__
                    # Public model configuration only, never OCR content.
                    metrics["detectorConfig"] = {key:value for key,value in model._params.items()
                                                if key in {"text_detection_model_name","text_recognition_model_name","text_recognition_batch_size","text_det_limit_side_len","text_det_limit_type"}}
                    connection.send(("phase", {"name":"model_initialized", **metrics}))
                begin = time.perf_counter()
                output = list(model.predict(image))
                metrics["inferenceSeconds"] += time.perf_counter()-begin
                metrics["inferenceCalls"] += 1
                return output
            try:
                result = analyze_document_bytes(data,kind,predict,DocumentLimits())
                metrics["childSeconds"] = time.perf_counter()-started
                metrics["rssAfterBytes"] = process.memory_info().rss
                connection.send(("result", {"analysis":result,"metrics":metrics}))
            except DocumentProcessingError as exc:
                connection.send(("error", {"code":exc.code}))
            except Exception as exc:
                connection.send(("error", {"code":"BENCHMARK_FAILURE","exceptionType":type(exc).__name__}))
            finally:
                data = result = None
    except (EOFError, BrokenPipeError, OSError):
        pass
    finally:
        connection.close()


class BenchmarkSession:
    def __init__(self, profile, model_root=None, *, min_available_mib=768, max_swap_growth_mib=512,
                 timeout=120, max_rss_mib=6144):
        self.profile,self.model_root=profile,model_root
        self.min_available=min_available_mib*1024**2
        self.max_swap_growth=max_swap_growth_mib*1024**2
        self.timeout,self.max_rss=timeout,max_rss_mib*1024**2
        self.process=self.connection=None
        self.boot_seconds=None

    def close(self):
        if self.connection: self.connection.close()
        if self.process:
            if self.process.is_alive(): self.process.terminate()
            self.process.join(1)
            if self.process.is_alive(): self.process.kill(); self.process.join(1)
            self.process.close()
        self.connection=self.process=None

    def analyze(self,data,kind):
        started=time.perf_counter()
        swap_start=psutil.swap_memory().used
        available_start=psutil.virtual_memory().available
        if available_start < self.min_available:
            return None,{"outcome":"HOST_MEMORY_GUARD","elapsedSeconds":0.,"peakRssBytes":0}
        cold=self.process is None
        if cold:
            ctx=multiprocessing.get_context("spawn")
            self.connection,child=ctx.Pipe()
            self.process=ctx.Process(target=_child,args=(child,self.profile,self.model_root),daemon=True)
            self.process.start();child.close()
        monitored=psutil.Process(self.process.pid)
        self.connection.send((data,kind))
        peak=parent_peak=0; minimum_available=available_start
        events=[]
        try:
            while True:
                elapsed=time.perf_counter()-started
                memory=psutil.virtual_memory(); swap=psutil.swap_memory()
                minimum_available=min(minimum_available,memory.available)
                try: rss=monitored.memory_info().rss
                except psutil.NoSuchProcess: rss=0
                peak=max(peak,rss)
                parent_peak=max(parent_peak,psutil.Process().memory_info().rss)
                abort=None
                if elapsed > self.timeout: abort="PROCESSING_TIMEOUT"
                elif rss > self.max_rss: abort="WORKER_MEMORY_GUARD"
                elif memory.available < self.min_available or swap.used-swap_start > self.max_swap_growth: abort="HOST_MEMORY_GUARD"
                if abort:
                    self.close()
                    return None,{"outcome":abort,"cold":cold,"elapsedSeconds":round(elapsed,4),"peakRssBytes":peak,
                                 "minimumAvailableBytes":minimum_available,"swapGrowthBytes":max(0,swap.used-swap_start),"events":events}
                if self.connection.poll(.05):
                    event,payload=self.connection.recv()
                    if event=="ready": self.boot_seconds=elapsed
                    elif event=="phase": events.append(dict(payload,elapsedSeconds=round(elapsed,4)))
                    else:
                        metrics={"outcome":"ok" if event=="result" else payload["code"],"cold":cold,
                                 "elapsedSeconds":round(time.perf_counter()-started,4),"peakRssBytes":peak,
                                 "parentPeakRssBytes":parent_peak,"minimumAvailableBytes":minimum_available,
                                 "swapGrowthBytes":max(0,swap.used-swap_start),"bootSeconds":self.boot_seconds}
                        if event=="result":
                            metrics.update(payload["metrics"])
                            return payload["analysis"],metrics
                        return None,metrics
                if not self.process.is_alive():
                    self.close();return None,{"outcome":"WORKER_EXITED","elapsedSeconds":elapsed,"peakRssBytes":peak}
        except (EOFError,BrokenPipeError,OSError):
            self.close();return None,{"outcome":"WORKER_EXITED","elapsedSeconds":time.perf_counter()-started,"peakRssBytes":peak}


def load_manifest(path):
    path=Path(path).expanduser().resolve()
    if path.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("Keep manifests and annotations outside the workspace.")
    manifest=json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("documents"),list):
        raise ValueError("Unsupported evaluation manifest schema.")
    ids=set()
    for item in manifest["documents"]:
        if not re.fullmatch(r"[A-Z]\d{3}",item["id"]) or item["id"] in ids or item["category"] not in CATEGORIES:
            raise ValueError("Use unique anonymized document identifiers and supported categories.")
        ids.add(item["id"])
        if item["provenance"] not in {"synthetic","real_private","anonymized_real"}:
            raise ValueError("Document provenance must be explicit.")
        if not Path(item["path"]).is_file() or not isinstance(item.get("groundTruth"),dict):
            raise ValueError("Document input or private ground truth is unavailable.")
    return manifest


def environment():
    return {"platform":platform.platform(),"machine":platform.machine(),"python":platform.python_version(),
            "logicalCpus":psutil.cpu_count(),"physicalCpus":psutil.cpu_count(logical=False),
            "totalRamBytes":psutil.virtual_memory().total,
            "versions":{p:importlib.metadata.version(p) for p in ("paddleocr","paddlepaddle","paddlex","numpy","Pillow","psutil","pypdfium2")},
            "samplingSeconds":.05,"measurement":"Worker RSS sampled by parent; not an exact allocation high-water mark.",
            "implementationSha256":{str(p.relative_to(Path(__file__).resolve().parents[1])):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in [Path(__file__).resolve().parents[1]/"services/ocr/paddle_extractor.py",
                            Path(__file__).resolve().parents[1]/"services/ocr/document_adapter.py",
                            Path(__file__).resolve().parents[1]/"services/documentAnalysis/fields/engine.py"]},
            "baselineDefaults":{"device":"cpu on this Mac","recognitionBatch":6,"cpuThreads":10,"enableMkldnnRequested":True,"detectorLongSide":1920}}


def summarize(rows):
    successful=[r for r in rows if r["resources"]["outcome"]=="ok"]
    result={"requests":len(rows),"successful":len(successful),"failed":len(rows)-len(successful),
            "unexpectedFailures":sum(not r.get("accepted",r["resources"]["outcome"]=="ok") for r in rows)}
    result["peakRssMiB"]=round(max((r["resources"]["peakRssBytes"] for r in rows),default=0)/1024**2,2)
    warm=[r["resources"]["elapsedSeconds"] for r in successful if not r["resources"]["cold"]]
    result["medianWarmSeconds"]=round(statistics.median(warm),4) if warm else None
    cold=[r["resources"]["elapsedSeconds"] for r in successful if r["resources"]["cold"]]
    result["coldSeconds"]=cold[0] if cold else None
    for name in ("deadlines","amounts"):
        scored=[r["accuracy"][name] for r in successful]
        expected=sum(r["expected"] for r in scored);matched=sum(r["matched"] for r in scored)
        result[name]={"expected":expected,"matched":matched,"recall":matched/expected if expected else None,
                      "falsePositivesCompleteAnnotations":sum(r["falsePositive"] for r in scored if r["falsePositive"] is not None) if any(r["falsePositive"] is not None for r in scored) else None,
                      "falsePositiveDocumentsScored":sum(r["falsePositive"] is not None for r in scored),
                      "exactRequests":sum(r["exact"] is True for r in scored),"unscoredPredictions":sum(r["unscoredPredictions"] for r in scored),
                      "labelMatches":sum(r["labelMatches"] for r in scored),"labelScored":sum(r["labelScored"] for r in scored)}
    for key in ("documentTypeCorrect","primaryDeadlineCorrect","primaryAmountCorrect","extractionStatusCorrect"):
        values=[r["accuracy"][key] for r in successful if r["accuracy"][key] is not None]
        result[key]={"correct":sum(values),"scored":len(values)}
    result["characterEdits"]=sum(r["accuracy"]["characterEdits"] for r in successful if r["accuracy"]["characterEdits"] is not None)
    result["characters"]=sum(r["accuracy"]["characters"] for r in successful if r["accuracy"]["characters"] is not None)
    return result


def run(args):
    manifest=load_manifest(args.manifest)
    documents=manifest["documents"]
    if args.ids: documents=[d for d in documents if d["id"] in args.ids.split(",")]
    documents=documents[:args.max_documents]
    if not documents: raise ValueError("No evaluation documents selected.")
    if args.min_available_mib < 512 or not 0 <= args.max_swap_growth_mib <= 1024 or not 256 <= args.max_rss_mib <= 6144 or not 0 < args.timeout <= 120:
        raise ValueError("Benchmarks must retain conservative host, worker and time guards.")
    profiles=args.profiles.split(",")
    if len(profiles)!=len(set(profiles)) or len(profiles)>len(PROFILES) or len(profiles)*len(documents)*args.repeat>1000:
        raise ValueError("Use unique profiles and at most 1000 requests per controlled run.")
    output=Path(args.output).expanduser().resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[2]): raise ValueError("Keep benchmark artifacts outside the workspace; publish only reviewed aggregate reports.")
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    report={"schemaVersion":1,"environment":environment(),"profiles":{},"dataset":{"documents":len(documents),"real":sum(d["provenance"]!="synthetic" for d in documents),"synthetic":sum(d["provenance"]=="synthetic" for d in documents)},"limits":{"minAvailableMiB":args.min_available_mib,"maxSwapGrowthMiB":args.max_swap_growth_mib,"maxRssMiB":args.max_rss_mib,"timeoutSeconds":args.timeout}}
    for profile_name in profiles:
        if profile_name not in PROFILES: raise ValueError("Unknown OCR profile.")
        session=BenchmarkSession(profile_name,args.model_root,min_available_mib=args.min_available_mib,
             max_swap_growth_mib=args.max_swap_growth_mib,max_rss_mib=args.max_rss_mib,timeout=args.timeout)
        rows=[]
        try:
            for repeat in range(args.repeat):
                for item in documents:
                    data=Path(item["path"]).read_bytes()
                    before=hashlib.sha256(data).hexdigest()
                    from middleware.file_validator import detect_document_kind
                    result,resources=session.analyze(data,detect_document_kind(data))
                    row={"expectedOutcome":item["groundTruth"].get("expectedError","ok"),"accepted":resources["outcome"]==item["groundTruth"].get("expectedError","ok"),"documentId":item["id"],"category":item["category"],"provenance":item["provenance"],"variant":item.get("variant","unspecified"),"repeat":repeat,"resources":resources}
                    if result:
                        row["accuracy"]=score_result(result,item["groundTruth"])
                        row["pages"]=len(result["pages"])
                        row["secondsPerPage"]=resources["elapsedSeconds"]/max(1,row["pages"])
                        row["extractionStatus"]=result["extractionStatus"]
                        if args.save_private_predictions:
                            path=output/f"{profile_name}-{item['id']}-{repeat}-private.json"
                            path.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding="utf-8");path.chmod(0o600)
                    assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()==before,"Input document was modified."
                    rows.append(row)
                    print(json.dumps({"profile":profile_name,"documentId":item["id"],"repeat":repeat,"outcome":resources["outcome"],"seconds":resources["elapsedSeconds"],"peakMiB":round(resources["peakRssBytes"]/1024**2)}),flush=True)
                    if resources["outcome"]=="HOST_MEMORY_GUARD": break
                if rows and rows[-1]["resources"]["outcome"]=="HOST_MEMORY_GUARD": break
        finally: session.close()
        report["profiles"][profile_name]={"configuration":asdict(PROFILES[profile_name]),"rows":rows,"summary":summarize(rows)}
        path=output/"metrics.json"
        path.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8");path.chmod(0o600)
        if rows and rows[-1]["resources"]["outcome"]=="HOST_MEMORY_GUARD":
            break  # Stop the whole run; do not cycle models under host pressure.
    return report


def main():
    parser=argparse.ArgumentParser(description="Local, sequential OCR evaluation with private annotations.")
    parser.add_argument("manifest",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--profiles",default="baseline-medium")
    parser.add_argument("--ids")
    parser.add_argument("--repeat",type=int,default=1,choices=range(1,6))
    parser.add_argument("--max-documents",type=int,default=50,choices=range(1,51))
    parser.add_argument("--model-root",type=Path)
    parser.add_argument("--min-available-mib",type=int,default=768)
    parser.add_argument("--max-swap-growth-mib",type=int,default=512)
    parser.add_argument("--max-rss-mib",type=int,default=6144)
    parser.add_argument("--timeout",type=float,default=120)
    parser.add_argument("--save-private-predictions",action="store_true")
    run(parser.parse_args())


if __name__=="__main__": main()
