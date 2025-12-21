"""Response composition."""

from __future__ import annotations

from typing import Any, Dict, List


def compose_response(question: str, plan: Dict[str, Any], outputs: Dict[str, Any], time_context: Dict[str, Any] | None) -> str:
    sections: List[str] = []
    if time_context:
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
