"""Django integration with real file decoding, synthetic data and mocked inference."""
import json
import os
from io import BytesIO
from unittest.mock import Mock, patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient
from PIL import Image

from services.ocr.document_adapter import analyze_document_bytes
from services.ocr.errors import DocumentProcessingError, ProcessingTimeout, WorkerBusy
from services.ocr.limits import DocumentLimits
from tests.test_document_fields import page


def image_bytes(format="PNG", size=(300, 180)):
    with BytesIO() as output, Image.new("RGB", size, "white") as image:
        image.save(output, format=format)
        return output.getvalue()


def pdf_bytes(*, scanned=False, pages=1, size=(400, 600), rotated=False):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib.utils import ImageReader
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=size)
    if rotated:
        pdf.setPageRotation(90)
    for _ in range(pages):
        if scanned:
            pdf.drawImage(ImageReader(BytesIO(image_bytes())), 0, 0, size[0], size[1])
        else:
            pdf.setFont("HeiseiMin-W3", 14)
            pdf.drawString(30, size[1] - 60, "納期限 令和8年11月2日")
            pdf.drawString(30, size[1] - 100, "納付額 18000円")
        pdf.showPage()
    pdf.save()
    return output.getvalue()


class InProcessWorker:
    """Exercise the production adapter and analyzer while replacing only OCR."""
    def __init__(self, records=None, limits=None):
        self.limits = limits or DocumentLimits()
        self.predict = Mock(return_value=[records or page(("納期限 2026年11月2日", 0, 0, 250, 20),
                                                          ("納付額 18000円", 0, 80, 200, 100))])

    def analyze(self, data, kind):
        return analyze_document_bytes(data, kind, self.predict, self.limits)


@override_settings(DOCUMENT_ANALYSIS_RATE="1000/min")
class DocumentUploadTests(SimpleTestCase):
    # SimpleTestCase forbids *all* database queries: successful uploads cannot
    # silently create document, summary, filename, text, or analysis records.
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.worker = InProcessWorker()
        self.worker_patch = patch("services.documentAnalysis.upload.get_document_worker", return_value=self.worker)
        self.worker_patch.start()
        self.addCleanup(self.worker_patch.stop)

    def upload(self, data=None, name="document.png", mime="image/png", **extra):
        file = SimpleUploadedFile(name, image_bytes() if data is None else data, content_type=mime)
        return self.client.post("/api/documents/analyze", {"file": file, **extra}, format="multipart")

    def test_valid_japanese_image_all_formats(self):
        for format, ext, mime in [("JPEG", "jpg", "image/jpeg"), ("JPEG", "jpeg", "image/jpeg"),
                                  ("PNG", "png", "image/png"), ("WEBP", "webp", "image/webp")]:
            with self.subTest(format=format, ext=ext):
                response = self.upload(image_bytes(format), "test." + ext, mime)
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertEqual(result["source"], "deterministic")
                self.assertEqual(result["extractionMethod"], "paddleocr")
                self.assertEqual(result["primaryDeadline"], "2026-11-02")
                self.assertEqual(result["deadline"], result["primaryDeadline"])
                self.assertEqual(result["primaryAmount"], 18000)
                self.assertIsNone(result["urgency"])
                self.assertIsNone(result["relatedGuide"])
                self.assertEqual(response["Cache-Control"], "no-store")

    def test_scanned_pdf_preserves_pages(self):
        response = self.upload(pdf_bytes(scanned=True, pages=2), "scan.pdf", "application/pdf")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["extractionMethod"], "paddleocr")
        self.assertEqual({e["page"] for e in result["evidence"]}, {1, 2})
        self.assertEqual(self.worker.predict.call_count, 2)
        self.assertTrue(all(p["coordinateSystem"] == "rendered_pixels" for p in result["pages"]))

    def test_embedded_japanese_pdf_skips_ocr(self):
        response = self.upload(pdf_bytes(pages=2), "text.pdf", "application/pdf")
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json()
        self.worker.predict.assert_not_called()
        self.assertEqual(result["extractionMethod"], "pdf_embedded_text")
        self.assertEqual(result["primaryDeadline"], "2026-11-02")
        self.assertEqual(result["primaryAmount"], 18000)
        self.assertEqual({e["page"] for e in result["evidence"]}, {1, 2})
        self.assertTrue(all(e["confidence"] is None for e in result["evidence"]))
        self.assertTrue(all(f["ocrConfidence"] is None for f in result["deadlines"] + result["amounts"]))
        self.assertTrue(all(p["coordinateSystem"] == "pdf_points" for p in result["pages"]))

    def test_unsupported_contents_not_trusted_by_filename(self):
        response = self.upload(b"not an image", "picture.jpg", "image/jpeg")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "UNSUPPORTED_FILE_TYPE")
        self.worker.predict.assert_not_called()

    def test_actual_contents_determine_format(self):
        response = self.upload(image_bytes(), "unrelated.pdf", "application/octet-stream")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["documentType"])

    def test_jpeg_mpo_primary_frame_with_explicit_warning(self):
        with BytesIO() as output, Image.new("RGB", (300,180), "white") as first, Image.new("RGB", (100,60), "gray") as second:
            first.save(output, format="MPO", save_all=True, append_images=[second])
            response = self.upload(output.getvalue(), "image.jpg", "image/jpeg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pages"][0]["auxiliaryFramesSkipped"], 1)
        self.assertTrue(any("primary image" in w for w in response.json()["warnings"]))
        self.worker.predict.assert_called_once()

    def test_empty_upload(self):
        response = self.upload(b"")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "EMPTY_FILE")

    def test_missing_file_and_text_only_do_not_call_legacy(self):
        with patch("services.documentAnalysis.analyzer.analyze_document_text", side_effect=AssertionError("Legacy invoked")):
            for payload in ({}, {"text": "納期限 2026/11/2"}):
                response = self.client.post("/api/documents/analyze", payload, format="json")
                self.assertEqual(response.status_code, 400)
        self.worker.predict.assert_not_called()

    def test_corrupted_image(self):
        response = self.upload(b"\x89PNG\r\n\x1a\ncorrupted")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_DOCUMENT")

    def test_corrupted_pdf(self):
        response = self.upload(b"%PDF-1.7 broken", "broken.pdf", "application/pdf")
        self.assertEqual(response.status_code, 400)

    def test_mime_spoofing(self):
        response = self.upload(image_bytes(), "a.pdf", "application/pdf")
        self.assertEqual(response.status_code, 400)
        self.worker.predict.assert_not_called()

    def test_ocr_failure_has_safe_message(self):
        self.worker.predict.side_effect = RuntimeError("PRIVATE_NAME SECRET_ACCOUNT trace")
        response = self.upload()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("PRIVATE_NAME", response.content.decode())
        self.assertNotIn("trace", response.content.decode())

    def test_known_ocr_failure(self):
        self.worker.predict.side_effect = DocumentProcessingError()
        response = self.upload()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "DOCUMENT_UNREADABLE")

    def test_missing_deadline(self):
        self.worker.predict.return_value = [page(("納付額 18000円", 0, 0, 240, 20))]
        result = self.upload().json()
        self.assertIsNone(result["deadline"])
        self.assertEqual(result["deadlines"], [])
        self.assertEqual(result["primaryAmount"], 18000)

    def test_missing_amount(self):
        self.worker.predict.return_value = [page(("提出期限 2026/11/2", 0, 0, 240, 20))]
        result = self.upload().json()
        self.assertIsNone(result["primaryAmount"])
        self.assertEqual(result["amounts"], [])

    def test_multiple_dates_roles_preserved(self):
        self.worker.predict.return_value = [page(("発行日 2026/01/01", 0, 0, 240, 20),
            ("納期限 2026/11/2", 0, 80, 240, 100), ("利用期限 2027/11/2", 0, 160, 240, 180))]
        result = self.upload().json()
        self.assertEqual(result["deadline"], "2026-11-02")
        self.assertEqual({d["kind"] for d in result["deadlines"]}, {"payment", "usage_expiration"})

    def test_duplicate_amounts_not_summed(self):
        self.worker.predict.return_value = [page(*[("納付額 18000円", 0, y, 240, y+20) for y in (0, 80, 160)])]
        result = self.upload().json()
        self.assertEqual(result["primaryAmount"], 18000)
        self.assertEqual(result["amounts"][0]["occurrences"], 3)

    def test_verified_amount_retained_when_primary_is_null(self):
        self.worker.predict.return_value = [page(("納付額 18000円", 0, 0, 240, 20), ("合計金額 不明", 0, 100, 240, 120))]
        result = self.upload().json()
        self.assertEqual(result["extractionStatus"], "partial")
        self.assertIsNone(result["primaryAmount"])
        self.assertTrue(any(a["status"] == "verified" and a["value"] == 18000 for a in result["amounts"]))

    def test_english_json_preserves_japanese_evidence(self):
        result = self.upload().json()
        self.assertTrue(any("納期限" in e["text"] for e in result["evidence"]))
        result["evidence"] = []
        self.assertFalse(any('\u3040' <= c <= '\u9fff' for c in json.dumps(result, ensure_ascii=False)))

    @override_settings(STORE_EXTRACTED_TEXT=True)
    def test_no_sensitive_storage_or_logging_even_with_legacy_retention_enabled(self):
        self.worker.predict.return_value = [page(("PRIVATE_NAME SECRET_ACCOUNT", 0, 0, 240, 20))]
        with self.assertNoLogs(level="WARNING"), patch.dict(os.environ, {"STORE_EXTRACTED_TEXT": "true"}):
            response = self.upload(name="PRIVATE_NAME.png")
        self.assertEqual(response.status_code, 200)
        self.assertIn("PRIVATE_NAME", response.json()["evidence"][0]["text"])
        # No DB access is permitted by SimpleTestCase. This includes summaries.

    def test_user_hints_and_pasted_text_cannot_inject_facts(self):
        response = self.upload(documentTypeHint="住民税", text="納期限 2030/1/1 納付額 999999円")
        result = response.json()
        self.assertIsNone(result["documentType"])
        self.assertEqual(result["primaryAmount"], 18000)
        self.assertEqual(result["primaryDeadline"], "2026-11-02")

    def test_page_and_dimension_limits(self):
        response = self.upload(pdf_bytes(pages=6), "too-many.pdf", "application/pdf")
        self.assertEqual(response.status_code, 413)
        self.worker.limits = DocumentLimits(max_dimension=100)
        response = self.upload()
        self.assertEqual(response.status_code, 413)
        self.worker.predict.assert_not_called()

    @override_settings(DOCUMENT_ANALYSIS_LIMITS={"max_file_bytes": 100})
    def test_streaming_upload_limit(self):
        response = self.upload(image_bytes() + b"x"*1000)
        self.assertEqual(response.status_code, 413)
        self.worker.predict.assert_not_called()

    def test_content_length_limit_before_processing(self):
        response = self.client.generic("POST", "/api/documents/analyze", b"x", content_type="application/octet-stream",
                                       CONTENT_LENGTH=str(11 * 1024**2))
        self.assertEqual(response.status_code, 413)

    def test_worker_timeout_and_busy_errors(self):
        for error, status in [(ProcessingTimeout(), 504), (WorkerBusy(), 503)]:
            with patch.object(self.worker, "analyze", side_effect=error):
                response = self.upload()
                self.assertEqual(response.status_code, status)

    @override_settings(DOCUMENT_ANALYSIS_RATE="1/min")
    def test_rate_limit(self):
        self.assertEqual(self.upload().status_code, 200)
        file = SimpleUploadedFile("a.png", image_bytes(), content_type="image/png")
        response = self.client.post("/api/documents/analyze", {"file": file}, format="multipart", HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_malformed_result_rejected_without_validation_data_leak(self):
        with patch.object(self.worker, "analyze", return_value={"PRIVATE_NAME": "SECRET_ACCOUNT"}):
            response = self.upload()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("SECRET_ACCOUNT", response.content.decode())

    def test_unsupported_request_type(self):
        response = self.client.generic("POST", "/api/documents/analyze", b"raw", content_type="text/plain")
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["code"], "UNSUPPORTED_REQUEST_TYPE")

    def test_no_django_temporary_upload_files(self):
        with patch("django.core.files.uploadhandler.TemporaryUploadedFile", side_effect=AssertionError("Temporary upload written")):
            self.assertEqual(self.upload().status_code, 200)

    def test_ocr_box_and_character_limits(self):
        self.worker.limits = DocumentLimits(max_boxes=1)
        self.assertEqual(self.upload().status_code, 413)
        self.worker.limits = DocumentLimits(max_characters=2)
        self.assertEqual(self.upload(pdf_bytes(), "text.pdf", "application/pdf").status_code, 413)

    def test_mixed_pdf_methods_and_rotated_pages(self):
        import pypdfium2 as pdfium
        output = BytesIO()
        with pdfium.PdfDocument(pdf_bytes()) as text, pdfium.PdfDocument(pdf_bytes(scanned=True)) as scanned:
            text.import_pages(scanned)
            text.save(output)
        response = self.upload(output.getvalue(), "mixed.pdf", "application/pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["extractionMethod"], "mixed")
        self.assertEqual([p["method"] for p in response.json()["pages"]], ["pdf_embedded_text", "paddleocr"])
        self.worker.predict.reset_mock()
        response = self.upload(pdf_bytes(rotated=True), "rotated.pdf", "application/pdf")
        self.assertEqual(response.status_code, 200)
        self.worker.predict.assert_called_once()

    def test_private_test_file_is_not_publicly_served(self):
        self.assertEqual(self.client.get("/test_documents/sample.jpg").status_code, 404)

    def test_health_route_preserved(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
