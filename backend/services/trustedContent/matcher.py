import re
from services.trustedContent.topics_data import TRUSTED_TOPICS_DATA

def extract_deadline_from_text(text: str) -> str | None:
    """
    စာသားထဲတွင် ပါဝင်နိုင်သော ရက်စွဲများ (ဥပမာ 2026年6月30日, 2026/06/30, 令和8年6月30日) ကို ရှာဖွေပေးသည်
    """
    if not text:
        return None

    match_standard = re.search(r"(20\d{2})\s*[年/\-\.]\s*(\d{1,2})\s*[月/\-\.]\s*(\d{1,2})\s*日?", text)
    if match_standard:
        year, month, day = match_standard.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    match_reiwa = re.search(r"令和\s*(\d{1,2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if match_reiwa:
        r_year, month, day = match_reiwa.groups()
        year = 2018 + int(r_year)
        return f"{year}-{int(month):02d}-{int(day):02d}"

    return None


def build_trusted_result(topic_id: str, raw_text: str = "") -> dict | None:
    """
    trustedTopics.ts data -> DocumentAnalysisResult shape သို့ ပြောင်းပေးသည့် Builder
    AI ကို လုံးဝမသုံးဘဲ deterministic နည်းဖြင့် တည်ဆောက်သည်။
    """
    topic = TRUSTED_TOPICS_DATA.get(topic_id)
    if not topic:
        return None

    warnings = topic.get("warnings", [])
    if isinstance(warnings, list):
        official_warning = " ".join(warnings) if warnings else "Please confirm details with the issuing authority."
    else:
        official_warning = str(warnings)

    detected_deadline = extract_deadline_from_text(raw_text)

    return {
        "source": "template",
        "documentType": topic["title"],
        "summary": topic["summary"],
        "deadline": detected_deadline,
        "urgency": topic.get("urgency", "important"),
        "importantPoints": list(topic.get("importantPoints", [])),
        "nextSteps": list(topic.get("nextSteps", [])),
        "relatedGuide": topic.get("relatedGuide", topic["id"]),
        "officialWarning": official_warning,
    }