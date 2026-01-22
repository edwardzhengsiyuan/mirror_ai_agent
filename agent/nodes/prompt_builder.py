"""Prompt assembly for nodes."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROMPTS_DIR = os.path.join(REPO_ROOT, "agent", "prompts", "templates")

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
    "GEJU": "geju.md",
    "WUXING_PREFS": "inter.md",
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
    geju = cache.get("GEJU", {}).get("output", {}).get("content", "")
    wuxing = cache.get("WUXING_PREFS", {}).get("output", {}).get("content", "")

    if node in FIXED_PROMPTS:
        prompt_text = _load_prompt(FIXED_PROMPTS[node])
    else:
        config = PROMPT_CONFIGS.get(prompt_config, PROMPT_CONFIGS["default"])
        prompt_text = _load_prompt(config[node])

    question_line = f"用户问题: {question}\n" if question else ""

    aspect_blocks = ""
    history_block = ""

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
    if geju:
        prompt_parts.append(f"## 格局:\n{geju}")
    if wuxing:
        prompt_parts.append(f"## 五行偏好:\n{wuxing}")

    # Aspect blocks (only for FINAL node, already filtered above)
    if aspect_blocks:
        prompt_parts.append(aspect_blocks.rstrip())

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
    geju = cache.get("GEJU", {}).get("output", {}).get("content", "")
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

    # Build user prompt
    prompt_parts = []
    
    # History and question
    if history_block:
        prompt_parts.append(history_block.rstrip())
    if question_line:
        prompt_parts.append(question_line.rstrip())

    # Basic paipan info
    if paipan_results:
        prompt_parts.append(f"## 排盘:\n{paipan_results}")
    if guji_results:
        prompt_parts.append(f"## 古籍:\n{guji_results}")

    # Year data (from time_context parameter)
    if year_data_text:
        prompt_parts.append(f"## 目标年份详情:\n{year_data_text}")

    # Dependent node outputs
    if overall:
        prompt_parts.append(f"## 整体分析:\n{overall}")
    if shishen:
        prompt_parts.append(f"## 十神:\n{shishen}")
    if geju:
        prompt_parts.append(f"## 格局:\n{geju}")
    if wuxing:
        prompt_parts.append(f"## 五行偏好:\n{wuxing}")

    # Aspect blocks
    if aspect_blocks:
        prompt_parts.append(aspect_blocks.rstrip())

    # Prompt template
    prompt_parts.append(prompt_text)

    user_prompt = "\n".join(prompt_parts)
    return {"system_prompt": SYSTEM_PROMPT, "user_prompt": user_prompt}
