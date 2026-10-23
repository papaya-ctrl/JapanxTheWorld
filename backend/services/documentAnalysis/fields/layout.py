"""Conservative horizontal/vertical text reconstruction without coordinate edits."""
from dataclasses import dataclass
import unicodedata
import re

from services.ocr.records import OCRBox


def normalize(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).split())


@dataclass
class TextRun:
    text: str
    characters: list[OCRBox]
    page: int
    orientation: str = "horizontal"

    def sources(self, start: int, end: int) -> list[OCRBox]:
        return list({box.id: box for box in self.characters[start:end]}.values())

    def bounds(self, start: int, end: int):
        boxes = self.sources(start, end)
        return (min(b.bbox[0] for b in boxes), min(b.bbox[1] for b in boxes),
                max(b.bbox[2] for b in boxes), max(b.bbox[3] for b in boxes))

    def reading_bounds(self, start: int, end: int):
        return reading_bounds(self.bounds(start, end), self.orientation)


def reading_bounds(bounds, orientation):
    # Vertical Japanese reads down a column, then moves to the column on its left.
    # Transform only the geometry used by the rules; evidence stays untouched.
    x1, y1, x2, y2 = bounds
    return (y1, -x2, y2, -x1) if orientation == "vertical" else bounds


def reconstruct(boxes: list[OCRBox]) -> tuple[list[TextRun], list[OCRBox]]:
    """Cluster baselines or columns; wide gutters break text runs.

    Tall multi-character OCR boxes establish vertical columns. Square single
    characters can join those columns only when adjacent. Unclear orientations
    remain separate rather than manufacturing a date from nearby columns.
    """
    runs = []
    for page in sorted({b.page for b in boxes}):
        page_boxes = [b for b in boxes if b.page == page]
        vertical = [b for b in page_boxes if len(normalize(b.text)) >= 2
                    and b.height >= 1.6 * (b.bbox[2] - b.bbox[0])]
        vertical_ids = {b.id for b in vertical} | _fragmented_vertical_ids(page_boxes)
        for b in page_boxes:
            if b.id in vertical_ids or len(normalize(b.text)) != 1:
                continue
            width = b.bbox[2] - b.bbox[0]
            if any(min(b.bbox[2], v.bbox[2]) - max(b.bbox[0], v.bbox[0]) >= .65 * width
                   and min(abs(b.bbox[1] - v.bbox[3]), abs(v.bbox[1] - b.bbox[3])) <= 2.5 * width
                   for v in vertical):
                vertical_ids.add(b.id)
        for orientation in ("horizontal", "vertical"):
            subset = [b for b in page_boxes if (b.id in vertical_ids) == (orientation == "vertical")]
            rows = []
            for box in sorted(subset, key=lambda b: _sort_key(b, orientation)):
                coords = reading_bounds(box.bbox, orientation)
                height = coords[3] - coords[1]
                best = None
                for row in rows:
                    anchor = reading_bounds(row[0].bbox, orientation)
                    overlap = min(anchor[3], coords[3]) - max(anchor[1], coords[1])
                    if overlap >= .65 * min(anchor[3] - anchor[1], height):
                        best = row
                        break
                if best is None:
                    rows.append([box])
                else:
                    best.append(box)
            for row in rows:
                row.sort(key=lambda b: (reading_bounds(b.bbox, orientation)[0], b.original_index))
                chunk = []
                for box in row:
                    coords = reading_bounds(box.bbox, orientation)
                    previous = reading_bounds(chunk[-1].bbox, orientation) if chunk else None
                    if previous and coords[0] - previous[2] > 2.5 * min(coords[3] - coords[1], previous[3] - previous[1]):
                        runs.append(_run(chunk, orientation))
                        chunk = []
                    chunk.append(box)
                if chunk:
                    runs.append(_run(chunk, orientation))
    # Top-to-bottom block order; vertical columns at the same top read right-to-left.
    runs.sort(key=lambda r: (r.page, r.bounds(0, len(r.text))[1] if r.text else 0,
                            -r.bounds(0, len(r.text))[2] if r.orientation == "vertical" and r.text
                            else r.bounds(0, len(r.text))[0] if r.text else 0))
    ordered = list({b.id: b for r in runs for b in r.characters}.values())
    # Empty OCR text remains source evidence too.
    ordered.extend(b for b in boxes if b.id not in {item.id for item in ordered})
    return runs, ordered


def _sort_key(box, orientation):
    coords = reading_bounds(box.bbox, orientation)
    return coords[1], coords[0], box.original_index


def _run(boxes, orientation):
    chars, text = [], ""
    for box in boxes:
        normalized = normalize(box.text)
        text += normalized
        chars.extend([box] * len(normalized))
    return TextRun(text, chars, boxes[0].page, orientation)


def _fragmented_vertical_ids(boxes):
    """Recover dense Japanese columns made entirely of square glyph boxes.

    Numeric table columns alone are excluded. This only reconstructs spatial
    reading order; date syntax, label association and confidence still decide
    verification in the engine.
    """
    candidates = [b for b in boxes if (len(normalize(b.text)) == 1 or re.fullmatch(r"\d{2}", normalize(b.text)))
                  and .6 <= b.height / (b.bbox[2] - b.bbox[0]) <= 1.6]
    columns = []
    for box in sorted(candidates, key=lambda b: (b.bbox[0], b.bbox[1])):
        width = box.bbox[2] - box.bbox[0]
        column = next((c for c in columns if abs((c[0].bbox[0] + c[0].bbox[2]) - (box.bbox[0] + box.bbox[2])) <= .6 * width), None)
        if column is None: columns.append([box])
        else: column.append(box)
    result = set()
    def accept(chunk):
        cjk = sum(bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", b.text)) for b in chunk)
        if len(chunk) >= 5 and cjk >= 3:
            result.update(b.id for b in chunk)
    for column in columns:
        chunk = []
        for box in sorted(column, key=lambda b: b.bbox[1]):
            if chunk and box.bbox[1] - chunk[-1].bbox[3] > .75 * min(box.bbox[2]-box.bbox[0], chunk[-1].bbox[2]-chunk[-1].bbox[0]):
                accept(chunk); chunk = []
            chunk.append(box)
        accept(chunk)
    return result
