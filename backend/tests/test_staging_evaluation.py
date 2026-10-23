import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from evaluation.annotations import create_manifest
from evaluation.review import apply_reviews,digest,summary,template
from evaluation.runner import load_manifest


class PrivateAnnotationTests(TestCase):
    def test_fifty_real_entries_start_unannotated_without_copying_or_inventing_facts(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);inputs=[]
            for index in range(50):
                path=root/f'private-{index}.png';path.write_bytes(b'unchanged-input');inputs.append(path)
            destination=root/'annotation'/'manifest.json'
            self.assertEqual(create_manifest(inputs,destination,provenance='real_private'),50)
            data=json.loads(destination.read_text());self.assertEqual(len(data['documents']),50)
            self.assertTrue(all(d['category'] is None and d['groundTruth']=={'complete':False,'annotationSource':'Pending independent manual annotation.','deadlines':[],'amounts':[]} for d in data['documents']))
            self.assertEqual(destination.stat().st_mode&0o777,0o600)
            self.assertTrue(all(path.read_bytes()==b'unchanged-input' for path in inputs))
            with self.assertRaises(ValueError):load_manifest(destination)
            with self.assertRaises(FileExistsError):create_manifest(inputs,destination,provenance='real_private')

    def test_over_capacity_duplicates_or_false_provenance_are_rejected(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);path=root/'input.png';path.touch()
            for inputs,provenance in [([path]*51,'real_private'),([path,path],'real_private'),([path],'invented_real')]:
                with self.subTest(provenance=provenance),self.assertRaises(ValueError):create_manifest(inputs,root/'out.json',provenance=provenance)


class StageReviewTests(TestCase):
    def setup_run(self,root):
        prediction={'source':'deterministic','evidence':[{'text':'PRIVATE_REVIEW_MARKER'}]}
        (root/'medium-side1600-R001-0-private.json').write_text(json.dumps(prediction))
        metrics={'profiles':{'medium-side1600':{'rows':[{'documentId':'R001','repeat':0,'resources':{'outcome':'ok'}}]}}}
        return metrics,prediction

    def test_unreviewed_causes_remain_null_and_review_does_not_copy_source_text(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);metrics,_=self.setup_run(root)
            review=template(metrics,root)
            self.assertNotIn('PRIVATE_REVIEW_MARKER',json.dumps(review))
            result=apply_reviews(metrics,root,review)
            scored=summary(result['profiles']['medium-side1600']['rows'])
            self.assertEqual(scored['reviewedRequests'],0);self.assertIsNone(scored['ocr_recognition'])

    def test_manual_ocr_field_and_interpretation_errors_are_separate(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);metrics,_=self.setup_run(root);review=template(metrics,root)
            review['reviews'][0].update(reviewed=True,errors=[{'stage':'ocr_recognition','category':'wrong_characters'},{'stage':'field_extraction','category':'wrong_label_association'},{'stage':'interpretation','category':'primary_selection'}])
            result=apply_reviews(metrics,root,review);scored=summary(result['profiles']['medium-side1600']['rows'])
            self.assertEqual(scored,{'reviewedRequests':1,'field_extraction':1,'interpretation':1,'ocr_recognition':1,'unresolved':0})

    def test_changed_predictions_unknown_stage_and_notes_are_rejected(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);metrics,prediction=self.setup_run(root);review=template(metrics,root)
            review['reviews'][0].update(reviewed=True,errors=[{'stage':'inferred_guess','category':'wrong_date'}])
            with self.assertRaises(ValueError):apply_reviews(metrics,root,review)
            review['reviews'][0]['errors']=[{'stage':'field_extraction','category':'wrong_date','note':'PRIVATE_MARKER'}]
            with self.assertRaises(ValueError):apply_reviews(metrics,root,review)
            review['reviews'][0]['errors']=[]
            (root/'medium-side1600-R001-0-private.json').write_text(json.dumps({'changed':True}))
            with self.assertRaises(ValueError):apply_reviews(metrics,root,review)

    def test_profile_path_traversal_and_duplicate_reviews_are_rejected(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);metrics,_=self.setup_run(root);review=template(metrics,root)
            review['reviews']*=2
            with self.assertRaises(ValueError):apply_reviews(metrics,root,review)
            metrics['profiles']['../../PRIVATE_PATH']=metrics['profiles'].pop('medium-side1600')
            with self.assertRaises(ValueError):template(metrics,root)
