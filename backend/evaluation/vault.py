"""Owner-only evaluation artifacts; optional authenticated encryption for evidence."""
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def private_path(value):
    path=Path(value).expanduser().resolve()
    if path.is_relative_to(ROOT):raise ValueError('Keep private evaluation artifacts outside the checkout.')
    return path


def write_private(path,data):
    path=private_path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.parent.stat().st_mode&0o077:raise ValueError('Artifact directories must be owner-only (0700).')
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as file:file.write(data)


def key_bytes(path,output=None):
    path=private_path(path)
    if path.stat().st_mode&0o077:raise ValueError('Evaluation encryption keys must be owner-only (0600).')
    if output and path.is_relative_to(private_path(output)):raise ValueError('Keep the recovery key outside the output directory.')
    return path.read_bytes().strip()


def save_json(path,value,key=None):
    data=json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2).encode()
    if key:
        from cryptography.fernet import Fernet
        data=Fernet(key_bytes(key,Path(path).parent)).encrypt(data)
    write_private(path,data)


def read_json(path,key=None):
    path=private_path(path)
    if path.stat().st_size>16*1024**2:raise ValueError('Private result exceeds the bounded limit.')
    data=path.read_bytes()
    if key:
        from cryptography.fernet import Fernet
        data=Fernet(key_bytes(key)).decrypt(data)
    return json.loads(data)
