"""Authenticated encrypted snapshots of disposable staging databases only.

The envelope contains SQLite bytes, not a directory archive. Private keys,
configuration, model caches, document files and logs cannot be swept into it.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from cryptography.fernet import Fernet, InvalidToken

MAXIMUM=128*1024**2


def _scope(path,root):
    path=Path(path).expanduser().resolve();root=Path(root).expanduser().resolve()
    if json.loads((root/'manifest.json').read_text()).get('purpose')!='disposable_staging_only' or not path.is_relative_to(root):
        raise ValueError('Only explicitly prepared disposable staging data is allowed.')
    return path


def _publish(data,target):
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if target.parent.stat().st_mode&0o077:raise ValueError('Use a private output directory (0700).')
    if target.exists() or target.is_symlink():raise FileExistsError('Refusing to replace an existing backup or database.')
    fd,name=tempfile.mkstemp(dir=target.parent,prefix='snapshot-')
    try:
        with os.fdopen(fd,'wb') as file:file.write(data);file.flush();os.fsync(file.fileno())
        os.link(name,target)
    finally:Path(name).unlink(missing_ok=True)


def seal(source,destination,keyfile,root):
    source=_scope(source,root);destination=_scope(destination,root);keyfile=_scope(keyfile,root)
    if keyfile.is_relative_to(destination.parent):raise ValueError('Keep the encryption key outside the backup directory.')
    if keyfile.stat().st_mode&0o077:raise ValueError('Encryption keys must be owner-only (0600).')
    if source.stat().st_size>MAXIMUM:raise ValueError('Use a streaming backup tool for databases over 128 MiB.')
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(dir=destination.parent,prefix='sqlite-snapshot-');os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as live,closing(sqlite3.connect(name)) as snapshot:
            live.backup(snapshot)
            snapshot.execute('PRAGMA journal_mode=DELETE')
            if snapshot.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Snapshot integrity check failed.')
        data=Path(name).read_bytes()
        if len(data)>MAXIMUM:raise ValueError('Snapshot exceeds the bounded staging limit.')
        _publish(Fernet(keyfile.read_bytes().strip()).encrypt(data),destination)
    finally:Path(name).unlink(missing_ok=True)


def restore(source,destination,keyfile,root):
    source=_scope(source,root);destination=_scope(destination,root);keyfile=_scope(keyfile,root)
    if keyfile.stat().st_mode&0o077:raise ValueError('Encryption keys must be owner-only (0600).')
    if destination.exists() or destination.is_symlink():raise FileExistsError('Restore into a new file; preserve current data.')
    if source.stat().st_size>MAXIMUM*2:raise ValueError('Encrypted staging snapshot exceeds the bounded limit.')
    try:data=Fernet(keyfile.read_bytes().strip()).decrypt(source.read_bytes())
    except InvalidToken:raise ValueError('Snapshot authentication failed; no restore was published.') from None
    if not data.startswith(b'SQLite format 3\x00') or len(data)>MAXIMUM:raise ValueError('Unexpected snapshot format.')
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(dir=destination.parent,prefix='restore-check-');os.close(fd)
    try:
        Path(name).write_bytes(data)
        with closing(sqlite3.connect(Path(name).as_uri()+'?mode=ro',uri=True)) as database:
            if database.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Restored integrity check failed.')
        _publish(data,destination)
    finally:Path(name).unlink(missing_ok=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['seal','restore']);parser.add_argument('--stage',type=Path,required=True);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--key',type=Path,required=True);args=parser.parse_args()
    os.umask(0o077)
    (seal if args.action=='seal' else restore)(args.source,args.output,args.key,args.stage)
    print('Disposable staging snapshot operation completed and integrity verified. Existing files were not replaced.')
