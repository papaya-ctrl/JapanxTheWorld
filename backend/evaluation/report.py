"""Publish only allowlisted aggregate metrics: no paths, facts, or OCR snippets."""
import argparse
import csv
import json
from math import isfinite
from pathlib import Path
from .runner import summarize
from .profiles import PROFILES


def publish(metric_paths, output):
    reports=[json.loads(Path(p).read_text()) for p in metric_paths]
    rows=[]
    for report_index,report in enumerate(reports):
        for name,profile in report["profiles"].items():
            if name not in PROFILES: raise ValueError("Unknown profile: refusing to publish unreviewed metadata.")
            for provenance in ("synthetic","real_private","anonymized_real"):
                selected=[r for r in profile["rows"] if r["provenance"]==provenance]
                if not selected:continue
                result=summarize(selected)
                rows.append({"run":report_index+1,"profile":name,"provenance":provenance,
                    "requests":result["requests"],"successful":result["successful"],"unexpectedFailures":result["unexpectedFailures"],
                    "peakRssMiB":result["peakRssMiB"],"coldSeconds":result["coldSeconds"],"medianWarmSeconds":result["medianWarmSeconds"],
                    "deadlineMatched":result["deadlines"]["matched"],"deadlineExpected":result["deadlines"]["expected"],
                    "amountMatched":result["amounts"]["matched"],"amountExpected":result["amounts"]["expected"],
                    "falseDeadlinesCompleteGT":result["deadlines"]["falsePositivesCompleteAnnotations"],
                    "falseAmountsCompleteGT":result["amounts"]["falsePositivesCompleteAnnotations"],
                    "falsePositiveDocumentsScored":result["deadlines"]["falsePositiveDocumentsScored"],
                    "deadlineExactRequests":result["deadlines"]["exactRequests"],
                    "amountExactRequests":result["amounts"]["exactRequests"],
                    "labelMatched":result["deadlines"]["labelMatches"]+result["amounts"]["labelMatches"],
                    "labelScored":result["deadlines"]["labelScored"]+result["amounts"]["labelScored"],
                    "characterEdits":result["characterEdits"],"charactersScored":result["characters"],
                    "characterErrorRate":result["characterEdits"]/result["characters"] if result["characters"] else None,
                    "primaryDeadlineCorrect":result["primaryDeadlineCorrect"]["correct"],
                    "primaryDeadlineScored":result["primaryDeadlineCorrect"]["scored"],
                    "primaryAmountCorrect":result["primaryAmountCorrect"]["correct"],
                    "primaryAmountScored":result["primaryAmountCorrect"]["scored"],
                    "documentTypeCorrect":result["documentTypeCorrect"]["correct"],
                    "documentTypeScored":result["documentTypeCorrect"]["scored"],
                    "extractionStatusCorrect":result["extractionStatusCorrect"]["correct"],
                    "extractionStatusScored":result["extractionStatusCorrect"]["scored"]})
    if not rows: raise ValueError("No supported aggregate rows to publish.")
    for row in rows:
        for key, value in row.items():
            if key not in {"profile", "provenance"} and value is not None:
                if not isinstance(value, (int, float)) or not isfinite(value):
                    raise ValueError("Refusing to publish nonnumeric aggregate metadata.")
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",newline="",encoding="utf-8") as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return rows


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("metrics",nargs="+",type=Path);parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args();publish(args.metrics,args.output)
    print("Published aggregate-only benchmark CSV.")
