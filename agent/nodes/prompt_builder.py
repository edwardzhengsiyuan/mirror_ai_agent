"""Prompt assembly for nodes.

Context injection is dependency-driven: each downstream node only sees the
upstream outputs it actually needs. Repeated text is deduplicated so we never
stack the same paragraph twice into a single prompt.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROMPTS_DIR = os.path.join(REPO_ROOT, "agent", "prompts", "templates")
GEJU_PROMPTS_DIR = os.path.join(REPO_ROOT, "agent", "prompts", "geju")

SYSTEM_PROMPT = "你是一位精通八字的算命师，具有深厚的命理学知识和丰富的分析经验。"

INTERNAL_NODE_INSTRUCTION = """# 中间节点输出约束

这是供后续节点继续推理使用的内部分析中间态，不是直接交付用户的最终答复。
请只输出可复核的命理逻辑、判定依据、关键矛盾和结论。
不要使用“缘主您好”“开运建议”“算命师箴言”“祝福语”“穿什么颜色/摆什么物件”等面向用户交付的包装内容。
如需给出注意事项，只保留与命理推理直接相关的风险依据，不要写泛化人生建议。"""

PROMPT_CONFIGS = {
    "default": {
        "RELATIONSHIP": "ganqing_lym.md",
        "CAREER": "shiye_lym.md",
        "HEALTH": "jiankang_lym.md",
        "LIUQIN": "liuqin_lym.md",
        "GUIREN": "guiren_lym.md",
        "XINGGE": "xingge_lym.md",
        "OTHER": "other_lym.md",
    },
}

FIXED_PROMPTS = {
    "OVERALL": "init_analysis.md",
    "SHISHEN": "shishen.md",
    "WUXING_PREFS": "inter.md",
}

GEJU_ROUTER_PROMPT = "# 格局判断路由.md"
GEJU_LEVEL_PROMPT = "# 格局层次分析.md"

GEJU_ANALYSIS_PROMPTS = {
    "正官格": "# 正格_正官格.md",
    "财格": "# 正格_财格.md",
    "印格": "# 正格_印格.md",
    "食神格": "# 正格_食神格.md",
    "七杀格": "# 正格_七杀格.md",
    "伤官格": "# 正格_伤官格.md",
    "建禄格": "# 正格_建禄格.md",
    "羊刃格": "# 正格_羊刃格.md",
    "SPECIAL_1": "# 特殊格局_专旺从格.md",
    "SPECIAL_2": "# 特殊格局_杂格.md",
    "NONE": "# 杂气无格.md",
}

RESPONSE_PROMPT = "final_answer.md"
ASPECT_NODES = [
    "CAREER",
    "RELATIONSHIP",
    "HEALTH",
    "GUIREN",
    "LIUQIN",
    "XINGGE",
    "OTHER",
]

# Per-node upstream context keys. Order is rendering order in the prompt.
NODE_CONTEXT: Dict[str, List[str]] = {
    "OVERALL": ["paipan", "guji", "dayun_liunian"],
    "SHISHEN": ["paipan", "guji", "dayun_liunian"],
    "GEJU_ROUTER": ["paipan", "guji", "dayun_liunian"],
    "GEJU_ANALYSIS": ["paipan", "guji", "dayun_liunian", "GEJU_ROUTER"],
    "GEJU_LEVEL": ["paipan", "guji", "dayun_liunian", "GEJU_ROUTER", "GEJU_ANALYSIS"],
    "WUXING_PREFS": ["paipan", "guji", "dayun_liunian", "OVERALL", "SHISHEN", "GEJU"],
    "CAREER": ["paipan", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"],
    "RELATIONSHIP": ["paipan", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"],
    "HEALTH": ["paipan", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"],
    "GUIREN": ["paipan", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"],
    "LIUQIN": ["paipan", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"],
    "XINGGE": ["paipan", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"],
    "OTHER": ["paipan", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"],
}

CONTEXT_LABELS: Dict[str, str] = {
    "paipan": "排盘",
    "guji": "古籍",
    "dayun_liunian": "完整大运流年信息",
    "OVERALL": "整体分析",
    "SHISHEN": "十神",
    "GEJU": "格局（三节点合并）",
    "GEJU_ROUTER": "格局判断",
    "GEJU_ANALYSIS": "格局详细分析",
    "GEJU_LEVEL": "格局层次",
    "WUXING_PREFS": "五行喜忌",
    "year_data": "目标年份详情",
    "CAREER": "事业",
    "RELATIONSHIP": "感情",
    "HEALTH": "健康",
    "GUIREN": "贵人",
    "LIUQIN": "六亲",
    "XINGGE": "性格",
    "OTHER": "综合",
}


def _load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_geju_prompt(filename: str) -> str:
    path = os.path.join(GEJU_PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_router_output(cache: Dict[str, Any]) -> Dict[str, Any]:
    """Parse GEJU_ROUTER JSON output from cache.

    Tolerates raw JSON, fenced JSON, and JSON wrapped in surrounding prose.
    """
    content = cache.get("GEJU_ROUTER", {}).get("output", {}).get("content", "")
    if not content:
        return {"category": "NONE", "patterns": []}

    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_str = content.strip()

    try:
        result = json.loads(json_str)
        return {
            "category": result.get("category", "NONE"),
            "patterns": result.get("patterns", []),
        }
    except (json.JSONDecodeError, TypeError):
        return {"category": "NONE", "patterns": []}


def _select_geju_analysis_prompt(router_output: Dict[str, Any]) -> str:
    category = router_output.get("category", "NONE")
    patterns = router_output.get("patterns", [])
    if category in ("SPECIAL_1", "SPECIAL_2", "NONE"):
        return GEJU_ANALYSIS_PROMPTS.get(category, GEJU_ANALYSIS_PROMPTS["NONE"])
    if patterns and category == "NORMAL":
        first_pattern_name = patterns[0].get("name", "")
        if first_pattern_name in GEJU_ANALYSIS_PROMPTS:
            return GEJU_ANALYSIS_PROMPTS[first_pattern_name]
    return GEJU_ANALYSIS_PROMPTS["NONE"]


def validate_geju_router_output(content: str) -> tuple[bool, str]:
    if not content or not content.strip():
        return False, "输出为空，请返回JSON格式的格局分类结果"
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        brace_match = re.search(r"\{[\s\S]*\}", content)
        json_str = brace_match.group(0) if brace_match else content.strip()
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as e:
        return False, f"JSON解析失败: {e}。请只返回有效的JSON格式，不要包含其他文字"
    if not isinstance(result, dict):
        return False, "输出必须是JSON对象，不是数组或其他类型"
    if "category" not in result:
        return False, "缺少'category'字段。必须包含: SPECIAL_1, NORMAL, SPECIAL_2, 或 NONE"
    valid_categories = {"SPECIAL_1", "NORMAL", "SPECIAL_2", "NONE"}
    if result["category"] not in valid_categories:
        return False, f"'category'值无效: {result['category']}。必须是: {', '.join(valid_categories)}"
    if "patterns" not in result:
        return False, "缺少'patterns'字段。必须是一个数组"
    if not isinstance(result["patterns"], list):
        return False, "'patterns'必须是数组格式"
    for i, pattern in enumerate(result["patterns"]):
        if not isinstance(pattern, dict):
            return False, f"patterns[{i}]必须是对象格式"
        if "name" not in pattern:
            return False, f"patterns[{i}]缺少'name'字段"
        if "reasoning" not in pattern:
            return False, f"patterns[{i}]缺少'reasoning'字段"
    return True, ""


NODE_VALIDATORS: Dict[str, Callable[[str], tuple[bool, str]]] = {
    "GEJU_ROUTER": validate_geju_router_output,
}


def _format_geju_context(cache: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("GEJU_ROUTER", "GEJU_ANALYSIS", "GEJU_LEVEL"):
        content = str(cache.get(key, {}).get("output", {}).get("content", "") or "").strip()
        if content:
            parts.append(f"## {CONTEXT_LABELS.get(key, key)}\n{content}")
    return "\n\n".join(parts)


def _format_dayun_liunian_context(cache: Dict[str, Any], runtime_context: Optional[Dict[str, Any]] = None) -> str:
    paipan = cache.get("PAIPAN", {}).get("output", {}) or {}
    parts: List[str] = []
    liupan = str(paipan.get("liupan_results") or "").strip()
    if liupan:
        parts.append("## 排盘脚本大运简排/流盘结果\n" + liupan)
    year_data = _format_year_data((runtime_context or {}).get("time_context"))
    if year_data:
        parts.append("## 目标年份大运/流年/流月详情\n" + year_data)
    return "\n\n".join(parts)


def _resolve_context_value(
    key: str,
    cache: Dict[str, Any],
    runtime_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Return the textual content for a context key, or empty string."""
    paipan = cache.get("PAIPAN", {}).get("output", {}) or {}
    if key == "paipan":
        return str(paipan.get("paipan_results") or "")
    if key == "guji":
        return str(paipan.get("guji_results") or "")
    if key == "dayun_liunian":
        return _format_dayun_liunian_context(cache, runtime_context=runtime_context)
    if key == "GEJU":
        return _format_geju_context(cache)
    return str(cache.get(key, {}).get("output", {}).get("content", "") or "")


class _DedupCollector:
    """Collect labelled text fragments while skipping duplicates / substrings.

    A fragment is dropped if its trimmed text is empty, is already present
    verbatim, or is fully contained in any previously kept fragment that is
    longer (e.g. a brief summary that the LLM already saw verbatim earlier).
    """

    _MIN_LEN_FOR_SUBSTRING_CHECK = 64

    def __init__(self) -> None:
        self._kept: List[tuple[str, str]] = []  # (label, text)
        self._seen_exact: set[str] = set()

    def add(self, label: str, text: str) -> bool:
        body = (text or "").strip()
        if not body:
            return False
        key = body
        if key in self._seen_exact:
            return False
        for _, prev in self._kept:
            if len(body) >= self._MIN_LEN_FOR_SUBSTRING_CHECK and body in prev:
                return False
        self._seen_exact.add(key)
        self._kept.append((label, body))
        return True

    def __iter__(self):
        return iter(self._kept)

    def render(self, heading_prefix: str = "##") -> List[str]:
        return [f"{heading_prefix} {label}:\n{text}" for label, text in self._kept]


def _build_context_for_node(
    node: str,
    cache: Dict[str, Any],
    extra_keys: Optional[Sequence[str]] = None,
    runtime_context: Optional[Dict[str, Any]] = None,
) -> _DedupCollector:
    """Collect dependency-driven context fragments for a node.

    ``extra_keys`` is for callers (e.g. RESPONSE) that want to add aspect
    nodes after the standard prereqs.
    """
    keys = list(NODE_CONTEXT.get(node, []))
    if extra_keys:
        for key in extra_keys:
            if key not in keys:
                keys.append(key)
    collector = _DedupCollector()
    for key in keys:
        text = _resolve_context_value(key, cache, runtime_context=runtime_context)
        label = CONTEXT_LABELS.get(key, key)
        collector.add(label, text)
    return collector


def build_prompt(
    node: str,
    cache: Dict[str, Any],
    prompt_config: str = "lingyun_cat",
    question: Optional[str] = None,  # kept for back-compat; aspect nodes ignore it
    history_rounds: Optional[list[dict[str, str]]] = None,  # ditto
    runtime_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Assemble system + user prompt for a persistent node.

    Only upstream outputs declared in :data:`NODE_CONTEXT` for ``node`` are
    injected. Repeated content across upstream nodes is deduplicated so the
    same paragraph never lands twice in one prompt.
    """
    if node == "GEJU_ROUTER":
        prompt_text = _load_geju_prompt(GEJU_ROUTER_PROMPT)
    elif node == "GEJU_ANALYSIS":
        router_output = _parse_router_output(cache)
        prompt_text = _load_geju_prompt(_select_geju_analysis_prompt(router_output))
    elif node == "GEJU_LEVEL":
        prompt_text = _load_geju_prompt(GEJU_LEVEL_PROMPT)
    elif node in FIXED_PROMPTS:
        prompt_text = _load_prompt(FIXED_PROMPTS[node])
    else:
        config = PROMPT_CONFIGS.get(prompt_config, PROMPT_CONFIGS["default"])
        if node not in config:
            config = PROMPT_CONFIGS["default"]
        prompt_text = _load_prompt(config[node])

    collector = _build_context_for_node(node, cache, runtime_context=runtime_context)
    context_blocks = collector.render(heading_prefix="##")

    parts: List[str] = [INTERNAL_NODE_INSTRUCTION]
    parts.extend(context_blocks)
    parts.append(prompt_text)
    return {"system_prompt": SYSTEM_PROMPT, "user_prompt": "\n".join(parts)}


def _format_year_data(time_context: Optional[Dict[str, Any]]) -> str:
    if not isinstance(time_context, dict):
        return ""
    year_data_list = time_context.get("year_data") or []
    if not year_data_list:
        return ""
    parts: List[str] = []
    for yd in year_data_list:
        year = yd.get("year")
        data = yd.get("data") or ""
        if not data:
            continue
        if year is not None:
            parts.append(f"{year}年:\n{data}")
        else:
            parts.append(str(data))
    return "\n\n".join(parts)


def _format_history_rounds(
    history_rounds: Optional[List[Dict[str, str]]],
    per_round_assistant_chars: int = 800,
    per_round_user_chars: int = 400,
) -> str:
    """Format recent rounds with light truncation.

    Full assistant outputs from earlier turns can be tens of KB each; we keep
    them at a useful summary length so the response prompt stays focused on
    the current turn.
    """
    if not history_rounds:
        return ""
    formatted: List[str] = []
    for idx, pair in enumerate(history_rounds, start=1):
        user_text = (pair.get("user") or "").strip()
        assistant_text = (pair.get("assistant") or "").strip()
        if len(user_text) > per_round_user_chars:
            user_text = user_text[:per_round_user_chars] + "...(truncated)"
        if len(assistant_text) > per_round_assistant_chars:
            assistant_text = assistant_text[:per_round_assistant_chars] + "...(truncated)"
        formatted.append(
            f"Round {idx}:\nUser: {user_text}\nAssistant: {assistant_text}"
        )
    return "\n\n".join(formatted)


def build_response_prompt(
    cache: Dict[str, Any],
    time_context: Optional[Dict[str, Any]],
    prompt_config: str = "lingyun_cat",  # kept for back-compat
    question: Optional[str] = None,
    history_rounds: Optional[List[Dict[str, str]]] = None,
    aspects: Optional[Sequence[str]] = None,
) -> Dict[str, str]:
    """Build the final-answer LLM prompt.

    Only the aspects produced **this turn** (passed via ``aspects``) are
    injected; stale aspect outputs lingering in ``profile.node_cache`` from
    earlier turns are ignored. Background context is filtered to the same set
    of upstream nodes the aspect prompts saw, with content-level dedup.

    When ``aspects`` is ``None`` we fall back to whatever aspect nodes are in
    the cache, preserving the legacy behaviour.
    """
    prompt_text = _load_prompt(RESPONSE_PROMPT)

    if aspects is None:
        aspect_keys: List[str] = [a for a in ASPECT_NODES if cache.get(a, {}).get("output", {}).get("content")]
    else:
        seen_aspects: set[str] = set()
        aspect_keys = []
        for aspect in aspects:
            normalized = str(aspect).upper()
            if normalized in seen_aspects:
                continue
            if normalized not in ASPECT_NODES:
                continue
            seen_aspects.add(normalized)
            aspect_keys.append(normalized)

    base_keys = ["paipan", "guji", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"]
    context_keys: List[str] = list(base_keys)
    for aspect in aspect_keys:
        if aspect not in context_keys:
            context_keys.append(aspect)

    collector = _DedupCollector()

    year_data_text = _format_year_data(time_context)
    if year_data_text:
        collector.add(CONTEXT_LABELS["year_data"], year_data_text)

    for key in context_keys:
        text = _resolve_context_value(key, cache)
        label = CONTEXT_LABELS.get(key, key)
        collector.add(label, text)

    parts: List[str] = []
    parts.append(f"## 任务说明\n{prompt_text}")
    if question:
        parts.append(f"## 用户问题\n{question}")

    history_text = _format_history_rounds(history_rounds)
    if history_text:
        parts.append(f"## 对话历史\n{history_text}")

    context_blocks = collector.render(heading_prefix="###")
    if context_blocks:
        parts.append("## 分析上下文\n" + "\n\n".join(context_blocks))

    return {"system_prompt": SYSTEM_PROMPT, "user_prompt": "\n\n".join(parts)}
