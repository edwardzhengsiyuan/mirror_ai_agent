"""Planner for aspect selection and time needs (rules + LLM)."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any, Dict, List, Optional

from .events import EventSink, emit_event
from .tools.llm_tool import llm_report_tool
from .tools.planning_tool import planning_tool

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

_GANZHI_PATTERN = r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]"
_DAYUN_REF_PATTERN = re.compile(rf"({_GANZHI_PATTERN})大运")


def classify_aspects(text: str) -> List[str]:
    matched = []
    for aspect, keys in ASPECT_KEYWORDS.items():
        if any(k in text for k in keys):
            matched.append(aspect)
    if not matched:
        matched.append("OTHER")
    return matched


def detect_times(text: str, now: dt.datetime | None = None) -> List[Dict]:
    now = now or dt.datetime.now()
    entries: List[Dict] = []
    seen = set()

    def push(item: Dict) -> None:
        key = (item.get("granularity"), item.get("year"), item.get("month"))
        if key in seen:
            return
        seen.add(key)
        entries.append(item)

    for key, offset in RELATIVE_TIME.items():
        if key in text:
            year = now.year + offset
            push({"need_tool": True, "granularity": "year", "ref_text": key, "year": year})

    month_spans = []
    year_spans = []
    for match in re.finditer(r"(\d{4})年(\d{1,2})月", text):
        month_spans.append(match.span())
        year = int(match.group(1))
        month = int(match.group(2))
        push({"need_tool": True, "granularity": "month", "ref_text": match.group(0), "year": year, "month": month})

    for match in re.finditer(r"(\d{4})年", text):
        span = match.span()
        if any(start <= span[0] < end for start, end in month_spans):
            continue
        year = int(match.group(1))
        year_spans.append(span)
        push({"need_tool": True, "granularity": "year", "ref_text": match.group(0), "year": year})

    for match in re.finditer(r"(?<!\d)(\d{4})(?!\d)", text):
        span = match.span()
        if any(start <= span[0] < end for start, end in month_spans):
            continue
        if any(start <= span[0] < end for start, end in year_spans):
            continue
        year = int(match.group(1))
        push({"need_tool": True, "granularity": "year", "ref_text": match.group(0), "year": year})

    for match in _DAYUN_REF_PATTERN.finditer(text):
        name = match.group(1)
        push({"need_tool": True, "granularity": "dayun", "ref_text": match.group(0), "dayun": name})

    return entries


def plan_with_rules(question: str, now: dt.datetime | None = None) -> Dict:
    aspects = classify_aspects(question)
    times = detect_times(question, now=now)
    primary = times[0] if times else {"need_tool": False, "granularity": None, "ref_text": None}
    plan = planning_tool(aspects, primary, times)
    plan["source"] = "rules"
    return plan


def _build_planner_prompt(
    question: str,
    now: dt.datetime,
    dayun_list: Optional[List[Dict[str, Any]]] = None,
) -> tuple[str, str]:
    system_prompt = (
        "你是一个规划助手，需要根据用户问题返回结构化的规划结果。"
        "只允许通过调用 planning_tool 返回 JSON，格式必须严格为："
        "{\"tool\":\"planning_tool\",\"args\":{\"aspects\":[...],\"times\":[...]}}"
        "。aspects 只能从 [CAREER, RELATIONSHIP, HEALTH, GUIREN, LIUQIN, XINGGE, OTHER] 中选择。"
        "times 为列表，每项包含 need_tool(boolean), granularity(year|month|null), "
        "ref_text(string|null), year(int|null), month(int|null)。"
        "如出现多个年份/月份，请输出多条 times。若无法判断时间则 times 为空。"
        "注意：只需指定年份(year)，系统会自动确定对应的大运信息。"
        "对于时间范围表达，如未来两年或接下来3年，请生成多个 times 条目，每个对应一个具体年份。"
    )
    dayun_hint = ""
    if dayun_list:
        lines = []
        for item in dayun_list:
            name = item.get("name") or "未知大运"
            start = item.get("start_year")
            end = item.get("end_year")
            if isinstance(start, int) and isinstance(end, int):
                lines.append(f"- {name} {start}-{end}")
        if lines:
            dayun_hint = "\n大运范围(起止年):\n" + "\n".join(lines)
    user_prompt = (
        f"现在时间: {now.date().isoformat()}\n"
        f"用户问题: {question}"
        f"{dayun_hint}\n"
        "返回 planning_tool 调用。"
    )
    return system_prompt, user_prompt


def _parse_tool_call(content: str) -> Optional[Dict]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and data.get("tool") == "planning_tool":
        return data.get("args") if isinstance(data.get("args"), dict) else None
    if isinstance(data, dict) and "aspects" in data and ("time" in data or "times" in data):
        return data
    return None


def plan_with_llm(
    question: str,
    now: dt.datetime | None = None,
    dayun_list: Optional[List[Dict[str, Any]]] = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
) -> Dict:
    now = now or dt.datetime.now()
    system_prompt, user_prompt = _build_planner_prompt(question, now, dayun_list=dayun_list)
    emit_event(
        event_sink,
        {
            "type": "llm_prompt",
            "node": "PLANNER",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
    )
    emit_event(event_sink, {"type": "tool_call", "tool": "llm_report_tool", "node": "PLANNER"})
    response = llm_report_tool(
        system_prompt,
        user_prompt,
        node="PLANNER",
        stream=stream,
        on_delta=(
            lambda chunk: emit_event(
                event_sink,
                {
                    "type": "node_delta",
                    "node": "PLANNER",
                    "delta": chunk.get("content", ""),
                    "reasoning_delta": chunk.get("reasoning_content", ""),
                },
            )
        )
        if event_sink
        else None,
    )
    emit_event(event_sink, {"type": "tool_result", "tool": "llm_report_tool", "node": "PLANNER"})
    args = _parse_tool_call(response.get("content", ""))
    if not args:
        return plan_with_rules(question, now=now)
    plan = planning_tool(args.get("aspects"), args.get("time"), args.get("times"))
    plan["source"] = "llm"
    return plan


def plan(
    question: str,
    now: dt.datetime | None = None,
    dayun_list: Optional[List[Dict[str, Any]]] = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
) -> Dict:
    mode = os.environ.get("LLM_PLANNER_MODE", "llm").lower()
    if mode == "rule" or os.environ.get("LLM_MODE", "").lower() == "stub":
        result = plan_with_rules(question, now=now)
    else:
        result = plan_with_llm(question, now=now, dayun_list=dayun_list, event_sink=event_sink, stream=stream)
    return _merge_times_from_question(result, question, now=now)


def _merge_times_from_question(
    plan_result: Dict,
    question: str,
    now: dt.datetime | None = None,
) -> Dict:
    detected = detect_times(question, now=now)
    if not detected:
        return plan_result
    times = plan_result.get("times")
    if not isinstance(times, list):
        times = []
    existing = {(t.get("granularity"), t.get("year"), t.get("month")) for t in times}
    for item in detected:
        key = (item.get("granularity"), item.get("year"), item.get("month"))
        if key in existing:
            continue
        times.append(item)
        existing.add(key)
    if times:
        plan_result["times"] = times
        plan_result["time"] = times[0]
    return plan_result
