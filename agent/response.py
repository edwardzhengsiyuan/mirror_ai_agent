"""Response composition."""

from __future__ import annotations

from typing import Any, Dict, List


def llm_output_failed(output: Any) -> bool:
    if not isinstance(output, dict):
        return True
    content = output.get("content")
    return (bool(output.get("error")) or not isinstance(content, str)
            or not content.strip() or content.startswith(("[LLM_ERROR:", "[NODE_ERROR:")))


LLM_FAILURE_MESSAGE = "暂时无法完成分析，请稍后重试。"


def compose_response(question: str, plan: Dict[str, Any], outputs: Dict[str, Any], time_context: Dict[str, Any] | None) -> str:
    sections: List[str] = []
    if time_context:
        if isinstance(time_context, list):
            lines = []
            for ctx in time_context:
                lines.append(str(ctx) if ctx else "None")
            sections.append("时间定位:\n" + "\n".join(lines))
        else:
            sections.append(f"时间定位: {time_context}")
    aspects = plan.get("aspects", [])
    for aspect in aspects:
        report = outputs.get(aspect)
        if isinstance(report, dict) and report.get("type") == "report":
            sections.append(f"{aspect}: {report.get('content', '')}")
        else:
            sections.append(f"{aspect}: 无可用报告")
    if not sections:
        return "未能生成回答。"
    return "\n\n".join(sections)
