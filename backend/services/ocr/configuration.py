"""Explicit CPU-only model settings selected by the Step 9 evaluation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class OCRConfiguration:
    detection_size: str = "medium"
    recognition_size: str = "medium"
    recognition_batch_size: int = 1
    cpu_threads: int = 4
    detector_side: int = 1600
    enable_mkldnn: bool = False
    engine: str = "paddle_static"

    def __post_init__(self):
        if self.detection_size not in {"medium","small"} or self.recognition_size not in {"medium","small"}:
            raise ValueError("Only locally installed Japanese-capable Small/Medium models are supported.")
        if not 1 <= self.recognition_batch_size <= 6 or not 1 <= self.cpu_threads <= 10:
            raise ValueError("OCR batching and CPU threads must be bounded.")
        if not 960 <= self.detector_side <= 1920 or self.engine != "paddle_static":
            raise ValueError("Use the evaluated CPU Paddle static backend and detector bounds.")
