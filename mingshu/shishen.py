"""Deterministic ten-god facts for print-first MingShu pages."""

from __future__ import annotations

from copy import deepcopy

from .shishen_assets import TEN_GOD_ASSET_BY_CODE


TEN_GOD_ORDER = [
    "SHISHEN:BIJIAN",
    "SHISHEN:JIECAI",
    "SHISHEN:SHISHEN",
    "SHISHEN:SHANGGUAN",
    "SHISHEN:ZHENGCAI",
    "SHISHEN:PIANCAI",
    "SHISHEN:ZHENGGUAN",
    "SHISHEN:QISHA",
    "SHISHEN:ZHENGYIN",
    "SHISHEN:PIANYIN",
]

TEN_GOD_FAMILIES = [
    ("peer", "比劫", ("SHISHEN:BIJIAN", "SHISHEN:JIECAI")),
    ("output", "食伤", ("SHISHEN:SHISHEN", "SHISHEN:SHANGGUAN")),
    ("wealth", "财星", ("SHISHEN:ZHENGCAI", "SHISHEN:PIANCAI")),
    ("authority", "官杀", ("SHISHEN:ZHENGGUAN", "SHISHEN:QISHA")),
    ("resource", "印星", ("SHISHEN:ZHENGYIN", "SHISHEN:PIANYIN")),
]

HIDDEN_RANKS = ("main", "middle", "residual")
HIDDEN_RANK_LABELS = {"main": "本气", "middle": "中气", "residual": "余气"}


def _relation_member(member: dict, pillars_by_key: dict[str, dict], field: str) -> dict:
    pillar = pillars_by_key.get(str(member.get("pillar") or ""), {})
    if field == "stem":
        gan = pillar.get("gan") or {}
        return {
            **deepcopy(member),
            "ten_god": gan.get("shishen"),
            "ten_god_label": gan.get("shishen_label"),
            "all_ten_gods": [gan.get("shishen_label")] if gan.get("shishen_label") else [],
        }
    hidden = (pillar.get("zhi") or {}).get("hidden_gans") or []
    return {
        **deepcopy(member),
        "ten_god": hidden[0].get("shishen") if hidden else None,
        "ten_god_label": hidden[0].get("shishen_label") if hidden else None,
        "all_ten_gods": [item.get("shishen_label") for item in hidden if item.get("shishen_label")],
    }


def build_ten_god_analysis(facts: dict) -> dict:
    """Build a reader-facing, evidence-linked ten-god data model."""
    series = ((facts.get("visuals") or {}).get("shishen_ratio") or {}).get("series") or []
    by_code = {str(item.get("code")): item for item in series}
    rizhu_ratio = float((by_code.get("SHISHEN:RIZHU") or {}).get("ratio") or 0.0)
    denominator = max(1.0 - rizhu_ratio, 0.0)

    radar = []
    for code in TEN_GOD_ORDER:
        source = by_code.get(code) or {"code": code, "label": code.split(":")[-1], "ratio": 0.0}
        asset = TEN_GOD_ASSET_BY_CODE[code]
        raw_ratio = float(source.get("ratio") or 0.0)
        display_ratio = raw_ratio / denominator if denominator else 0.0
        radar.append(
            {
                "code": code,
                "label": source.get("label"),
                "raw_percent": round(raw_ratio * 100, 2),
                "ratio": round(display_ratio, 8),
                "percent": round(display_ratio * 100, 2),
                "image": asset["image"],
                "visual_theme": asset["theme"],
                "visual_tagline": asset["tagline"],
            }
        )

    radar_by_code = {item["code"]: item for item in radar}
    families = []
    for family_code, label, members in TEN_GOD_FAMILIES:
        percent = sum(radar_by_code[code]["percent"] for code in members)
        families.append(
            {
                "code": family_code,
                "label": label,
                "members": [radar_by_code[code] for code in members],
                "percent": round(percent, 2),
            }
        )

    pillars = (facts.get("chart") or {}).get("pillars") or []
    placements = []
    for pillar in pillars[:4]:
        pillar_key = str(pillar.get("key") or "")
        gan = pillar.get("gan") or {}
        placements.append(
            {
                "id": f"ten-god:{pillar_key}:stem",
                "pillar": pillar_key,
                "pillar_label": pillar.get("label"),
                "layer": "stem",
                "visibility": "visible",
                "visibility_label": "透干",
                "source_code": gan.get("name"),
                "source_label": gan.get("name_label"),
                "ten_god": gan.get("shishen"),
                "ten_god_label": gan.get("shishen_label"),
                "hidden_rank": None,
                "hidden_rank_label": None,
            }
        )
        for index, hidden in enumerate((pillar.get("zhi") or {}).get("hidden_gans") or []):
            rank = HIDDEN_RANKS[min(index, len(HIDDEN_RANKS) - 1)]
            placements.append(
                {
                    "id": f"ten-god:{pillar_key}:hidden:{index}",
                    "pillar": pillar_key,
                    "pillar_label": pillar.get("label"),
                    "layer": "hidden",
                    "visibility": "hidden",
                    "visibility_label": "藏支",
                    "source_code": hidden.get("name"),
                    "source_label": hidden.get("name_label"),
                    "ten_god": hidden.get("shishen"),
                    "ten_god_label": hidden.get("shishen_label"),
                    "hidden_rank": rank,
                    "hidden_rank_label": HIDDEN_RANK_LABELS[rank],
                }
            )

    pillars_by_key = {str(item.get("key")): item for item in pillars[:4]}
    relations = []
    for relation in (facts.get("analysis_facts") or {}).get("origin_relations") or []:
        field = str(relation.get("field") or "branch")
        members = [
            _relation_member(member, pillars_by_key, field)
            for member in (relation.get("members") or [])
        ]
        state = "resolved_force" if relation.get("source") == "resolved_force" else "structural_rule"
        relations.append(
            {
                **deepcopy(relation),
                "members": members,
                "state": state,
                "state_label": "已计入力量作用" if state == "resolved_force" else "结构关系",
                "boundary": (
                    "此关系已进入脚本的力量变换。"
                    if state == "resolved_force"
                    else "此处只作位置与结构观察，不据此改写雷达图比例。"
                ),
            }
        )

    ranked = sorted(radar, key=lambda item: (-item["percent"], TEN_GOD_ORDER.index(item["code"])))
    absent = [item for item in radar if item["percent"] == 0]
    low = [item for item in radar if 0 < item["percent"] < 5]
    clues = []
    for clue in (facts.get("analysis_facts") or {}).get("shishen_clues") or []:
        finding = str(clue.get("finding") or "")
        unsafe = str(clue.get("area_code") or "") == "HEALTH" or any(
            token in finding for token in ("长寿", "夭", "死亡", "疾病")
        )
        clues.append({**deepcopy(clue), "reader_safe": not unsafe})

    return {
        "schema_version": "ten-god-analysis/1.0",
        "basis": {
            "day_master": ((facts.get("chart") or {}).get("day_master") or {}).get("code"),
            "day_master_label": ((facts.get("chart") or {}).get("day_master") or {}).get("label"),
            "rizhu_reference_percent": round(rizhu_ratio * 100, 2),
            "ratio_method": "exclude_rizhu_and_renormalize",
        },
        "radar": radar,
        "families": families,
        "placements": placements,
        "relations": relations,
        "rankings": {
            "top": ranked[:3],
            "middle": [item for item in ranked[3:] if item["percent"] >= 5],
            "low": low,
            "absent": absent,
        },
        "script_clues": clues,
    }
