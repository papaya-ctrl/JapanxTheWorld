"""Optional local Step 6 smoke test. Never writes images or modifies the input."""
import argparse
import json
from pathlib import Path

from services.ocr.paddle_extractor import analyze_file

BASE_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Analyze a Japanese document with local PP-OCRv6 Medium models.")
    parser.add_argument("document", nargs="?", type=Path,
                        default=BASE_DIR / "test_documents" / "sample.jpg")
    parser.add_argument("--model-root", type=Path, help="Directory containing the installed Medium models.")
    parser.add_argument("--output", type=Path, help="Optional private JSON output path. Contains original OCR evidence.")
    args = parser.parse_args()
    if not args.document.is_file():
        parser.error("The document file does not exist.")
    output = None
    if args.output:
        # Validate destinations before loading OCR or processing private data.
        output = args.output.expanduser().resolve()
        if output.is_relative_to(BASE_DIR.parent):
            parser.error("Save private OCR results outside the project workspace.")
        if output == args.document.resolve():
            parser.error("The output path must not overwrite the input document.")
    result = analyze_file(args.document, model_root=args.model_root)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized + "\n", encoding="utf-8")
        output.chmod(0o600)
        print("Analysis saved to the requested private output path.")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
