from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from tests import test_llm_live  # type: ignore


SCENARIOS = {
    "fast_nano": {
        "LLM_MODEL_FAST": "gpt-5-nano",
        "LLM_MODEL_REASONING": "gpt-5-nano",
        "LLM_LIVE_FULL": os.environ.get("LLM_LIVE_FULL", "0"),
    },
    "reasoning_gpt5": {
        "LLM_MODEL_FAST": "gpt-5-nano",
        "LLM_MODEL_REASONING": "gpt-5",
        "LLM_LIVE_FULL": os.environ.get("LLM_LIVE_FULL", "1"),
    },
    "force_error_overall": {
        "LLM_MODEL_FAST": "gpt-5-nano",
        "LLM_MODEL_REASONING": os.environ.get("LLM_MODEL_REASONING", "gpt-5"),
        "LLM_FORCE_ERROR": "OVERALL",
        "LLM_LIVE_FULL": "0",
    },
}


def apply_overrides(overrides: dict[str, str]) -> None:
    for key, value in overrides.items():
        os.environ[key] = value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live LLM suite across scenarios.")
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS.keys(),
        default="fast_nano",
        help="Which scenario to run",
    )
    args = parser.parse_args()
    apply_overrides(SCENARIOS[args.scenario])
    print(f"Running live scenario={args.scenario} with overrides={SCENARIOS[args.scenario]}")
    test_llm_live.main()


if __name__ == "__main__":
    main()
