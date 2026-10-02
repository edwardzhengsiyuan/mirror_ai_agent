"""User profile persistence."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from typing import Any, Dict
from .locking import ProfileLease, profile_lock_path


@contextmanager
def edit_profile(path: str):
    """Hold the shared lease across read, computation and atomic save.

    Exceptions discard in-memory edits and always release the lease. Use this
    transaction boundary for CLI/direct Python code sharing HTTP profiles.
    """
    with ProfileLease(profile_lock_path(path)):
        profile = load_profile(path)
        yield profile
        save_profile(path, profile)


def load_profile(path: str) -> Dict[str, Any]:
    # utf-8-sig silently strips a BOM if some editor/tool wrote one.
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_profile(path: str, profile: Dict[str, Any]) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    # Serialize before touching the existing profile; replace on the same volume.
    payload = json.dumps(profile, ensure_ascii=False, indent=2)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         prefix=".profile-", suffix=".tmp", delete=False) as f:
            temporary = f.name
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
