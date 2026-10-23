"""Host/user-wide model lease; no document contents or identifiers are written."""
from contextlib import contextmanager
import os
from pathlib import Path

from .errors import ModelsUnavailable, WorkerBusy


@contextmanager
def exclusive_worker_lease(path=None):
    import fcntl
    path = Path(path) if path else Path.home()/".cache/japanxtheworld/ocr-worker.lock"
    descriptor = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os,"O_NOFOLLOW",0), 0o600)
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise WorkerBusy() from None
        yield
    except (WorkerBusy, ModelsUnavailable):
        raise
    except OSError:
        raise ModelsUnavailable() from None
    finally:
        if descriptor is not None:
            # Never unlink: another process may already be waiting on this inode.
            os.close(descriptor)
