"""Optional PaddleOCR image/PDF runner; model loading is deliberately lazy."""
import os
from pathlib import Path
from .configuration import OCRConfiguration


def create_paddle_ocr(model_root: Path | None = None, *, config: OCRConfiguration | None = None):
    """Use installed PP-OCRv6 Medium models without model downloads.

    A caller may inject its own initialized PaddleOCR instance into analyze_file.
    Importing this module or the field engine never loads OCR models.
    """
    root = Path(model_root) if model_root else Path.home() / ".paddlex" / "official_models"
    config = config or OCRConfiguration()
    detector_name = f"PP-OCRv6_{config.detection_size}_det"
    recognizer_name = f"PP-OCRv6_{config.recognition_size}_rec"
    detector = root / detector_name
    recognizer = root / recognizer_name
    if not all((path / "inference.yml").is_file() and (path / "inference.pdiparams").is_file()
               for path in (detector, recognizer)):
        raise FileNotFoundError("Local PP-OCRv6 Medium models are missing; supply the installed model root.")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    from paddleocr import PaddleOCR

    return PaddleOCR(
        text_detection_model_name=detector_name,
        text_detection_model_dir=str(detector),
        text_recognition_model_name=recognizer_name,
        text_recognition_model_dir=str(recognizer),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_rec_score_thresh=0.0,
        # Bound detector activation memory on large phone photos. Paddle maps
        # detections back to input coordinates and crops recognition at source
        # resolution, so evidence coordinates remain in the original image.
        text_det_limit_side_len=config.detector_side,
        text_det_limit_type="max",
        text_recognition_batch_size=config.recognition_batch_size,
        cpu_threads=config.cpu_threads,
        enable_mkldnn=config.enable_mkldnn,
        engine=config.engine,
        device="cpu",
    )


def analyze_file(path: str | Path, *, ocr=None, model_root: Path | None = None) -> dict:
    """Accept an image or PDF without deriving any fields from its filename."""
    from services.documentAnalysis.analyzer import analyze_ocr_document

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("The document file does not exist.")
    engine = ocr if ocr is not None else create_paddle_ocr(model_root)
    return analyze_ocr_document(engine.predict(str(path)))
