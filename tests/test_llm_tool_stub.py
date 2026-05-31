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
    assert response_route["model"] == "gemini-3.1-pro-preview"
    assert response_route["api_key"] == "gpt-key"
    assert response_route["authorization_scheme"] == "Bearer"
    assert shishen_route["model"] == "gemini-3.1-pro-preview"
    assert shishen_route["api_key"] == "gpt-key"
    assert shishen_route["authorization_scheme"] == "Bearer"

    # SHISHEN should use the global/profile model; GEJU keeps node route defaults.
    shishen_default = resolve_llm_settings("SHISHEN", requested_model="gemini-3.1-pro-preview")
    assert shishen_default["model"] == "gemini-3.1-pro-preview"
    assert shishen_default["provider"] == "gptproto"
    geju_default = resolve_llm_settings("GEJU_ROUTER", requested_model="gemini-3.1-pro-preview")
    assert geju_default["model"] == "qwen3-max"
    assert geju_default["provider"] == "qwen"

    # Explicit per-node override wins over the global model.
    shishen_override = resolve_llm_settings(
        "SHISHEN",
        requested_model="gemini-3.1-pro-preview",
        node_model_overrides={"SHISHEN": "qwen3-max"},
    )
    assert shishen_override["model"] == "qwen3-max"
    assert shishen_override["provider"] == "qwen"

    # Nodes without a route default use the global/profile model.
    career_global = resolve_llm_settings("CAREER", requested_model="qwen3-max")
    assert career_global["model"] == "qwen3-max"
    assert career_global["provider"] == "qwen"

    print("llm stub ok")


if __name__ == "__main__":
    main()
