"""LLM tool stub tests."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.models import DEFAULT_MODEL
from agent.llm_config import resolve_llm_settings
from agent.tools.llm_tool import llm_report_tool


def main() -> None:
    os.environ["LLM_MODE"] = "stub"
    res = llm_report_tool("sys", "user", node="CAREER")
    assert res["type"] == "report"
    assert "LLM_PLACEHOLDER:CAREER" in res["content"]
    assert res["reasoning_content"] is None

    os.environ["LLM_MODE"] = "stub"
    res2 = llm_report_tool("sys", "user", model=DEFAULT_MODEL, node="OVERALL")
    assert "LLM_PLACEHOLDER:OVERALL" in res2["content"]

    os.environ["GPTPROTO_API_KEY"] = "gpt-key"
    os.environ["QWEN_API_KEY"] = "qwen-key"
    response_route = resolve_llm_settings("RESPONSE")
    shishen_route = resolve_llm_settings("SHISHEN")
    assert response_route["model"] == "gemini-3-pro-preview"
    assert response_route["api_key"] == "gpt-key"
    assert shishen_route["model"] == "qwen3-max"
    assert shishen_route["api_key"] == "qwen-key"

    # Node route defaults take priority over the profile/global requested model.
    shishen_default = resolve_llm_settings("SHISHEN", requested_model="gemini-3-pro-preview")
    assert shishen_default["model"] == "qwen3-max"
    assert shishen_default["provider"] == "qwen"

    # Explicit per-node override wins over both node route defaults and global model.
    shishen_override = resolve_llm_settings(
        "SHISHEN",
        requested_model="qwen3-max",
        node_model_overrides={"SHISHEN": "gemini-3-pro-preview"},
    )
    assert shishen_override["model"] == "gemini-3-pro-preview"
    assert shishen_override["provider"] == "gptproto"

    # Nodes without a route default use the global/profile model.
    career_global = resolve_llm_settings("CAREER", requested_model="qwen3-max")
    assert career_global["model"] == "qwen3-max"
    assert career_global["provider"] == "qwen"

    print("llm stub ok")


if __name__ == "__main__":
    main()
