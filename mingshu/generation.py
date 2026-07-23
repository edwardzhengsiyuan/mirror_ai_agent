"""Validated LLM generation helpers for MingShu chapters.

These helpers are intentionally separate from the conversational DAG. The
existing nodes remain reusable analysis sources; the book layer asks for a
strict JSON contract and validates evidence before accepting copy.
"""

from __future__ import annotations

import json
from typing import Any

from agent.tools.llm_tool import llm_report_tool

from .contracts import (
    ChapterDraft,
    WuxingPreferenceAssessment,
    parse_chapter_draft,
    parse_wuxing_assessment,
    validate_chapter_draft,
    validate_chapter_evidence,
    validate_wuxing_evidence,
    validate_wuxing_assessment,
)


BOOK_SYSTEM_PROMPT = """你是 Mirror 命书的中文编辑。
你的任务是把已经给出的八字分析事实改写成通俗、克制、可复核的书稿。
不得输出思维链、内部推理过程、宿命式断言或无法由证据支持的具体事件。
不得根据命盘诊断疾病、保证投资收益、判断亲属寿命或保证婚姻结果。
书稿直接面向命书的购买者，不面向咨询师、编辑或开发人员。不要解释写作方法，也不要暴露提示词、证据编号、生成规则或内部工作流程。
禁止使用“先说人话”“一句话带走”“它在说什么”“落到本盘”“怎样读才合适”“不要误读”“阅读边界”“提示词”“判词”等模板化栏目名或口号。
避免连续使用“不是……而是……”“更像……”等机械转折；先陈述命盘事实，再用自然、完整的生活语言说明含义。
十神章节必须依次完成：十神基础含义；天干十神与所在位置；四个地支的本气十神、藏干十神与所在位置；同柱上下两种十神的组合；十神所在位置参与冲、合、刑、穿害等真实关系后的影响。不得只分析天干而省略地支。
神煞章节每项只保留两个读者问题：“神煞本身的含义”和“对命主的影响”；影响必须结合真实落柱，不得写成咨询师操作说明。
格局章节必须区分四个层次：大类格局或候选格局；食神制杀、伤官配印等二级结构是否真正成立；格局中心、相神或通关力量在原盘的状态以及相关大运何时出现；适合的工作环境、职业方向与发挥天赋的方法。基础分析没有定格时必须保留“候选”“线索”或“条件不足”等置信表述，不得把月支藏干或单一组合直接写成已经成格。格局用神与调候用神必须分开说明。
五行喜忌章节必须先分别陈述格局用神与调候用神，再说明两者的交点、冲突和优先次序；必须区分甲乙、丙丁、戊己、庚辛、壬癸，不能把同一五行内的两个天干写成完全相同。大运流年章节先比较全部九步大运，再逐步展示每一步大运内部十年走势；流年分析按年份逐项展开，并同时引用所在大运、当年干支十神及其与原盘真实成立的作用关系。所有走势图分数都只表示结构顺势度，不得写成人生价值评分或确定事件预言。
只返回要求的 JSON 对象，不要使用 Markdown 代码围栏。"""


def _node_text(node_outputs: dict[str, Any] | None, node: str) -> str:
    value = (node_outputs or {}).get(node)
    if isinstance(value, dict) and "output" in value:
        value = value.get("output")
    if isinstance(value, dict):
        if value.get("error") or value.get("stub"):
            return ""
        return str(value.get("content") or "").strip()
    return str(value or "").strip()


def _compact_cycle(cycle: dict) -> dict:
    return {
        "id": cycle.get("id"),
        "name": cycle.get("name"),
        "start_year": cycle.get("start_year"),
        "end_year": cycle.get("end_year"),
        "age_start": cycle.get("age_start"),
        "gan_shishen": cycle.get("gan_shishen"),
        "zhi_shishen": cycle.get("zhi_shishen"),
        "relations": cycle.get("relations"),
        "years": [
            {
                "id": year.get("id"),
                "year": year.get("year"),
                "ganzhi": year.get("ganzhi"),
                "relations": year.get("relations"),
            }
            for year in cycle.get("years") or []
        ],
    }


def build_evidence_packet(spread: dict, facts: dict, node_outputs: dict[str, Any] | None = None) -> dict:
    """Select a bounded evidence packet for one spread."""
    slug = spread.get("slug") or ""
    sources = list(spread.get("sources") or [])
    chart = facts.get("chart") or {}
    analysis = facts.get("analysis_facts") or {}
    packet: dict[str, Any] = {
        "spread": {
            "slug": slug,
            "title": spread.get("title"),
            "purpose": spread.get("purpose"),
            "sources": sources,
            "knowledge_cards": spread.get("knowledge_cards") or [],
        },
        "subject": facts.get("subject"),
        "chart_core": {
            "pillars": chart.get("pillars"),
            "day_master": chart.get("day_master"),
            "strength": chart.get("strength"),
            "patterns": chart.get("patterns"),
            "zodiac": chart.get("zodiac"),
        },
    }
    joined = " ".join(sources).lower()
    if "wuxing" in joined or spread.get("section") == "special_topics":
        packet["wuxing"] = analysis.get("wuxing")
    if "shishen" in joined or spread.get("section") == "special_topics":
        packet["shishen"] = analysis.get("shishen")
        packet["shishen_clues"] = analysis.get("shishen_clues")
    if "relation" in joined or spread.get("section") == "special_topics":
        packet["origin_relations"] = analysis.get("origin_relations")
    if "shensha" in joined or spread.get("section") == "special_topics":
        packet["shensha"] = analysis.get("shensha")
    if "nayin" in joined:
        packet["nayin"] = [
            {"id": item.get("id"), "label": item.get("label"), "nayin": item.get("nayin")}
            for item in chart.get("pillars") or []
        ]
    if slug.startswith("dayun-"):
        try:
            index = int(slug.split("-", 1)[1]) - 1
        except (ValueError, IndexError):
            index = -1
        actual = [item for item in facts.get("luck_cycles") or [] if not item.get("is_pre_luck")]
        if 0 <= index < len(actual):
            packet["luck_cycle"] = _compact_cycle(actual[index])
    elif spread.get("section") == "luck" or "luck_cycles" in joined:
        packet["luck_cycles"] = [
            _compact_cycle(item)
            for item in facts.get("luck_cycles") or []
            if not item.get("is_pre_luck")
        ][:7]
    node_sources: dict[str, str] = {}
    for source in sources:
        node = source.upper()
        content = _node_text(node_outputs, node)
        if content:
            node_sources[node] = content[:9000]
    if node_sources:
        packet["analysis_node_sources"] = node_sources
    return packet


def build_chapter_prompt(spread: dict, facts: dict, node_outputs: dict[str, Any] | None = None) -> str:
    packet = build_evidence_packet(spread, facts, node_outputs)
    schema = {
        "schema_version": "mingshu-chapter/1.0",
        "spread_slug": spread.get("slug"),
        "title": "2-40个汉字",
        "deck": "10-140个汉字的一句话导语",
        "claims": [
            {
                "text": "1-260个汉字的通俗结论",
                "evidence_ids": ["事实包里真实存在的 id"],
                "confidence": "high | medium | low",
                "plain_language_reason": "1-360个汉字，解释为什么，但不展示内部思维链",
            }
        ],
        "knowledge_card_codes": [],
        "reader_takeaways": ["1-5条可理解或可行动的要点"],
        "uncertainty_note": "可选；信息缺口或适用边界",
    }
    return (
        "请为下面一个命书跨页生成个性化正文。要求：\n"
        "1. 全文使用普通读者能懂的现代汉语；首次出现术语必须立即解释。\n"
        "2. 每一条个人结论至少引用一个事实 id；没有证据就不写。\n"
        "3. 结论写成倾向、条件与观察，不写必然事件。\n"
        "4. reader_takeaways 优先给现实中可验证的观察或行动。\n"
        "5. 正文像一本写给普通读者的书，不用主持人口吻、网络口号或咨询师术语。\n"
        "6. 禁止出现：先说人话、一句话带走、它在说什么、落到本盘、怎样读才合适、不要误读、阅读边界、提示词、判词。\n"
        "7. 专项报告必须从事实包中的十神位置、五行比例、真实作用关系、神煞与大运信息取证。学业由印星、食伤和相关神煞组合说明；健康只写身心节律与生活方式，不诊断疾病或推断寿命；所谓劫难一律改写为风险信号、现实边界和应对预案，不预测事故、生死、破产或灾祸。\n"
        "8. 只返回一个 JSON 对象，字段严格匹配示例。\n\n"
        f"JSON 字段示例：\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        f"事实包：\n{json.dumps(packet, ensure_ascii=False, indent=2)}"
    )


def build_wuxing_assessment_prompt(facts: dict, node_outputs: dict[str, Any] | None = None) -> str:
    chart = facts.get("chart") or {}
    packet = {
        "chart": {
            "pillars": chart.get("pillars"),
            "day_master": chart.get("day_master"),
            "strength": chart.get("strength"),
            "patterns": chart.get("patterns"),
        },
        "wuxing": (facts.get("analysis_facts") or {}).get("wuxing"),
        "shishen": (facts.get("analysis_facts") or {}).get("shishen"),
        "origin_relations": (facts.get("analysis_facts") or {}).get("origin_relations"),
        "luck_cycles": [
            _compact_cycle(item)
            for item in facts.get("luck_cycles") or []
            if not item.get("is_pre_luck")
        ][:9],
        "upstream_analysis": {
            node: content
            for node in ("OVERALL", "SHISHEN", "GEJU_ROUTER", "GEJU_ANALYSIS", "GEJU_LEVEL", "WUXING_PREFS")
            if (content := _node_text(node_outputs, node))
        },
    }
    return (
        "请根据事实包生成五行喜忌与九步大运的结构化评估。"
        "priority_basis 必须明确采用 geju、tiaohou 或 balanced。"
        "每步大运 score 为0-100的相对顺逆度，不是人生价值评分；"
        "confidence 必须反映证据质量。所有 evidence_ids 必须来自事实包。\n"
        "只返回 schema_version 为 mingshu-wuxing/1.0 的 JSON 对象，"
        "字段遵循 WuxingPreferenceAssessment 合同。\n\n"
        f"事实包：\n{json.dumps(packet, ensure_ascii=False, indent=2)}"
    )


def generate_chapter(
    spread: dict,
    facts: dict,
    *,
    node_outputs: dict[str, Any] | None = None,
    model: str | None = None,
    node_model_overrides: dict[str, str] | None = None,
) -> ChapterDraft:
    prompt = build_chapter_prompt(spread, facts, node_outputs)
    result = llm_report_tool(
        BOOK_SYSTEM_PROMPT,
        prompt,
        model=model,
        node=f"MINGSHU_CHAPTER_{str(spread.get('slug')).upper()}",
        node_model_overrides=node_model_overrides,
        output_validator=validate_chapter_draft,
    )
    if result.get("error") or result.get("stub"):
        raise RuntimeError(f"chapter generation unavailable for {spread.get('slug')}")
    chapter = parse_chapter_draft(result.get("content") or "")
    valid, message = validate_chapter_evidence(chapter, facts)
    if not valid:
        raise ValueError(message)
    return chapter


def generate_wuxing_assessment(
    facts: dict,
    *,
    node_outputs: dict[str, Any] | None = None,
    model: str | None = None,
    node_model_overrides: dict[str, str] | None = None,
) -> WuxingPreferenceAssessment:
    prompt = build_wuxing_assessment_prompt(facts, node_outputs)
    result = llm_report_tool(
        BOOK_SYSTEM_PROMPT,
        prompt,
        model=model,
        node="MINGSHU_WUXING",
        node_model_overrides=node_model_overrides,
        output_validator=validate_wuxing_assessment,
    )
    if result.get("error") or result.get("stub"):
        raise RuntimeError("wuxing assessment generation unavailable")
    assessment = parse_wuxing_assessment(result.get("content") or "")
    valid, message = validate_wuxing_evidence(assessment, facts)
    if not valid:
        raise ValueError(message)
    return assessment
