from services.classification.classifier import normalize_text, classify_document
from services.trustedContent.matcher import build_trusted_result
from services.ai.openai_client import analyze_with_ai_fallback
from models.schemas import DocumentAnalysisResultSchema

def analyze_document_text(raw_text: str) -> dict:
    # 1. Normalize user text
    normalized = normalize_text(raw_text)

    # 2. Classify into trusted topic
    classification = classify_document(normalized)

    # 3. Trusted Knowledge First: Topic match ဖြစ်လျှင် Builder ဖြင့် Result တည်ဆောက်မည် (AI မခေါ်ပါ)
    if classification["is_confident"] and classification["topic_id"]:
        trusted_result = build_trusted_result(
            topic_id=classification["topic_id"],
            raw_text=normalized
        )
        if trusted_result:
            validated = DocumentAnalysisResultSchema(**trusted_result)
            return validated.model_dump()

    # 4. AI Fallback (Trusted topic မရှိမှသာ ခေါ်မည်)
    ai_result = analyze_with_ai_fallback(raw_text)
    validated = DocumentAnalysisResultSchema(**ai_result)
    return validated.model_dump()