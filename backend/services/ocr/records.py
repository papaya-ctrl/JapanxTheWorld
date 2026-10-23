"""Validated, dependency-free OCR records. Source coordinates are never rewritten."""
from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping


@dataclass(frozen=True)
class OCRBox:
    id: str
    text: str
    confidence: float
    bbox: tuple[float, float, float, float]
    page: int
    original_index: int
    polygon: tuple[tuple[float, float], ...] | None = None

    @property
    def height(self):
        return self.bbox[3] - self.bbox[1]


def boxes_from_paddle(results: Iterable[Mapping]) -> list[OCRBox]:
    """Accept PaddleOCR 3.x prediction results, including numpy arrays.

    page_index is zero based in Paddle; public page numbers are one based.
    Missing page_index uses result sequence order. Invalid geometry or parallel
    arrays fail closed rather than silently truncating evidence with zip().
    """
    boxes = []
    seen_pages = set()
    for result_index, result in enumerate(results):
        page_index = result.get("page_index")
        if page_index is None:
            page_index = result_index
        if int(page_index) != page_index or page_index < 0:
            raise ValueError("OCR page indices must be nonnegative integers.")
        page = int(page_index) + 1
        if page in seen_pages:
            raise ValueError("Duplicate OCR page index.")
        seen_pages.add(page)
        texts = result.get("rec_texts", [])
        scores = result.get("rec_scores", [])
        rects = result.get("rec_boxes", [])
        polygons = result.get("rec_polys")
        if len({len(texts), len(scores), len(rects)}) != 1:
            raise ValueError("OCR text, score, and box arrays must have equal lengths.")
        if polygons is not None and len(polygons) != len(texts):
            raise ValueError("OCR polygon and text arrays must have equal lengths.")
        for index, (text, score, rect) in enumerate(zip(texts, scores, rects)):
            if not isinstance(text, str):
                raise ValueError("OCR text must be a string.")
            score = float(score)
            coords = tuple(float(v) for v in rect)
            if not isfinite(score) or not 0 <= score <= 1:
                raise ValueError("OCR confidence must be finite and between zero and one.")
            if (len(coords) != 4 or not all(isfinite(v) for v in coords)
                    or coords[2] <= coords[0] or coords[3] <= coords[1]):
                raise ValueError("OCR boxes must contain finite, positive rectangles.")
            polygon = None
            if polygons is not None:
                polygon = tuple(tuple(float(v) for v in point) for point in polygons[index])
                if (len(polygon) < 4 or any(len(p) != 2 for p in polygon)
                        or not all(isfinite(v) for p in polygon for v in p)):
                    raise ValueError("OCR polygons must contain finite coordinate pairs.")
            boxes.append(OCRBox(f"p{page}-b{index}", text, score, coords,
                                page, index, polygon))
    return boxes
