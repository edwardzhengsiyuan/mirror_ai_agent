"""Prompt assembly for nodes."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROMPTS_DIR = os.path.join(REPO_ROOT, "agent", "prompts", "templates")
GEJU_PROMPTS_DIR = os.path.join(REPO_ROOT, "agent", "prompts", "geju")

SYSTEM_PROMPT = "你是一位精通八字的算命师，具有深厚的命理学知识和丰富的分析经验。"

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

# GEJU multi-stage prompt mappings
GEJU_ROUTER_PROMPT = "# 格局判断路由.md"
GEJU_LEVEL_PROMPT = "# 格局层次分析.md"

# GEJU_ANALYSIS prompt selection based on router category/pattern
GEJU_ANALYSIS_PROMPTS = {
    # Normal patterns (正格)
    "正官格": "# 正格_正官格.md",
    "财格": "# 正格_财格.md",
    "印格": "# 正格_印格.md",
    "食神格": "# 正格_食神格.md",
    "七杀格": "# 正格_七杀格.md",
    "伤官格": "# 正格_伤官格.md",
    "建禄格": "# 正格_建禄格.md",
    "羊刃格": "# 正格_羊刃格.md",
    # Special patterns
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


def _load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_geju_prompt(filename: str) -> str:
    """Load a prompt from the geju prompts directory."""
    path = os.path.join(GEJU_PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_router_output(cache: Dict[str, Any]) -> Dict[str, Any]:
    """Parse GEJU_ROUTER JSON output from cache.

    Supports both raw JSON and JSON wrapped in markdown code blocks.
    Returns: {"category": str, "patterns": list} or default on error.
    """
    content = cache.get("GEJU_ROUTER", {}).get("output", {}).get("content", "")
    if not content:
        return {"category": "NONE", "patterns": []}

    # Try to extract JSON from markdown code block
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Assume the entire content is JSON
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
    """Select the appropriate GEJU_ANALYSIS prompt based on router output.

    Uses the first pattern's name for normal patterns, or category for special/none.
    """
    category = router_output.get("category", "NONE")
    patterns = router_output.get("patterns", [])

    # For SPECIAL_1, SPECIAL_2, NONE - use category directly
    if category in ("SPECIAL_1", "SPECIAL_2", "NONE"):
        return GEJU_ANALYSIS_PROMPTS.get(category, GEJU_ANALYSIS_PROMPTS["NONE"])

    # For NORMAL category, use the first pattern's name
    if patterns and category == "NORMAL":
        first_pattern_name = patterns[0].get("name", "")
        if first_pattern_name in GEJU_ANALYSIS_PROMPTS:
            return GEJU_ANALYSIS_PROMPTS[first_pattern_name]

    # Default fallback
    return GEJU_ANALYSIS_PROMPTS["NONE"]


def validate_geju_router_output(content: str) -> tuple[bool, str]:
    """Validate GEJU_ROUTER output format.

    Expected output is JSON with 'category' and 'patterns' fields.
    Supports raw JSON or JSON wrapped in markdown code blocks.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content or not content.strip():
        return False, "输出为空，请返回JSON格式的格局分类结果"

    # Try to extract JSON from markdown code block
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find JSON object in content
        # Look for { ... } pattern
        brace_match = re.search(r"\{[\s\S]*\}", content)
        if brace_match:
            json_str = brace_match.group(0)
        else:
            json_str = content.strip()

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

    # Validate each pattern has required fields
    for i, pattern in enumerate(result["patterns"]):
        if not isinstance(pattern, dict):
            return False, f"patterns[{i}]必须是对象格式"
        if "name" not in pattern:
            return False, f"patterns[{i}]缺少'name'字段"
        if "reasoning" not in pattern:
            return False, f"patterns[{i}]缺少'reasoning'字段"

    return True, ""


# Export validators for use by execution layer
NODE_VALIDATORS = {
    "GEJU_ROUTER": validate_geju_router_output,
}


def build_prompt(
    node: str,
    cache: Dict[str, Any],
    prompt_config: str = "lingyun_cat",
    question: Optional[str] = None,
    history_rounds: Optional[list[dict[str, str]]] = None,
) -> Dict[str, str]:
    paipan = cache.get("PAIPAN", {}).get("output", {})
    paipan_results = paipan.get("paipan_results", "")
    guji_results = paipan.get("guji_results", "")
    overall = cache.get("OVERALL", {}).get("output", {}).get("content", "")
    shishen = cache.get("SHISHEN", {}).get("output", {}).get("content", "")

    # GEJU multi-stage outputs
    geju_router = cache.get("GEJU_ROUTER", {}).get("output", {}).get("content", "")
    geju_analysis = cache.get("GEJU_ANALYSIS", {}).get("output", {}).get("content", "")
    geju_level = cache.get("GEJU_LEVEL", {}).get("output", {}).get("content", "")

    wuxing = cache.get("WUXING_PREFS", {}).get("output", {}).get("content", "")

    # Determine prompt text based on node type
    if node == "GEJU_ROUTER":
        prompt_text = _load_geju_prompt(GEJU_ROUTER_PROMPT)
    elif node == "GEJU_ANALYSIS":
        router_output = _parse_router_output(cache)
        prompt_filename = _select_geju_analysis_prompt(router_output)
        prompt_text = _load_geju_prompt(prompt_filename)
    elif node == "GEJU_LEVEL":
        prompt_text = _load_geju_prompt(GEJU_LEVEL_PROMPT)
    elif node in FIXED_PROMPTS:
        prompt_text = _load_prompt(FIXED_PROMPTS[node])
    else:
        config = PROMPT_CONFIGS.get(prompt_config, PROMPT_CONFIGS["default"])
        prompt_text = _load_prompt(config[node])

    # Build user prompt dynamically based on available content
    prompt_parts = []

    # Basic paipan info (always present after PAIPAN node)
    if paipan_results:
        prompt_parts.append(f"## 排盘:\n{paipan_results}")
    if guji_results:
        prompt_parts.append(f"## 古籍:\n{guji_results}")

    # Dependent node outputs - only include if they have content
    if overall:
        prompt_parts.append(f"## 整体分析:\n{overall}")
    if shishen:
        prompt_parts.append(f"## 十神:\n{shishen}")

    # GEJU multi-stage outputs - include based on node dependencies
    if geju_router and node not in ("GEJU_ROUTER",):
        prompt_parts.append(f"## 格局判断:\n{geju_router}")
    if geju_analysis and node not in ("GEJU_ROUTER", "GEJU_ANALYSIS"):
        prompt_parts.append(f"## 格局详细分析:\n{geju_analysis}")
    if geju_level and node not in ("GEJU_ROUTER", "GEJU_ANALYSIS", "GEJU_LEVEL"):
        prompt_parts.append(f"## 格局层次:\n{geju_level}")

    if wuxing:
        prompt_parts.append(f"## 五行喜忌:\n{wuxing}")

    # Prompt template
    prompt_parts.append(prompt_text)

    user_prompt = "\n".join(prompt_parts)
    return {"system_prompt": SYSTEM_PROMPT, "user_prompt": user_prompt}


def build_response_prompt(
    cache: Dict[str, Any],
    time_context: Optional[Dict[str, Any]],
    prompt_config: str = "lingyun_cat",
    question: Optional[str] = None,
    history_rounds: Optional[list[dict[str, str]]] = None,
) -> Dict[str, str]:
    """Build prompt for final response generation.

    This is separate from build_prompt() because Response is not a node -
    it's a conversation-level entity that doesn't get cached in profile.node_cache.
    The time_context is passed directly instead of read from cache.
    """
    paipan = cache.get("PAIPAN", {}).get("output", {})
    paipan_results = paipan.get("paipan_results", "")
    guji_results = paipan.get("guji_results", "")
    overall = cache.get("OVERALL", {}).get("output", {}).get("content", "")
    shishen = cache.get("SHISHEN", {}).get("output", {}).get("content", "")

    # GEJU multi-stage outputs - combine for response
    geju_router = cache.get("GEJU_ROUTER", {}).get("output", {}).get("content", "")
    geju_analysis = cache.get("GEJU_ANALYSIS", {}).get("output", {}).get("content", "")
    geju_level = cache.get("GEJU_LEVEL", {}).get("output", {}).get("content", "")

    wuxing = cache.get("WUXING_PREFS", {}).get("output", {}).get("content", "")

    prompt_text = _load_prompt(RESPONSE_PROMPT)
    question_line = f"用户问题: {question}\n" if question else ""

    # Extract year_data from time_context (passed directly, not from cache)
    year_data_text = ""
    if isinstance(time_context, dict):
        year_data_list = time_context.get("year_data", [])
        if year_data_list:
            year_data_text = "\n目标年份详情:\n"
            for yd in year_data_list:
                year_data_text += f"\n{yd['year']}年:\n{yd['data']}\n"

    # Collect aspect node outputs
    aspect_blocks = ""
    parts = []
    for aspect in ASPECT_NODES:
        content = cache.get(aspect, {}).get("output", {}).get("content", "")
        if content:
            parts.append(f"{aspect}:\n{content}")
    if parts:
        aspect_blocks = "\n".join(parts) + "\n"

    # Format history rounds
    history_block = ""
    if history_rounds:
        formatted = []
        for idx, pair in enumerate(history_rounds, start=1):
            user_text = pair.get("user", "")
            assistant_text = pair.get("assistant", "")
            formatted.append(f"Round {idx}:\nUser: {user_text}\nAssistant: {assistant_text}")
        history_block = f"Recent conversation (last {len(history_rounds)} rounds):\n" + "\n".join(formatted) + "\n"

    # Build user prompt with instructions FIRST for better LLM attention
    prompt_parts = []

    # 1. Instructions (template) - placed first for LLM attention priority
    prompt_parts.append(f"## 任务说明\n{prompt_text}")

    # 2. User question - immediately after instructions
    if question_line:
        prompt_parts.append(f"## 用户问题\n{question_line.rstrip()}")

    # 3. Conversation history (if any)
    if history_block:
        prompt_parts.append(f"## 对话历史\n{history_block.rstrip()}")

    # 4. Analysis context sections
    context_parts = []

    # Basic paipan info
    if paipan_results:
        context_parts.append(f"### 排盘:\n{paipan_results}")
    if guji_results:
        context_parts.append(f"### 古籍:\n{guji_results}")

    # Year data (from time_context parameter)
    if year_data_text:
        context_parts.append(f"### 目标年份详情:\n{year_data_text}")

    # Dependent node outputs
    if overall:
        context_parts.append(f"### 整体分析:\n{overall}")
    if shishen:
        context_parts.append(f"### 十神:\n{shishen}")

    # GEJU multi-stage outputs - combine for response
    if geju_router or geju_analysis or geju_level:
        geju_parts = []
        if geju_router:
            geju_parts.append(f"#### 格局判断:\n{geju_router}")
        if geju_analysis:
            geju_parts.append(f"#### 格局详细分析:\n{geju_analysis}")
        if geju_level:
            geju_parts.append(f"#### 格局层次:\n{geju_level}")
        context_parts.append(f"### 格局:\n" + "\n".join(geju_parts))

    if wuxing:
        context_parts.append(f"### 五行喜忌:\n{wuxing}")

    # Aspect blocks
    if aspect_blocks:
        context_parts.append(aspect_blocks.rstrip())

    # Add context section if there's any content
    if context_parts:
        prompt_parts.append(f"## 分析上下文\n" + "\n".join(context_parts))

    user_prompt = "\n".join(prompt_parts)
    return {"system_prompt": SYSTEM_PROMPT, "user_prompt": user_prompt}
