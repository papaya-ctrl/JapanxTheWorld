"""Guard/report tests; these never load models or claim native Linux inference."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ci import linux_ocr as ci


class CheckoutTests(TestCase):
    def bootstrap(self, missing=None):
        import yaml
        workflow = yaml.safe_load((ci.PROJECT / '.github/workflows/linux-x86-ocr.yml').read_text())
        step = next(step for step in workflow['jobs']['verify']['steps']
                    if step['name'] == 'Verify checkout includes all verification entry points')
        with TemporaryDirectory() as directory:
            root = Path(directory)
            # Copy public source only, exactly as a checkout containing the fix would.
            names = ('ci/__init__.py', 'ci/linux_ocr.py', 'ci/test_linux_ocr.py',
                'backend/staging_tools/__init__.py', 'backend/staging_tools/verify_linux_ocr.py',
                'backend/staging_tools/fixtures.py', 'backend/download_ocr_models.py',
                'backend/manage.py', 'backend/requirements.txt', 'backend/requirements-dev.txt')
            for name in names:
                if name != missing:
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ci.PROJECT / name, target)
            # A clean interpreter needs no installed OCR/Django packages for this check.
            env = {**os.environ, 'PYTHONPATH': str(root / 'backend') + os.pathsep + str(root),
                   'PYTHONDONTWRITEBYTECODE': '1'}
            script = step['run'].split("python - <<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
            return subprocess.run([sys.executable, '-S', '-c', script], cwd=root,
                                  env=env, capture_output=True, text=True, timeout=15)

    def test_clean_checkout_resolves_ci_and_backend_verifier_without_ocr_imports(self):
        result = self.bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_incomplete_checkout_identifies_each_missing_entry_point(self):
        for name in ('ci/linux_ocr.py', 'ci/test_linux_ocr.py', 'backend/staging_tools/verify_linux_ocr.py'):
            with self.subTest(name=name):
                result = self.bootstrap(name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Incomplete verification checkout', result.stderr)
                self.assertIn(name, result.stderr)


class ResourceTests(TestCase):
    def test_unbounded_cgroup_still_reports_current_and_lifetime_peak(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'memory.max').write_text('max')
            (root / 'memory.current').write_text('123')
            (root / 'memory.peak').write_text('456')
            membership = root / 'membership'; membership.write_text('0::/\n')
            self.assertEqual(ci.cgroups(root, membership), [
                {'version': 2, 'limitBytes': None, 'currentBytes': 123, 'kernelPeakBytes': 456}])

    def test_ancestor_memory_limit_reduces_effective_available_memory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            meminfo = root / 'meminfo'
            meminfo.write_text('MemTotal: 16000000 kB\nMemAvailable: 12000000 kB\n')
            groups = [{'limitBytes': 8 * ci.GIB, 'currentBytes': 6 * ci.GIB}]
            self.assertEqual(ci.memory_available(meminfo, groups)[1], 2 * ci.GIB)

    def test_v1_membership_and_ancestor_counters_are_preserved(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            leaf = root / 'memory' / 'job'; leaf.mkdir(parents=True)
            (leaf / 'memory.limit_in_bytes').write_text(str(8 * ci.GIB))
            (leaf / 'memory.usage_in_bytes').write_text(str(2 * ci.GIB))
            (leaf / 'memory.max_usage_in_bytes').write_text(str(3 * ci.GIB))
            membership = root / 'membership'; membership.write_text('3:memory:/job\n')
            self.assertEqual(ci.cgroups(root, membership)[0], {'version': 1,
                'limitBytes': 8 * ci.GIB, 'currentBytes': 2 * ci.GIB,
                'kernelPeakBytes': 3 * ci.GIB})

    def test_wrong_architecture_fails_before_reading_linux_native_state(self):
        with patch.object(ci.platform, 'machine', return_value='aarch64'):
            with self.assertRaisesRegex(ci.GateError, 'native Ubuntu'):
                ci.preflight(Path('/unused'))

    def test_guard_stops_and_records_a_timed_out_process(self):
        with TemporaryDirectory() as directory, \
             patch.object(ci, 'memory_available', return_value=(16 * ci.GIB, 10 * ci.GIB)), \
             patch.object(ci.shutil, 'disk_usage', return_value=SimpleNamespace(free=10 * ci.GIB)):
            root = Path(directory)
            with self.assertRaisesRegex(ci.GateError, 'TIME_LIMIT'):
                ci.guarded(root, 'inference', .05, [sys.executable, '-c', 'import time; time.sleep(5)'])
            result = json.loads((root / 'inference-status.json').read_text())
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['code'], 'TIME_LIMIT')

    def test_low_disk_guard_never_reports_success(self):
        with TemporaryDirectory() as directory, \
             patch.object(ci.shutil, 'disk_usage', return_value=SimpleNamespace(free=ci.GIB)):
            root = Path(directory)
            with self.assertRaisesRegex(ci.GateError, 'DISK_HEADROOM_LIMIT'):
                ci.guarded(root, 'install', 5, [sys.executable, '-c', 'import time; time.sleep(5)'])
            self.assertEqual(json.loads((root / 'install-status.json').read_text())['status'], 'failed')


class WheelTests(TestCase):
    def plan(self, change=None):
        directory = TemporaryDirectory(); self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / 'backend').mkdir()
        (root / 'backend' / 'requirements.txt').write_text('example==1.0\n')
        (root / 'backend' / 'requirements-dev.txt').write_text('-r requirements.txt\n')
        item = {'metadata': {'name': 'example', 'version': '1.0'}, 'download_info': {
            'url': 'https://files.pythonhosted.org/example-1.0-py3-none-any.whl',
            'archive_info': {'hashes': {'sha256': 'a' * 64}}}}
        if change:
            change(item)
        (root / 'pip-plan.json').write_text(json.dumps({'install': [item]}))
        with patch.object(ci, 'PROJECT', root):
            ci.validate_plan(root)
        return root

    def test_exact_compatible_wheel_hash_is_written_for_installation(self):
        root = self.plan()
        self.assertEqual((root / 'resolved.txt').read_text(), 'example==1.0 --hash=sha256:' + 'a' * 64 + '\n')

    def test_source_distributions_fail(self):
        with self.assertRaisesRegex(ci.GateError, 'No binary wheel'):
            self.plan(lambda item: item['download_info'].update(url='https://example.invalid/package.tar.gz'))

    def test_gpu_transitives_fail(self):
        with self.assertRaisesRegex(ci.GateError, 'Forbidden GPU'):
            self.plan(lambda item: item['metadata'].update(name='nvidia-cublas-cu12'))

    def test_wrong_architecture_wheel_fails(self):
        with self.assertRaisesRegex(ci.GateError, 'Incompatible wheel'):
            self.plan(lambda item: item['download_info'].update(url='https://example.invalid/example-1.0-cp312-cp312-win_amd64.whl'))

    def test_missing_hash_and_changed_pin_fail(self):
        with self.assertRaisesRegex(ci.GateError, 'Missing wheel SHA-256'):
            self.plan(lambda item: item['download_info']['archive_info']['hashes'].clear())
        def changed(item):
            item['metadata']['version'] = '2.0'
            item['download_info']['url'] = 'https://example.invalid/example-2.0-py3-none-any.whl'
        with self.assertRaisesRegex(ci.GateError, 'Pinned dependency absent or changed'):
            self.plan(changed)


class ReportTests(TestCase):
    def test_worker_memory_failure_closes_worker_and_reports_only_safe_failure_code(self):
        from staging_tools import verify_linux_ocr as verify
        from services.ocr.errors import ProcessingMemoryExceeded
        worker = Mock(_process=None, last_peak_rss_bytes=123, last_metrics={})
        worker.analyze.side_effect = ProcessingMemoryExceeded()
        with TemporaryDirectory() as directory, \
             patch.object(verify.platform, 'system', return_value='Linux'), \
             patch.object(verify.platform, 'machine', return_value='x86_64'), \
             patch.object(verify, 'LocalDocumentWorker', return_value=worker) as constructor, \
             patch('services.ocr.resources.available_memory_bytes', return_value=4 * ci.GIB):
            root = Path(directory)
            self.assertFalse(verify.run(root, 'import'))
            worker.close.assert_called_once()
            self.assertEqual(constructor.call_args.args[0].max_worker_rss_bytes, 5 * ci.GIB)
            report = json.loads((root / 'import-probe.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['failureCode'], ProcessingMemoryExceeded.code)
            self.assertTrue(report['workerClosed'])
            self.assertEqual(report['rows'], [])

    def test_cli_modes_reject_wrong_platform_with_failed_reports_before_creating_worker(self):
        from staging_tools import verify_linux_ocr as verify
        for mode, report in (('import', 'import-probe.json'), ('inference', 'inference.json')):
            with self.subTest(mode=mode), TemporaryDirectory() as directory, \
                 patch.object(verify.platform, 'machine', return_value='aarch64'), \
                 patch.object(verify, 'LocalDocumentWorker') as constructor, \
                 patch.object(sys, 'argv', ['verify_linux_ocr', mode, '--state', directory]):
                Path(directory).chmod(0o700)
                self.assertEqual(verify.main(), 1)
                constructor.assert_not_called()
                result = json.loads((Path(directory) / report).read_text())
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['failureCode'], 'LINUX_X86_64_REQUIRED')

    def test_cleanup_cli_refuses_an_unmarked_private_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); root.chmod(0o700)
            (root / 'models').mkdir()
            sentinel = root / 'models' / 'keep'; sentinel.write_text('keep')
            result = subprocess.run([sys.executable, str(ci.PROJECT / 'ci/linux_ocr.py'),
                'cleanup', '--state', str(root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(sentinel.is_file())

    def test_summary_excludes_logs_predictions_and_model_caches(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('inference.log', 'predictions.json', 'credentials.json'):
                (root / name).write_text('NEVER_PUBLISH_THIS_MARKER')
            (root / 'inference.json').write_text('{"status":"failed","failureCode":"OCR_UNAVAILABLE"}')
            output = StringIO()
            with patch.dict(ci.os.environ, {'GITHUB_STEP_SUMMARY': ''}), redirect_stdout(output):
                ci.summarize(root)
            self.assertNotIn('NEVER_PUBLISH_THIS_MARKER', output.getvalue())
            self.assertIn('NOT RUN', output.getvalue())
            self.assertIn('OCR_UNAVAILABLE', output.getvalue())

    def test_synthetic_verifier_rejects_missing_or_wrong_recognition(self):
        from staging_tools.verify_linux_ocr import verify_result
        from tests.test_document_fields import page
        from services.ocr.document_adapter import analyze_document_bytes
        from services.ocr.limits import DocumentLimits
        from PIL import Image
        from io import BytesIO
        records = page(('国民健康保険税', 0, 0, 500, 30),
                         ('納期限 令和13年6月30日', 0, 100, 600, 130),
                         ('利用期限 2032年6月30日', 0, 200, 600, 230),
                         ('納付額 5,000円', 0, 300, 500, 330),
                         ('合計金額 不明', 0, 400, 500, 430))
        buffer = BytesIO()
        with Image.new('RGB', (640, 640), 'white') as fixture:
            fixture.save(buffer, format='PNG')
        result = analyze_document_bytes(buffer.getvalue(), 'png', lambda image: [records], DocumentLimits())
        self.assertTrue(all(verify_result(result).values()))
        corrupted = deepcopy(result)
        corrupted['primaryAmount'] = 5000
        with self.assertRaises((AssertionError, ValueError)):
            verify_result(corrupted)
        corrupted = deepcopy(result)
        corrupted['evidence'] = []
        with self.assertRaises(ValueError):
            verify_result(corrupted)
