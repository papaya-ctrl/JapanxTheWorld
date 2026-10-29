"""Synthetic-only regression data; no private sample values or OCR models."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from pydantic import ValidationError

from evaluation.schema import Dataset
from evaluation.pilot import inventory,review_gaps,REVIEW_FLAGS
from evaluation.quality_report import public_report
from evaluation.quality import score_document
from evaluation.accuracy import native,report
from tests.test_document_fields import analyze
from tests.test_accuracy_evaluation import result,truth


def document(identifier='R001',provenance='real_private'):
    return {'id':identifier,'path':'/private/authorized/synthetic-test-only.png',
        'inputSha256':'1'*64,'provenance':provenance,'category':'unknown',
        'authorizationConfirmed':True,'groundTruth':{'complete':False,
            'verification':{'status':'unreviewed','method':'pending'}}}


def reviewed_document(identifier='R001',provenance='real_private'):
    item=document(identifier,provenance)
    item['groundTruth']={'complete':True,'verification':{'status':'verified','method':'independent_human','reviewerId':'H001'},
        'documentType':None,'deadlines':[],'amounts':[],'primaryDeadline':None,'primaryAmount':None,
        'extractionStatus':'no_fields','missingFields':['deadlines','amounts'],'uncertainFields':[],
        'englishInterpretation':'No payment facts are established by this notice.',
        'pilotReview':{'reviewerId':'H001',**{flag:True for flag in REVIEW_FLAGS}}}
    return item


class HumanPilotGateTests(TestCase):
    def test_one_unreviewed_issued_document_does_not_claim_a_completed_pilot(self):
        data=Dataset.model_validate({'documents':[document()]})
        summary=inventory(data)
        self.assertEqual(summary['targetIssuedDocuments'],40)
        self.assertEqual(summary['groups']['issued_documents']['samples'],1)
        self.assertEqual(summary['groups']['issued_documents']['pilotEligible'],0)
        self.assertFalse(summary['realAccuracyEstablished'])

    def test_public_sample_forms_require_distinct_ids_and_remain_separate(self):
        issued=reviewed_document();form=reviewed_document('P001','public_sample_form')
        form['path']='/private/forms/synthetic-test-only.png';form['inputSha256']='2'*64
        summary=inventory(Dataset.model_validate({'documents':[issued,form]}))
        self.assertEqual(summary['groups']['issued_documents']['samples'],1)
        self.assertEqual(summary['groups']['public_sample_forms']['samples'],1)
        wrong=deepcopy(form);wrong['id']='R002'
        with self.assertRaises(ValidationError):Dataset.model_validate({'documents':[wrong]})

    def test_all_human_review_requirements_must_be_explicit(self):
        item=reviewed_document();self.assertEqual(review_gaps(item),[])
        for flag in REVIEW_FLAGS:
            changed=deepcopy(item);changed['groundTruth']['pilotReview'][flag]=False
            with self.subTest(flag=flag):self.assertIn('human_review_checklist_incomplete',review_gaps(changed))
        changed=deepcopy(item);del changed['groundTruth']['missingFields']
        self.assertIn('required_review_fields_missing',review_gaps(changed))
        changed=deepcopy(item);changed['groundTruth']['pilotReview']['reviewerId']='H002'
        self.assertIn('reviewer_binding_missing',review_gaps(changed))

    def test_formal_pilot_gate_stops_before_model_loading_for_partial_truth(self):
        with patch('evaluation.accuracy.documents',return_value=[document()]),patch('services.ocr.worker.LocalDocumentWorker') as worker:
            with self.assertRaises(ValueError):native('/private/unused','/private/output',require_pilot_review=True)
            worker.assert_not_called()

    def test_english_interpretation_is_separate_from_original_japanese_evidence(self):
        item=reviewed_document();item['groundTruth']['englishInterpretation']='納期限を確認'
        with self.assertRaises(ValidationError):Dataset.model_validate({'documents':[item]})

    def test_publication_cannot_count_public_forms_as_issued_coverage(self):
        row={'id':'P001','category':'utility','provenance':'public_sample_form','outcome':'ok','resources':{},
            'accuracy':score_document(result(),truth())}
        output=public_report({'mode':'fresh_native','rows':[row]})
        self.assertEqual(output['datasetGroupCounts']['issued_documents'],0)
        self.assertEqual(output['datasetGroupCounts']['public_sample_forms'],1)
        self.assertIn('utility',report([row],'fresh_native')['missingRealCategories'])

    def test_encrypted_legacy_known_facts_remain_partial_and_need_explicit_opt_in(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from cryptography.fernet import Fernet
        from evaluation.vault import save_json,write_private
        from evaluation.accuracy import documents
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.png';source.write_bytes(b'synthetic-test-only')
            key=root/'keys/key';write_private(key,Fernet.generate_key())
            item={'id':'R001','path':str(source),'category':'unknown','provenance':'real_private',
                'groundTruth':truth(complete=False)}
            manifest=root/'annotations/legacy.fernet';save_json(manifest,{'schemaVersion':1,'documents':[item]},key)
            with self.assertRaises(ValueError):documents(manifest,key=key)
            loaded=documents(manifest,legacy=True,key=key)
            self.assertFalse(loaded[0]['groundTruth']['complete'])


class ConfirmedBlurRecognitionRegression(TestCase):
    def test_observed_high_confidence_wrong_label_is_not_repaired_or_verified(self):
        # Observed on both generated blurred slip sections after full detection,
        # detected-crop recognition and oracle-crop recognition (Step 13).
        observed=analyze(('納付额5,000円',24,355,210,390,.957499),
                         ('納付额5,000円',24,450,210,485,.957499))
        self.assertIsNone(observed['primaryAmount'])
        self.assertEqual(observed['amounts'][0]['value'],5000)
        self.assertEqual(observed['amounts'][0]['status'],'unverified')
        self.assertEqual(observed['amounts'][0]['kind'],'unknown')
        self.assertEqual(observed['amounts'][0]['occurrences'],2)
        self.assertEqual(observed['evidence'][0]['text'],'納付额5,000円')
        self.assertFalse(any(a['status']=='verified' for a in observed['amounts']))

    def test_control_with_correctly_recognized_label_keeps_existing_association(self):
        control=analyze(('納付額5,000円',24,355,210,390,.957499),
                        ('納付額5,000円',24,450,210,485,.957499))
        self.assertEqual(control['primaryAmount'],5000)
        self.assertEqual(control['amounts'][0]['kind'],'payment')
        self.assertEqual(control['amounts'][0]['occurrences'],2)
