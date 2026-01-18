"""Prompt assembly for nodes."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROMPTS_DIR = os.path.join(REPO_ROOT, "agent", "prompts", "templates")

SYSTEM_PROMPT = "You are a helpful bazi analysis assistant."

PROMPT_CONFIGS = {
    "lingyun_cat": {
        "RELATIONSHIP": "ganqing_lym.md",
        "CAREER": "shiye_lym.md",
        "HEALTH": "jiankang_lym.md",
        "LIUQIN": "liuqin_lym.md",
        "GUIREN": "guiren_lym.md",
        "XINGGE": "xingge_lym.md",
        "OTHER": "other_lym.md",
    },
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
    "FINAL": "final_answer.md",
}
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
    liupan_results = paipan.get("liupan_results", "")
    guji_results = paipan.get("guji_results", "")
    overall = cache.get("OVERALL", {}).get("output", {}).get("content", "")
    shishen = cache.get("SHISHEN", {}).get("output", {}).get("content", "")
    geju = cache.get("GEJU", {}).get("output", {}).get("content", "")
    wuxing = cache.get("WUXING_PREFS", {}).get("output", {}).get("content", "")
    time_context = cache.get("TIME_CONTEXT", {}).get("output")

    if node in FIXED_PROMPTS:
        prompt_text = _load_prompt(FIXED_PROMPTS[node])
    else:
        config = PROMPT_CONFIGS.get(prompt_config, PROMPT_CONFIGS["lingyun_cat"])
        prompt_text = _load_prompt(config[node])

    question_line = f"User question: {question}\n" if question else ""
    time_block = f"TIME_CONTEXT:\n{time_context}\n" if time_context else ""
    aspect_blocks = ""
    history_block = ""
    if node == "FINAL":
        parts = []
        for aspect in ASPECT_NODES:
            content = cache.get(aspect, {}).get("output", {}).get("content", "")
            if content:
                parts.append(f"{aspect}:\n{content}")
        if parts:
            aspect_blocks = "\n".join(parts) + "\n"
        if history_rounds:
            formatted = []
            for idx, pair in enumerate(history_rounds, start=1):
                user_text = pair.get("user", "")
                assistant_text = pair.get("assistant", "")
                formatted.append(f"Round {idx}:\nUser: {user_text}\nAssistant: {assistant_text}")
            history_block = f"Recent conversation (last {len(history_rounds)} rounds):\n" + "\n".join(formatted) + "\n"
    user_prompt = (
        f"User question context for {node}.\n"
        f"{question_line}"
        f"{history_block}"
        f"Paipan:\n{paipan_results}\n"
        f"Liupan:\n{liupan_results}\n"
        f"Guji:\n{guji_results}\n"
        f"{time_block}"
        f"OVERALL:\n{overall}\n"
        f"SHISHEN:\n{shishen}\n"
        f"GEJU:\n{geju}\n"
        f"WUXING_PREFS:\n{wuxing}\n"
        f"{aspect_blocks}"
        f"\nPrompt:\n{prompt_text}\n"
    )
    return {"system_prompt": SYSTEM_PROMPT, "user_prompt": user_prompt}
