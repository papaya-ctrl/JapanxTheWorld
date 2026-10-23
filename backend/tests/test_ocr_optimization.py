"""Regression coverage for CPU settings, pixel lifetimes, and host-wide leasing."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from services.ocr.configuration import OCRConfiguration
from services.ocr.document_adapter import extract_document
from services.ocr.errors import ModelsUnavailable, WorkerBusy
from services.ocr.lease import exclusive_worker_lease
from services.ocr.limits import DocumentLimits
from services.ocr.paddle_extractor import create_paddle_ocr
from services.ocr.worker import LocalDocumentWorker, _worker_main


def leased_fake_worker(connection, limits, lock_path):
    class Model:
        def __init__(self):self.calls=0
        def predict(self, image):
            self.calls+=1
            return [{"rec_texts":[f"納付額 {self.calls}円"],"rec_scores":[.99],"rec_boxes":[[0,0,60,20]]}]
    with patch("services.ocr.paddle_extractor.create_paddle_ocr",side_effect=lambda root:Model()):
        _worker_main(connection,limits,None,lock_path=lock_path)


def pixels():
    output=BytesIO()
    with Image.new("RGB",(60,30),(10,20,30)) as image:image.save(output,format="PNG")
    return output.getvalue()


class OptimizationTests(unittest.TestCase):
    def test_default_model_settings_are_explicit_cpu_and_japanese_capable(self):
        factory=Mock()
        with TemporaryDirectory() as directory:
            for name in ("PP-OCRv6_medium_det","PP-OCRv6_medium_rec"):
                path=Path(directory)/name;path.mkdir()
                (path/"inference.yml").touch();(path/"inference.pdiparams").touch()
            with patch.dict(sys.modules,{"paddleocr":SimpleNamespace(PaddleOCR=factory)}):
                create_paddle_ocr(Path(directory))
        kwargs=factory.call_args.kwargs
        self.assertEqual(kwargs["text_recognition_batch_size"],1)
        self.assertEqual(kwargs["text_det_limit_side_len"],1600)
        self.assertEqual(kwargs["cpu_threads"],4)
        self.assertEqual(kwargs["device"],"cpu")
        self.assertEqual(kwargs["engine"],"paddle_static")
        self.assertFalse(kwargs["enable_mkldnn"])

    def test_missing_weights_never_trigger_download_or_factory_initialization(self):
        with TemporaryDirectory() as directory,self.assertRaises(FileNotFoundError):
            create_paddle_ocr(Path(directory))
        for kwargs in ({"recognition_size":"tiny"},{"cpu_threads":100},{"detector_side":200},{"engine":"transformers"}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):OCRConfiguration(**kwargs)

    def test_single_packed_bgr_buffer_preserves_pixels_and_geometry(self):
        def predict(image):
            self.assertEqual(image.shape,(30,60,3))
            self.assertEqual(image[0,0].tolist(),[30,20,10])
            self.assertFalse(image.flags.writeable)
            return [{"rec_texts":["納付額1円"],"rec_scores":[.99],"rec_boxes":[[0,0,60,20]]}]
        records,pages=extract_document(pixels(),"png",predict,DocumentLimits())
        self.assertEqual(records[0]["rec_boxes"],[[0,0,60,20]])
        self.assertEqual((pages[0]["width"],pages[0]["height"]),(60,30))

    def test_lease_is_exclusive_and_released_without_deleting_inode(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/"worker.lock"
            with exclusive_worker_lease(path):
                with self.assertRaises(WorkerBusy):
                    with exclusive_worker_lease(path):pass
            with exclusive_worker_lease(path):pass
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(path.stat().st_size,0)

    def test_two_processes_cannot_load_models_at_the_same_time(self):
        with TemporaryDirectory() as directory:
            path=str(Path(directory)/"worker.lock")
            first=LocalDocumentWorker(target=leased_fake_worker,model_root=path)
            second=LocalDocumentWorker(target=leased_fake_worker,model_root=path)
            try:
                self.assertEqual(first.analyze(pixels(),"png")["primaryAmount"],1)
                with self.assertRaises(WorkerBusy):second.analyze(pixels(),"png")
                self.assertEqual(first.analyze(pixels(),"png")["primaryAmount"],2)
                self.assertEqual(first.last_metrics["modelInitSeconds"],0)
            finally:first.close();second.close()

    def test_idle_worker_releases_its_lease_and_restarts_on_demand(self):
        with TemporaryDirectory() as directory:
            worker=LocalDocumentWorker(target=leased_fake_worker,model_root=str(Path(directory)/"worker.lock"),
                                       limits=DocumentLimits(worker_idle_seconds=.2))
            try:
                worker.analyze(pixels(),"png")
                worker._process.join(timeout=3)
                self.assertFalse(worker._process.is_alive())
                self.assertEqual(worker.analyze(pixels(),"png")["primaryAmount"],1)
            finally:worker.close()

    def test_request_count_recycling_occurs_only_between_jobs(self):
        with TemporaryDirectory() as directory:
            worker=LocalDocumentWorker(target=leased_fake_worker,model_root=str(Path(directory)/"worker.lock"),
                                       limits=DocumentLimits(max_worker_requests=1))
            try:
                self.assertEqual(worker.analyze(pixels(),"png")["primaryAmount"],1)
                # A new request may arrive before the retiring child has exited.
                self.assertEqual(worker.analyze(pixels(),"png")["primaryAmount"],1)
            finally:worker.close()
