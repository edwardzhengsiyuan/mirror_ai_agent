"""CeZi character divination input tool."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict


def _is_cjk_character(value: str) -> bool:
    return len(value) == 1 and "\u4e00" <= value <= "\u9fff"


def cezi_tool(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize a character-divination request."""
    character = str(inputs.get("character") or "").strip()
    question = str(inputs.get("question") or "").strip()
    if not character:
        raise ValueError("character required")
    if not _is_cjk_character(character):
        raise ValueError("character must be a single Chinese character")
    if not question:
        raise ValueError("question required")

    return {
        "type": "cezi",
        "computed_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "character": character,
        "question": question,
    }
