"""Explicit benchmark candidates. Only Small/Medium recognition supports Japanese."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRProfile:
    name: str
    detection: str = "medium"
    recognition: str = "medium"
    batch_size: int | None = None
    cpu_threads: int | None = None
    mkldnn: bool | None = None
    engine: str | None = None
    detector_side: int = 1920

    def __post_init__(self):
        if self.detection not in {"small", "medium"} or self.recognition not in {"small", "medium"}:
            raise ValueError("Only Japanese-capable Small and Medium profiles are allowed.")
        if self.batch_size is not None and not 1 <= self.batch_size <= 6:
            raise ValueError("Recognition batching must be bounded from one to six.")
        if self.cpu_threads is not None and not 1 <= self.cpu_threads <= 10:
            raise ValueError("CPU threads must be bounded from one to ten.")
        if not 960 <= self.detector_side <= 1920 or self.engine not in {None, "paddle_static"}:
            raise ValueError("Use bounded detector sizing and the evaluated CPU backend.")

    def create(self, model_root=None):
        # Baseline kwargs below freeze Step 8 settings even after defaults change.
        root = Path(model_root) if model_root else Path.home()/".paddlex/official_models"
        detector, recognizer = f"PP-OCRv6_{self.detection}_det", f"PP-OCRv6_{self.recognition}_rec"
        for name in (detector, recognizer):
            if not all((root/name/file).is_file() for file in ("inference.yml", "inference.pdiparams")):
                raise FileNotFoundError("A requested local OCR model is not installed.")
        from paddleocr import PaddleOCR
        kwargs = dict(text_detection_model_name=detector, text_detection_model_dir=str(root/detector),
                      text_recognition_model_name=recognizer, text_recognition_model_dir=str(root/recognizer),
                      use_doc_orientation_classify=False, use_doc_unwarping=False,
                      use_textline_orientation=False, text_rec_score_thresh=0.,
                      text_det_limit_side_len=self.detector_side, text_det_limit_type="max", device="cpu")
        if self.batch_size is not None: kwargs["text_recognition_batch_size"] = self.batch_size
        if self.cpu_threads is not None: kwargs["cpu_threads"] = self.cpu_threads
        if self.mkldnn is not None: kwargs["enable_mkldnn"] = self.mkldnn
        if self.engine is not None: kwargs["engine"] = self.engine
        return PaddleOCR(**kwargs)


PROFILES = {
    "baseline-medium": OCRProfile("baseline-medium"),
    "medium-batch1": OCRProfile("medium-batch1", batch_size=1),
    "medium-batch2": OCRProfile("medium-batch2", batch_size=2),
    "medium-cpu4": OCRProfile("medium-cpu4", batch_size=1, cpu_threads=4, mkldnn=False, engine="paddle_static"),
    "medium-side1792": OCRProfile("medium-side1792", batch_size=1, cpu_threads=4, mkldnn=False, engine="paddle_static", detector_side=1792),
    "medium-side1600": OCRProfile("medium-side1600", batch_size=1, cpu_threads=4, mkldnn=False, engine="paddle_static", detector_side=1600),
    "medium-cpu2": OCRProfile("medium-cpu2", batch_size=1, cpu_threads=2, mkldnn=False, engine="paddle_static"),
    "small-small": OCRProfile("small-small", "small", "small", batch_size=1, cpu_threads=4, mkldnn=False, engine="paddle_static"),
    "small-medium": OCRProfile("small-medium", "small", "medium", batch_size=1, cpu_threads=4, mkldnn=False, engine="paddle_static"),
    "medium-small": OCRProfile("medium-small", "medium", "small", batch_size=1, cpu_threads=4, mkldnn=False, engine="paddle_static"),
}
