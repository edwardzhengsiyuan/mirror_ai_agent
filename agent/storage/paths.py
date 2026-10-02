"""Helpers for organizing per-user storage paths."""

from __future__ import annotations

import datetime as dt
import os
import re
import uuid
from pathlib import PureWindowsPath
from typing import Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
STORAGE_ROOT = os.path.join(ROOT, "storage")


def valid_storage_id(value: object) -> bool:
    return (isinstance(value, str)
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value) is not None
            and value not in {".", ".."}
            and not value.endswith(".")
            and not PureWindowsPath(value).is_reserved())


def _require_id(value: str) -> str:
    if not valid_storage_id(value):
        raise ValueError("Invalid storage identifier")
    return value


def user_dir(user_id: str) -> str:
    return os.path.join(STORAGE_ROOT, "users", _require_id(user_id))


def profile_path(user_id: str, profile_name: Optional[str] = None) -> str:
    """Return a profile path for a given user (optionally suffixed)."""
    base = user_dir(user_id)
    name = _require_id(profile_name or "profile")
    return os.path.join(base, f"{name}.json")


def session_paths(
    user_id: str,
    session_id: Optional[str] = None,
    profile_name: Optional[str] = None,
) -> Tuple[str, str]:
    """Return (profile_path, conversation_path) for a user/session."""
    session = _require_id(session_id or (dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:12]))
    base = user_dir(user_id)
    convo_dir = os.path.join(base, "conversations")
    convo_path = os.path.join(convo_dir, f"{session}.jsonl")
    return profile_path(user_id, profile_name=profile_name), convo_path
