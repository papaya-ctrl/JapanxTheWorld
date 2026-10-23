"""Export a consistent disposable SQLite snapshot, never a directory archive."""
import os
from contextlib import closing
from pathlib import Path
import re
import sqlite3
import sys
import tempfile


def snapshot_bytes(state,project):
    state=Path(state).resolve()
    if not re.fullmatch(r'jxtw-staging-[a-z0-9-]{6,32}',project) or (state/'.staging-project').read_text().strip()!=project:
        raise ValueError('Only marked disposable staging may be exported.')
    source=state/'app.sqlite3';maximum=128*1024**2
    if not source.is_file() or source.stat().st_size>maximum:raise ValueError('Use a bounded existing staging database.')
    fd,name=tempfile.mkstemp(dir=state/'tmp',prefix='export-');os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as live,closing(sqlite3.connect(name)) as snapshot:
            live.backup(snapshot)
            snapshot.execute('PRAGMA journal_mode=DELETE')
            if snapshot.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integrity check failed.')
        if Path(name).stat().st_size>maximum:raise ValueError('Snapshot exceeds bounded staging size.')
        return Path(name).read_bytes()
    finally:Path(name).unlink(missing_ok=True)


if __name__=='__main__':
    try:
        os.umask(0o077)
        data=snapshot_bytes(os.environ['DJANGO_STATE_DIR'],os.environ['STAGING_PROJECT'])
        sys.stdout.buffer.write(data)
    except Exception:
        print('Disposable staging snapshot export failed; no directory archive created.',file=sys.stderr)
        raise SystemExit(1) from None
