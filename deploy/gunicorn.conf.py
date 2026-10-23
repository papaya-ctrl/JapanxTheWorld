"""One application process; native OCR is a separately supervised lazy child."""
import os
from pathlib import Path
import re

project = Path(__file__).resolve().parent.parent
pythonpath = str(project / 'backend')
chdir = pythonpath
if os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings_production') != 'config.settings_production':
    raise RuntimeError('The production server requires config.settings_production.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_production'
os.umask(0o077)
bind = os.environ.get('JXTW_BIND', '127.0.0.1:8000')
if not re.fullmatch(r'127\.0\.0\.1:[0-9]{1,5}', bind):
    raise RuntimeError('Bind the application to loopback behind the trusted proxy.')
workers = 1
worker_class = 'gthread'
threads = 4
worker_connections = 4
backlog = 8
preload_app = False
max_requests = 0
keepalive = 2
timeout = 150
graceful_timeout = 150
limit_request_line = 2048
limit_request_fields = 32
limit_request_field_size = 4094
forwarded_allow_ips = '127.0.0.1,::1'
accesslog = None  # Operations middleware emits fixed route categories, not paths/IPs.
errorlog = '-'
loglevel = 'info'
logger_class = 'security.server_logging.PrivateGunicornLogger'
capture_output = False


def worker_exit(server, worker):
    from services.ocr import worker as module
    if module._worker is not None:
        module._worker.close()
