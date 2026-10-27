"""Confirmed Step 12 synthetic failures; never private document literals."""
from unittest import TestCase
from evaluation.challenges import cases,analyze_case
from evaluation.quality import score_document
from tests.test_document_fields import analyze


class ExtractionAccuracyRegressions(TestCase):
    def case(self,name):return next(c for c in cases() if c['variant']==name)

    def test_illustrative_deadline_stays_unverified(self):
        result=analyze_case(self.case('illustrative_deadline'))
        self.assertIsNone(result['primaryDeadline']);self.assertEqual(result['deadlines'][0]['status'],'unverified')
        self.assertIn('illustrative',result['deadlines'][0]['reasons'][0])

    def test_illustrative_amount_stays_unverified(self):
        result=analyze_case(self.case('illustrative_amount'))
        self.assertIsNone(result['primaryAmount']);self.assertEqual(result['amounts'][0]['status'],'unverified')

    def test_illustrative_document_type_is_not_confirmed(self):
        self.assertIsNone(analyze_case(self.case('illustrative_type'))['documentType'])

    def test_illustrative_paid_stamp_does_not_suppress_real_amount(self):
        result=analyze_case(self.case('illustrative_paid_stamp'))
        self.assertEqual(result['primaryAmount'],5000);self.assertEqual(result['completedPaymentEvidenceIds'],[])

    def test_literal_kanji_era_numerals_are_converted_without_digit_repair(self):
        result=analyze_case(self.case('kanji_era'))
        self.assertEqual(result['primaryDeadline'],'2031-06-30')
        for text in ['平成三十一年五月一日','令和十三年二月三十日','令和十十三年六月三十日','令和B年六月三十日']:
            with self.subTest(text=text):self.assertIsNone(analyze((f'納期限 {text}',0,0,500,25))['primaryDeadline'])

    def test_example_qualifier_does_not_cross_a_clause_or_separate_row(self):
        result=analyze(('記入例。納付額 7,300円',0,0,500,25),('見本',0,100,100,125))
        self.assertEqual(result['primaryAmount'],7300)

    def test_all_controlled_scenarios_keep_safety_expectations(self):
        for case in cases():
            with self.subTest(case=case['variant']):
                result=analyze_case(case);score=score_document(result,case['groundTruth'])
                for name in ['documentType','primaryAmount','primaryDeadline','extractionStatus']:
                    self.assertIsNot(score[name+'Correct'],False)
                self.assertEqual(score['deadlines']['falsePositive'],0)
                self.assertEqual(score['amounts']['falsePositive'],0)
                # Low confidence remains an honest FN, even though withholding
                # verification and the primary amount is the correct safety behavior.
                if case['variant']!='low_confidence':self.assertTrue(score['amounts']['exact'])
                self.assertTrue(score['deadlines']['exact'])
                self.assertEqual(score['uncertainty']['correct'],score['uncertainty']['scored'])
