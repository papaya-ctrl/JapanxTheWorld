"""Bounded, atomic fixed-window limits shared by local processes (no raw IDs)."""
import hashlib
import hmac
import math
import os
from pathlib import Path
import sqlite3
import stat
import time
from django.conf import settings


class RateStoreUnavailable(Exception):
    pass


def consume(scope, identity, rate, *, now=None):
    count, period = rate.split('/')
    maximum = int(count)
    seconds = {'sec': 1, 'min': 60, 'hour': 3600, 'day': 86400}[period]
    now = time.time() if now is None else now
    window = int(now // seconds) * seconds
    expires = window + seconds
    key = hmac.new(settings.SECRET_KEY.encode(), f'{scope}:{identity}'.encode(), hashlib.sha256).hexdigest()
    path = Path(settings.RATE_LIMIT_DB)
    connection = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = path.parent.stat()
        if directory.st_mode & 0o077 or directory.st_uid != os.getuid():
            raise RateStoreUnavailable()
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise RateStoreUnavailable()
        finally:
            os.close(descriptor)
        connection = sqlite3.connect(path, timeout=.05)
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('CREATE TABLE IF NOT EXISTS buckets (key TEXT PRIMARY KEY, expires INTEGER NOT NULL, count INTEGER NOT NULL)')
        connection.execute('CREATE INDEX IF NOT EXISTS buckets_expiry ON buckets(expires)')
        connection.execute('DELETE FROM buckets WHERE expires <= ?', (int(now),))
        row = connection.execute('SELECT count FROM buckets WHERE key = ?', (key,)).fetchone()
        if row and row[0] >= maximum:
            connection.rollback()
            return max(1, math.ceil(expires - now))
        if not row and connection.execute('SELECT count(*) FROM buckets').fetchone()[0] >= settings.RATE_LIMIT_MAX_BUCKETS:
            raise RateStoreUnavailable()
        connection.execute('INSERT INTO buckets VALUES (?, ?, 1) ON CONFLICT(key) DO UPDATE SET count=count+1', (key, expires))
        connection.commit()
        return 0
    except (OSError, sqlite3.Error):
        raise RateStoreUnavailable() from None
    finally:
        if connection is not None:
            connection.close()
