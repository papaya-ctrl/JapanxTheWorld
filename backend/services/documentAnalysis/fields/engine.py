"""Evidence-backed fields. No templates, document hints, network, or AI imports."""
from dataclasses import dataclass
import re

from services.ocr.records import OCRBox
from .dates import DATE_PATTERN, DATE_LIKE, parse_date
from .layout import reconstruct

# Longest matches win: 支払済金額 must never become 支払金額 or 金額.
DEADLINE_LABELS = {
    "までにお支払い": ("Payment deadline", "payment"),
    "までに納付": ("Payment deadline", "payment"),
    "までに支払": ("Payment deadline", "payment"),
    "までに提出": ("Submission deadline", "submission"),
    "までに申請": ("Application deadline", "application"),
    "までに返送": ("Return deadline", "return"),
    "までに回答": ("Response deadline", "response"),
    "納付締切": ("Payment deadline", "payment"),
    "支払い期日": ("Payment due date", "payment"),
    "支払締切": ("Payment deadline", "payment"),
    "提出期日": ("Submission deadline", "submission"),
    "申請締切": ("Application deadline", "application"),
    "申込み期限": ("Application deadline", "application"),
    "納付期限": ("Payment deadline", "payment"),
    "納期限": ("Payment deadline", "payment"),
    "支払期限": ("Payment deadline", "payment"),
    "支払い期限": ("Payment deadline", "payment"),
    "支払期日": ("Payment due date", "payment"),
    "納付期日": ("Payment due date", "payment"),
    "払込期限": ("Payment deadline", "payment"),
    "払込期日": ("Payment due date", "payment"),
    "お支払い期限": ("Payment deadline", "payment"),
    "提出期限": ("Submission deadline", "submission"),
    "提出締切": ("Submission deadline", "submission"),
    "申請期限": ("Application deadline", "application"),
    "申込期限": ("Application deadline", "application"),
    "申込締切": ("Application deadline", "application"),
    "受付期限": ("Acceptance deadline", "acceptance"),
    "受付締切": ("Acceptance deadline", "acceptance"),
    "回答期限": ("Response deadline", "response"),
    "返送期限": ("Return deadline", "return"),
    "利用期限": ("Usage expiration date", "usage_expiration"),
    "有効期限": ("Validity expiration date", "validity_expiration"),
}
DATE_BLOCKERS = {key: (label, "non_deadline") for key, label in {
    "発行日": "Issue date", "発行年月日": "Issue date", "作成日": "Creation date",
    "通知日": "Notification date", "領収日": "Receipt date", "領収年月日": "Receipt date",
    "支払日": "Payment date", "支払済日": "Completed payment date",
    "納付日": "Payment date", "利用期間": "Usage period", "請求期間": "Billing period",
    "対象期間": "Applicable period", "対象年月": "Applicable month", "生年月日": "Date of birth",
    "支払予定日": "Scheduled payment date", "口座振替日": "Scheduled debit date",
}.items()}
AMOUNT_LABELS = {
    "納付額": ("Payment amount", "payment"), "納付金額": ("Payment amount", "payment"),
    "請求金額": ("Billed amount", "billed"), "ご請求額": ("Billed amount", "billed"),
    "請求額": ("Billed amount", "billed"), "合計金額": ("Total amount", "total"),
    "支払金額": ("Payment amount", "payment"), "支払額": ("Payment amount", "payment"),
    "支払い金額": ("Payment amount", "payment"), "税額": ("Tax amount", "tax"),
    "延滞金": ("Late fee", "late_fee"), "支払済金額": ("Already-paid amount", "paid"),
    "支払済額": ("Already-paid amount", "paid"), "納付済額": ("Already-paid amount", "paid"),
    "領収金額": ("Received amount", "paid"), "領収額": ("Received amount", "paid"),
    "未納額": ("Unpaid amount", "outstanding"), "未納金額": ("Unpaid amount", "outstanding"),
    "差引納付額": ("Net payment amount", "payment"),
    "金額": ("Unspecified amount", "unknown"), "料金": ("Unspecified charge", "unknown"),
    "電話番号": ("Telephone number", "non_amount"), "番号": ("Reference number", "non_amount"),
    "郵便番号": ("Postal code", "non_amount"), "年度": ("Fiscal year", "non_amount"),
}
ALL_LABELS = DEADLINE_LABELS | DATE_BLOCKERS | AMOUNT_LABELS
LABEL_PATTERN = re.compile("|".join(re.escape(x) for x in sorted(ALL_LABELS, key=len, reverse=True)))
AMOUNT_PATTERN = re.compile(
    r"(?<![\d,.A-Za-z])(?:[¥￥]?[+−△▲-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?円?)(?![\d,.A-Za-z])"
)
PAID_PATTERN = re.compile(r"(?:お支払済み|支払い済み|支払済み|支払済|納付済み|納付済|領収済み|領収済|入金済み|入金済|お支払いが完了|支払いが完了|納付が完了)(?![額金])")
NEGATION = re.compile(r"ではありません|ではない|ではなく|しない|わない|不要|免除|必要ありません|できません|対象外|取消|取り消し|無効|未確定|予定|場合|支払済では|納付済では")


@dataclass
class Token:
    run: int
    start: int
    end: int
    source: str
    label: str = ""
    kind: str = ""
    value: object = None
    valid: bool = True


def _source(runs, token):
    return runs[token.run].sources(token.start, token.end)


def _confidence(boxes):
    return min((b.confidence for b in boxes), default=0.)


def _associate(value, labels, runs):
    """Rank text-local labels first, then rightward and below-label geometry.

    Return ambiguity instead of resolving near-ties by OCR array order. Labels
    with conflicting semantics participate even if they are not target fields.
    """
    scores = []
    vr = runs[value.run]
    vbox = vr.reading_bounds(value.start, value.end)
    vh = max(1., vbox[3] - vbox[1])
    for label in labels:
        lr = runs[label.run]
        if lr.page != vr.page or lr.orientation != vr.orientation:
            continue
        score = None
        if label.run == value.run:
            if label.end <= value.start and value.start - label.end <= 18:
                gap = vr.text[label.end:value.start]
                # A prior field value separates this label from the current value.
                if not re.search(r"\d|円", gap):
                    score = .1 + (value.start - label.end) / 20
            elif value.end <= label.start and label.start - value.end <= 4:
                gap = vr.text[value.end:label.start]
                # A following table cell is not a trailing label. Only explicit
                # "by this date" wording or parenthetical labels establish that.
                if label.source.startswith("まで") or gap in ("(", "（"):
                    score = 1.5 + (label.start - value.end) / 10
        else:
            lb = lr.reading_bounds(label.start, label.end)
            lh = max(1., lb[3] - lb[1])
            h = min(vh, lh)
            overlap_y = min(lb[3], vbox[3]) - max(lb[1], vbox[1])
            gap_x = vbox[0] - lb[2]
            if overlap_y >= .65 * min(lh, vh) and 0 <= gap_x <= 8 * h:
                score = 3 + gap_x / (8 * h)
            gap_y = vbox[1] - lb[3]
            overlap_x = min(lb[2], vbox[2]) - max(lb[0], vbox[0])
            align = abs(vbox[0] - lb[0])
            if (0 <= gap_y <= 1.5 * h and overlap_x > 0
                    and (align <= 2 * h or overlap_x >= .6 * min(lb[2] - lb[0], vbox[2] - vbox[0]))):
                score = min(score if score is not None else 99, 4 + gap_y / (2 * h) + align / (8 * h))
        if score is not None:
            scores.append((score, label))
    scores.sort(key=lambda pair: pair[0])
    if not scores:
        return None, False, []
    best = scores[0][1]
    alternatives = [label for score, label in scores if score - scores[0][0] <= .3]
    ambiguous = len({(label.label, label.kind) for label in alternatives}) > 1
    return best, ambiguous, alternatives


def _labels(runs):
    return [Token(i, m.start(), m.end(), m.group(), *ALL_LABELS[m.group()])
            for i, run in enumerate(runs) for m in LABEL_PATTERN.finditer(run.text)
            if not (m.group() in {"金額", "料金"} and run.text[m.end():m.end() + 1] in {"を", "の"})]


def _date_tokens(runs):
    tokens = []
    for i, run in enumerate(runs):
        matches = list(DATE_PATTERN.finditer(run.text))
        for match in matches:
            value = parse_date(match)
            tokens.append(Token(i, match.start(), match.end(), match.group(), value=value, valid=value is not None))
        for match in DATE_LIKE.finditer(run.text):
            if not any(m.start() < match.end() and m.end() > match.start() for m in matches):
                tokens.append(Token(i, match.start(), match.end(), match.group(), valid=False))
    return tokens


def _amount_tokens(runs, dates):
    tokens = []
    for i, run in enumerate(runs):
        for match in AMOUNT_PATTERN.finditer(run.text):
            if any(d.run == i and match.start() < d.end and match.end() > d.start for d in dates):
                continue
            # Date components, years, percentages and units cannot be bare money.
            suffix = run.text[match.end():match.end() + 1]
            if suffix and suffix in "年月日%割件番号歳才":
                continue
            raw = match.group()
            currency = "円" in raw or "¥" in raw or "￥" in raw
            valid = not any(c in raw for c in ".+−△▲-")
            number = raw.translate(str.maketrans("", "", "¥￥円,"))
            value = int(number) if valid else None
            tokens.append(Token(i, match.start(), match.end(), raw,
                                kind="currency" if currency or "," in raw else "bare",
                                value=value, valid=valid))
    return tokens


def _range(token, tokens, runs):
    for other in tokens:
        if other is token or other.run != token.run:
            continue
        a, b = sorted((token, other), key=lambda t: t.start)
        if re.fullmatch(r"[~〜～\-–—から至]+", runs[token.run].text[a.end:b.start]):
            return True
    return False


def _entry(token, label, alternatives, ambiguous, runs, minimum_confidence, category):
    boxes = _source(runs, token)
    for item in alternatives:
        boxes.extend(_source(runs, item))
    boxes = list({b.id: b for b in boxes}.values())
    reasons = []
    if not token.valid:
        reasons.append("Invalid or incomplete date." if category == "date" else "Invalid or unsupported monetary format.")
    if label is None:
        reasons.append("No supported label association.")
    elif label.kind == "unknown":
        reasons.append("The label does not establish the amount's payment role.")
    if ambiguous:
        reasons.append("Competing labels have similar association strength.")
    if category == "amount" and label and token.kind == "bare":
        vr, lr = runs[token.run], runs[label.run]
        vb, lb = vr.reading_bounds(token.start, token.end), lr.reading_bounds(label.start, label.end)
        if vr.orientation == "vertical" and min(vb[3], lb[3]) <= max(vb[1], lb[1]):
            reasons.append("A bare number in a neighbouring vertical column does not establish a monetary value.")
    contexts = [(token.run, max(0, token.start - 4), token.end + 12)]
    if label:
        contexts.append((label.run, max(0, label.start - 4), label.end + 12))
    if label and label.run == token.run:
        contexts.append((token.run, max(0, min(label.start, token.start) - 4), max(label.end, token.end) + 12))
    negated = False
    for run_index, start, end in contexts:
        if NEGATION.search(runs[run_index].text[start:end]):
            negated = True
            boxes.extend(runs[run_index].sources(start, end))
    boxes = list({b.id: b for b in boxes}.values())
    if negated:
        reasons.append("The surrounding text is conditional, negated, or cancelled.")
    if _confidence(boxes) < minimum_confidence:
        reasons.append("Source OCR confidence is below the verification threshold.")
    entry = {
        "label": label.label if label else ("Unassociated date" if category == "date" else "Unassociated amount"),
        "kind": label.kind if label else "unknown",
        "date" if category == "date" else "value": token.value,
        "status": "unverified" if reasons else "verified",
        "reasons": reasons,
        "evidenceIds": [b.id for b in boxes],
        "ocrConfidence": _confidence(boxes),
        "association": "text_and_geometry" if label else "none",
    }
    if category == "amount":
        entry["currency"] = "JPY"
    return entry


def _deduplicate(entries, value_key):
    merged = {}
    for entry in entries:
        # Never merge an uncertain occurrence into a verified occurrence.
        key = (entry["label"], entry["kind"], entry[value_key], entry["status"], tuple(entry["reasons"]))
        if key in merged:
            current = merged[key]
            current["evidenceIds"] = list(dict.fromkeys(current["evidenceIds"] + entry["evidenceIds"]))
            current["ocrConfidence"] = min(current["ocrConfidence"], entry["ocrConfidence"])
            current["occurrences"] += 1
        else:
            merged[key] = dict(entry, occurrences=1)
    return list(merged.values())


def _primary(entries, key, kinds):
    candidates = [e for e in entries if e["kind"] in kinds]
    # Any competing uncertain value prevents selecting an apparently unique field.
    if not candidates or any(e["status"] != "verified" for e in candidates):
        return None
    if len({e[key] for e in candidates}) != 1:
        return None
    return candidates[0][key]


def _identify(runs, threshold):
    rules = [("国民健康保険税", "National Health Insurance Tax", 2),
             ("住民税", "Residence Tax", 2), ("納付書", "Payment Slip", 1),
             ("国民年金のお知らせ", "National Pension Notice", 2),
             ("電気料金のお知らせ", "Electricity Notice", 2),
             ("学校通知", "School Notice", 2),
             ("雇用条件通知書", "Employment Conditions Notice", 2),
             ("市役所からのお知らせ", "Municipal Notice", 2)]
    found = []
    for run in runs:
        for japanese, english, specificity in rules:
            for match in re.finditer(japanese, run.text):
                sources = run.sources(match.start(), match.end())
                context = run.text[max(0, match.start() - 4):match.end() + 12]
                if (_confidence(sources) >= threshold and not NEGATION.search(context)
                        and run.text[match.end():match.end() + 1] != "を"):
                    found.append((english, specificity, [b.id for b in sources]))
    if not found:
        return None, [], False
    top = max(item[1] for item in found)
    names = {name for name, rank, _ in found if rank == top}
    return (next(iter(names)) if len(names) == 1 else None,
            list(dict.fromkeys(i for _, _, ids in found for i in ids)), len(names) > 1)


def extract_fields(boxes: list[OCRBox], *, minimum_confidence: float = .85) -> dict:
    """Return JSON-safe English fields with original Japanese only in evidence.

    'verified' means these conservative extraction rules passed, not that OCR
    text or a document's authenticity has been independently confirmed.
    No value is summed and no primary field is selected by array order.
    """
    if not 0 <= minimum_confidence <= 1:
        raise ValueError("The OCR confidence threshold must be between zero and one.")
    runs, ordered = reconstruct(boxes)
    labels = _labels(runs)
    date_labels = [t for t in labels if t.source in DEADLINE_LABELS or t.source in DATE_BLOCKERS]
    money_labels = [t for t in labels if t.source in AMOUNT_LABELS]
    date_tokens = _date_tokens(runs)
    deadlines, amounts, warnings = [], [], []
    matched_labels = set()
    for token in date_tokens:
        label, ambiguous, alternatives = _associate(token, date_labels, runs)
        if label is None:
            warnings.append("Unassociated dates were not treated as deadlines.")
            continue
        if label.kind == "non_deadline" and not ambiguous:
            continue
        for item in alternatives:
            matched_labels.add((item.run, item.start))
        entry = _entry(token, label, alternatives, ambiguous, runs, minimum_confidence, "date")
        if _range(token, date_tokens, runs):
            entry["status"] = "unverified"
            entry["reasons"].append("A date range cannot establish a single deadline.")
        deadlines.append(entry)
    for label in date_labels:
        if label.kind == "non_deadline" or (label.run, label.start) in matched_labels:
            continue
        entry = _entry(Token(label.run, label.start, label.end, "", valid=False),
                       label, [label], False, runs, minimum_confidence, "date")
        entry["reasons"][0] = "No complete calendar date is associated with this label."
        deadlines.append(entry)
    matched_amount_labels = set()
    for token in _amount_tokens(runs, date_tokens):
        label, ambiguous, alternatives = _associate(token, money_labels, runs)
        if label and label.kind == "non_amount" and not ambiguous:
            continue
        if token.kind == "bare" and label is None:
            continue
        for item in alternatives:
            matched_amount_labels.add((item.run, item.start))
        entry = _entry(token, label, alternatives, ambiguous, runs, minimum_confidence, "amount")
        amounts.append(entry)
    for label in money_labels:
        if label.kind == "non_amount" or (label.run, label.start) in matched_amount_labels:
            continue
        entry = _entry(Token(label.run, label.start, label.end, "", valid=False),
                       label, [label], False, runs, minimum_confidence, "amount")
        entry["reasons"][0] = "No readable monetary value is associated with this label."
        amounts.append(entry)
    deadlines = _deduplicate(deadlines, "date")
    amounts = _deduplicate(amounts, "value")
    document_type, type_ids, type_conflict = _identify(runs, minimum_confidence)
    if type_conflict:
        warnings.append("Conflicting document type evidence; the document type is unverified.")
    if not document_type:
        warnings.append("The document type could not be verified from OCR evidence.")
    paid_ids = []
    for run in runs:
        for match in PAID_PATTERN.finditer(run.text):
            context = run.text[max(0, match.start() - 8):match.end() + 12]
            if NEGATION.search(context) or any(x in context for x in ("場合", "確認", "未納", "一部", "ください", "済印", "済欄", "□", "☐", "未記入")):
                continue
            sources = run.sources(match.start(), match.end())
            if _confidence(sources) >= minimum_confidence:
                paid_ids.extend(b.id for b in sources)
    if paid_ids:
        warnings.append("A completed-payment statement is present; outstanding payment is not inferred.")
    if any(e["kind"] == "paid" for e in amounts):
        warnings.append("Already-paid amounts do not establish an outstanding balance.")
    if any(e["status"] == "unverified" for e in deadlines + amounts):
        warnings.append("Some fields are unverified; check their source evidence.")
    primary_deadline = _primary(deadlines, "date", {"payment", "submission", "application", "acceptance", "response", "return"})
    primary_amount = _primary(amounts, "value", {"payment", "billed", "total", "outstanding"})
    if paid_ids:
        primary_amount = None
    important = []
    for entry in deadlines:
        if entry["status"] == "verified":
            important.append(f'{entry["label"]}: {entry["date"]}.')
    for entry in amounts:
        if entry["status"] == "verified":
            important.append(f'{entry["label"]}: JPY {entry["value"]:,}.')
    if paid_ids:
        important.append("The document contains a completed-payment statement.")
    summary = " ".join(([f"Document identified as {document_type}."] if document_type else []) + important) or None
    next_steps = []
    if any(e["status"] == "unverified" for e in deadlines + amounts):
        next_steps.append("Verify the unverified fields against the original document.")
    if primary_deadline:
        next_steps.append(f"Review the stated deadline: {primary_deadline}.")
    verified = any(e["status"] == "verified" for e in deadlines + amounts) or bool(document_type) or bool(paid_ids)
    uncertain = any(e["status"] == "unverified" for e in deadlines + amounts) or type_conflict
    status = "partial" if verified and uncertain else "verified" if verified else "unverified" if uncertain else "no_fields"
    return {
        "documentType": document_type, "summary": summary,
        "deadlines": deadlines, "amounts": amounts,
        "primaryDeadline": primary_deadline, "primaryAmount": primary_amount,
        "importantPoints": list(dict.fromkeys(important)), "nextSteps": next_steps,
        "evidence": [{"id": b.id, "text": b.text, "confidence": b.confidence,
                      "bbox": list(b.bbox), "polygon": [list(p) for p in b.polygon] if b.polygon else None,
                      "page": b.page, "originalIndex": b.original_index, "readingOrder": index}
                     for index, b in enumerate(ordered)],
        "documentTypeEvidenceIds": type_ids,
        "completedPaymentEvidenceIds": list(dict.fromkeys(paid_ids)),
        "warnings": list(dict.fromkeys(warnings)), "extractionStatus": status,
    }
