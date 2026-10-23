"""Supervision tests use tiny spawned stubs, never OCR model downloads."""
import subprocess
import sys
import threading
import unittest
from io import BytesIO
from pathlib import Path

from services.ocr.worker import LocalDocumentWorker, _worker_main
from services.ocr.errors import ProcessingMemoryExceeded, ProcessingTimeout, WorkerBusy
from services.ocr.limits import DocumentLimits


def echo_worker(connection, limits, model_root):
    jobs = 0
    try:
        while True:
            connection.recv()
            jobs += 1
            connection.send(("ok", {"jobs": jobs}))
    except EOFError:
        pass


def hung_worker(connection, limits, model_root):
    connection.recv()
    threading.Event().wait(30)


def fake_model_worker(connection, limits, model_root):
    from unittest.mock import patch

    class Predictor:
        def __init__(self):
            self.calls = 0

        def predict(self, image):
            self.calls += 1
            # Deliberate third-party privacy leak attempt; FD redirection must
            # prevent these synthetic strings reaching the web process logs.
            print("SENSITIVE_OCR_MARKER", flush=True)
            print("SENSITIVE_OCR_MARKER", file=sys.stderr, flush=True)
            return [{"rec_texts": [f"納付額 {10000 + self.calls}円"], "rec_scores": [.99],
                     "rec_boxes": [[0, 0, 240, 20]]}]

    with patch("services.ocr.paddle_extractor.create_paddle_ocr", side_effect=lambda root: Predictor()):
        _worker_main(connection, limits, model_root)


class WorkerTests(unittest.TestCase):
    def test_one_process_reused_across_jobs(self):
        worker = LocalDocumentWorker(target=echo_worker, limits=DocumentLimits(timeout_seconds=5))
        try:
            self.assertEqual(worker.analyze(b"a", "png"), {"jobs": 1})
            pid = worker._process.pid
            self.assertEqual(worker.analyze(b"b", "png"), {"jobs": 2})
            self.assertEqual(worker._process.pid, pid)
        finally:
            worker.close()

    def test_lazy_model_instance_reused(self):
        from PIL import Image
        output = BytesIO()
        Image.new("RGB", (300, 180), "white").save(output, format="PNG")
        worker = LocalDocumentWorker(target=fake_model_worker, limits=DocumentLimits(timeout_seconds=10))
        try:
            self.assertIsNone(worker._process)
            self.assertEqual(worker.analyze(output.getvalue(), "png")["primaryAmount"], 10001)
            self.assertEqual(worker.analyze(output.getvalue(), "png")["primaryAmount"], 10002)
        finally:
            worker.close()

    def test_timeout_terminates_and_allows_next_request(self):
        worker = LocalDocumentWorker(target=hung_worker, limits=DocumentLimits(timeout_seconds=.3))
        try:
            with self.assertRaises(ProcessingTimeout):
                worker.analyze(b"x", "png")
            self.assertIsNone(worker._process)
            worker._target = echo_worker
            worker.limits = DocumentLimits(timeout_seconds=5)
            self.assertEqual(worker.analyze(b"x", "png"), {"jobs": 1})
        finally:
            worker.close()

    def test_memory_limit_terminates_worker(self):
        worker = LocalDocumentWorker(target=hung_worker,
                                     limits=DocumentLimits(timeout_seconds=5, max_worker_rss_bytes=1))
        try:
            with self.assertRaises(ProcessingMemoryExceeded):
                worker.analyze(b"x", "png")
            self.assertIsNone(worker._process)
        finally:
            worker.close()

    def test_busy_worker_does_not_queue_unbounded_requests(self):
        worker = LocalDocumentWorker(target=echo_worker)
        worker._lock.acquire()
        try:
            with self.assertRaises(WorkerBusy):
                worker.analyze(b"x", "png")
        finally:
            worker._lock.release()
            worker.close()

    def test_native_stdout_and_stderr_do_not_leak_ocr(self):
        script = '''
from io import BytesIO
from PIL import Image
from tests.test_document_worker import fake_model_worker
from services.ocr.worker import LocalDocumentWorker
output = BytesIO()
Image.new('RGB', (300,180), 'white').save(output, format='PNG')
worker = LocalDocumentWorker(target=fake_model_worker)
try:
    assert worker.analyze(output.getvalue(), 'png')['primaryAmount'] == 10001
finally:
    worker.close()
print('OK')
'''
        process = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                                 cwd=Path(__file__).resolve().parents[1], timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn("SENSITIVE_OCR_MARKER", process.stdout + process.stderr)
        self.assertIn("OK", process.stdout)

    def test_django_upload_never_imports_paid_or_template_analyzers(self):
        script = '''
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['OPENAI_API_KEY'] = 'dummy-key-must-never-be-used'
class Block:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'openai', 'anthropic', 'ollama', 'google.generativeai'} or fullname.startswith(('services.ai', 'services.classification', 'services.trustedContent.matcher', 'google.generativeai', 'google.genai')):
            raise AssertionError('Forbidden upload dependency: ' + fullname)
sys.meta_path.insert(0, Block())
from unittest.mock import patch
from django.test import override_settings
from tests.test_document_uploads import InProcessWorker, image_bytes
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
with override_settings(ALLOWED_HOSTS=['testserver']), patch('services.documentAnalysis.upload.get_document_worker', return_value=InProcessWorker()):
    response = APIClient().post('/api/documents/analyze', {'file':SimpleUploadedFile('file.png', image_bytes(), content_type='image/png')}, format='multipart')
assert response.status_code == 200, response.status_code
assert response.json()['source'] == 'deterministic'
'''
        process = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                                 cwd=Path(__file__).resolve().parents[1], timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
