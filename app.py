"""Minimal CLI entry for the agent."""

from __future__ import annotations

import argparse
import json

from agent.orchestrator import run_turn
from agent.storage.profile_store import edit_profile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="user_profile.json")
    parser.add_argument("--question", required=True)
    args = parser.parse_args()

    with edit_profile(args.profile) as profile:
        result = run_turn(profile, args.question)

    print(result["response"])


if __name__ == "__main__":
    main()
