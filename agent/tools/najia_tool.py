"""Najia/Liuyao divination tool wrapper."""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import random
from typing import Any, Dict, List


def _generate_random_yao_values() -> List[int]:
    return [random.randint(0, 7) for _ in range(6)]


def _validate_yao_values(values: Any) -> List[int]:
    if values is None:
        return _generate_random_yao_values()
    if not isinstance(values, list) or len(values) != 6:
        raise ValueError("yao_values must be a list of six integers")
    normalized: List[int] = []
    for idx, value in enumerate(values):
        try:
            int_value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"yao_values[{idx}] invalid") from exc
        if int_value < 0 or int_value > 7:
            raise ValueError(f"yao_values[{idx}] must be between 0 and 7")
        normalized.append(int_value)
    return normalized


def _line_symbol(is_yang: int) -> str:
    return "---" if is_yang == 1 else "- -"


def _line_role(index: int, shi_index: int, ying_index: int) -> str:
    if index == shi_index:
        return "世"
    if index == ying_index:
        return "应"
    return ""


def _format_line(
    *,
    line_no: int,
    source,
    changed: bool = False,
    liushen: str | None = None,
) -> Dict[str, Any]:
    idx = line_no - 1
    return {
        "line_no": line_no,
        "position": ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"][idx],
        "liushen": liushen or "",
        "symbol": _line_symbol(source.yaoYinyangList[idx]),
        "is_yang": bool(source.yaoYinyangList[idx]),
        "changed": changed,
        "najia": source.najia[idx],
        "liuqin": source.liuqin[idx],
        "role": _line_role(idx, source.shiyao, source.yingyao),
    }


def _format_gua_text(title: str, gua: Any, lines: List[Dict[str, Any]]) -> str:
    parts = [
        f"{title}: {gua.fullname}",
        f"{gua.gong}宫 {gua.gongwei} 卦，五行属{gua.wuxing.name}",
    ]
    for line in reversed(lines):
        marker = "x" if line.get("changed") else " "
        role = line.get("role") or " "
        liushen = (line.get("liushen") + " ") if line.get("liushen") else ""
        parts.append(
            f"{line['position']} {liushen}{line['symbol']} {line['najia']} {line['liuqin']} {marker} {role}".rstrip()
        )
    return "\n".join(parts)


def najia_tool(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a Najia/Liuyao hexagram and return structured outputs."""
    from najia.Gua import GuaGenerator

    question = str(inputs.get("question") or "").strip()
    if not question:
        raise ValueError("question required")
    yao_values = _validate_yao_values(inputs.get("yao_values"))

    # The legacy generator prints time info; capture it and expose as data.
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        generator = GuaGenerator(yao_values)

    bengua = generator.selfgua
    if bengua is None:
        raise ValueError("failed to generate gua")
    biangua = bengua.getBiangua()

    bengua_lines = [
        _format_line(
            line_no=i + 1,
            source=bengua,
            changed=bool(bengua.bianyaoList[i]),
            liushen=bengua.liushen[i] if bengua.liushen else "",
        )
        for i in range(6)
    ]
    biangua_lines = [_format_line(line_no=i + 1, source=biangua) for i in range(6)]

    raw_text = "\n\n".join(
        [
            _format_gua_text("本卦", bengua, bengua_lines),
            _format_gua_text("变卦", biangua, biangua_lines),
        ]
    )

    return {
        "type": "najia",
        "computed_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "question": question,
        "yao_values": yao_values,
        "time_info": {
            "bazi": getattr(generator, "time_info", "").strip(),
            "xunkong": bengua.xunkong,
            "generator_output": captured.getvalue().strip(),
        },
        "bengua": {
            "name": bengua.name,
            "fullname": bengua.fullname,
            "gong": bengua.gong,
            "gongwei": bengua.gongwei,
            "wuxing": bengua.wuxing.name,
            "shi_index": bengua.shiyao,
            "ying_index": bengua.yingyao,
            "lines": bengua_lines,
        },
        "biangua": {
            "name": biangua.name,
            "fullname": biangua.fullname,
            "gong": biangua.gong,
            "gongwei": biangua.gongwei,
            "wuxing": biangua.wuxing.name,
            "shi_index": biangua.shiyao,
            "ying_index": biangua.yingyao,
            "lines": biangua_lines,
        },
        "raw_text": raw_text,
    }
