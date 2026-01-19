"""Helpers for organizing per-user storage paths."""

from __future__ import annotations

import datetime as dt
import os
from typing import Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
STORAGE_ROOT = os.path.join(ROOT, "storage")


def user_dir(user_id: str) -> str:
    return os.path.join(STORAGE_ROOT, "users", user_id)


def profile_path(user_id: str, profile_name: Optional[str] = None) -> str:
    """Return a profile path for a given user (optionally suffixed)."""
    base = user_dir(user_id)
    name = profile_name or "profile"
    return os.path.join(base, f"{name}.json")


def session_paths(
    user_id: str,
    session_id: Optional[str] = None,
    profile_name: Optional[str] = None,
) -> Tuple[str, str]:
    """Return (profile_path, conversation_path) for a user/session."""
    session = session_id or dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S")
    base = user_dir(user_id)
    convo_dir = os.path.join(base, "conversations")
    convo_path = os.path.join(convo_dir, f"{session}.jsonl")
    return profile_path(user_id, profile_name=profile_name), convo_path
