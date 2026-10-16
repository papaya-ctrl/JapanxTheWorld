import re
import unicodedata

TOPIC_RULES = {
    "residence-tax": {
        "primary": ["住民税", "市民税", "県民税", "特別区民税", "市県民税", "都民税", "府民税", "道民税", "residence tax"],
        "aliases": ["納税通知書", "課税証明書", "非課税証明書", "特別徴収", "普通徴収"]
    },
    "national-pension": {
        "primary": ["国民年金", "年金保険料", "日本年金機構", "基礎年金番号", "ねんきん定期便", "national pension"],
        "aliases": ["年金手帳", "学生納付特例", "保険料免除", "納付猶予"]
    },
    "national-health-insurance": {
        "primary": ["国民健康保険", "国民健康保険料", "国民健康保険税", "国保", "national health insurance"],
        "aliases": ["被保険者証", "保険証", "資格取得", "医療費のお知らせ"]
    },
    "address-registration-moving": {
        "primary": ["転入届", "転出届", "転居届", "住民票", "転出証明書", "address registration", "moving notice"],
        "aliases": ["マイナンバー", "住所変更", "異動届", "世帯主"]
    },
    "residence-status-renewal": {
        "primary": ["在留期間更新", "在留期間更新許可申請", "在留カードの更新", "visa renewal"],
        "aliases": ["在留カード", "出入国在留管理局", "在留期限", "入管"]
    },
    "student-to-worker": {
        "primary": ["在留資格変更", "在留資格変更許可申請", "技術・人文知識・国際業務", "留学から就労", "student to worker"],
        "aliases": ["就労ビザ", "卒業証明書", "内定通知書"]
    },
    "part-time-work-permission": {
        "primary": ["資格外活動許可", "資格外活動許可申請", "週28時間", "28時間以内", "part-time work permission"],
        "aliases": ["アルバイト", "就労制限", "資格外活動"]
    },
    "employment-contract": {
        "primary": ["労働条件通知書", "雇用契約書", "就業規則", "employment contract", "working conditions"],
        "aliases": ["基本給", "労働時間", "試用期間", "有給休暇"]
    }
}

CONFIDENCE_THRESHOLD = 2


def normalize_text(text: str) -> str:
    """စာသားကို NFKC normalize လုပ်ပြီး space များကို ရှင်းလင်းသည်"""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


def classify_document(normalized_text: str) -> dict:
    """
    Ambiguous / Unknown protection:
    1. Primary keyword အနည်းဆုံး ၁ ခု မပါလျှင် လုံးဝ match မလုပ်ပါ (Alias ချည်းပဲ ပါနေလျှင် score = 0)။
    2. Topic ၂ ခု အမှတ်တူနေလျှင် (Tie / Ambiguous) လျှောက်မမှန်းဘဲ is_confident = False ပြန်ပေးမည်။
    """
    scores = {}
    matched_map = {}

    for topic_id, rules in TOPIC_RULES.items():
        primary_matches = [kw for kw in rules["primary"] if kw.lower() in normalized_text]

        if not primary_matches:
            continue

        alias_matches = [alias for alias in rules["aliases"] if alias.lower() in normalized_text]
        score = (len(primary_matches) * 2) + (len(alias_matches) * 1)

        scores[topic_id] = score
        matched_map[topic_id] = primary_matches + alias_matches

    if not scores:
        return {
            "topic_id": None,
            "score": 0,
            "is_confident": False,
            "reason": "no_primary_keyword_matched",
            "matched_keywords": []
        }

    sorted_topics = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_topic, highest_score = sorted_topics[0]

    if len(sorted_topics) > 1 and sorted_topics[1][1] == highest_score:
        return {
            "topic_id": None,
            "score": highest_score,
            "is_confident": False,
            "reason": "ambiguous_tie",
            "matched_keywords": []
        }

    is_confident = highest_score >= CONFIDENCE_THRESHOLD

    return {
        "topic_id": best_topic if is_confident else None,
        "score": highest_score,
        "is_confident": is_confident,
        "reason": "confident_match" if is_confident else "low_confidence",
        "matched_keywords": matched_map[best_topic] if is_confident else []
    }