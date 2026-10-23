"""Explicit one-time download of official Japanese-capable OCR model weights.

This utility is never called from a request or model initialization. No input
image, annotation, OCR text, or user credential is sent to the model repository.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description="Download official PP-OCRv6 Small/Medium weights, without inference services.")
    parser.add_argument("--root",type=Path,default=Path.home()/".paddlex/official_models")
    parser.add_argument("--size",choices=("small","medium"),default="small")
    args=parser.parse_args()
    from huggingface_hub import HfApi, snapshot_download
    for component in ("det","rec"):
        name=f"PP-OCRv6_{args.size}_{component}"
        destination=args.root.expanduser()/name
        if (destination/"inference.yml").is_file() and (destination/"inference.pdiparams").is_file():
            print(name,"already installed.");continue
        repository="PaddlePaddle/"+name
        revision=HfApi(token=False).model_info(repository).sha
        snapshot_download(repository,revision=revision,local_dir=destination,
                          allow_patterns=["inference.json","inference.yml","inference.pdiparams"],
                          token=False,max_workers=1)
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.glob("inference.*")}
        (destination/"installation.json").write_text(json.dumps({"repository":repository,"revision":revision,"sha256":hashes},indent=2)+"\n")
        print(name,"installed from official pinned revision",revision)


if __name__=="__main__": main()
