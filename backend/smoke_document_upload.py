"""Optional real-image Django integration check. Output stays outside the repo."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run a private sample through the real Django upload endpoint.")
    parser.add_argument("document", type=Path, nargs="?", default=Path(__file__).resolve().parent / "test_documents/sample.jpg")
    parser.add_argument("--output", type=Path, default=Path.home() / "ocr_private_test/step7-analysis.json")
    parser.add_argument("--repeat", type=int, default=2, choices=(1, 2, 3),
                        help="Repeat requests in one process to verify model/worker reuse.")
    args = parser.parse_args()
    if not args.document.is_file():
        parser.error("The sample document is not available.")
    output = args.output.expanduser().resolve()
    if output.is_relative_to(Path(__file__).resolve().parent.parent) or output == args.document.resolve():
        parser.error("Save private output outside the project and never overwrite the input document.")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    # The smoke check deliberately runs with no paid API key, regardless of .env.
    os.environ["OPENAI_API_KEY"] = ""
    import django
    django.setup()
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import override_settings
    from rest_framework.test import APIClient
    from services.ocr.worker import get_document_worker

    original = args.document.read_bytes()
    digest = hashlib.sha256(original).digest()
    try:
        measurements, pids = [], []
        for _ in range(args.repeat):
            with override_settings(ALLOWED_HOSTS=["testserver"]):
                response = APIClient().post("/api/documents/analyze", {
                    "file": SimpleUploadedFile("document", original, content_type="application/octet-stream")
                }, format="multipart")
            if response.status_code != 200:
                # Print only allowlisted API error, never native exception/input.
                raise SystemExit(f"Smoke test failed: HTTP {response.status_code}, {response.json().get('code', 'UNKNOWN_ERROR')}; peak worker MiB: {get_document_worker().last_peak_rss_bytes / 1024**2:.0f}")
            worker = get_document_worker()
            pids.append(worker._process.pid)
            measurements.append({"peakWorkerMiB": round(worker.last_peak_rss_bytes / 1024**2),
                                 "processingSeconds": round(worker.last_elapsed_seconds, 1),
                                 "phases": worker.last_metrics.copy()})
        assert len(set(pids)) == 1, "The analysis worker was not reused."
        result = response.json()
        assert result["source"] == "deterministic"
        assert result["extractionMethod"] == "paddleocr"
        assert result["evidence"]
        assert hashlib.sha256(args.document.read_bytes()).digest() == digest
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as destination:
            os.fchmod(destination.fileno(), 0o600)
            json.dump(result, destination, ensure_ascii=False, allow_nan=False, indent=2)
        print(json.dumps({"httpStatus": response.status_code, "extractionStatus": result["extractionStatus"],
                          "evidenceBoxes": len(result["evidence"]), "deadlines": len(result["deadlines"]),
                          "amounts": len(result["amounts"]), "inputUnchanged": True,
                          "successfulRequests": args.repeat, "workerReused": len(set(pids)) == 1,
                          "measurements": measurements}))
    finally:
        get_document_worker().close()


if __name__ == "__main__":
    main()
