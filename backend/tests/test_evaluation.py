"""Evaluation logic tests contain only synthetic fields; no model initialization."""
import unittest

from evaluation.metrics import edit_distance, score_fields, score_result
from evaluation.profiles import OCRProfile


class EvaluationTests(unittest.TestCase):
    def test_false_payment_values_are_penalized_only_with_complete_annotations(self):
        predictions=[{"kind":"payment","value":100,"label":"Payment amount","status":"verified"},
                     {"kind":"paid","value":200,"label":"Already-paid amount","status":"verified"},
                     {"kind":"late_fee","value":300,"label":"Late fee","status":"unverified"}]
        truth=[{"kind":"payment","value":100,"label":"Payment amount"}]
        complete=score_fields(predictions,truth,"value",True)
        self.assertEqual(complete["matched"],1)
        self.assertEqual(complete["falsePositive"],1)
        self.assertFalse(complete["exact"])
        partial=score_fields(predictions,truth,"value",False)
        self.assertIsNone(partial["falsePositive"])
        self.assertIsNone(partial["exact"])
        self.assertEqual(partial["unscoredPredictions"],1)

    def test_dates_must_match_role_as_well_as_value(self):
        result=score_fields([{"kind":"usage_expiration","date":"2031-01-01","status":"verified","label":"Usage expiration date"}],
                            [{"kind":"payment","date":"2031-01-01"}],"date",True)
        self.assertEqual(result["matched"],0)
        self.assertEqual(result["falsePositive"],1)

    def test_duplicates_do_not_inflate_true_positives(self):
        value={"kind":"payment","value":100,"status":"verified","label":"Payment amount"}
        result=score_fields([value,value],[{"kind":"payment","value":100}],"value",True)
        self.assertEqual(result["matched"],1)
        self.assertEqual(result["verified"],1)
        self.assertEqual(result["labelScored"],0)  # No annotation of the precise English label.

    def test_uncertainty_and_unknown_types_are_scored_without_coercion(self):
        result={"deadlines":[],"amounts":[],"documentType":None,"primaryDeadline":None,"primaryAmount":None,
                "extractionStatus":"unverified","evidence":[]}
        metrics=score_result(result,{"complete":True,"documentType":None,"primaryAmount":None,"extractionStatus":"unverified"})
        self.assertTrue(metrics["documentTypeCorrect"])
        self.assertTrue(metrics["primaryAmountCorrect"])
        self.assertIsNone(metrics["primaryDeadlineCorrect"])
        self.assertIsNone(metrics["characters"])

    def test_character_error_scoring_is_exact_and_bounded(self):
        self.assertEqual(edit_distance("納期限","納期日"),1)
        result={"deadlines":[],"amounts":[],"evidence":[{"text":"納期日"}]}
        metrics=score_result(result,{"transcription":"納期限","complete":True})
        self.assertEqual(metrics["characterEdits"],1)
        self.assertEqual(metrics["characters"],3)
        metrics=score_result(result,{"transcription":"字"*5001})
        self.assertEqual(metrics["textScoringSkipped"],"bounded_edit_distance_limit")

    def test_tiny_and_unbounded_profiles_are_rejected(self):
        for kwargs in ({"recognition":"tiny"},{"detection":"tiny"},{"batch_size":20},{"cpu_threads":999}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                OCRProfile("invalid",**kwargs)


class EvaluationPublicationTests(unittest.TestCase):
    def test_published_csv_excludes_private_paths_text_and_unscored_false_positive_claims(self):
        import csv,json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from evaluation.report import publish
        analysis={"deadlines":[],"amounts":[],"evidence":[{"text":"PRIVATE_SYNTHETIC_MARKER"}]}
        accuracy=score_result(analysis,{"complete":False})
        row={"documentId":"R001","category":"unknown","provenance":"real_private",
             "privatePath":"/private/PRIVATE_SYNTHETIC_MARKER.png","sourceText":"PRIVATE_SYNTHETIC_MARKER",
             "resources":{"outcome":"ok","peakRssBytes":1048576,"elapsedSeconds":1.,"cold":True},"accuracy":accuracy}
        with TemporaryDirectory() as directory:
            source=Path(directory)/"input.json";output=Path(directory)/"report.csv"
            source.write_text(json.dumps({"profiles":{"baseline-medium":{"rows":[row]}}}))
            publish([source],output)
            self.assertNotIn("PRIVATE_SYNTHETIC_MARKER",output.read_text())
            with output.open() as file:
                result=list(csv.DictReader(file))[0]
            self.assertEqual(result["falseDeadlinesCompleteGT"],"")
            self.assertEqual(result["falseAmountsCompleteGT"],"")

    def test_unknown_profile_metadata_is_not_published(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from evaluation.report import publish
        with TemporaryDirectory() as directory:
            source=Path(directory)/"input.json";output=Path(directory)/"report.csv"
            source.write_text(json.dumps({"profiles":{"PRIVATE_SYNTHETIC_MARKER":{"rows":[]}}}))
            with self.assertRaises(ValueError):publish([source],output)
            self.assertFalse(output.exists())
