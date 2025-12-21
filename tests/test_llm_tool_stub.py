"""LLM tool stub tests."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.tools.llm_tool import llm_report_tool


def main() -> None:
    os.environ["LLM_MODE"] = "stub"
    res = llm_report_tool("sys", "user", node="CAREER")
    assert res["type"] == "report"
    assert "LLM_PLACEHOLDER:CAREER" in res["content"]
    assert res["reasoning_content"] is None

    os.environ["LLM_MODE"] = "stub"
    res2 = llm_report_tool("sys", "user", model="reasoning", node="OVERALL")
    assert "LLM_PLACEHOLDER:OVERALL" in res2["content"]
    print("llm stub ok")


if __name__ == "__main__":
    main()
