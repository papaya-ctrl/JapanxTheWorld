"""Synthetic-only tests: standard library, no OCR model or network dependency."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from services.documentAnalysis.analyzer import analyze_ocr_document
from services.ocr.paddle_extractor import analyze_file


def page(*items, page_index=None):
    """Items are text, left, top, right, bottom, optional confidence."""
    return {"page_index": page_index,
            "rec_texts": [x[0] for x in items],
            "rec_boxes": [list(x[1:5]) for x in items],
            "rec_scores": [x[5] if len(x) > 5 else .99 for x in items]}


def analyze(*items):
    return analyze_ocr_document([page(*items)])


class DocumentFieldTests(unittest.TestCase):
    def test_health_insurance_tax(self):
        result = analyze(("国民健康保険税 納付書", 0, 0, 300, 20),
                         ("納期限 令和8年11月2日", 0, 60, 300, 80),
                         ("納付額 ￥18,000", 0, 100, 250, 120))
        self.assertEqual(result["documentType"], "National Health Insurance Tax")
        self.assertEqual(result["primaryDeadline"], "2026-11-02")
        self.assertEqual(result["primaryAmount"], 18000)
        self.assertEqual(result["extractionStatus"], "verified")
        json.dumps(result, allow_nan=False)
        # Japanese is retained in evidence, never in generated prose/labels.
        without_evidence = dict(result, evidence=[])
        self.assertFalse(any('\u3040' <= c <= '\u9fff' for c in json.dumps(without_evidence, ensure_ascii=False)))
        self.assertEqual(result["evidence"][0]["text"], "国民健康保険税 納付書")

    def test_identical_amounts_not_summed(self):
        result = analyze(*[("納付額 18,000円", 0, y, 220, y + 20) for y in (0, 100, 200)])
        self.assertEqual(result["primaryAmount"], 18000)
        self.assertEqual(len(result["amounts"]), 1)
        self.assertEqual(result["amounts"][0]["occurrences"], 3)
        self.assertEqual(len(result["amounts"][0]["evidenceIds"]), 3)

    def test_distinguish_dates(self):
        result = analyze(("発行日 2026年1月3日", 0, 0, 300, 20),
                         ("領収日 2026年2月4日", 0, 60, 300, 80),
                         ("請求期間 2026年3月1日〜2026年3月31日", 0, 120, 500, 140),
                         ("利用期限 2026年4月5日", 0, 180, 300, 200),
                         ("納期限 2026年5月6日", 0, 240, 300, 260))
        self.assertEqual(result["primaryDeadline"], "2026-05-06")
        self.assertEqual({d["kind"] for d in result["deadlines"]}, {"payment", "usage_expiration"})
        self.assertEqual(result["amounts"], [])

    def test_split_date_and_shuffled_order(self):
        result = analyze(("2日", 235, 50, 265, 70), ("11月", 190, 50, 230, 70),
                         ("納期限", 0, 50, 70, 70), ("令和", 90, 50, 130, 70),
                         ("8年", 140, 50, 175, 70))
        self.assertEqual(result["primaryDeadline"], "2026-11-02")
        self.assertEqual([e["originalIndex"] for e in result["evidence"]], [2, 3, 4, 1, 0])
        self.assertEqual(len(result["deadlines"][0]["evidenceIds"]), 5)

    def test_japanese_eras(self):
        for text, expected in [("令和元年5月1日", "2019-05-01"), ("令和8年11月2日", "2026-11-02"),
                               ("平成31年4月30日", "2019-04-30"), ("昭和64年1月7日", "1989-01-07")]:
            with self.subTest(text=text):
                self.assertEqual(analyze(("納期限 " + text, 0, 0, 400, 20))["primaryDeadline"], expected)

    def test_explicit_date_followed_by_required_action(self):
        for action, kind in [("納付", "payment"), ("提出", "submission"), ("申請", "application")]:
            with self.subTest(action=action):
                result = analyze(("2026年11月2日までに" + action + "してください", 0, 0, 500, 20))
                self.assertEqual(result["primaryDeadline"], "2026-11-02")
                self.assertEqual(result["deadlines"][0]["kind"], kind)

    def test_invalid_amount_formats_are_not_repaired(self):
        for text in ["18,00円", "1,8000円", "18.5円", "-18000円", "−18000円", "△18000円", "不明"]:
            with self.subTest(text=text):
                result = analyze(("納付額 " + text, 0, 0, 300, 20))
                self.assertIsNone(result["primaryAmount"])
                self.assertEqual(result["amounts"][0]["status"], "unverified")

    def test_missing_labelled_values_are_unverified(self):
        result = analyze(("納期限 不明", 0, 0, 200, 20), ("納付額 未定", 0, 100, 200, 120))
        self.assertIsNone(result["primaryAmount"])
        self.assertIsNone(result["primaryDeadline"])
        self.assertEqual(result["amounts"][0]["status"], "unverified")
        self.assertEqual(result["deadlines"][0]["status"], "unverified")

    def test_low_confidence_amount_blocks_primary(self):
        result = analyze(("納付額 18000円", 0, 0, 300, 20),
                         ("納付額 19000円", 0, 100, 300, 120, .3))
        self.assertIsNone(result["primaryAmount"])
        self.assertEqual(result["extractionStatus"], "partial")

    def test_negated_actions_and_document_types(self):
        result = analyze(("これは納付書ではありません", 0, 0, 400, 20),
                         ("2026年11月2日までに支払わないでください", 0, 100, 500, 120))
        self.assertIsNone(result["documentType"])
        self.assertIsNone(result["primaryDeadline"])

    def test_conditional_label_in_separate_box(self):
        result = analyze(("納期限（予定）", 0, 0, 180, 20),
                         ("2026年11月2日", 0, 30, 240, 50))
        self.assertIsNone(result["primaryDeadline"])
        self.assertEqual(result["deadlines"][0]["status"], "unverified")

    def test_empty_paid_stamp_field_not_a_completed_payment(self):
        for text in ["支払済印", "□ 納付済", "支払済欄"]:
            with self.subTest(text=text):
                result = analyze(("納付額 18000円", 0, 0, 240, 20), (text, 0, 100, 180, 120))
                self.assertEqual(result["completedPaymentEvidenceIds"], [])
                self.assertEqual(result["primaryAmount"], 18000)

    def test_missing_deadline(self):
        result = analyze(("納付額 18000円", 0, 0, 220, 20))
        self.assertIsNone(result["primaryDeadline"])
        self.assertEqual(result["deadlines"], [])

    def test_missing_amount(self):
        result = analyze(("提出期限 2026/11/02", 0, 0, 300, 20))
        self.assertIsNone(result["primaryAmount"])
        self.assertEqual(result["amounts"], [])

    def test_unknown_document_still_extracts(self):
        result = analyze(("お知らせ", 0, 0, 130, 20), ("申請期限 2027-02-19", 0, 80, 280, 100),
                         ("請求金額 9500円", 0, 160, 220, 180))
        self.assertIsNone(result["documentType"])
        self.assertEqual(result["primaryDeadline"], "2027-02-19")
        self.assertEqual(result["primaryAmount"], 9500)

    def test_low_confidence_value_and_label(self):
        for scores in [(.4, .99), (.99, .4)]:
            with self.subTest(scores=scores):
                result = analyze(("納期限", 0, 0, 80, 20, scores[0]),
                                 ("2026年11月2日", 100, 0, 300, 20, scores[1]))
                self.assertIsNone(result["primaryDeadline"])
                self.assertEqual(result["deadlines"][0]["status"], "unverified")

    def test_corrupted_date_no_digit_repair(self):
        result = analyze(("納期限 令和B年11月2日", 0, 0, 280, 20))
        self.assertIsNone(result["primaryDeadline"])
        self.assertEqual(result["deadlines"][0]["status"], "unverified")
        self.assertEqual(result["amounts"], [])

    def test_already_paid_amount(self):
        result = analyze(("支払済金額 18000円", 0, 0, 280, 20))
        self.assertIsNone(result["primaryAmount"])
        self.assertEqual(result["amounts"][0]["kind"], "paid")

    def test_completed_payment_statement_suppresses_primary(self):
        result = analyze(("納付額 18000円", 0, 0, 240, 20), ("納付済", 0, 80, 90, 100))
        self.assertIsNone(result["primaryAmount"])
        self.assertTrue(result["completedPaymentEvidenceIds"])
        self.assertFalse(any("pay " in s.lower() for s in result["nextSteps"]))

    def test_conditional_paid_text_is_not_completion(self):
        result = analyze(("納付額 18000円", 0, 0, 240, 20), ("納付済の場合はご確認ください", 0, 80, 350, 100))
        self.assertEqual(result["primaryAmount"], 18000)
        self.assertEqual(result["completedPaymentEvidenceIds"], [])

    def test_multiple_genuine_deadlines(self):
        result = analyze(("納期限 2026年11月2日", 0, 0, 300, 20),
                         ("提出期限 2026年11月9日", 0, 100, 300, 120))
        self.assertEqual(len(result["deadlines"]), 2)
        self.assertTrue(all(d["status"] == "verified" for d in result["deadlines"]))
        self.assertIsNone(result["primaryDeadline"])

    def test_invalid_dates_and_era_boundaries(self):
        for text in ["2026年2月30日", "2026年13月2日", "令和元年4月30日", "令和0年11月2日",
                     "平成31年5月1日", "昭和64年1月8日", "2026/02/29", "0000年1月1日"]:
            with self.subTest(text=text):
                result = analyze(("納期限 " + text, 0, 0, 350, 20))
                self.assertIsNone(result["primaryDeadline"])
                self.assertEqual(result["deadlines"][0]["status"], "unverified")

    def test_amount_formats(self):
        for text in ["18,000", "18,000円", "¥18,000", "￥18000", "18000円", "１８，０００円"]:
            with self.subTest(text=text):
                self.assertEqual(analyze(("納付額 " + text, 0, 0, 300, 20))["primaryAmount"], 18000)

    def test_split_amount(self):
        result = analyze(("納付額", 0, 0, 80, 20), ("￥", 100, 0, 115, 20),
                         ("18,", 125, 0, 160, 20), ("000", 170, 0, 210, 20), ("円", 220, 0, 240, 20))
        self.assertEqual(result["primaryAmount"], 18000)
        self.assertEqual(len(result["amounts"][0]["evidenceIds"]), 5)

    def test_distinct_amount_roles(self):
        result = analyze(("請求金額 18000円", 0, 0, 300, 20), ("税額 15000円", 0, 70, 300, 90),
                         ("延滞金 3000円", 0, 140, 300, 160), ("支払済金額 1000円", 0, 210, 300, 230))
        self.assertEqual(result["primaryAmount"], 18000)
        self.assertEqual({a["kind"] for a in result["amounts"]}, {"billed", "tax", "late_fee", "paid"})

    def test_unlabelled_amount_is_unverified(self):
        result = analyze(("18,000円", 0, 0, 200, 20))
        self.assertIsNone(result["primaryAmount"])
        self.assertEqual(result["amounts"][0]["status"], "unverified")

    def test_unrelated_date_not_a_deadline(self):
        result = analyze(("2026/10/01", 0, 0, 200, 20), ("発行日 2026/09/01", 0, 100, 280, 120))
        self.assertEqual(result["deadlines"], [])
        self.assertIsNone(result["primaryDeadline"])

    def test_below_label_geometry(self):
        result = analyze(("納期限", 0, 0, 80, 20), ("納付額", 400, 0, 480, 20),
                         ("2026年11月2日", 0, 30, 220, 50), ("18000円", 400, 30, 550, 50))
        self.assertEqual(result["primaryDeadline"], "2026-11-02")
        self.assertEqual(result["primaryAmount"], 18000)

    def test_distant_label_does_not_associate(self):
        result = analyze(("納期限", 0, 0, 80, 20), ("2026年11月2日", 0, 250, 220, 270),
                         ("納付額", 0, 400, 80, 420), ("18000円", 700, 400, 850, 420))
        self.assertIsNone(result["primaryDeadline"])
        self.assertIsNone(result["primaryAmount"])

    def test_literal_notice_titles_are_identified_without_inventing_procedures(self):
        for text, expected in [("国民年金のお知らせ","National Pension Notice"),
                               ("電気料金のお知らせ","Electricity Notice"),
                               ("学校通知","School Notice"),
                               ("雇用条件通知書","Employment Conditions Notice"),
                               ("市役所からのお知らせ","Municipal Notice")]:
            with self.subTest(text=text):
                result = analyze((text,0,0,400,20))
                self.assertEqual(result["documentType"],expected)
                self.assertEqual(result["deadlines"],[])
                self.assertEqual(result["nextSteps"],[])
                self.assertIsNone(result["primaryAmount"])

    def test_generic_or_negated_pension_mentions_do_not_force_a_document_type(self):
        for text in ("国民年金の制度について","国民年金のお知らせではありません"):
            with self.subTest(text=text):
                self.assertIsNone(analyze((text,0,0,500,20))["documentType"])

    def test_vertical_date_and_label_fragmented_into_square_glyphs(self):
        text = "納期限令和9年3月5日"
        items = [(char, 100, index*24, 120, index*24+20) for index,char in enumerate(text)]
        result = analyze(*reversed(items))
        self.assertEqual(result["primaryDeadline"], "2027-03-05")
        self.assertEqual(len(result["deadlines"][0]["evidenceIds"]), len(text))

    def test_vertical_numeric_table_rows_are_not_concatenated_into_amount(self):
        result = analyze(("納付額",0,0,80,20), *[(str(n),0,60+i*24,20,80+i*24) for i,n in enumerate(range(1,6))])
        self.assertIsNone(result["primaryAmount"])
        self.assertFalse(any(a["status"]=="verified" for a in result["amounts"]))

    def test_low_confidence_fragment_cannot_become_a_verified_vertical_date(self):
        text = "納期限令和9年3月5日"
        result = analyze(*[(char,100,i*24,120,i*24+20,.3 if char=="9" else .99) for i,char in enumerate(text)])
        self.assertIsNone(result["primaryDeadline"])
        self.assertEqual(result["deadlines"][0]["status"],"unverified")

    def test_vertical_split_date_and_label(self):
        result = analyze(("2日", 100, 240, 120, 280), ("令和", 100, 90, 120, 130),
                         ("納期限", 100, 0, 120, 60), ("8年11月", 100, 145, 120, 225))
        self.assertEqual(result["primaryDeadline"], "2026-11-02")
        self.assertEqual(len(result["deadlines"][0]["evidenceIds"]), 4)
        self.assertEqual([e["originalIndex"] for e in result["evidence"]], [2, 1, 3, 0])

    def test_vertical_label_in_right_hand_column(self):
        result = analyze(("納期限", 140, 0, 160, 60), ("令和8年11月2日", 100, 0, 120, 200))
        self.assertEqual(result["primaryDeadline"], "2026-11-02")

    def test_vertical_payment_label_same_column(self):
        result = analyze(("納付額", 100, 0, 120, 60), ("18,000", 100, 160, 125, 280))
        self.assertEqual(result["primaryAmount"], 18000)

    def test_vertical_bare_number_next_column_is_unverified(self):
        result = analyze(("延滞金", 140, 0, 160, 60), ("123456789", 100, 0, 120, 200))
        self.assertIsNone(result["primaryAmount"])
        self.assertFalse(any(a["status"] == "verified" for a in result["amounts"]))

    def test_vertical_date_fragments_in_different_columns_not_joined(self):
        result = analyze(("納期限令和", 100, 0, 120, 120), ("8年11月", 200, 130, 220, 210),
                         ("2日", 300, 220, 320, 260))
        self.assertIsNone(result["primaryDeadline"])

    def test_amount_reference_in_instructions_is_not_a_field(self):
        result = analyze(("金額を訂正した場合は確認してください", 0, 0, 500, 20))
        self.assertEqual(result["amounts"], [])

    def test_empty_text_is_preserved(self):
        result = analyze(("", 0, 0, 10, 20), (" ", 30, 0, 40, 20))
        self.assertEqual([e["text"] for e in result["evidence"]], ["", " "])
        self.assertEqual(result["extractionStatus"], "no_fields")

    def test_page_separation_and_evidence(self):
        p1 = page(("納期限", 0, 0, 80, 20), page_index=0)
        p2 = page(("2026年11月2日", 100, 0, 320, 20), page_index=1)
        p2["rec_polys"] = [[[100, 0], [320, 0], [320, 20], [100, 20]]]
        result = analyze_ocr_document([p1, p2])
        self.assertIsNone(result["primaryDeadline"])
        self.assertEqual([e["page"] for e in result["evidence"]], [1, 2])
        self.assertEqual(result["evidence"][1]["polygon"], p2["rec_polys"][0])

    def test_conflicting_amounts_no_arbitrary_primary(self):
        result = analyze(("納付額 18000円", 0, 0, 300, 20), ("請求金額 19000円", 0, 100, 300, 120))
        self.assertIsNone(result["primaryAmount"])
        self.assertEqual(len(result["amounts"]), 2)

    def test_ambiguous_geometric_labels(self):
        result = analyze(("納期限", 0, 0, 80, 20), ("提出期限", 100, 0, 180, 20),
                         ("2026年11月2日", 50, 30, 250, 50))
        self.assertIsNone(result["primaryDeadline"])
        self.assertTrue(any(d["status"] == "unverified" for d in result["deadlines"]))

    def test_date_range_unverified(self):
        result = analyze(("申請期限 2026年1月1日〜2026年2月1日", 0, 0, 600, 20))
        self.assertIsNone(result["primaryDeadline"])
        self.assertFalse(any(d["status"] == "verified" for d in result["deadlines"]))

    def test_negated_deadline(self):
        result = analyze(("納期限 2026年11月2日ではありません", 0, 0, 500, 20))
        self.assertIsNone(result["primaryDeadline"])

    def test_unknown_and_empty(self):
        for data in [[], [page(("お知らせ", 0, 0, 160, 20))]]:
            result = analyze_ocr_document(data)
            self.assertIsNone(result["summary"])
            self.assertEqual(result["nextSteps"], [])
            self.assertEqual(result["extractionStatus"], "no_fields")

    def test_conflicting_document_types(self):
        result = analyze(("国民健康保険税", 0, 0, 240, 20), ("住民税", 0, 100, 100, 120))
        self.assertIsNone(result["documentType"])
        self.assertEqual(result["extractionStatus"], "unverified")

    def test_low_confidence_type(self):
        self.assertIsNone(analyze(("国民健康保険税", 0, 0, 240, 20, .2))["documentType"])

    def test_malformed_ocr_rejected(self):
        bad = page(("test", 0, 0, 100, 20))
        for key, value in [("rec_scores", []), ("rec_scores", [float("nan")]),
                           ("rec_boxes", [[0, 0, 0, 20]]), ("rec_boxes", [[0, 0, float("inf"), 20]]),
                           ("rec_polys", [[]])]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                analyze_ocr_document([bad | {key: value}])

    def test_phone_and_reference_not_money(self):
        result = analyze(("電話番号 0312345678", 0, 0, 300, 20), ("番号 18000", 0, 100, 300, 120))
        self.assertEqual(result["amounts"], [])

    def test_file_runner_does_not_use_filename_and_accepts_pdf(self):
        engine = Mock()
        engine.predict.return_value = [page(("提出期限 2026/12/10", 0, 0, 300, 20))]
        with tempfile.TemporaryDirectory() as directory:
            for name in ("unknown.pdf", "arbitrary.jpg"):
                path = Path(directory) / name
                path.touch()
                result = analyze_file(path, ocr=engine)
                self.assertIsNone(result["documentType"])
                self.assertEqual(result["primaryDeadline"], "2026-12-10")
                engine.predict.assert_called_with(str(path))

    def test_engine_import_has_no_ai_or_ocr_runtime_dependencies(self):
        backend = Path(__file__).resolve().parents[1]
        script = '''
import sys
class Block:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'openai', 'paddleocr', 'paddle', 'django', 'pydantic'} or fullname.startswith('services.ai'):
            raise AssertionError('Unexpected dependency: ' + fullname)
sys.meta_path.insert(0, Block())
from services.documentAnalysis.analyzer import analyze_ocr_document
assert analyze_ocr_document([])['extractionStatus'] == 'no_fields'
'''
        subprocess.run([sys.executable, "-c", script], cwd=backend, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
