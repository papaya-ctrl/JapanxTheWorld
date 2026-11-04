"""Small, standard-library CI guards. Never reads documents, .env or local DBs."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit

GIB = 1024**3
PROJECT = Path(__file__).resolve().parents[1]
MARKER = 'jxtw-linux-ocr-synthetic-v1\n'


class GateError(Exception):
    pass


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')
    path.chmod(0o600)


def state_path(value):
    root = Path(value).expanduser().resolve()
    if root == Path('/') or root == Path.home() or root.is_relative_to(PROJECT):
        raise GateError('CI state must be a dedicated directory outside the checkout.')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise GateError('CI state must be owned by this user with mode 0700.')
    return root


def integer(path):
    try:
        value = path.read_text()[:128].strip()
        return int(value) if value.isdecimal() else None
    except OSError:
        return None


def cgroups(root=Path('/sys/fs/cgroup'), membership=Path('/proc/self/cgroup')):
    """Report leaf AND ancestor counters, including unbounded v2 cgroups."""
    paths = {root}
    try:
        for line in membership.read_text().splitlines():
            hierarchy, controllers, name = line.split(':', 2)
            if '..' in Path(name).parts:
                continue
            if hierarchy == '0' and not controllers:
                path = root / name.lstrip('/')
            elif 'memory' in controllers.split(','):
                path = root / 'memory' / name.lstrip('/')
            else:
                continue
            while path.is_relative_to(root):
                paths.add(path)
                if path == root:
                    break
                path = path.parent
    except (OSError, ValueError):
        pass
    rows = []
    for path in sorted(paths):
        for version, names in ((2, ('memory.max', 'memory.current', 'memory.peak')),
                               (1, ('memory.limit_in_bytes', 'memory.usage_in_bytes', 'memory.max_usage_in_bytes'))):
            if not (path / names[1]).is_file():
                continue
            limit = integer(path / names[0])
            if limit is not None and limit >= 2**60:
                limit = None
            rows.append({'version': version, 'limitBytes': limit,
                         'currentBytes': integer(path / names[1]),
                         'kernelPeakBytes': integer(path / names[2])})
    return rows


def memory_available(meminfo=Path('/proc/meminfo'), groups=None):
    values = {}
    for line in meminfo.read_text().splitlines():
        key, value = line.split(':', 1)
        values[key] = int(value.split()[0]) * 1024
    available = values['MemAvailable']
    for row in cgroups() if groups is None else groups:
        if row['limitBytes'] is not None and row['currentBytes'] is not None:
            available = min(available, max(0, row['limitBytes'] - row['currentBytes']))
    return values['MemTotal'], available


def preflight(state):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or sys.version_info[:2] != (3, 12):
        raise GateError('Requires native Ubuntu 24.04 x86_64 and Python 3.12.')
    groups = cgroups()
    total, available = memory_available(groups=groups)
    distribution = platform.freedesktop_os_release()
    flags = Path('/proc/cpuinfo').read_text().lower()
    cores = len(os.sched_getaffinity(0))
    data = {'os': distribution.get('PRETTY_NAME'), 'kernel': platform.release(),
            'architecture': platform.machine(), 'python': platform.python_version(),
            'logicalCpus': os.cpu_count(), 'availableCpus': cores,
            'totalRamBytes': total, 'effectiveAvailableRamBytes': available,
            'freeDiskBytes': shutil.disk_usage(state).free, 'cgroups': groups,
            'commit': os.environ.get('GITHUB_SHA'), 'runnerImage': os.environ.get('ImageVersion')}
    write_json(state / 'environment.json', data)
    print(json.dumps(data))
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or distribution.get('ID') != 'ubuntu' or distribution.get('VERSION_ID') != '24.04'
            or sys.version_info[:2] != (3, 12)):
        raise GateError('Requires native Ubuntu 24.04 x86_64 and Python 3.12.')
    if cores < 4 or not re.search(r'\bavx\b', flags):
        raise GateError('Requires four available CPUs and AVX for the CPU wheel.')
    if available < 8 * GIB or data['freeDiskBytes'] < 8 * GIB:
        raise GateError('Requires 8 GiB effective available RAM and 8 GiB free disk before installation.')


def gpu_package(name):
    name = re.sub(r'[-_.]+', '-', name.lower())
    return (name.startswith(('nvidia-', 'cuda-', 'cudnn', 'cupy', 'tensorrt', 'paddlepaddle-gpu',
                             'torch', 'triton', 'vllm', 'sglang', 'jax', 'tensorflow')))


def validate_plan(state):
    # pip is already present after setup-python; no bootstrap download is required.
    from pip._vendor.packaging.tags import sys_tags
    from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
    from pip._vendor.packaging.version import Version
    plan = json.loads((state / 'pip-plan.json').read_text())
    tags = set(sys_tags())
    rows = []
    installed = {}
    for item in plan['install']:
        name, version = item['metadata']['name'], item['metadata']['version']
        filename = Path(unquote(urlsplit(item['download_info']['url']).path)).name
        if gpu_package(name):
            raise GateError(f'Forbidden GPU/LLM dependency: {name}=={version}')
        if not filename.endswith('.whl'):
            raise GateError(f'No binary wheel in resolved plan: {name}=={version}')
        wheel_name, wheel_version, _, wheel_tags = parse_wheel_filename(filename)
        if canonicalize_name(name) != wheel_name or Version(version) != wheel_version or not wheel_tags & tags:
            raise GateError(f'Incompatible wheel: {filename}')
        sha = item['download_info'].get('archive_info', {}).get('hashes', {}).get('sha256')
        if not sha or not re.fullmatch('[a-f0-9]{64}', sha):
            raise GateError(f'Missing wheel SHA-256: {name}=={version}')
        rows.append({'name': name, 'version': version, 'wheel': filename, 'sha256': sha})
        installed[canonicalize_name(name)] = version
    # Ensure the project's pins were actually honored, including dev test utilities.
    for file in ('requirements.txt', 'requirements-dev.txt'):
        for line in (PROJECT / 'backend' / file).read_text().splitlines():
            if '==' in line and not line.startswith('#'):
                name, version = line.strip().split('==')
                if installed.get(canonicalize_name(name)) != version:
                    raise GateError(f'Pinned dependency absent or changed: {name}=={version}')
    write_json(state / 'wheels.json', rows)
    # Install the exact inspected wheels, hash-checked, with no second resolution.
    (state / 'resolved.txt').write_text(''.join(
        f"{row['name']}=={row['version']} --hash=sha256:{row['sha256']}\n" for row in rows))
    print('Compatible binary CPU dependency plan:', len(rows), 'wheels')


def group_rss(group):
    total = 0
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            tail = path.read_text().rsplit(')', 1)[1].split()
            if int(tail[2]) == group:
                total += int(tail[21]) * os.sysconf('SC_PAGE_SIZE')
        except (OSError, ValueError, IndexError):
            pass
    return total


def guarded(state, label, timeout, command):
    """Cancel a dedicated process group on disk/RAM/time limits; never publish raw logs."""
    started = time.monotonic()
    log = state / (label + '.log')
    outcome = {'status': 'failed', 'code': 'COMMAND_FAILED', 'seconds': None}
    process = None
    try:
        with log.open('wb') as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=stream, start_new_session=True)
            while process.poll() is None:
                if time.monotonic() - started > timeout:
                    raise GateError('TIME_LIMIT')
                if shutil.disk_usage(state).free < 2 * GIB:
                    raise GateError('DISK_HEADROOM_LIMIT')
                if memory_available()[1] < GIB or group_rss(process.pid) > 6 * GIB:
                    raise GateError('MEMORY_HEADROOM_LIMIT')
                if log.stat().st_size > 10 * 1024**2:
                    raise GateError('LOG_SIZE_LIMIT')
                time.sleep(.1)
            if process.returncode:
                # Dependency resolver diagnostics contain package specs only; publish those
                # separately below. All other native/test output remains unpublished.
                if label == 'resolve':
                    for line in log.read_text(errors='replace').splitlines():
                        if line.startswith('ERROR:'):
                            print(line[:1000])
                raise GateError('COMMAND_FAILED')
        outcome.update(status='passed', code=None)
    except GateError as error:
        outcome['code'] = str(error)
        raise
    finally:
        if process is not None:
            # The parent may have exited with a native child still alive.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            if platform.system() == 'Linux' and group_rss(process.pid):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        outcome['seconds'] = round(time.monotonic() - started, 4)
        if label == 'regressions' and log.exists():
            match = re.search(r'Ran (\d+) tests? in ', log.read_text(errors='replace'))
            outcome['testsRun'] = int(match[1]) if match else None
        write_json(state / (label + '-status.json'), outcome)
        print(label, outcome['status'], outcome['code'] or '')


def installed_versions(state):
    data = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
    if any(gpu_package(name) for name in data):
        raise GateError('GPU/LLM package unexpectedly installed.')
    write_json(state / 'versions.json', data)


def summarize(state):
    parts = ['# Linux x86_64 PaddleOCR verification',
             'Only completed gates below count as executed. Missing gates are NOT RUN.',
             'Synthetic smoke only; not real-document accuracy, VPS sizing or public readiness.']
    # Only these explicitly generated numeric/status reports are published. No glob/log uploads.
    for name in ('preflight-status', 'environment', 'resolve-status', 'plan-status', 'wheels',
                 'install-status', 'versions', 'models-status', 'regressions-status',
                 'import-status', 'import-probe', 'inference-status', 'inference', 'cleanup-status'):
        path = state / (name + '.json')
        parts += ['## ' + name, '```json', path.read_text().strip() if path.exists() else '"NOT RUN"', '```']
    report = '\n\n'.join(parts) + '\n'
    destination = os.environ.get('GITHUB_STEP_SUMMARY')
    if destination:
        with open(destination, 'a') as stream:
            stream.write(report)
    else:
        print(report)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight', 'plan', 'versions', 'summary', 'guard', 'cleanup'])
    parser.add_argument('--state', required=True)
    parser.add_argument('--label', choices=['resolve', 'install', 'models', 'regressions', 'import', 'inference'])
    parser.add_argument('--timeout', type=int, default=300)
    # Split subprocess arguments explicitly so flags above are parsed normally.
    args_list = sys.argv[1:]
    command = args_list[args_list.index('--') + 1:] if '--' in args_list else []
    if '--' in args_list:
        args_list = args_list[:args_list.index('--')]
    args = parser.parse_args(args_list)
    state = state_path(args.state)
    try:
        if args.action == 'preflight':
            if any(state.iterdir()):
                raise GateError('Use a fresh empty CI state directory; stale results are forbidden.')
            (state / '.ci-state').write_text(MARKER)
            preflight(state)
        elif args.action == 'plan':
            validate_plan(state)
        elif args.action == 'versions':
            installed_versions(state)
        elif args.action == 'summary':
            summarize(state)
        elif args.action == 'guard':
            if not command or not args.label or not 1 <= args.timeout <= 900:
                raise GateError('Provide a bounded timeout, label and command after --.')
            guarded(state, args.label, args.timeout, command)
        elif args.action == 'cleanup':
            if not (state / '.ci-state').is_file() or (state / '.ci-state').read_text() != MARKER:
                raise GateError('Refusing cleanup of unmarked state.')
            # Delete only known generated cache/model/log files; preserve summary JSON until VM disposal.
            for name in ('models', 'cache', 'tmp'):
                path = state / name
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
            for name in ('resolve', 'install', 'models', 'regressions', 'import', 'inference'):
                (state / (name + '.log')).unlink(missing_ok=True)
        if args.action in {'preflight', 'plan', 'versions', 'cleanup'}:
            write_json(state / (args.action + '-status.json'), {'status': 'passed'})
    except GateError as error:
        if args.action in {'preflight', 'plan', 'versions', 'cleanup'}:
            write_json(state / (args.action + '-status.json'), {'status': 'failed', 'code': str(error)})
        print('Verification stopped:', error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
