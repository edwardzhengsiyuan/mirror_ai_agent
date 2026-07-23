"""Reusable, precomputed classical and climate-reading copy for the book."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


LIBRARY_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "mingshu"
    / "content"
    / "tiaohou-library-v1.json"
)


@lru_cache(maxsize=1)
def load_tiaohou_library() -> dict:
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


def daymaster_classic(gan: str) -> dict:
    return dict(load_tiaohou_library()["daymasters"][gan])


def tiaohou_combo(gan: str, month: str) -> dict:
    return dict(load_tiaohou_library()["combinations"][f"{gan}-{month}"])

