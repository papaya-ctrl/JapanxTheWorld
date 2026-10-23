"""Portable host/cgroup memory observations. Unavailable measurements stay null."""
from pathlib import Path
import platform
import psutil


def _integer(path):
    try:
        with path.open() as file:value=file.read(129).strip()
        if len(value)>128:return None
        return int(value) if value.isdecimal() else None
    except (OSError, ValueError):
        return None


def cgroup_memory(root=Path('/sys/fs/cgroup'), membership=Path('/proc/self/cgroup')):
    if not root.is_dir():
        return {'limitBytes': None, 'currentBytes': None, 'remainingBytes': None, 'version': None}
    candidates = [root]
    try:
        for line in membership.read_text().splitlines()[:32]:
            parts = line.split(':', 2)
            if len(parts) != 3 or '..' in Path(parts[2]).parts:
                continue
            relative = parts[2].lstrip('/')
            if parts[0] == '0' and not parts[1]:
                path = root / relative
            elif 'memory' in parts[1].split(','):
                path = root / 'memory' / relative
            else:
                continue
            for _ in range(32):
                if not path.is_relative_to(root): break
                candidates.append(path)
                if path == root: break
                path = path.parent
    except OSError:
        pass
    observations = []
    for path in set(candidates):
        for version, maximum, current in [(2, 'memory.max', 'memory.current'),
                                           (1, 'memory.limit_in_bytes', 'memory.usage_in_bytes')]:
            limit, used = _integer(path / maximum), _integer(path / current)
            if limit is not None and used is not None and 0 < limit < 2**60:
                observations.append({'limitBytes': limit, 'currentBytes': used,
                                     'remainingBytes': max(0, limit-used), 'version': version})
    return min(observations, key=lambda item: item['remainingBytes']) if observations else {
        'limitBytes': None, 'currentBytes': None, 'remainingBytes': None, 'version': None}


def available_memory_bytes():
    host = psutil.virtual_memory().available
    remaining = cgroup_memory()['remainingBytes'] if platform.system() == 'Linux' else None
    return min(host, remaining) if remaining is not None else host
