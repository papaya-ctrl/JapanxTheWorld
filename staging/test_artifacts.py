"""Host-only backup and staging configuration checks; no Docker/model loading."""
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from cryptography.fernet import Fernet
from staging.backup import seal,restore
from staging.prepare import private_directory,nginx_configuration
from staging.run import compose,require_idle


class StagingArtifactTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.root.chmod(0o700)
        (self.root/'manifest.json').write_text(json.dumps({'purpose':'disposable_staging_only'}))
        (self.root/'secrets').mkdir(mode=0o700)
        self.key=self.root/'secrets/key';self.key.write_bytes(Fernet.generate_key());self.key.chmod(0o600)
        self.db=self.root/'app.sqlite3'
        with sqlite3.connect(self.db) as db:db.execute('create table test(value text)');db.execute('insert into test values (?)',('synthetic-only',))
        self.archive=self.root/'backups/db.fernet';self.restored=self.root/'restored/app.sqlite3'

    def test_encrypted_consistent_database_round_trip_and_permissions(self):
        (self.root/'secrets/private-document.txt').write_text('EXCLUDED_SENTINEL')
        seal(self.db,self.archive,self.key,self.root)
        self.assertNotIn(b'synthetic-only',self.archive.read_bytes())
        self.assertNotIn(b'EXCLUDED_SENTINEL',Fernet(self.key.read_bytes()).decrypt(self.archive.read_bytes()))
        restore(self.archive,self.restored,self.key,self.root)
        with sqlite3.connect(self.restored) as db:self.assertEqual(db.execute('select value from test').fetchone(),('synthetic-only',))
        self.assertEqual(self.archive.stat().st_mode&0o777,0o600);self.assertEqual(self.restored.stat().st_mode&0o777,0o600)
        self.assertEqual(list(self.archive.parent.iterdir()),[self.archive])

    def test_wrong_key_and_tampering_never_publish_restore(self):
        seal(self.db,self.archive,self.key,self.root)
        original=self.key.read_bytes();self.key.write_bytes(Fernet.generate_key())
        with self.assertRaises(ValueError):restore(self.archive,self.restored,self.key,self.root)
        self.assertFalse(self.restored.exists());self.key.write_bytes(original)
        self.archive.write_bytes(self.archive.read_bytes()[:-5]+b'bad!!')
        with self.assertRaises(ValueError):restore(self.archive,self.restored,self.key,self.root)
        self.assertFalse(self.restored.exists())

    def test_existing_files_and_out_of_scope_source_are_preserved(self):
        seal(self.db,self.archive,self.key,self.root);original=self.archive.read_bytes()
        with self.assertRaises(FileExistsError):seal(self.db,self.archive,self.key,self.root)
        self.assertEqual(self.archive.read_bytes(),original)
        with self.assertRaises(ValueError):seal(self.root.parent/'unrelated.sqlite3',self.archive,self.key,self.root)
        restore(self.archive,self.restored,self.key,self.root)
        with self.assertRaises(FileExistsError):restore(self.archive,self.restored,self.key,self.root)

    def test_public_key_permissions_and_unmarked_stage_are_rejected(self):
        self.key.chmod(0o644)
        with self.assertRaises(ValueError):seal(self.db,self.archive,self.key,self.root)
        self.key.chmod(0o600);(self.root/'manifest.json').write_text('{}')
        with self.assertRaises(ValueError):seal(self.db,self.archive,self.key,self.root)
        with self.assertRaises(ValueError):compose(self.root)

    def test_checkout_and_compose_env_injection_paths_are_rejected(self):
        with self.assertRaises(ValueError):private_directory(Path(__file__).parent/'secrets')
        with self.assertRaises(ValueError):private_directory(self.root/'unsafe$directory')

    def test_proxy_keeps_security_and_distinct_origins(self):
        text=nginx_configuration()
        for expected in ['limit_req','client_max_body_size','ssl_protocols TLSv1.2 TLSv1.3','https://api.staging.test:18443','/run/secrets/tls_key.pem','127.0.0.1:8000']:
            self.assertIn(expected,text)
        self.assertNotIn('server_name api.example.invalid',text)
        self.assertNotIn('/live/api.example.invalid',text)
        with self.assertRaises(ValueError):nginx_configuration(tls_port=80)

    def test_isolated_commands_reject_running_heavy_service(self):
        from subprocess import CompletedProcess
        with patch('staging.run.execute',return_value=CompletedProcess([],0,'backend\nproxy\n')):
            with self.assertRaises(RuntimeError):require_idle(['docker','compose'])

    def test_daemon_guard_never_starts_a_vm(self):
        from staging.preflight import inspect
        from subprocess import CompletedProcess
        with patch('staging.preflight.subprocess.run',return_value=CompletedProcess([],1,'','unavailable')) as process:
            report=inspect();self.assertFalse(report['linuxExecutionAllowed'])
            self.assertEqual(process.call_args.args[0][:2],['docker','info'])

    def test_named_volume_export_captures_committed_wal_and_cleans_temporary_files(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
        from staging_tools.export_snapshot import snapshot_bytes
        project='jxtw-staging-abcdef12'
        (self.root/'.staging-project').write_text(project);(self.root/'tmp').mkdir(mode=0o700)
        with sqlite3.connect(self.db) as live:
            live.execute('PRAGMA journal_mode=WAL');live.execute('insert into test values (?)',('committed-wal',));live.commit()
            data=snapshot_bytes(self.root,project)
            seal(self.db,self.archive,self.key,self.root)
        restore(self.archive,self.restored,self.key,self.root)
        with sqlite3.connect(self.restored) as db:self.assertEqual(db.execute('select count(*) from test').fetchone()[0],2)
        self.assertEqual(list(self.archive.parent.iterdir()),[self.archive])
        restored=self.root/'export.sqlite3';restored.write_bytes(data)
        with sqlite3.connect(restored) as db:self.assertEqual(db.execute('select count(*) from test').fetchone()[0],2)
        self.assertEqual(list((self.root/'tmp').iterdir()),[])
        with self.assertRaises(ValueError):snapshot_bytes(self.root,'jxtw-staging-wrong123')
