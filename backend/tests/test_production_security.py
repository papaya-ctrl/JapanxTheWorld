"""Production controls, real auth/migration tables, and private resource boundaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import BytesIO, StringIO
import json
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from middleware.document_upload import BoundedDocumentUpload
from security.observability import OperationalFormatter
from security.rate_limit import consume, RateStoreUnavailable
from services.ocr.worker import LocalDocumentWorker
from tests.test_document_uploads import InProcessWorker, image_bytes


class ProductionConfigurationTests(SimpleTestCase):
    def run_config(self, changes=None, deploy=False):
        with TemporaryDirectory() as directory:
            root = Path(directory); state = root/'state'; state.mkdir(mode=0o700)
            (state/'tmp').mkdir(mode=0o700)
            models = root/'models'
            for name in ('PP-OCRv6_medium_det', 'PP-OCRv6_medium_rec'):
                path = models/name; path.mkdir(parents=True)
                (path/'inference.yml').touch(); (path/'inference.pdiparams').touch()
            env = {k:v for k,v in os.environ.items() if not k.startswith(('DJANGO_', 'DOCUMENT_OCR_'))}
            env.update(DJANGO_SETTINGS_MODULE='config.settings_production', DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
                DJANGO_ALLOWED_HOSTS='api.example.test', DJANGO_CORS_ALLOWED_ORIGINS='https://app.example.test',
                DJANGO_CSRF_TRUSTED_ORIGINS='https://app.example.test,https://api.example.test',
                DJANGO_TRUSTED_PROXY_IPS='127.0.0.1,::1', DJANGO_STATE_DIR=str(state),
                DJANGO_STATIC_ROOT=str(root/'static'), DOCUMENT_OCR_MODEL_ROOT=str(models))
            for key, value in (changes or {}).items():
                if value is None: env.pop(key, None)
                else: env[key] = value
            command = [sys.executable, 'manage.py', 'check', '--deploy'] if deploy else [sys.executable, '-c',
                "import config.settings_production as s; assert s.DEBUG is False and s.DOCUMENT_REQUIRE_AUTH and not s.ALLOW_REGISTRATION; assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE; assert s.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']==['rest_framework.permissions.IsAuthenticated']; print('CONFIG_OK')"]
            return subprocess.run(command, cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, timeout=15)

    def test_production_is_secure_without_debug_or_development_fallback(self):
        result = self.run_config()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CONFIG_OK', result.stdout)

    def test_missing_essential_configuration_fails_closed(self):
        for key in ('DJANGO_SECRET_KEY','DJANGO_ALLOWED_HOSTS','DJANGO_CORS_ALLOWED_ORIGINS','DJANGO_CSRF_TRUSTED_ORIGINS','DJANGO_TRUSTED_PROXY_IPS','DJANGO_STATE_DIR','DJANGO_STATIC_ROOT','DOCUMENT_OCR_MODEL_ROOT'):
            with self.subTest(key=key):
                result = self.run_config({key: None})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)

    def test_unsafe_hosts_origins_secrets_and_debug_are_rejected(self):
        cases = [{'DJANGO_DEBUG':'true'}, {'DJANGO_ALLOWED_HOSTS':'*'}, {'DJANGO_ALLOWED_HOSTS':'.example.test'},
                 {'DJANGO_CORS_ALLOWED_ORIGINS':'http://app.example.test'}, {'DJANGO_CSRF_TRUSTED_ORIGINS':'https://user:password@app.example.test'},
                 {'DJANGO_SECRET_KEY':'django-insecure-committed-development-value'}, {'DJANGO_TRUSTED_PROXY_IPS':'0.0.0.0/0'},
                 {'DJANGO_STATE_DIR':'relative'}, {'DJANGO_STATIC_ROOT':'/'}]
        for case in cases:
            with self.subTest(keys=list(case)):
                self.assertNotEqual(self.run_config(case).returncode, 0)

    def test_deployment_checks_report_only_deliberate_hsts_policy_warnings(self):
        result = self.run_config(deploy=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('security.W005', result.stderr)
        self.assertIn('security.W021', result.stderr)
        self.assertNotIn('security.W018', result.stderr)
        self.assertNotIn('security.W009', result.stderr)
        opted_in = self.run_config({'DJANGO_HSTS_INCLUDE_SUBDOMAINS':'true','DJANGO_HSTS_PRELOAD':'true'}, deploy=True)
        self.assertEqual(opted_in.returncode, 0, opted_in.stderr)
        self.assertIn('no issues', opted_in.stdout)


@override_settings(DOCUMENT_REQUIRE_AUTH=True, ALLOW_ANONYMOUS_CHECKLIST=False, ALLOW_REGISTRATION=False,
                   ATOMIC_RATE_LIMITING=True, API_IP_RATE='1000/min', AUTH_IP_RATE='1000/min', DOCUMENT_IP_RATE='1000/min', DOCUMENT_USER_RATE='1000/min')
class AuthorizedAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('synthetic-alice', password='TestOnly!VeryStrong247')
        cls.bob = User.objects.create_user('synthetic-bob', password='TestOnly!VeryStrong248')
        cls.alice.user_permissions.add(Permission.objects.get(codename='analyze_document'))

    def setUp(self):
        cache.clear()
        self.directory = TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name)
        self.config = override_settings(RATE_LIMIT_DB=self.state/'rates.sqlite3')
        self.config.enable(); self.addCleanup(self.config.disable)
        self.token = Token.objects.create(user=self.alice)
        self.client = APIClient(); self.client.credentials(HTTP_AUTHORIZATION='Token '+self.token.key)
        self.worker = InProcessWorker()
        self.mock = patch('services.documentAnalysis.upload.get_document_worker', return_value=self.worker)
        self.mock.start(); self.addCleanup(self.mock.stop)

    def upload(self, client=None, name='synthetic.png', data=None):
        return (client or self.client).post('/api/documents/analyze', {'file':SimpleUploadedFile(name, image_bytes() if data is None else data, content_type='image/png')}, format='multipart')

    def test_anonymous_and_unprivileged_uploads_fail_before_ocr(self):
        self.assertEqual(self.upload(APIClient()).status_code, 401)
        self.assertEqual(APIClient().get('/api/documents/access').status_code, 401)
        bob = APIClient(); bob.credentials(HTTP_AUTHORIZATION='Token '+Token.objects.create(user=self.bob).key)
        self.assertEqual(self.upload(bob).status_code, 403)
        self.assertEqual(bob.get('/api/documents/access').status_code, 403)
        self.assertEqual(self.client.get('/api/documents/access').status_code, 204)
        self.worker.predict.assert_not_called()

    def test_invalid_expired_and_inactive_credentials_are_denied(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token '+'f'*40)
        self.assertEqual(self.upload().status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Token '+self.token.key)
        Token.objects.filter(key=self.token.key).update(created=timezone.now()-timedelta(hours=2))
        self.assertEqual(self.upload().status_code, 401)
        Token.objects.filter(key=self.token.key).update(created=timezone.now())
        self.alice.is_active=False; self.alice.save(update_fields=['is_active'])
        self.assertEqual(self.upload().status_code, 401)
        self.worker.predict.assert_not_called()

    def test_authorized_upload_preserves_private_evidence_without_storing_it(self):
        from models.db_models import Document, AnalysisResult
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['evidence'])
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(Document.objects.count(), 0); self.assertEqual(AnalysisResult.objects.count(), 0)
        self.assertFalse(any(p.suffix in {'.png','.pdf','.jpg'} for p in self.state.iterdir()))

    def test_user_rate_cannot_be_bypassed_with_new_ip_or_token(self):
        with override_settings(DOCUMENT_USER_RATE='1/min'):
            self.assertEqual(self.upload().status_code, 200)
            response = self.client.post('/api/documents/analyze', {'file':SimpleUploadedFile('a.png', image_bytes(), content_type='image/png')}, format='multipart', REMOTE_ADDR='192.0.2.22')
            self.assertEqual(response.status_code, 429)
            self.assertIn('Retry-After', response)
            self.worker.predict.assert_called_once()

    def test_ip_limit_ignores_untrusted_forwarded_addresses(self):
        with override_settings(DOCUMENT_IP_RATE='1/min', TRUSTED_PROXY_IPS=[]):
            self.assertEqual(self.upload().status_code, 200)
            response = self.client.post('/api/documents/analyze', {}, format='json', HTTP_X_FORWARDED_FOR='192.0.2.50', HTTP_X_REAL_IP='192.0.2.51')
            self.assertEqual(response.status_code, 429)
            self.worker.predict.assert_called_once()

    def test_rate_store_failure_fails_closed(self):
        with patch('security.middleware.consume', side_effect=RateStoreUnavailable()):
            response = self.upload()
        self.assertEqual(response.status_code, 503); self.assertIn('Retry-After', response)
        self.worker.predict.assert_not_called()

    def test_body_size_and_missing_length_rejected_before_authentication_or_decode(self):
        anonymous = APIClient()
        response = anonymous.generic('POST','/api/documents/analyze',b'x',content_type='application/octet-stream',CONTENT_LENGTH=str(11*1024**2))
        self.assertEqual(response.status_code, 413)
        response = anonymous.generic('POST','/api/documents/analyze',b'',content_type='application/octet-stream',CONTENT_LENGTH='')
        self.assertEqual(response.status_code, 411)
        response = anonymous.generic('POST','/api/auth/login',b'not-json',content_type='application/json; charset=base64_codec')
        self.assertEqual(response.status_code, 415)
        self.worker.predict.assert_not_called()

    def test_registration_is_closed_and_login_rotates_expiring_credentials(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.post('/api/auth/register', {'username':'blocked','password':'ignored'}, format='json').status_code, 403)
        response = anonymous.post('/api/auth/login', {'username':'synthetic-alice','password':'TestOnly!VeryStrong247'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['expiresIn'], 3600)
        self.assertNotEqual(response.json()['token'], self.token.key)
        self.assertEqual(self.upload().status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Token '+response.json()['token'])
        self.assertEqual(self.client.get('/api/auth/me').json()['user']['id'], self.alice.pk)
        self.assertEqual(self.client.post('/api/auth/logout', {}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_bad_login_inputs_and_passwords_do_not_echo_credentials(self):
        anonymous = APIClient()
        response = anonymous.post('/api/auth/login', {'username':{'private':'SECRET_MARKER'},'password':'SECRET_PASSWORD_MARKER'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('SECRET_', response.content.decode())
        response = anonymous.post('/api/auth/login', {'username':'synthetic-alice','password':'not-a-valid-password'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_checklist_is_scoped_to_the_authenticated_account(self):
        from models.db_models import ChecklistItem
        orphan = ChecklistItem.objects.create(title='Legacy private orphan')
        response = self.client.post('/api/checklist', {'title':'Synthetic private task','category':'Administration','dueDate':'2031-06-30','user':self.bob.pk,'user_id':self.bob.pk},format='json')
        self.assertEqual(response.status_code, 201)
        item = ChecklistItem.objects.get(pk=response.json()['id']); self.assertEqual(item.user_id,self.alice.pk)
        self.assertIsInstance(response.json()['id'],str)
        self.assertEqual(response.json()['category'],'Administration')
        self.assertEqual(response.json()['dueDate'],'2031-06-30')
        bob = APIClient(); bob.credentials(HTTP_AUTHORIZATION='Token '+Token.objects.create(user=self.bob).key)
        self.assertEqual(bob.get('/api/checklist').json(), [])
        self.assertEqual(bob.patch(f'/api/checklist/{item.pk}', {'completed':True},format='json').status_code, 404)
        self.assertEqual(bob.delete(f'/api/checklist/{item.pk}').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/checklist/{item.pk}',{'completed':True,'category':'School','user':self.bob.pk},format='json').status_code,200)
        item.refresh_from_db(); self.assertTrue(item.completed); self.assertEqual(item.user_id,self.alice.pk);self.assertEqual(item.category,'School')
        self.assertEqual(APIClient().get('/api/checklist').status_code,401)
        self.assertEqual(self.client.delete(f'/api/checklist/{orphan.pk}').status_code,404)
        self.assertEqual(self.client.delete(f'/api/checklist/{item.pk}').status_code,204)
        self.assertTrue(ChecklistItem.objects.filter(pk=orphan.pk).exists())

    def test_session_authentication_requires_csrf_for_mutations(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.alice)
        response = client.post('/api/checklist', {'title':'Must fail without CSRF'}, format='json')
        self.assertEqual(response.status_code,403)
        self.assertEqual(response.json()['code'],'ACCESS_DENIED')

    def test_exhausted_worker_rejects_immediately_without_spawning_or_queueing(self):
        worker = LocalDocumentWorker(); worker._lock.acquire()
        try:
            with patch('services.documentAnalysis.upload.get_document_worker', return_value=worker):
                response = self.upload()
            self.assertEqual(response.status_code,503); self.assertEqual(response.json()['code'],'ANALYSIS_BUSY')
            self.assertIsNone(worker._process)
        finally: worker._lock.release(); worker.close()
        self.assertEqual(self.upload().status_code,200)

    def test_disallowed_extension_and_signature_do_not_reach_ocr(self):
        self.assertEqual(self.upload(name='private.exe').status_code,400)
        self.assertEqual(self.upload(data=b'not-a-real-image').status_code,400)
        self.worker.predict.assert_not_called()

    def test_upload_buffers_close_after_success_decode_error_and_exception(self):
        handlers=[]
        original = BoundedDocumentUpload.__init__
        def capture(handler,*args,**kwargs):
            original(handler,*args,**kwargs); handlers.append(handler)
        with patch.object(BoundedDocumentUpload,'__init__',capture), patch('django.core.files.uploadhandler.TemporaryUploadedFile',side_effect=AssertionError('Unexpected disk upload')):
            self.assertEqual(self.upload().status_code,200)
            self.assertEqual(self.upload(data=b'\x89PNG\r\n\x1a\ncorrupt').status_code,400)
            with patch.object(self.worker,'analyze',side_effect=RuntimeError('PRIVATE_OCR_MARKER')):
                self.assertEqual(self.upload().status_code,500)
            from services.ocr.errors import ProcessingTimeout,ProcessingMemoryExceeded,WorkerBusy
            for error, status in [(ProcessingTimeout(),504),(ProcessingMemoryExceeded(),413),(WorkerBusy(),503)]:
                with patch.object(self.worker,'analyze',side_effect=error):
                    self.assertEqual(self.upload().status_code,status)
        self.assertEqual(len(handlers),6)
        self.assertTrue(all(h.buffer.closed for h in handlers))

    def test_interrupted_multipart_upload_releases_the_partial_buffer(self):
        handlers=[];original=BoundedDocumentUpload.__init__
        def capture(handler,*args,**kwargs):
            original(handler,*args,**kwargs);handlers.append(handler)
        body=b'--partial\r\nContent-Disposition: form-data; name="file"; filename="synthetic.png"\r\nContent-Type: image/png\r\n\r\n'+image_bytes()[:40]
        with patch.object(BoundedDocumentUpload,'__init__',capture):
            response=self.client.generic('POST','/api/documents/analyze',body,content_type='multipart/form-data; boundary=partial')
        self.assertEqual(response.status_code,400)
        self.assertTrue(all(h.buffer is None or h.buffer.closed for h in handlers))
        self.worker.predict.assert_not_called()

    def test_proxy_tls_host_cors_and_security_headers(self):
        with override_settings(SECURE_SSL_REDIRECT=True,SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https'),TRUSTED_PROXY_IPS=['127.0.0.1'],CORS_ALLOWED_ORIGINS=['https://app.example.test']):
            response = self.client.get('/api/health',HTTP_X_FORWARDED_PROTO='https',HTTP_ORIGIN='https://app.example.test')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['Access-Control-Allow-Origin'],'https://app.example.test')
            self.assertEqual(response['X-Content-Type-Options'],'nosniff')
            self.assertIn("default-src 'none'",response['Content-Security-Policy'])
            self.assertEqual(self.client.get('/api/health',HTTP_X_FORWARDED_PROTO='https',REMOTE_ADDR='192.0.2.7').status_code,301)
            self.assertEqual(self.client.get('/api/health',HTTP_X_FORWARDED_PROTO='https, http').status_code,400)
            denied = self.client.get('/api/health',HTTP_X_FORWARDED_PROTO='https',HTTP_ORIGIN='https://evil.example.test')
            self.assertNotIn('Access-Control-Allow-Origin',denied)
            self.assertEqual(self.client.get('/api/health',HTTP_X_FORWARDED_PROTO='https',HTTP_HOST='untrusted.example.test').status_code,400)


class AtomicRateLimitTests(SimpleTestCase):
    def test_concurrent_requests_do_not_exceed_the_atomic_limit(self):
        with TemporaryDirectory() as directory,override_settings(RATE_LIMIT_DB=Path(directory)/'rates.sqlite3'):
            def request(_):
                try:return consume('test','synthetic-user','1/min',now=100)
                except RateStoreUnavailable:return -1
            with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(request,range(12)))
            self.assertEqual(results.count(0),1)
            self.assertTrue(all(value==0 or value==-1 or value>0 for value in results))
            self.assertEqual(consume('test','synthetic-user','1/min',now=161),0)
            data=(Path(directory)/'rates.sqlite3').read_bytes()
            self.assertNotIn(b'synthetic-user',data)
            self.assertEqual((Path(directory)/'rates.sqlite3').stat().st_mode & 0o777,0o600)

    def test_bucket_capacity_and_insecure_permissions_fail_closed(self):
        with TemporaryDirectory() as directory,override_settings(RATE_LIMIT_DB=Path(directory)/'rates.sqlite3',RATE_LIMIT_MAX_BUCKETS=1):
            self.assertEqual(consume('test','one','1/min',now=100),0)
            with self.assertRaises(RateStoreUnavailable):consume('test','two','1/min',now=100)
            Path(settings.RATE_LIMIT_DB).chmod(0o644)
            with self.assertRaises(RateStoreUnavailable):consume('test','one','1/min',now=100)


class PrivateLoggingTests(SimpleTestCase):
    def test_messages_requests_headers_and_exception_values_are_not_serialized(self):
        output=StringIO();handler=logging.StreamHandler(output);handler.setFormatter(OperationalFormatter())
        logger=logging.Logger('private-test');logger.addHandler(handler)
        try:raise ValueError('PRIVATE_DOCUMENT_TEXT')
        except ValueError:
            logger.exception('PRIVATE_FILENAME Authorization: SECRET_TOKEN',extra={'request':'PRIVATE_REQUEST','event':'request','route':'ocr','status':500,'durationSeconds':1.2})
        text=output.getvalue()
        for marker in ('PRIVATE_', 'SECRET_TOKEN', 'Authorization', 'ValueError','Traceback'):
            self.assertNotIn(marker,text)
        result=json.loads(text);self.assertEqual(result['status'],500);self.assertEqual(result['route'],'ocr')
        output.seek(0);output.truncate(0)
        logger.error('PRIVATE_STRUCTURED_LOG',extra={'event':[], 'route':{'private':'PRIVATE_MARKER'}, 'code':[], 'status':10**1000, 'durationSeconds':float('nan')})
        self.assertNotIn('PRIVATE_',output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['event'],'server')

    def test_unhandled_api_exception_returns_a_generic_error(self):
        from security.exceptions import safe_exception_handler
        response=safe_exception_handler(RuntimeError('PRIVATE_NAME_AND_ACCOUNT'),{})
        self.assertEqual(response.status_code,500)
        self.assertNotIn('PRIVATE_',json.dumps(response.data))


class DisposableMigrationTests(SimpleTestCase):
    def test_migrations_repeat_backup_restore_and_grants_preserve_user_checklists(self):
        import sqlite3
        with TemporaryDirectory() as directory:
            root=Path(directory);database=root/'test.sqlite3'
            env={**os.environ,'DJANGO_SETTINGS_MODULE':'config.settings_development','DJANGO_DB_PATH':str(database)}
            backend=Path(__file__).resolve().parents[1]
            def command(*args):
                return subprocess.run([sys.executable,'manage.py',*args],cwd=backend,env=env,capture_output=True,text=True,timeout=20)
            legacy=command('migrate','models','0001','--noinput');self.assertEqual(legacy.returncode,0,legacy.stderr)
            with sqlite3.connect(database) as connection:
                connection.execute("INSERT INTO checklist_items (title,completed,created_at,user_id) VALUES ('Legacy synthetic task',1,'2031-01-01',NULL)")
            first=command('migrate','--noinput');self.assertEqual(first.returncode,0,first.stderr)
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute('SELECT title,category FROM checklist_items').fetchone(),('Legacy synthetic task',''))
            again=command('migrate','--noinput');self.assertEqual(again.returncode,0,again.stderr)
            self.assertIn('No migrations to apply',again.stdout)
            script="""
import django;django.setup()
from django.contrib.auth.models import User
from models.db_models import ChecklistItem
from django.contrib.auth import authenticate
user=User.objects.create_user('synthetic-migration-user',password='TestOnly!BackupSecurity247')
ChecklistItem.objects.create(user=user,title='Synthetic restore check',completed=True)
assert authenticate(username=user.username,password='TestOnly!BackupSecurity247').pk==user.pk
"""
            seeded=subprocess.run([sys.executable,'-c',script],cwd=backend,env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(seeded.returncode,0,seeded.stderr)
            self.assertEqual(command('grant_document_access','synthetic-migration-user').returncode,0)
            backup=root/'backups'/'snapshot.sqlite3'
            result=command('backup_database',str(backup));self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(backup.stat().st_mode & 0o777,0o600)
            self.assertNotEqual(command('backup_database',str(backup)).returncode,0)
            restored=root/'restored.sqlite3'
            with sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(restored) as destination:
                source.backup(destination)
                self.assertEqual(destination.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(destination.execute('SELECT count(*) FROM checklist_items WHERE completed=1 AND user_id IS NOT NULL').fetchone()[0],1)
                self.assertEqual(destination.execute('SELECT count(*) FROM auth_user').fetchone()[0],1)
                self.assertEqual(destination.execute('SELECT count(*) FROM auth_user_user_permissions').fetchone()[0],1)
            restored_env={**env,'DJANGO_DB_PATH':str(restored)}
            verify=subprocess.run([sys.executable,'manage.py','migrate','--check'],cwd=backend,env=restored_env,capture_output=True,text=True,timeout=15)
            self.assertEqual(verify.returncode,0,verify.stderr)
            self.assertEqual(command('grant_document_access','synthetic-migration-user','--revoke').returncode,0)
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute('SELECT count(*) FROM auth_user_user_permissions').fetchone()[0],0)
                self.assertEqual(connection.execute('SELECT count(*) FROM checklist_items').fetchone()[0],2)
