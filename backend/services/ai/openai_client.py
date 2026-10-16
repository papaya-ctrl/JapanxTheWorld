import json
import os
import re
from openai import OpenAI
from pydantic import ValidationError
from models.schemas import DocumentAnalysisResultSchema
from services.trustedContent.matcher import extract_deadline_from_text

STRICT_AI_SYSTEM_PROMPT = """You are a careful assistant helping foreign residents in Japan understand Japanese documents.
You are the fallback analyzer when a document does not match a pre-verified template.

CRITICAL SAFETY & ANTI-HALLUCINATION RULES:
Do not invent:
- deadlines
- fees
- payment amounts
- eligibility
- visa approval
- tax rates
- pension exemptions

DEADLINE RULE:
- Only extract a deadline if an explicit date is written in the user's text.
- If no explicit date/deadline is found in the text, "deadline" MUST be null. Never guess or fabricate a date.

AMBIGUOUS / GENERIC TEXT RULE:
- If the text only says general things like "納付期限があります。期限までに支払ってください。" without specifying the exact document or organization, do NOT guess that it is Residence Tax, Pension, or Health Insurance.
- In such ambiguous cases, set "documentType" to "Unidentified / Ambiguous Document", start "summary" with "Unable to confidently identify this document.", and set "relatedGuide" to null.

OUTPUT FORMAT:
Return ONLY valid JSON matching the exact schema:
{
  "source": "ai",
  "documentType": "string",
  "summary": "string",
  "deadline": "YYYY-MM-DD or null",
  "urgency": "low" | "important" | "urgent",
  "importantPoints": ["string"],
  "nextSteps": ["string"],
  "relatedGuide": null,
  "officialWarning": "string"
}"""


def _text_has_explicit_date(text: str) -> bool:
    """မူရင်းစာသားထဲတွင် ရက်စွဲ (ဂဏန်း သို့မဟုတ် 年/月/日) အမှန်တကယ် ပါ/မပါ စစ်ဆေးသည်"""
    if extract_deadline_from_text(text):
        return True
    date_patterns = [
        r"\d{1,2}\s*月\s*\d{1,2}\s*日",
        r"\d{4}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{1,2}",
        r"(令和|平成)\s*\d{1,2}\s*年",
    ]
    return any(re.search(pattern, text) for pattern in date_patterns)


def build_safe_unknown_result(raw_text: str) -> dict:
    """အမျိုးအစား မခွဲခြားနိုင်သော စာသား သို့မဟုတ် API Key မရှိသည့်အခါ ပြန်ပေးမည့် Safe Result"""
    detected_deadline = extract_deadline_from_text(raw_text)
    has_payment_terms = any(term in raw_text for term in ["納付", "支払", "期限", "納期限", "請求"])

    result = {
        "source": "ai",
        "documentType": "Unidentified / Ambiguous Document",
        "summary": "Unable to confidently identify this document. The provided text does not contain enough specific information to determine the exact procedure or issuing authority.",
        "deadline": detected_deadline,
        "urgency": "important" if (has_payment_terms or detected_deadline) else "low",
        "importantPoints": [
            "Only the general notice text was detected; specific document titles, fees, or eligibility details were not found in the text.",
            "Check the physical document header (書類名) and sender (発行元) for exact details."
        ],
        "nextSteps": [
            "Provide the full document title or contact the issuing office printed on the notice for confirmation."
        ],
        "relatedGuide": None,
        "officialWarning": "Unable to confidently identify this document. Please verify all deadlines, fees, and requirements directly with the issuing organization."
    }
    validated = DocumentAnalysisResultSchema.model_validate(result)
    return validated.model_dump()


def analyze_with_ai_fallback(text: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    detected_deadline = extract_deadline_from_text(text)
    has_date_in_text = _text_has_explicit_date(text)

    has_specific_noun = any(
        noun in text for noun in ["水道", "ガス", "電気", "NHK", "病院", "郵便", "不在票", "契約", "学校", "銀行", "督促", "お知らせ", "通知"]
    )
    if len(text.strip()) < 28 and not has_specific_noun:
        return build_safe_unknown_result(text)

    if not api_key or api_key.startswith("sk-proj-your"):
        if "水道" in text or "電気" in text or "ガス" in text:
            utility_result = {
                "source": "ai",
                "documentType": "Utility Usage / Billing Notice",
                "summary": "This notice provides information regarding your utility usage (water, electricity, or gas) or billing statement.",
                "deadline": detected_deadline if has_date_in_text else None,
                "urgency": "important" if detected_deadline else "low",
                "importantPoints": [
                    "Review the usage period and meter reading details written on the slip.",
                    "Do not rely on estimated amounts—check the exact billed amount printed on your official statement."
                ],
                "nextSteps": [
                    "If a payment slip is attached, pay via convenience store, bank transfer, or registered payment method.",
                    "Contact the utility bureau printed on the notice if you have questions about your usage."
                ],
                "relatedGuide": None,
                "officialWarning": "AI-generated guidance. Please confirm exact payment amounts and deadlines directly on your utility statement."
            }
            return DocumentAnalysisResultSchema.model_validate(utility_result).model_dump()

        return build_safe_unknown_result(text)

    # 3. Real OpenAI API Call with Strict Schema Validation
    try:
        client = OpenAI(api_key=api_key)

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            temperature=0.0,  
            messages=[
                {"role": "system", "content": STRICT_AI_SYSTEM_PROMPT},
                {"role": "user", "content": f"Document text:\n{text}"}
            ],
            response_format=DocumentAnalysisResultSchema,
        )

        raw_json_str = completion.choices[0].message.content
        validated_obj = DocumentAnalysisResultSchema.model_validate_json(raw_json_str)
        result_dict = validated_obj.model_dump()

        # Force source = "ai"
        result_dict["source"] = "ai"

        if not has_date_in_text:
            result_dict["deadline"] = None
        elif detected_deadline and not result_dict.get("deadline"):
            result_dict["deadline"] = detected_deadline

        # Re-validate final dictionary against schema
        final_validated = DocumentAnalysisResultSchema.model_validate(result_dict)
        return final_validated.model_dump()

    except (ValidationError, json.JSONDecodeError, Exception):
        return build_safe_unknown_result(text)