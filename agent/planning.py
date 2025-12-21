"""Simple planner for aspect selection and time needs."""

from __future__ import annotations

import datetime as dt
import re
from typing import Dict, List

ASPECT_KEYWORDS = {
    "CAREER": ["事业", "工作", "职业", "升职", "学业", "考试"],
    "RELATIONSHIP": ["感情", "婚姻", "恋爱", "对象", "桃花"],
    "HEALTH": ["健康", "身体", "疾病", "生病", "睡眠"],
    "GUIREN": ["贵人"],
    "LIUQIN": ["六亲", "父母", "父亲", "母亲", "兄弟", "姐妹", "子女"],
    "XINGGE": ["性格", "性情", "气质"],
    "OTHER": ["财运", "性格", "运势", "综合", "总体"],
}

RELATIVE_TIME = {
    "今年": 0,
    "明年": 1,
    "去年": -1,
}


def classify_aspects(text: str) -> List[str]:
    matched = []
    for aspect, keys in ASPECT_KEYWORDS.items():
        if any(k in text for k in keys):
            matched.append(aspect)
    if not matched:
        matched.append("OTHER")
    return matched


def detect_time(text: str, now: dt.datetime | None = None) -> Dict:
    now = now or dt.datetime.now()
    for key, offset in RELATIVE_TIME.items():
        if key in text:
            year = now.year + offset
            return {"need_tool": True, "granularity": "year", "ref_text": key, "year": year}
    m = re.search(r"(\d{4})年(\d{1,2})月", text)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        return {"need_tool": True, "granularity": "month", "ref_text": m.group(0), "year": year, "month": month}
    m = re.search(r"(\d{4})年", text)
    if m:
        year = int(m.group(1))
        return {"need_tool": True, "granularity": "year", "ref_text": m.group(0), "year": year}
    return {"need_tool": False, "granularity": None, "ref_text": None}


def plan(question: str, now: dt.datetime | None = None) -> Dict:
    aspects = classify_aspects(question)
    time = detect_time(question, now=now)
    return {"aspects": aspects, "time": time}
