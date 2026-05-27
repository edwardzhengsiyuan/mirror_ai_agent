"""One-shot helper: trim a demo user's profile.json down to its config core.

Usage:
    .venv/Scripts/python.exe scripts/clean_demo_profile.py [user_id ...]

For each user this script:
1. Backs up ``storage/users/<user>/profile.json`` into ``_backup/`` with a
   timestamp.
2. Rewrites the file keeping only configuration fields
   (birth/gender/llm_model/node_model_overrides/bypass_cache/prompt_config)
   and resets ``node_cache`` to ``{}``.

It does NOT touch conversation logs.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys


KEEP_KEYS = {
    "user_id",
    "birth",
    "gender",
    "birth_time_unknown",
    "prompt_config",
    "llm_model",
    "node_model_overrides",
    "bypass_cache",
}


def clean_profile(user_id: str, root: str) -> None:
    user_dir = os.path.join(root, "storage", "users", user_id)
    profile_path = os.path.join(user_dir, "profile.json")
    if not os.path.exists(profile_path):
        print(f"[skip] {user_id}: no profile.json at {profile_path}")
        return

    backup_dir = os.path.join(user_dir, "_backup")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = os.path.join(backup_dir, f"profile.{stamp}.json")
    shutil.copy2(profile_path, backup_path)

    with open(profile_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    cleaned = {k: data[k] for k in KEEP_KEYS if k in data}
    cleaned.setdefault("user_id", user_id)
    cleaned.setdefault("prompt_config", "lingyun_cat")
    cleaned.setdefault("birth_time_unknown", False)
    cleaned["node_cache"] = {}

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"[ok]   {user_id}: backup -> {backup_path}")
    print(f"        kept: {sorted(cleaned.keys())}")
    print(f"        new size: {os.path.getsize(profile_path)} bytes")


def main(argv: list[str]) -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    users = argv[1:] or ["auto_manual_199711190400_male"]
    for user_id in users:
        clean_profile(user_id, root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
