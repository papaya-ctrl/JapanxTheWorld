"""Ground-truth scoring that never treats partial annotations as full truth."""
import unicodedata


def normalized_text(text):
    return "".join(unicodedata.normalize("NFKC", text).split())


def edit_distance(expected, actual):
    previous = list(range(len(actual) + 1))
    for row, left in enumerate(expected, 1):
        current = [row]
        for column, right in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column-1] + (left != right)))
        previous = current
    return previous[-1]


def score_fields(predictions, expected, value_key, complete):
    verified = [p for p in predictions if p["status"] == "verified"]
    def key(item):
        return item["kind"], item[value_key]
    wanted = {key(item) for item in expected}
    found = {key(item) for item in verified}
    matched = wanted & found
    labels = {(item["kind"], item[value_key]): item.get("label") for item in expected}
    labeled = {item for item in matched if labels[item] is not None}
    associations = sum(any(key(p) == item and p["label"] == labels[item]
                           for p in verified) for item in labeled)
    return {"expected": len(wanted), "verified": len(found), "matched": len(matched),
            "missed": len(wanted - found), "falsePositive": len(found - wanted) if complete else None,
            "unscoredPredictions": 0 if complete else len(found - wanted),
            "exact": wanted == found if complete else None,
            "knownFieldsRecovered": wanted <= found,
            "labelMatches": associations, "labelScored": len(labeled),
            "unverified": sum(p["status"] == "unverified" for p in predictions)}


def score_result(result, truth):
    complete = truth.get("complete", False)
    metrics = {
        "deadlines": score_fields(result["deadlines"], truth.get("deadlines", []), "date", complete),
        "amounts": score_fields(result["amounts"], truth.get("amounts", []), "value", complete),
    }
    for key in ("documentType", "primaryDeadline", "primaryAmount", "extractionStatus"):
        metrics[key + "Correct"] = result[key] == truth[key] if key in truth else None
    transcription = truth.get("transcription")
    if transcription is not None:
        expected = normalized_text(transcription)
        actual = normalized_text("".join(e["text"] for e in result["evidence"]))
        if len(expected) <= 5000 and len(actual) <= 10000:
            metrics["characterEdits"] = edit_distance(expected, actual)
            metrics["characters"] = len(expected)
        else:
            metrics["characterEdits"] = metrics["characters"] = None
            metrics["textScoringSkipped"] = "bounded_edit_distance_limit"
    else:
        metrics["characterEdits"] = metrics["characters"] = None
    return metrics
