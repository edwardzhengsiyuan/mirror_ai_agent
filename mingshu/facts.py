"""Normalize paipan output into a compact, chart-ready MingShu fact layer."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Iterable

from bazi.core.property import (
    DiShi,
    Gan,
    GejuEnum,
    ShenQiangRuo,
    Shishen,
    Wuxing,
    Zhi,
    strip_ns,
)

from .knowledge import get_nayin_card, get_ten_god_card, get_zodiac_card
from .relations import collect_established_relations


SCHEMA_VERSION = "mingshu-facts/1.0"

PILLAR_LABELS = {
    "year": "年柱",
    "month": "月柱",
    "day": "日柱",
    "hour": "时柱",
    "taiyuan": "胎元",
    "minggong": "命宫",
    "shengong": "身宫",
}

SHISHEN_LABELS = {item.name: item.chinese_name for item in Shishen}
WUXING_LABELS = {item.name: item.chinese_name for item in Wuxing}
GAN_LABELS = {item.name: item.chinese_name for item in Gan}
ZHI_LABELS = {item.name: item.chinese_name for item in Zhi}
DISHI_LABELS = {
    "CHANGSHENG": "长生",
    "MUYU": "沐浴",
    "GUANDAI": "冠带",
    "LINGUAN": "临官",
    "DIWANG": "帝旺",
    "SHUAI": "衰",
    "BING": "病",
    "SI": "死",
    "MU": "墓",
    "JUE": "绝",
    "TAI": "胎",
    "YANG": "养",
}
YINYANG_LABELS = {"YANG": "阳", "YIN": "阴"}
SHENQIANG_LABELS = {item.name: item.chinese_name for item in ShenQiangRuo}
GEJU_LABELS = {item.name: item.chinese_name for item in GejuEnum}

SHENGXIAO_LABELS = {
    "SHU": "鼠",
    "NIU": "牛",
    "HU": "虎",
    "TU": "兔",
    "LONG": "龙",
    "SHE": "蛇",
    "MA": "马",
    "YANG": "羊",
    "HOU": "猴",
    "JI": "鸡",
    "GOU": "狗",
    "ZHU": "猪",
}

RELATION_LABELS = {
    "WUHE": "五合",
    "SANHUI": "三会",
    "SANHE": "三合",
    "BANHE": "半合",
    "GONGHE": "拱合",
    "SANXING": "三刑",
    "XING": "刑",
    "ZIXING": "自刑",
    "LIUHE": "六合",
    "LIUCHONG": "六冲",
    "LIUHAI": "害",
    "XIANGPO": "破",
    "CHUAN": "穿",
}


def _label(code: Any) -> str:
    value = str(code or "")
    bare = strip_ns(value) or value
    namespace = value.split(":", 1)[0] if ":" in value else ""
    mappings = {
        "GAN": GAN_LABELS,
        "ZHI": ZHI_LABELS,
        "WUXING": WUXING_LABELS,
        "SHISHEN": SHISHEN_LABELS,
        "YINYANG": YINYANG_LABELS,
        "DISHI": DISHI_LABELS,
        "SHENQIANGRUO": SHENQIANG_LABELS,
        "SHENGXIAO": SHENGXIAO_LABELS,
        "GEJU": GEJU_LABELS,
    }
    if namespace == "NAYIN":
        card = get_nayin_card(value)
        return card.name if card else bare
    return mappings.get(namespace, {}).get(bare, bare)


def _round_percent(value: Any) -> float:
    try:
        return round(float(value) * 100.0, 2)
    except (TypeError, ValueError):
        return 0.0


def _series(values: Dict[str, Any], prefix: str) -> list[dict]:
    return [
        {
            "id": f"fact:{prefix}:{strip_ns(code)}",
            "code": code,
            "label": _label(code),
            "ratio": round(float(value), 6),
            "percent": _round_percent(value),
        }
        for code, value in values.items()
    ]


def _pillar_fact(
    key: str,
    raw: Dict[str, Any],
    nayin_code: str | None,
    daygan_dishi: str | None,
    zizuo_dishi: str | None,
) -> dict:
    gan = deepcopy(raw.get("gan") or {})
    zhi = deepcopy(raw.get("zhi") or {})
    hidden = []
    for item in zhi.get("hidden_gans") or []:
        hidden.append(
            {
                **item,
                "name_label": _label(item.get("name")),
                "wuxing_label": _label(item.get("wuxing")),
                "yinyang_label": _label(item.get("yinyang")),
                "shishen_label": _label(item.get("shishen")),
            }
        )
    zhi["hidden_gans"] = hidden
    fact = {
        "id": f"fact:pillar:{key}",
        "key": key,
        "label": PILLAR_LABELS[key],
        "ganzhi": f"{_label(gan.get('name'))}{_label(zhi.get('name'))}",
        "gan": {
            **gan,
            "name_label": _label(gan.get("name")),
            "wuxing_label": _label(gan.get("wuxing")),
            "yinyang_label": _label(gan.get("yinyang")),
            "shishen_label": _label(gan.get("shishen")),
        },
        "zhi": {
            **zhi,
            "name_label": _label(zhi.get("name")),
            "wuxing_label": _label(zhi.get("wuxing")),
            "yinyang_label": _label(zhi.get("yinyang")),
        },
        "nayin": None,
        "daygan_dishi": (
            {"code": daygan_dishi, "label": _label(daygan_dishi)}
            if daygan_dishi
            else None
        ),
        "zizuo_dishi": (
            {"code": zizuo_dishi, "label": _label(zizuo_dishi)}
            if zizuo_dishi
            else None
        ),
    }
    if nayin_code:
        card = get_nayin_card(nayin_code)
        fact["nayin"] = {
            "code": nayin_code,
            "label": _label(nayin_code),
            "knowledge": card.to_dict() if card else None,
        }
    return fact


def _compact_relations(raw_relations: Iterable[dict]) -> list[dict]:
    result = []
    for relation in raw_relations or []:
        item = deepcopy(relation)
        for member in item.get("members") or []:
            member["label"] = _label(member.get("code"))
            member["wuxing_label"] = _label(member.get("wuxing"))
            member["pillar_label"] = PILLAR_LABELS.get(member.get("pillar"), member.get("pillar"))
        if item.get("result_wuxing"):
            item["result_wuxing_label"] = _label(item["result_wuxing"])
        result.append(item)
    return result


def _compact_yun_relations(values: Iterable[dict]) -> list[dict]:
    result = []
    for relation in values or []:
        relation_type = strip_ns(relation.get("type")) or relation.get("type")
        members = relation.get("members") or []
        result.append(
            {
                "type": relation.get("type"),
                "label": RELATION_LABELS.get(relation_type, relation_type),
                "members": [
                    {"code": code, "label": _label(code)}
                    for code in members
                ],
            }
        )
    return result


def _compact_luck_cycles(paipan_result: dict, raw_cycles: list[dict]) -> list[dict]:
    dayun_list = paipan_result.get("dayun_list") or []
    result = []
    for index, raw in enumerate(raw_cycles):
        meta = dayun_list[index] if index < len(dayun_list) else {}
        stem = raw.get("gan")
        branch = raw.get("zhi")
        is_pre_luck = not stem or not branch
        years = []
        for year in raw.get("liunian") or []:
            year_stem = year.get("gan")
            year_branch = year.get("zhi")
            months = []
            for sequence, month in enumerate(year.get("liuyue") or [], start=1):
                month_stem = month.get("gan")
                month_branch = month.get("zhi")
                months.append(
                    {
                        "id": f"fact:liuyue:{year.get('year')}:{sequence:02d}",
                        "sequence": sequence,
                        "solar_month": month.get("month"),
                        "solar_day": month.get("day"),
                        "ganzhi": f"{_label(month_stem)}{_label(month_branch)}",
                        "gan": {"code": month_stem, "label": _label(month_stem)},
                        "zhi": {"code": month_branch, "label": _label(month_branch)},
                        "gan_shishen": {
                            "code": month.get("gan_shishen"),
                            "label": _label(month.get("gan_shishen")),
                        },
                        "zhi_shishen": {
                            "code": month.get("zhi_shishen"),
                            "label": _label(month.get("zhi_shishen")),
                        },
                        "relations": _compact_yun_relations(
                            (month.get("gan_relation") or []) + (month.get("zhi_relation") or [])
                        ),
                    }
                )
            years.append(
                {
                    "id": f"fact:liunian:{year.get('year')}",
                    "year": year.get("year"),
                    "age": year.get("age"),
                    "ganzhi": f"{_label(year_stem)}{_label(year_branch)}",
                    "gan": {"code": year_stem, "label": _label(year_stem)},
                    "zhi": {"code": year_branch, "label": _label(year_branch)},
                    "gan_shishen": {
                        "code": year.get("gan_shishen"),
                        "label": _label(year.get("gan_shishen")),
                    },
                    "zhi_shishen": {
                        "code": year.get("zhi_shishen"),
                        "label": _label(year.get("zhi_shishen")),
                    },
                    "relations": _compact_yun_relations(
                        (year.get("gan_relation") or []) + (year.get("zhi_relation") or [])
                    ),
                    "shensha": list(year.get("shensha") or []),
                    "months": months,
                }
            )
        result.append(
            {
                "id": f"fact:dayun:{index:02d}",
                "index": index,
                "is_pre_luck": is_pre_luck,
                "name": "起运前" if is_pre_luck else f"{_label(stem)}{_label(branch)}",
                "start_year": meta.get("start_year", raw.get("year")),
                "end_year": meta.get("end_year"),
                "age_start": meta.get("age_start", raw.get("age")),
                "gan": None if is_pre_luck else {"code": stem, "label": _label(stem)},
                "zhi": None if is_pre_luck else {"code": branch, "label": _label(branch)},
                "gan_shishen": (
                    None
                    if is_pre_luck
                    else {
                        "code": raw.get("gan_shishen"),
                        "label": _label(raw.get("gan_shishen")),
                    }
                ),
                "zhi_shishen": (
                    None
                    if is_pre_luck
                    else {
                        "code": raw.get("zhi_shishen"),
                        "label": _label(raw.get("zhi_shishen")),
                    }
                ),
                "relations": _compact_yun_relations(
                    (raw.get("gan_relation") or []) + (raw.get("zhi_relation") or [])
                ),
                "shensha": list(raw.get("shensha") or []),
                "years": years,
                # A favorable/unfavorable score must come from a validated
                # structured 喜忌 result. Do not fabricate it here.
                "score": None,
                "score_status": "requires_structured_wuxing_preferences",
            }
        )
    return result


def _flow_visual(wuxing_series: list[dict]) -> dict:
    values = {item["code"]: item["percent"] for item in wuxing_series}
    order = [
        ("WUXING:MU", "WUXING:HUO"),
        ("WUXING:HUO", "WUXING:TU"),
        ("WUXING:TU", "WUXING:JIN"),
        ("WUXING:JIN", "WUXING:SHUI"),
        ("WUXING:SHUI", "WUXING:MU"),
    ]
    controls = [
        ("WUXING:MU", "WUXING:TU"),
        ("WUXING:TU", "WUXING:SHUI"),
        ("WUXING:SHUI", "WUXING:HUO"),
        ("WUXING:HUO", "WUXING:JIN"),
        ("WUXING:JIN", "WUXING:MU"),
    ]
    nodes = [
        {
            "id": code,
            "label": _label(code),
            "value": values.get(code, 0.0),
        }
        for code in [
            "WUXING:MU",
            "WUXING:HUO",
            "WUXING:TU",
            "WUXING:JIN",
            "WUXING:SHUI",
        ]
    ]
    edges = [
        {
            "source": source,
            "target": target,
            "kind": "generate",
            "weight": round(min(values.get(source, 0.0), values.get(target, 0.0)), 2),
        }
        for source, target in order
    ]
    edges.extend(
        {
            "source": source,
            "target": target,
            "kind": "control",
            "weight": round(min(values.get(source, 0.0), values.get(target, 0.0)), 2),
        }
        for source, target in controls
    )
    return {
        "type": "five_element_flow",
        "nodes": nodes,
        "edges": edges,
        "note": "连线表示五行生克的阅读关系；节点数值来自原盘力量比例，不代表单独吉凶。",
    }


def build_book_facts(paipan_result: dict, profile: dict | None = None) -> dict:
    """Build a compact, JSON-safe fact package for book generation."""
    if not isinstance(paipan_result, dict):
        raise TypeError("paipan_result must be a dict")
    raw = paipan_result.get("paipan_output")
    if not isinstance(raw, dict):
        raise ValueError("paipan_result.paipan_output is required")

    profile = profile or {}
    zhu_list = raw.get("zhu_list") or {}
    nayin = raw.get("nayin") or []
    daygan_dishi = raw.get("daygan_dishi") or []
    zizuo_dishi = raw.get("zizuo_dishi") or []

    original_keys = ["year", "month", "day", "hour"]
    pillars = []
    for index, key in enumerate(original_keys):
        raw_pillar = zhu_list.get(f"{key}_zhu")
        if not raw_pillar:
            continue
        pillars.append(
            _pillar_fact(
                key,
                raw_pillar,
                nayin[index] if index < len(nayin) else None,
                daygan_dishi[index] if index < len(daygan_dishi) else None,
                zizuo_dishi[index] if index < len(zizuo_dishi) else None,
            )
        )

    auxiliary = []
    for key in ["taiyuan", "minggong", "shengong"]:
        raw_pillar = zhu_list.get(f"{key}_zhu")
        if raw_pillar:
            auxiliary.append(_pillar_fact(key, raw_pillar, None, None, None))

    wuxing_series = _series(raw.get("wuxing_proportions") or {}, "wuxing")
    shishen_series = _series(raw.get("shishen_proportions") or {}, "shishen")
    effective_origin_relations = _compact_relations(raw.get("origin_relations") or [])
    origin_relations = collect_established_relations(pillars, effective_origin_relations)
    luck_cycles = _compact_luck_cycles(paipan_result, raw.get("yun") or [])

    zodiac_code = raw.get("shengxiao")
    zodiac_card = get_zodiac_card(zodiac_code)
    source_payload = json.dumps(raw, ensure_ascii=True, sort_keys=True, default=str)
    source_hash = hashlib.sha256(source_payload.encode("utf-8")).hexdigest()

    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "kind": "paipan_tool",
            "sha256": source_hash,
        },
        "subject": {
            "display_name": profile.get("display_name") or profile.get("name") or "命主",
            "birth": deepcopy(profile.get("birth") or {}),
            "gender": profile.get("gender"),
            "birth_time_unknown": bool(profile.get("birth_time_unknown", False)),
            "confidence_note": (
                "出生时辰尚未确定，涉及时柱的内容只能作为暂时参考。"
                if profile.get("birth_time_unknown")
                else "本次排盘按所提供的出生日期与时辰计算；若原始记录有误，相关结果会随之改变。"
            ),
        },
        "chart": {
            "pillars": pillars,
            "auxiliary_pillars": auxiliary,
            "day_master": next(
                (
                    {
                        "code": pillar["gan"]["name"],
                        "label": pillar["gan"]["name_label"],
                        "wuxing": pillar["gan"]["wuxing"],
                        "wuxing_label": pillar["gan"]["wuxing_label"],
                    }
                    for pillar in pillars
                    if pillar["key"] == "day"
                ),
                None,
            ),
            "strength": {
                "code": raw.get("shenqiangshenruo"),
                "label": _label(raw.get("shenqiangshenruo")),
            },
            "patterns": [
                {"code": code, "label": _label(code)}
                for code in raw.get("geju") or []
            ],
            "zodiac": {
                "code": zodiac_code,
                "label": _label(zodiac_code),
                "knowledge": zodiac_card.to_dict() if zodiac_card else None,
            },
            "xunkong": [
                [{"code": code, "label": _label(code)} for code in pair]
                for pair in raw.get("xunkong") or []
            ],
        },
        "analysis_facts": {
            "wuxing": wuxing_series,
            "shishen": shishen_series,
            "origin_relations": origin_relations,
            "shensha": deepcopy(raw.get("shensha_details") or {}),
            "shishen_clues": deepcopy(raw.get("shishen_clues") or []),
            "ten_god_knowledge": [
                card.to_dict()
                for item in shishen_series
                if (card := get_ten_god_card(item["code"])) is not None
            ],
        },
        "luck_cycles": luck_cycles,
        "visuals": {
            "wuxing_ratio": {"type": "donut", "series": wuxing_series},
            "wuxing_flow": _flow_visual(wuxing_series),
            "shishen_ratio": {"type": "horizontal_bar", "series": shishen_series},
            "origin_network": {
                "type": "pillar_relation_network",
                "pillars": [
                    {"key": item["key"], "label": item["label"], "ganzhi": item["ganzhi"]}
                    for item in pillars
                ],
                "relations": origin_relations,
            },
            "dayun_timeline": {
                "type": "cycle_timeline",
                "series": [
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "start_year": item["start_year"],
                        "end_year": item["end_year"],
                        "age_start": item["age_start"],
                        "score": item["score"],
                    }
                    for item in luck_cycles
                    if not item["is_pre_luck"]
                ],
                "score_note": "待结构化喜忌节点产出并通过校验后再生成走势分数。",
            },
        },
    }
