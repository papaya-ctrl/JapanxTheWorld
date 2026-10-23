"""One lazy, reusable OCR subprocess per Django process, with hard cancellation.

All native decoding and inference runs in the child. A single-flight lock avoids
concurrent access to Paddle/PDFium and unbounded request queues. Timeouts/RSS
breaches kill the worker, so a hung native call cannot continue in a thread.
"""
import atexit
import multiprocessing
import os
import threading
import time

from .errors import (DocumentProcessingError, ERROR_TYPES, ModelsUnavailable,
                     ProcessingMemoryExceeded, ProcessingTimeout, WorkerBusy)
from .limits import DocumentLimits


def _worker_main(connection, limits, model_root, config=None, lock_path=None):
    # Third-party libraries may print input text or paths in exceptions. Suppress
    # child stdout/stderr at FD level; only allowlisted error codes cross IPC.
    with open(os.devnull, "w") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    from .lease import exclusive_worker_lease
    try:
        with exclusive_worker_lease(lock_path):
            connection.send(("ready", None))
            _worker_loop(connection, limits, model_root, config)
    except DocumentProcessingError as exc:
        try: connection.send(("error", exc.code))
        except (OSError, BrokenPipeError): pass
    finally:
        connection.close()


def _worker_loop(connection, limits, model_root, config):
    from .document_adapter import analyze_document_bytes
    from .paddle_extractor import create_paddle_ocr
    model = None
    requests = 0
    try:
        while requests < limits.max_worker_requests and connection.poll(limits.worker_idle_seconds):
            data, kind = connection.recv()
            timings = {"modelInitSeconds": 0., "inferenceSeconds": 0., "inferenceCalls": 0}
            def predict(image):
                nonlocal model
                if model is None:
                    begin = time.monotonic()
                    try:
                        model = create_paddle_ocr(model_root) if config is None else create_paddle_ocr(model_root, config=config)
                    except Exception:
                        raise ModelsUnavailable() from None
                    timings["modelInitSeconds"] = time.monotonic() - begin
                begin = time.monotonic()
                try:
                    output = list(model.predict(image))
                except Exception:
                    raise DocumentProcessingError() from None
                timings["inferenceSeconds"] += time.monotonic() - begin
                timings["inferenceCalls"] += 1
                return output
            try:
                result = analyze_document_bytes(data, kind, predict, limits)
                connection.send(("metrics", timings))
                connection.send(("ok", result))
            except DocumentProcessingError as exc:
                connection.send(("error", exc.code))
            except Exception:
                connection.send(("error", DocumentProcessingError.code))
            finally:
                requests += 1
                data = result = None
    except (EOFError, BrokenPipeError, OSError):
        pass


class LocalDocumentWorker:
    def __init__(self, limits=None, model_root=None, *, target=_worker_main, config=None, lock_path=None):
        self.limits = limits or DocumentLimits()
        self.model_root = model_root
        self._target = target
        self.config, self.lock_path = config, lock_path
        self._handshake = target is _worker_main
        self._ready = False
        self._completed = 0
        self._last_completed = None
        self.last_metrics = {}
        self._lock = threading.Lock()
        self._process = self._connection = None
        self.last_peak_rss_bytes = 0
        self.last_elapsed_seconds = 0

    def _start(self):
        if self._process is not None and self._process.is_alive():
            idle_margin = min(.25, self.limits.worker_idle_seconds / 4)
            retiring = (self._completed >= self.limits.max_worker_requests or
                        (self._last_completed is not None and
                         time.monotonic() - self._last_completed >= self.limits.worker_idle_seconds - idle_margin))
            if not retiring:
                return
        self._stop()
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        args = (child, self.limits, self.model_root)
        if self._handshake: args += (self.config, self.lock_path)
        process = context.Process(target=self._target, args=args,
                                  name="jxtw-document-worker", daemon=True)
        process.start()
        child.close()
        self._process, self._connection = process, parent
        self._ready = not self._handshake
        self._completed = 0
        self._last_completed = None

    def _stop(self):
        if self._connection is not None:
            self._connection.close()
        if self._process is not None:
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1)
                if self._process.is_alive():
                    self._process.kill()
                    self._process.join(timeout=1)
            else:
                self._process.join(timeout=1)
            self._process.close()
        self._connection = self._process = None
        self._ready = False

    def analyze(self, data, kind):
        import psutil

        if not self._lock.acquire(blocking=False):
            raise WorkerBusy()
        started = time.monotonic()
        self.last_peak_rss_bytes = 0
        self.last_metrics = {}
        try:
            self._start()
            sent = False
            monitor = psutil.Process(self._process.pid)
            while True:
                if time.monotonic() - started > self.limits.timeout_seconds:
                    self._stop()
                    raise ProcessingTimeout()
                try:
                    rss = monitor.memory_info().rss
                    self.last_peak_rss_bytes = max(self.last_peak_rss_bytes, rss)
                    if rss > self.limits.max_worker_rss_bytes or psutil.virtual_memory().available < self.limits.min_host_available_bytes:
                        self._stop()
                        raise ProcessingMemoryExceeded()
                except psutil.NoSuchProcess:
                    raise DocumentProcessingError() from None
                if self._ready and not sent:
                    self._connection.send((data, kind))
                    sent = True
                if self._connection.poll(.05):
                    outcome, payload = self._connection.recv()
                    if outcome == "ready":
                        self._ready = True
                        continue
                    if outcome == "metrics":
                        self.last_metrics = payload
                        continue
                    self._completed += 1
                    self._last_completed = time.monotonic()
                    if outcome == "ok":
                        self.last_metrics["rssAfterBytes"] = rss
                        return payload
                    error = ERROR_TYPES.get(payload, DocumentProcessingError)()
                    if not sent: self._stop()
                    raise error
                if not self._process.is_alive():
                    self._stop()
                    raise DocumentProcessingError()
        except (EOFError, BrokenPipeError, OSError):
            self._stop()
            raise DocumentProcessingError() from None
        finally:
            self.last_elapsed_seconds = time.monotonic() - started
            self._lock.release()
            import logging
            logging.getLogger('operations').info('ocr', extra={'event':'ocr', 'route':'ocr',
                'durationSeconds':self.last_elapsed_seconds, 'peakRssMiB':self.last_peak_rss_bytes/1024**2})

    def close(self):
        with self._lock:
            self._stop()


_worker = None
_worker_lock = threading.Lock()


def get_document_worker():
    global _worker
    if _worker is None:
        with _worker_lock:
            if _worker is None:
                from django.conf import settings
                limits = DocumentLimits(**getattr(settings, "DOCUMENT_ANALYSIS_LIMITS", {}))
                from .configuration import OCRConfiguration
                config = OCRConfiguration(**getattr(settings, "DOCUMENT_OCR_CONFIGURATION", {}))
                _worker = LocalDocumentWorker(limits, getattr(settings, "DOCUMENT_OCR_MODEL_ROOT", None),
                    config=config, lock_path=getattr(settings, "DOCUMENT_OCR_LOCK_PATH", None))
                atexit.register(_worker.close)
    return _worker
