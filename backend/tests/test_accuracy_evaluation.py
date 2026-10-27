"""Independent annotation, denominator, privacy and admission regression tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from cryptography.fernet import Fernet
from pydantic import ValidationError

from evaluation.accuracy import initialize,documents,native
from evaluation.quality import score_document,summarize_quality
from evaluation.schema import Dataset,truth_dict
from evaluation.vault import save_json,read_json,write_private


def truth(**extra):
    return {'complete':True,'deadlines':[{'kind':'payment','date':'2031-06-30','label':'Payment deadline'}],
            'amounts':[{'kind':'payment','value':5000,'label':'Payment amount'}],**extra}


def result(**extra):
    return {'deadlines':[{'kind':'payment','date':'2031-06-30','label':'Payment deadline','status':'verified','evidenceIds':['b1']}],
        'amounts':[{'kind':'payment','value':5000,'label':'Payment amount','status':'verified','evidenceIds':['b2'],'occurrences':1}],
        'primaryDeadline':'2031-06-30','primaryAmount':5000,'documentType':None,'extractionStatus':'verified',
        'evidence':[{'id':'b1','text':'納期限 令和13年6月30日','page':1},{'id':'b2','text':'納付額 5,000円','page':1}],**extra}


class AccuracyMetricTests(TestCase):
    def row(self,prediction,gt,outcome='ok'):
        return {'outcome':outcome,'accuracy':score_document(prediction,gt,outcome=outcome),'resources':{}}

    def test_failed_processing_remains_false_negative_and_exact_failure(self):
        summary=summarize_quality([self.row(result(),truth()),self.row(None,truth(),outcome='ANALYSIS_TIMEOUT')])
        self.assertEqual(summary['deadlines']['recall'],{'numerator':1,'denominator':2,'value':.5})
        self.assertEqual(summary['amounts']['exactMatch']['value'],.5)
        self.assertEqual(summary['failedOrNotExecuted'],1)

    def test_partial_truth_cannot_claim_precision_or_full_recall(self):
        gt=truth();gt['complete']=False
        score=summarize_quality([self.row(result(),gt)])
        self.assertIsNone(score['deadlines']['precision']['value']);self.assertIsNone(score['deadlines']['recall']['value'])
        self.assertIsNone(score['deadlines']['falsePositive']);self.assertEqual(score['deadlines']['knownFieldRecall']['value'],1)

    def test_wrong_role_is_both_false_positive_and_false_negative(self):
        prediction=result();prediction['deadlines'][0]['kind']='usage_expiration'
        score=summarize_quality([self.row(prediction,truth())])['deadlines']
        self.assertEqual((score['truePositive'],score['falsePositive'],score['falseNegative']),(0,1,1))
        self.assertEqual(score['falsePositiveDocumentRate']['value'],1)

    def test_missed_fields_and_wrong_pages_stay_in_label_evidence_denominators(self):
        gt=truth();gt['deadlines'][0]['evidence']=[{'page':2,'text':'納期限 令和13年6月30日'}]
        score=score_document(result(amounts=[]),gt)
        self.assertEqual(score['deadlines']['labelCorrect'],0);self.assertEqual(score['deadlines']['evidenceCorrect'],0)
        self.assertEqual(score['amounts']['labelExpected'],1);self.assertEqual(score['amounts']['labelCorrect'],0)

    def test_uncertain_predictions_are_false_negatives_without_becoming_false_positives(self):
        prediction=result();prediction['amounts'][0]['status']='unverified';prediction['primaryAmount']=None
        score=summarize_quality([self.row(prediction,truth())])['amounts']
        self.assertEqual(score['falseNegative'],1);self.assertEqual(score['unverifiedPredictions'],1)
        self.assertEqual(score['falsePositive'],0);self.assertIsNone(score['precision']['value'])

    def test_duplicates_are_not_hidden_by_set_based_true_positive_scoring(self):
        prediction=result();prediction['amounts']*=2
        gt=truth(repeatedAmounts=[{'kind':'payment','value':5000,'occurrences':2}])
        score=score_document(prediction,gt)
        self.assertEqual(score['amounts']['matched'],1);self.assertEqual(score['amounts']['duplicateVerifiedEntries'],1)
        self.assertEqual(score['deduplication'],{'correct':0,'scored':1})

    def test_missing_and_ambiguous_expectations_require_explicit_safe_output(self):
        prediction=result(primaryAmount=5000)
        gt=truth(uncertainFields=[{'field':'amounts','kind':'payment','value':5000}],missingFields=['primaryAmount'])
        score=score_document(prediction,gt)
        self.assertEqual(score['uncertainty']['correct'],0);self.assertEqual(score['missingFields']['correct'],0)

    def test_era_conversion_checks_bind_to_original_literal_and_page(self):
        gt=truth(eraChecks=[{'literal':'令和13年6月30日','expectedDate':'2031-06-30','kind':'payment','page':1}])
        self.assertEqual(score_document(result(),gt)['eraConversion']['correct'],1)
        prediction=result();prediction['evidence'][0]['text']='納期限 2031年6月30日'
        self.assertEqual(score_document(prediction,gt)['eraConversion']['correct'],0)

    def test_not_executed_is_explicitly_pending_rather_than_invented_accuracy(self):
        score=summarize_quality([self.row(None,truth(),outcome='NOT_EXECUTED_START_MEMORY_GUARD')])
        self.assertEqual(score['notExecuted'],1);self.assertEqual(score['pendingKnownDeadlines'],1)
        self.assertIsNone(score['deadlines']['exactMatch']['value']);self.assertEqual(score['unreviewedAnnotations'],0)

    def test_successful_ocr_on_unreviewed_truth_never_becomes_an_accuracy_claim(self):
        gt={'verification':{'status':'unreviewed'},'complete':False,'deadlines':[],'amounts':[]}
        row=self.row(result(),gt)
        self.assertTrue(row['accuracy']['processingSucceeded']);self.assertFalse(row['accuracy']['scorable'])
        summary=summarize_quality([row])
        self.assertEqual(summary['successful'],1);self.assertEqual(summary['unreviewedAnnotations'],1)
        self.assertIsNone(summary['amounts']['precision']['value'])


class AnnotationWorkflowTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def scaffold(self,count=1):
        inputs=[]
        for i in range(count):
            path=self.root/f'input{i}.png';path.write_bytes(f'untouched-{i}'.encode());inputs.append(path)
        manifest=self.root/'annotations/manifest.json';initialize(inputs,manifest,authorized=True)
        return inputs,manifest

    def test_target_forty_starts_unreviewed_with_hashes_without_invented_facts(self):
        inputs,manifest=self.scaffold(40);dataset=Dataset.model_validate_json(manifest.read_bytes())
        self.assertEqual(dataset.targetRealDocuments,40);self.assertEqual(len(dataset.documents),40)
        self.assertEqual(truth_dict(dataset.documents[0]),{'verification':{'status':'unreviewed','method':'pending'},'complete':False,'deadlines':[],'amounts':[]})
        self.assertTrue(all(p.read_bytes()==f'untouched-{i}'.encode() for i,p in enumerate(inputs)))
        self.assertEqual(manifest.stat().st_mode&0o777,0o600)

    def test_ocr_cannot_be_declared_verified_human_truth(self):
        _,manifest=self.scaffold();raw=json.loads(manifest.read_text());gt=raw['documents'][0]['groundTruth']
        gt['complete']=True
        with self.assertRaises(ValidationError):Dataset.model_validate(raw)
        gt['verification']={'status':'verified','method':'synthetic_specification'}
        with self.assertRaises(ValidationError):Dataset.model_validate(raw)
        gt['verification']={'status':'verified','method':'independent_human'}
        with self.assertRaises(ValidationError):Dataset.model_validate(raw)

    def test_partial_review_does_not_coerce_omitted_primary_to_null_assertion(self):
        _,manifest=self.scaffold();raw=json.loads(manifest.read_text());gt=raw['documents'][0]['groundTruth']
        gt['verification']={'status':'partial','method':'independent_human','reviewerId':'H001'}
        raw['documents'][0]['category']='unknown'
        dataset=Dataset.model_validate(raw);self.assertNotIn('primaryAmount',truth_dict(dataset.documents[0]))

    def test_complete_review_cannot_silently_invent_empty_field_lists(self):
        _,manifest=self.scaffold();raw=json.loads(manifest.read_text());raw['documents'][0]['category']='unknown'
        raw['documents'][0]['groundTruth']={'complete':True,'verification':{'status':'verified','method':'independent_human','reviewerId':'H001'}}
        with self.assertRaises(ValidationError):Dataset.model_validate(raw)

    def test_missing_amount_does_not_conflict_with_a_valid_annotated_zero(self):
        from evaluation.schema import GroundTruth
        data={'complete':True,'verification':{'status':'verified','method':'synthetic_specification'},'deadlines':[],
            'amounts':[{'kind':'payment','value':0,'label':'Payment amount','evidence':[{'text':'納付額 0円','page':1}]}],
            'primaryAmount':0,'missingFields':['primaryAmount']}
        with self.assertRaises(ValidationError):GroundTruth.model_validate(data)

    def test_changed_images_and_unauthorized_inputs_fail_before_ocr(self):
        inputs,manifest=self.scaffold();inputs[0].write_bytes(b'changed')
        with self.assertRaises(ValueError):documents(manifest)
        raw=json.loads(manifest.read_text());raw['documents'][0]['authorizationConfirmed']=False
        manifest.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):documents(manifest)

    def test_duplicate_bytes_cannot_inflate_dataset_size(self):
        _,manifest=self.scaffold();raw=json.loads(manifest.read_text());other=deepcopy(raw['documents'][0]);other['id']='R002';other['path']=str(self.root/'other.png');raw['documents'].append(other)
        with self.assertRaises(ValidationError):Dataset.model_validate(raw)

    def test_small_memory_exception_never_allows_real_documents(self):
        _,manifest=self.scaffold()
        with self.assertRaises(ValueError):native(manifest,self.root/'outputs',small=True)

    def test_normal_memory_guard_retains_all_planned_samples_without_starting_a_model(self):
        _,manifest=self.scaffold(2)
        with patch('services.ocr.resources.available_memory_bytes',return_value=4*1024**3),patch('services.ocr.worker.LocalDocumentWorker.analyze') as analyze:
            report=native(manifest,self.root/'outputs');analyze.assert_not_called()
        self.assertEqual(len(report['rows']),2)
        self.assertTrue(all(r['outcome']=='NOT_EXECUTED_START_MEMORY_GUARD' for r in report['rows']))


class EvaluationPrivacyTests(TestCase):
    def test_authenticated_encryption_permissions_and_no_overwrite(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);key=root/'keys/key';write_private(key,Fernet.generate_key())
            artifact=root/'results/private.fernet';data={'evidence':[{'text':'SYNTHETIC_PRIVATE_MARKER'}]}
            save_json(artifact,data,key);self.assertNotIn(b'SYNTHETIC_PRIVATE_MARKER',artifact.read_bytes())
            self.assertEqual(read_json(artifact,key),data);self.assertEqual(artifact.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):save_json(artifact,data,key)
            key.chmod(0o644)
            with self.assertRaises(ValueError):read_json(artifact,key)

    def test_cli_error_never_echoes_private_source_or_path(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);manifest=root/'PRIVATE_PATH_MARKER.json';manifest.write_text('{"PRIVATE_CONTENT_MARKER":true}')
            backend=Path(__file__).resolve().parents[1]
            process=subprocess.run([sys.executable,'-m','evaluation.accuracy','run','--manifest',str(manifest),'--output',str(root/'output')],cwd=backend,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(process.returncode,0)
            self.assertNotIn('PRIVATE_',process.stdout+process.stderr);self.assertNotIn('Traceback',process.stderr)

    def test_publisher_drops_paths_facts_hashes_and_arbitrary_notes(self):
        from evaluation.quality_report import public_report
        row={'id':'R001','category':'unknown','provenance':'real_private','outcome':'ok',
            'accuracy':score_document(result(),truth()),'resources':{'elapsedSeconds':1.,'privatePath':'PRIVATE_MARKER'},
            'groundTruth':{'text':'PRIVATE_MARKER'},'privatePath':'PRIVATE_MARKER','notes':'PRIVATE_MARKER'}
        output=public_report({'mode':'fresh_native','rows':[row],'privateNotes':'PRIVATE_MARKER'})
        self.assertNotIn('PRIVATE_MARKER',json.dumps(output))
        self.assertEqual(output['groups']['real_private']['summary']['deadlines']['recall']['denominator'],1)
        self.assertIsNone(output['groups']['real_private']['errorStages']['ocr_recognition'])

    def test_publisher_rejects_secret_strings_disguised_as_metadata_or_counts(self):
        from evaluation.quality_report import public_report
        row={'id':'R001','category':'unknown','provenance':'real_private','outcome':'ok','accuracy':score_document(result(),truth()),'resources':{}}
        for key in ['id','category','outcome']:
            changed=deepcopy(row);changed[key]='PRIVATE_MARKER'
            with self.assertRaises(ValueError):public_report({'mode':'fresh_native','rows':[changed]})
        row['accuracy']['deadlines']['matched']='PRIVATE_MARKER'
        with self.assertRaises(ValueError):public_report({'mode':'fresh_native','rows':[row]})

    def test_review_binds_prediction_and_truth_and_real_causes_require_human(self):
        from evaluation.quality_review import template,apply
        from evaluation.review import digest
        with TemporaryDirectory() as directory:
            root=Path(directory);key=root/'keys/key';write_private(key,Fernet.generate_key());outputs=root/'outputs'
            save_json(outputs/'R001.result.fernet',result(),key)
            metrics={'rows':[{'id':'R001','outcome':'ok','provenance':'real_private','groundTruthSha256':digest(truth())}]}
            reviews=template(metrics,outputs,key)
            self.assertNotIn('納期限',json.dumps(reviews,ensure_ascii=False))
            reviews['reviews'][0].update(reviewed=True,reviewerKind='controlled_synthetic_investigation',errors=[{'stage':'ocr_recognition','category':'wrong_characters'}])
            with self.assertRaises(ValueError):apply(metrics,outputs,key,reviews)
            reviews['reviews'][0]['reviewerKind']='independent_human'
            checked=apply(metrics,outputs,key,reviews)
            self.assertEqual(checked['rows'][0]['manualErrorReview']['counts']['ocr_recognition'],1)
            metrics['rows'][0]['groundTruthSha256']='changed'
            with self.assertRaises(ValueError):apply(metrics,outputs,key,reviews)

    def test_annotations_can_be_encrypted_without_promoting_their_review_status(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);key=root/'keys/key';write_private(key,Fernet.generate_key());source=root/'synthetic-input.png';source.write_bytes(b'synthetic-input')
            encrypted=root/'annotations/manifest.fernet';initialize([source],encrypted,authorized=True,key=key)
            self.assertNotIn(str(source).encode(),encrypted.read_bytes())
            loaded=documents(encrypted,key=key)
            self.assertEqual(loaded[0]['groundTruth']['verification']['status'],'unreviewed')
