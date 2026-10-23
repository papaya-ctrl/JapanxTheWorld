"""Strict calendar dates; never repair OCR digits or infer missing years."""
from datetime import date
import re

DATE_PATTERN = re.compile(
    r"(?<![\dA-Za-z])(?:(?P<era>令和|平成|昭和)(?P<ey>元|\d{1,2})年"
    r"(?P<em>\d{1,2})月(?P<ed>\d{1,2})日"
    r"|(?P<year>\d{4})(?:年(?P<jm>\d{1,2})月(?P<jd>\d{1,2})日"
    r"|(?P<sep>[/.-])(?P<month>\d{1,2})(?P=sep)(?P<day>\d{1,2})))(?!\d)"
)
# Also surface malformed/incomplete dates next to a deadline label for review.
DATE_LIKE = re.compile(r"(?:令和|平成|昭和)[元\dA-Za-z]+年[^、。:：]{0,14}?[日]|\d{4}年\d{1,2}月(?:\d{1,2}日)?")
ERAS = {
    "令和": (2018, date(2019, 5, 1), None),
    "平成": (1988, date(1989, 1, 8), date(2019, 4, 30)),
    "昭和": (1925, date(1926, 12, 25), date(1989, 1, 7)),
}


def parse_date(match: re.Match) -> str | None:
    try:
        if match["era"]:
            offset, start, end = ERAS[match["era"]]
            era_year = 1 if match["ey"] == "元" else int(match["ey"])
            if era_year < 1:
                return None
            value = date(offset + era_year, int(match["em"]), int(match["ed"]))
            if value < start or (end and value > end):
                return None
        else:
            value = date(int(match["year"]), int(match["jm"] or match["month"]),
                         int(match["jd"] or match["day"]))
        return value.isoformat()
    except ValueError:
        return None
