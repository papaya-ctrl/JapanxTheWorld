from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentLimits:
    max_file_bytes: int = 10 * 1024 * 1024
    max_pages: int = 5
    max_dimension: int = 8000
    max_page_pixels: int = 16_000_000
    max_document_pixels: int = 50_000_000
    max_boxes: int = 4000
    max_characters: int = 50_000
    pdf_dpi: int = 150
    timeout_seconds: float = 120
    max_worker_rss_bytes: int = 5 * 1024**3
    min_host_available_bytes: int = 512 * 1024**2
    worker_idle_seconds: float = 120
    max_worker_requests: int = 64

    def __post_init__(self):
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("Document limits must be positive.")
