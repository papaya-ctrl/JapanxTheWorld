"""Bounded fault injection; no physical OOM, disk fill or real-user mutations."""
from io import StringIO
import logging
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest import TestCase as UnitTestCase
from unittest.mock import patch

from django.contrib.auth.models import User,Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError
from django.test import TestCase,override_settings
from rest_framework.test import APIClient
from services.ocr.errors import DocumentProcessingError,ProcessingMemoryExceeded
from services.ocr.limits import DocumentLimits
from services.ocr.worker import LocalDocumentWorker
from tests.test_document_uploads import image_bytes
from tests.test_document_worker import echo_worker,hung_worker
from tests.staging_worker_targets import crashed_worker


class NativeSupervisorFaultTests(UnitTestCase):
    def test_crashed_worker_cleans_channel_and_recovers(self):
        worker=LocalDocumentWorker(target=crashed_worker,limits=DocumentLimits(timeout_seconds=5))
        try:
            with self.assertRaises(DocumentProcessingError):worker.analyze(b'synthetic','png')
            self.assertIsNone(worker._process);self.assertIsNone(worker._connection)
            worker._target=echo_worker
            self.assertEqual(worker.analyze(b'synthetic','png'),{'jobs':1})
        finally:worker.close()

    def test_memory_cancellation_recovers_without_exhausting_the_host(self):
        worker=LocalDocumentWorker(target=hung_worker,limits=DocumentLimits(timeout_seconds=5,max_worker_rss_bytes=1))
        try:
            with self.assertRaises(ProcessingMemoryExceeded):worker.analyze(b'synthetic','png')
            self.assertIsNone(worker._process)
            worker.limits=DocumentLimits(timeout_seconds=5);worker._target=echo_worker
            self.assertEqual(worker.analyze(b'synthetic','png'),{'jobs':1})
        finally:worker.close()


@override_settings(DOCUMENT_REQUIRE_AUTH=True,ALLOW_ANONYMOUS_CHECKLIST=False,ATOMIC_RATE_LIMITING=False,DOCUMENT_ANALYSIS_RATE='1000/min')
class StagingAPIFaultTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('synthetic-failure-user',password='TestOnly!StrongDatabasePassword247')
        self.user.user_permissions.add(Permission.objects.get(codename='analyze_document'))
        self.client=APIClient();self.client.force_authenticate(self.user)

    def test_database_failure_returns_no_analysis_or_private_trace(self):
        with patch('controllers.checklist_controller.ChecklistItem.objects.filter',side_effect=OperationalError('PRIVATE_ACCOUNT_VALUE')):
            response=self.client.get('/api/checklist')
        self.assertEqual(response.status_code,500)
        self.assertEqual(set(response.json()),{'code','message'})
        self.assertNotIn('PRIVATE_',response.content.decode())
        self.assertNotIn('summary',response.json())

    def test_database_unavailable_readiness_is_safe(self):
        with patch('controllers.readiness_controller.MigrationExecutor',side_effect=OperationalError('PRIVATE_DATABASE_PATH')):
            response=self.client.get('/api/ready')
        self.assertEqual(response.status_code,503);self.assertEqual(response.json(),{'status':'not_ready'})
        self.assertNotIn('PRIVATE_',response.content.decode())

    def test_missing_models_fail_before_any_download_or_fabricated_result(self):
        with TemporaryDirectory() as directory:
            worker=LocalDocumentWorker(model_root=directory,limits=DocumentLimits(timeout_seconds=5))
            try:
                with patch('services.documentAnalysis.upload.get_document_worker',return_value=worker):
                    response=self.client.post('/api/documents/analyze',{'file':SimpleUploadedFile('synthetic.png',image_bytes(),content_type='image/png')},format='multipart')
                self.assertEqual(response.status_code,503);self.assertEqual(response.json()['code'],'OCR_UNAVAILABLE')
                self.assertNotIn('evidence',response.json())
                self.assertEqual(list(Path(directory).iterdir()),[])
            finally:worker.close()

    def test_simulated_storage_exhaustion_fails_closed_without_filling_disk(self):
        with TemporaryDirectory() as directory,override_settings(ATOMIC_RATE_LIMITING=True,RATE_LIMIT_DB=Path(directory)/'rates.sqlite3'):
            with patch('security.rate_limit.sqlite3.connect',side_effect=sqlite3.OperationalError('database or disk is full PRIVATE_CREDENTIAL')):
                response=self.client.get('/api/health')
            self.assertEqual(response.status_code,503);self.assertIn('Retry-After',response)
            self.assertEqual(response.json()['code'],'SERVICE_BUSY')
            self.assertNotIn('PRIVATE_',response.content.decode())

    def test_development_registration_works_without_granting_production_ocr(self):
        with override_settings(ALLOW_REGISTRATION=True):
            client=APIClient()
            response=client.post('/api/auth/register',{'username':'synthetic-new-account','password':'TestOnly!LongRegistrationPassword247'},format='json')
            self.assertEqual(response.status_code,201)
            self.assertFalse(response.json()['user']['canAnalyzeDocuments'])
            client.credentials(HTTP_AUTHORIZATION='Token '+response.json()['token'])
            denied=client.post('/api/documents/analyze',{},format='json')
            self.assertEqual(denied.status_code,403)
