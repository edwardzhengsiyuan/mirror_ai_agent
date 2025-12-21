"""Minimal CLI entry for the agent."""

from __future__ import annotations

import argparse
import json

from agent.orchestrator import run_turn
from agent.storage.profile_store import load_profile, save_profile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="user_profile.json")
    parser.add_argument("--question", required=True)
    args = parser.parse_args()

    profile = load_profile(args.profile)
    result = run_turn(profile, args.question)
    save_profile(args.profile, profile)

    print(result["response"])


if __name__ == "__main__":
    main()
