"""Image/PDF decoding inside a supervised worker. No document files are written."""
from contextlib import closing
from io import BytesIO
from math import ceil, isfinite
import warnings

from .errors import InvalidDocument, DocumentLimitExceeded, DocumentProcessingError
from .limits import DocumentLimits
from .records import boxes_from_paddle


def _dimensions(width, height, limits):
    if (not all(isfinite(v) and v > 0 for v in (width, height))
            or max(width, height) > limits.max_dimension
            or width * height > limits.max_page_pixels):
        raise DocumentLimitExceeded()


def _check_records(results, limits):
    boxes = boxes_from_paddle(results)
    if len(boxes) > limits.max_boxes or sum(len(b.text) for b in boxes) > limits.max_characters:
        raise DocumentLimitExceeded()


def _predict(image, page_index, predict):
    # Materialize while the image buffer is alive; no model/debug save methods.
    results = list(predict(image))
    if len(results) != 1:
        raise DocumentProcessingError()
    result = results[0]
    output = {key: result[key] for key in ("rec_texts", "rec_scores", "rec_boxes")}
    if result.get("rec_polys") is not None:
        output["rec_polys"] = result["rec_polys"]
    output["page_index"] = page_index
    return output


def extract_document(data: bytes, kind: str, predict, limits: DocumentLimits):
    if len(data) > limits.max_file_bytes:
        raise DocumentLimitExceeded()
    if kind == "pdf":
        return _pdf(data, predict, limits)
    return _image(data, kind, predict, limits)


def _image(data, kind, predict, limits):
    from PIL import Image
    import numpy as np

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                source_format = source.format.lower()
                if source_format != kind and not (kind == "jpeg" and source_format == "mpo"):
                    raise InvalidDocument()
                _dimensions(source.width, source.height, limits)
                frames = getattr(source, "n_frames", 1)
                if frames != 1 and source_format != "mpo":
                    raise InvalidDocument()
                width, height = source.size
                source.verify()
            with Image.open(BytesIO(data)) as source:
                source.load()
                if source.mode == "RGB":
                    bgr_bytes = source.tobytes("raw", "BGR")
                else:
                    with source.convert("RGB") as rgb:
                        bgr_bytes = rgb.tobytes("raw", "BGR")
            # Keep only one packed BGR buffer alive during inference. The view is
            # read-only, preserving source pixels without redundant RGB/array copies.
            pixels = np.frombuffer(bgr_bytes, dtype=np.uint8).reshape(height, width, 3)
            result = _predict(pixels, 0, predict)
            del pixels, bgr_bytes
        _check_records([result], limits)
        return [result], [{"page": 1, "method": "paddleocr", "coordinateSystem": "image_pixels",
                           "width": width, "height": height, "auxiliaryFramesSkipped": frames - 1}]
    except (InvalidDocument, DocumentLimitExceeded, DocumentProcessingError):
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise DocumentLimitExceeded() from None
    except (OSError, ValueError, SyntaxError):
        raise InvalidDocument() from None


def _embedded_text(page, limits):
    """Group adjacent PDF characters without losing geometry or Unicode text.

    Null confidence is restored at the API boundary: the 1.0 scores here are an
    adapter sentinel for exact embedded text, not claimed OCR probabilities.
    """
    import pypdfium2.raw as raw
    page_height = page.get_height()
    with closing(page.get_textpage()) as textpage:
        count = textpage.count_chars()
        if count > limits.max_characters:
            raise DocumentLimitExceeded()
        chunks, current, previous = [], [], None
        for index in range(count):
            # GetUnicode preserves non-BMP characters and avoids text-index drift.
            codepoint = raw.FPDFText_GetUnicode(textpage, index)
            char = chr(codepoint) if codepoint else ""
            if not char or char.isspace() or not char.isprintable():
                if current:
                    chunks.append(current)
                current, previous = [], None
                continue
            x1, y1, x2, y2 = textpage.get_charbox(index, loose=True)
            rect = (x1, page_height - y2, x2, page_height - y1)
            if not all(isfinite(v) for v in rect) or x2 <= x1 or y2 <= y1:
                continue
            if previous:
                px1, py1, px2, py2 = previous
                h, w = max(py2 - py1, rect[3] - rect[1]), max(px2 - px1, rect[2] - rect[0])
                horizontal = abs((py1 + py2) - (rect[1] + rect[3])) <= h * .8 and -.5 * h <= rect[0] - px2 <= 1.5 * h
                vertical = abs((px1 + px2) - (rect[0] + rect[2])) <= w * .8 and -.5 * w <= rect[1] - py2 <= 1.5 * w
                if not horizontal and not vertical:
                    chunks.append(current)
                    current = []
            current.append((char, rect))
            previous = rect
        if current:
            chunks.append(current)
    texts = ["".join(c for c, _ in chunk) for chunk in chunks]
    combined = "".join(texts)
    # Broken character maps and opaque glyph IDs should use raster OCR instead.
    meaningful = sum(c.isalnum() for c in combined)
    bad = sum(c == "\ufffd" or 0xE000 <= ord(c) <= 0xF8FF for c in combined)
    usable = meaningful >= 3 and not bad
    rects = [[min(r[0] for _, r in chunk), min(r[1] for _, r in chunk),
              max(r[2] for _, r in chunk), max(r[3] for _, r in chunk)] for chunk in chunks]
    return {"rec_texts": texts, "rec_scores": [1.] * len(texts), "rec_boxes": rects}, usable


def _pdf(data, predict, limits):
    import pypdfium2 as pdfium
    from pypdfium2 import raw

    results, metadata, rendered_pixels = [], [], 0
    try:
        with pdfium.PdfDocument(data) as document:
            if not 1 <= len(document) <= limits.max_pages:
                raise DocumentLimitExceeded()
            for index in range(len(document)):
                with closing(document[index]) as page:
                    width, height = page.get_size()
                    # Bound dimensions before PDF parsing/raster allocation.
                    scale = limits.pdf_dpi / 72
                    pixel_width, pixel_height = ceil(width * scale), ceil(height * scale)
                    _dimensions(pixel_width, pixel_height, limits)
                    record, usable = _embedded_text(page, limits)
                    image_area = 0
                    for number, obj in enumerate(page.get_objects(max_depth=5)):
                        if number > 10_000:
                            raise DocumentLimitExceeded()
                        if obj.type == raw.FPDF_PAGEOBJ_IMAGE:
                            left, bottom, right, top = obj.get_bounds()
                            image_area += abs((right - left) * (top - bottom))
                    # Mixed scanned/text pages use a single full-page OCR pass.
                    # Rotated embedded coordinates need transformation, so OCR
                    # those pages instead of returning misleading positions.
                    if usable and image_area <= .1 * width * height and page.get_rotation() == 0:
                        method, coords, size = "pdf_embedded_text", "pdf_points", (width, height)
                    else:
                        rendered_pixels += pixel_width * pixel_height
                        if rendered_pixels > limits.max_document_pixels:
                            raise DocumentLimitExceeded()
                        with closing(page.render(scale=scale, force_bitmap_format=raw.FPDFBitmap_BGR)) as bitmap:
                            # Zero-copy view remains inside the bitmap lifetime.
                            pixels = bitmap.to_numpy()
                            record = _predict(pixels, index, predict)
                            del pixels
                        method, coords, size = "paddleocr", "rendered_pixels", (pixel_width, pixel_height)
                    record["page_index"] = index
                    results.append(record)
                    metadata.append({"page": index + 1, "method": method, "coordinateSystem": coords,
                                     "width": size[0], "height": size[1]})
                    _check_records(results, limits)
        return results, metadata
    except (DocumentLimitExceeded, DocumentProcessingError):
        raise
    except Exception:
        raise InvalidDocument() from None


def analyze_document_bytes(data, kind, predict, limits):
    """Adapt decoded pages to Step 6, retaining honest source/confidence metadata."""
    from services.documentAnalysis.analyzer import analyze_ocr_document

    records, pages = extract_document(data, kind, predict, limits)
    result = analyze_ocr_document(records)
    result["pages"] = pages
    if any(p.get("auxiliaryFramesSkipped", 0) for p in pages):
        result["warnings"].append("The JPEG contains additional image frames; only its primary image was analyzed.")
        if result["extractionStatus"] == "verified":
            result["extractionStatus"] = "partial"
    methods = {p["method"] for p in pages}
    result["extractionMethod"] = next(iter(methods)) if len(methods) == 1 else "mixed"
    embedded_pages = {p["page"] for p in pages if p["method"] == "pdf_embedded_text"}
    for evidence in result["evidence"]:
        embedded = evidence["page"] in embedded_pages
        evidence["extractionMethod"] = "pdf_embedded_text" if embedded else "paddleocr"
        if embedded:
            evidence["confidence"] = None
    by_id = {e["id"]: e for e in result["evidence"]}
    for field in result["deadlines"] + result["amounts"]:
        scores = [by_id[i]["confidence"] for i in field["evidenceIds"] if by_id[i]["confidence"] is not None]
        field["ocrConfidence"] = min(scores) if scores else None
    return result
