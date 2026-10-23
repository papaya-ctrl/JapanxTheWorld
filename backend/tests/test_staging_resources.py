from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace

from services.ocr.resources import available_memory_bytes, cgroup_memory


class CgroupResourceTests(TestCase):
    def test_v2_container_limit_is_used_instead_of_host_free_memory(self):
        with patch('services.ocr.resources.platform.system',return_value='Linux'), patch('services.ocr.resources.psutil.virtual_memory',return_value=SimpleNamespace(available=10000)), patch('services.ocr.resources.cgroup_memory',return_value={'remainingBytes':300}):
            self.assertEqual(available_memory_bytes(),300)

    def test_nested_v2_uses_the_tightest_ancestor_headroom(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);leaf=root/'system.slice/service';leaf.mkdir(parents=True)
            (root/'memory.max').write_text('max');(root/'memory.current').write_text('100')
            (root/'system.slice/memory.max').write_text('1000');(root/'system.slice/memory.current').write_text('900')
            (leaf/'memory.max').write_text('500');(leaf/'memory.current').write_text('300')
            membership=root/'membership';membership.write_text('0::/system.slice/service\n')
            result=cgroup_memory(root,membership)
            self.assertEqual(result['remainingBytes'],100);self.assertEqual(result['limitBytes'],1000)

    def test_private_namespace_root_and_v1_are_supported(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);membership=root/'membership';membership.write_text('0::/not-visible-on-this-mount\n')
            (root/'memory.max').write_text('500');(root/'memory.current').write_text('600')
            self.assertEqual(cgroup_memory(root,membership)['remainingBytes'],0)
            (root/'memory.max').unlink();(root/'memory.current').unlink()
            path=root/'memory/group';path.mkdir(parents=True);membership.write_text('7:memory:/group\n')
            (path/'memory.limit_in_bytes').write_text('800');(path/'memory.usage_in_bytes').write_text('200')
            self.assertEqual(cgroup_memory(root,membership)['version'],1)
            self.assertEqual(cgroup_memory(root,membership)['remainingBytes'],600)

    def test_unavailable_unlimited_and_invalid_values_are_not_fabricated(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertIsNone(cgroup_memory(root,root/'absent')['currentBytes'])
            (root/'memory.max').write_text(str(2**63-1));(root/'memory.current').write_text('100')
            self.assertIsNone(cgroup_memory(root,root/'absent')['limitBytes'])
            (root/'memory.max').write_text('500');(root/'memory.current').write_text('invalid')
            self.assertIsNone(cgroup_memory(root,root/'absent')['remainingBytes'])
        with patch('services.ocr.resources.platform.system',return_value='Darwin'),patch('services.ocr.resources.psutil.virtual_memory',return_value=SimpleNamespace(available=1234)):
            self.assertEqual(available_memory_bytes(),1234)
