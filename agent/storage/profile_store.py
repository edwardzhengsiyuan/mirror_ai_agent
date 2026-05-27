"""User profile persistence."""

from __future__ import annotations

import json
import os
from typing import Any, Dict


def load_profile(path: str) -> Dict[str, Any]:
    # utf-8-sig silently strips a BOM if some editor/tool wrote one.
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_profile(path: str, profile: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
