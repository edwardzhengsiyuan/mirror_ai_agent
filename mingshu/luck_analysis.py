"""Evidence-bound five-element preferences and luck-cycle scoring for MingShu."""

from __future__ import annotations

from typing import Any

from .opening_v2 import _view
from .pattern import build_pattern_analysis
from .shensha_library import get_shensha_knowledge
from .luck_power import calculate_luck_wuxing_power


STEM_PROFILE = {
    "甲": {"element": "木", "pattern": 2, "climate": 12, "total": 12, "role": "调候承续", "tone": "有助"},
    "乙": {"element": "木", "pattern": -5, "climate": 1, "total": -4, "role": "方法与现实协调", "tone": "审慎"},
    "丙": {"element": "火", "pattern": -8, "climate": -8, "total": -12, "role": "火势再增", "tone": "谨慎"},
    "丁": {"element": "火", "pattern": -6, "climate": -4, "total": -8, "role": "同类再临", "tone": "谨慎"},
    "戊": {"element": "土", "pattern": 12, "climate": 5, "total": 12, "role": "伤官生财", "tone": "有助"},
    "己": {"element": "土", "pattern": 10, "climate": 2, "total": 9, "role": "食神生财", "tone": "有助"},
    "庚": {"element": "金", "pattern": 12, "climate": 12, "total": 14, "role": "格局调候交点", "tone": "优先"},
    "辛": {"element": "金", "pattern": 9, "climate": 1, "total": 8, "role": "财星兑现", "tone": "有助"},
    "壬": {"element": "水", "pattern": 5, "climate": 7, "total": 7, "role": "规则承接", "tone": "有条件"},
    "癸": {"element": "水", "pattern": 3, "climate": -10, "total": -6, "role": "湿甲伤丁之忧", "tone": "谨慎"},
}

BRANCH_PROFILE = {
    "子": {"element": "水", "total": -2}, "丑": {"element": "土", "total": 8},
    "寅": {"element": "木", "total": 5}, "卯": {"element": "木", "total": -3},
    "辰": {"element": "土", "total": 6}, "巳": {"element": "火", "total": -9},
    "午": {"element": "火", "total": -12}, "未": {"element": "土", "total": 4},
    "申": {"element": "金", "total": 12}, "酉": {"element": "金", "total": 10},
    "戌": {"element": "土", "total": 5}, "亥": {"element": "水", "total": 6},
}


def _activate_case_profiles(facts: dict) -> None:
    """Select scoring weights for the current day master and seasonal climate."""
    global STEM_PROFILE, BRANCH_PROFILE
    chart = facts.get("chart") or {}
    pillars = chart.get("pillars") or []
    day_master = str((chart.get("day_master") or {}).get("label") or "")
    month = str(((pillars[1].get("zhi") or {}).get("name_label") if len(pillars) > 1 else "") or "")
    if day_master == "辛" and month == "午":
        STEM_PROFILE = {
            "甲": {"element": "木", "pattern": -6, "climate": -2, "total": -6, "role": "财星继续生火", "tone": "谨慎"},
            "乙": {"element": "木", "pattern": -5, "climate": -2, "total": -5, "role": "目标与责任继续增加", "tone": "谨慎"},
            "丙": {"element": "火", "pattern": -10, "climate": -12, "total": -13, "role": "官火再增", "tone": "谨慎"},
            "丁": {"element": "火", "pattern": -11, "climate": -12, "total": -14, "role": "七杀与暑热再增", "tone": "谨慎"},
            "戊": {"element": "土", "pattern": 9, "climate": 7, "total": 10, "role": "印星承压并扶身", "tone": "有助"},
            "己": {"element": "土", "pattern": 12, "climate": 13, "total": 14, "role": "调候培金并化杀", "tone": "优先"},
            "庚": {"element": "金", "pattern": 11, "climate": 4, "total": 11, "role": "同类扶身与建立边界", "tone": "有助"},
            "辛": {"element": "金", "pattern": 12, "climate": 4, "total": 12, "role": "补足日主与自主判断", "tone": "有助"},
            "壬": {"element": "水", "pattern": 8, "climate": 14, "total": 14, "role": "调候降温并发挥伤官方法", "tone": "优先"},
            "癸": {"element": "水", "pattern": 5, "climate": 8, "total": 8, "role": "润燥但力量较缓", "tone": "有条件"},
        }
        BRANCH_PROFILE = {
            "子": {"element": "水", "total": 8}, "丑": {"element": "土", "total": 10},
            "寅": {"element": "木", "total": -4}, "卯": {"element": "木", "total": -6},
            "辰": {"element": "土", "total": 8}, "巳": {"element": "火", "total": -10},
            "午": {"element": "火", "total": -13}, "未": {"element": "土", "total": 4},
            "申": {"element": "金", "total": 11}, "酉": {"element": "金", "total": 12},
            "戌": {"element": "土", "total": 5}, "亥": {"element": "水", "total": 10},
        }

TEN_GOD_FOCUS = {
    "比肩": "自主判断与亲自投入", "劫财": "协作、竞争与分配边界",
    "食神": "稳定产出与经验沉淀", "伤官": "改进方法与表达主张",
    "正财": "可核算的资源与长期兑现", "偏财": "机会判断与外部资源",
    "正官": "规则、责任与可验证标准", "七杀": "期限、压力与迅速决断",
    "正印": "系统学习与稳定支持", "偏印": "独立研究与跨域方法",
}

TEN_GOD_YEAR_READING = {
    "比肩": {"domain": "自主与同辈", "use": "适合亲自推进、确认自己的判断，也适合与能力相近的人并肩完成任务。", "watch": "共同做事时要先分清职责，避免所有人都在决策，却没有人对结果负责。"},
    "劫财": {"domain": "协作与分配", "use": "人际流动和协作速度较快，适合借助团队、社群或伙伴打开局面。", "watch": "投入、收益、时间和署名需要提前说清，不能只靠默契维持。"},
    "食神": {"domain": "稳定产出", "use": "适合把经验整理为作品、流程、课程或长期可复用的成果。", "watch": "舒适感增加时也容易放慢决策，重要项目仍需保留节点和验收标准。"},
    "伤官": {"domain": "表达与改进", "use": "更容易看见旧方法的问题，适合提案、创作、技术改进和公开表达。", "watch": "观点越明确，越要注意表达对象与制度边界，先解决问题再证明谁对。"},
    "正财": {"domain": "稳定资源", "use": "适合核算成本、整理现金流、建立长期客户或让成果进入稳定交换。", "watch": "不要因追求确定性而把所有弹性都取消，仍需给新方向保留小规模试验。"},
    "偏财": {"domain": "机会与外部资源", "use": "对市场、人脉和机会变化较敏感，适合筛选合作、渠道与增量资源。", "watch": "机会多时更需要进入条件、预算上限和退出规则，避免同时摊开过多战线。"},
    "正官": {"domain": "责任与规则", "use": "适合承担正式职责、完善标准、处理资质流程或进入更清楚的组织位置。", "watch": "规则增加也会带来约束，重要决定要确认权限、责任与评价方式是否匹配。"},
    "七杀": {"domain": "压力与决断", "use": "期限和外部要求会推动行动，适合集中解决久拖未决的问题。", "watch": "不要在持续高压下把每件事都当成紧急事件，需要明确优先级和恢复时间。"},
    "正印": {"domain": "学习与支持", "use": "适合系统学习、补齐资质、向成熟体系取经，也容易得到较稳定的支持。", "watch": "输入增多时要安排输出和应用，否则知识容易停留在准备阶段。"},
    "偏印": {"domain": "研究与转向", "use": "适合独立研究、跨领域连接和寻找不寻常的解决路径。", "watch": "兴趣分叉会增加，最好保留一个长期主线，并用阶段成果判断是否继续。"},
}

RELATION_READING = {
    "五合": "两股力量需要协商和重新组合，容易出现合作、绑定或取舍。",
    "六合": "事务之间的连接变紧，适合谈合作，也要防止承诺过多造成牵绊。",
    "三合": "同类议题形成连续推动，能量更集中，方向需要尽早确定。",
    "半合": "已有靠拢和共同方向，但条件尚未完全齐备，适合先做阶段验证。",
    "拱合": "结构存在牵引，缺少的条件若被补足，原有主题会更明显。",
    "六冲": "原有安排更容易被推动、替换或重新排序，变化需要预留缓冲。",
    "冲": "两种要求正面相遇，适合做清楚选择，不宜同时维持互相冲突的目标。",
    "刑": "规则、步骤或人际压力容易反复出现，越需要清楚流程与责任边界。",
    "自刑": "同一问题可能在内部反复，需要用记录和复盘打断惯性。",
    "害": "摩擦不一定正面爆发，常表现为信息落差、误解或隐性消耗。",
    "六害": "摩擦不一定正面爆发，常表现为信息落差、误解或隐性消耗。",
    "穿": "现实细节容易侵入原有秩序，需优先处理日常安排与边界。",
    "破": "既有结构出现松动，适合检查旧约定、旧流程是否仍然有效。",
    "相破": "既有结构出现松动，适合检查旧约定、旧流程是否仍然有效。",
}

PALACE_DOMAIN = {
    "年柱": "家族外缘、早年经验与公共形象",
    "月柱": "工作环境、成长方式与日常秩序",
    "日柱": "自我核心、共同生活与亲密关系",
    "时柱": "长期计划、个人作品与未来安排",
}


def _label(value: Any) -> str:
    return str((value or {}).get("label") or "") if isinstance(value, dict) else str(value or "")


def _members(relation: dict) -> set[str]:
    return {_label(item) for item in relation.get("members") or []}


def _relation_adjustment(relations: list[dict]) -> tuple[int, list[str], list[str]]:
    adjustment = 0
    support: list[str] = []
    movement: list[str] = []
    for relation in relations:
        label = str(relation.get("label") or "")
        members = _members(relation)
        if {"巳", "酉", "丑"}.issubset(members):
            adjustment += 8
            support.append("巳酉丑金局补强财星主线")
        elif {"巳", "丑"}.issubset(members) and label in {"拱合", "半合", "三合"}:
            adjustment += 4
            support.append("巳丑之间继续牵动金气")
        elif {"巳", "午", "未"}.issubset(members):
            adjustment -= 8
            movement.append("巳午未火势汇聚，原局暖燥被放大")
        elif label in {"五合", "六合", "暗合"}:
            adjustment += 1
            support.append(f"{label}增加连接与协作机会")
        if label in {"六冲", "冲", "刑", "自刑", "穿", "害", "六害", "破", "相破"}:
            adjustment -= 2
            movement.append(f"{label}使原有安排更容易调整")
    return max(-10, min(10, adjustment)), list(dict.fromkeys(support)), list(dict.fromkeys(movement))


def _score_parts(gan: str, zhi: str, relations: list[dict]) -> dict[str, int]:
    stem = STEM_PROFILE.get(gan, {"pattern": 0, "climate": 0, "total": 0})
    branch = BRANCH_PROFILE.get(zhi, {"total": 0})
    relation, _, _ = _relation_adjustment(relations)
    pattern = max(20, min(80, 50 + int(stem.get("pattern", 0)) + int(branch.get("total", 0))))
    climate = max(20, min(80, 50 + int(stem.get("climate", 0)) + int(branch.get("total", 0)) // 2))
    relation_score = max(20, min(80, 50 + relation * 2))
    score = max(25, min(82, 50 + int(stem.get("total", 0)) + int(branch.get("total", 0)) + relation))
    return {"pattern": pattern, "climate": climate, "relations": relation_score, "score": score}


def _band(score: int) -> str:
    if score >= 68:
        return "顺势较多"
    if score >= 58:
        return "可用条件较多"
    if score >= 48:
        return "进退并见"
    return "调整较多"


def _relation_text(relations: list[dict]) -> list[str]:
    result: list[str] = []
    for relation in relations:
        members = "、".join(_label(item) for item in relation.get("members") or [])
        label = str(relation.get("label") or "作用")
        result.append(f"{members}{label}" if members else label)
    return list(dict.fromkeys(result))


def _original_positions(facts: dict) -> dict[str, list[str]]:
    positions: dict[str, list[str]] = {}
    for pillar in facts.get("chart", {}).get("pillars") or []:
        label = str(pillar.get("label") or "")
        for char in (
            str((pillar.get("gan") or {}).get("name_label") or _label(pillar.get("gan"))),
            str((pillar.get("zhi") or {}).get("name_label") or _label(pillar.get("zhi"))),
        ):
            if char:
                positions.setdefault(char, []).append(label)
    return positions


def _relation_details(relations: list[dict], facts: dict) -> list[dict]:
    positions = _original_positions(facts)
    result: list[dict] = []
    seen: set[str] = set()
    for relation in relations:
        members = [_label(item) for item in relation.get("members") or []]
        label = str(relation.get("label") or "作用")
        title = f"{'、'.join(members)}{label}" if members else label
        if title in seen:
            continue
        seen.add(title)
        pillars = list(dict.fromkeys(p for member in members for p in positions.get(member, [])))
        domains = [PALACE_DOMAIN.get(item, item) for item in pillars]
        base = RELATION_READING.get(label, "这一组作用会改变原有力量的连接方式，需要结合现实事务继续观察。")
        affected = "、".join(domains)
        result.append(
            {
                "title": title,
                "relation": label,
                "members": members,
                "pillars": pillars,
                "reading": f"{base}{' 主要牵动' + affected + '。' if affected else ''}",
            }
        )
    return result


def _ten_god_reading(gan_god: str, zhi_god: str, *, scope: str = "流年") -> list[dict]:
    result = []
    for layer, god in ((f"{scope}天干", gan_god), (f"{scope}地支", zhi_god)):
        item = TEN_GOD_YEAR_READING.get(god, {"domain": god, "use": TEN_GOD_FOCUS.get(god, god), "watch": "仍需结合所在大运和现实处境。"})
        result.append({"layer": layer, "god": god, **item})
    return result


def _shensha_readings(values: list[str]) -> list[dict]:
    result: list[dict] = []
    for code in values:
        normalized = code if str(code).startswith("SHENSHA:") else f"SHENSHA:{str(code).split(':')[-1]}"
        try:
            item = get_shensha_knowledge(normalized)
        except (KeyError, ValueError):
            continue
        result.append(
            {
                "code": normalized,
                "name": item["name"],
                "tagline": item["tagline"],
                "cluster": item["cluster"],
            }
        )
    return result


def _overlap_notes(year: dict, cycle: dict, facts: dict) -> list[str]:
    notes: list[str] = []
    ganzhi = str(year.get("ganzhi") or "")
    if ganzhi and ganzhi == str(cycle.get("name") or ""):
        notes.append("流年与大运同柱，传统称“岁运并临”：十年主调在这一年被重复强调，宜把目标收束到少数重点。")
    for pillar in facts.get("chart", {}).get("pillars") or []:
        if ganzhi and ganzhi == str(pillar.get("ganzhi") or ""):
            notes.append(f"流年复见{pillar.get('label')}的{ganzhi}，传统称“伏吟”：{PALACE_DOMAIN.get(str(pillar.get('label')), '该柱事务')}更值得复盘旧问题与旧选择。")
    if not notes:
        notes.append("流年没有与大运或原局整柱重复，变化重点更多来自当年十神和实际冲合。")
    return notes


def _month_record(month: dict, year_score: int, facts: dict) -> dict:
    gan, zhi = _label(month.get("gan")), _label(month.get("zhi"))
    relations = list(month.get("relations") or [])
    parts = _score_parts(gan, zhi, relations)
    score = round(year_score * 0.5 + parts["score"] * 0.5)
    gan_god, zhi_god = _label(month.get("gan_shishen")), _label(month.get("zhi_shishen"))
    details = _relation_details(relations, facts)
    return {
        "id": month.get("id"),
        "sequence": month.get("sequence"),
        "solar_month": month.get("solar_month"),
        "solar_day": month.get("solar_day"),
        "start_label": f"约{month.get('solar_month')}月{month.get('solar_day')}日起",
        "ganzhi": month.get("ganzhi"),
        "gan_ten_god": gan_god,
        "zhi_ten_god": zhi_god,
        "score": score,
        "band": _band(score),
        "relation_count": len(details),
        "relations": details,
        "focus": TEN_GOD_YEAR_READING.get(gan_god, {}).get("domain", gan_god),
    }


def _focus(gan_god: str, zhi_god: str) -> str:
    first = TEN_GOD_FOCUS.get(gan_god, gan_god)
    second = TEN_GOD_FOCUS.get(zhi_god, zhi_god)
    return f"外在主题偏向{first}，具体落地又会牵动{second}。"


def _stem_reading(gan: str) -> tuple[str, str]:
    profile = STEM_PROFILE.get(gan, {})
    tone = profile.get("tone", "有条件")
    role = profile.get("role", "需要结合位置")
    if tone in {"优先", "有助"}:
        return f"{gan}在本盘中属于{tone}力量，主要帮助{role}。", "适合把这股力量用于明确目标、完成作品和建立可复用成果。"
    if tone == "谨慎":
        return f"{gan}在本盘中需要谨慎使用，容易带来{role}。", "先给变化设定边界和完成标准，比一味加速更能保存成果。"
    return f"{gan}的作用有条件，重点在{role}。", "它能否转为助力，取决于是否有清楚规则、节奏和现实承接。"


def _cycle_record(cycle: dict, facts: dict) -> dict:
    gan, zhi = _label(cycle.get("gan")), _label(cycle.get("zhi"))
    relations = list(cycle.get("relations") or [])
    parts = _score_parts(gan, zhi, relations)
    _, support, movement = _relation_adjustment(relations)
    gan_god, zhi_god = _label(cycle.get("gan_shishen")), _label(cycle.get("zhi_shishen"))
    stem_note, action = _stem_reading(gan)
    return {
        "id": cycle.get("id"), "name": cycle.get("name"), "gan": gan, "zhi": zhi,
        "start_year": cycle.get("start_year"), "end_year": cycle.get("end_year"), "age_start": cycle.get("age_start"),
        "gan_ten_god": gan_god, "zhi_ten_god": zhi_god, "relations": _relation_text(relations),
        "relation_details": _relation_details(relations, facts),
        "ten_god_readings": _ten_god_reading(gan_god, zhi_god, scope="大运"),
        "shensha": _shensha_readings(list(cycle.get("shensha") or [])),
        "support": support, "movement": movement, "score": parts["score"], "band": _band(parts["score"]),
        "components": {key: parts[key] for key in ("pattern", "climate", "relations")},
        "headline": _focus(gan_god, zhi_god), "stem_note": stem_note, "action": action,
        "wuxing_shift": calculate_luck_wuxing_power(facts, cycle),
    }


def _cycle_phases(years: list[dict]) -> list[dict]:
    """Split a ten-year cycle into readable early, middle and late phases."""

    phases: list[dict] = []
    for label, rows in (("前段", years[:3]), ("中段", years[3:7]), ("后段", years[7:])):
        if not rows:
            continue
        high = max(rows, key=lambda item: item["score"])
        dense = max(rows, key=lambda item: len(item.get("relation_details") or []))
        average = round(sum(item["score"] for item in rows) / len(rows))
        phases.append(
            {
                "label": label,
                "years": f'{rows[0]["year"]}—{rows[-1]["year"]}',
                "average": average,
                "high_year": high["year"],
                "high_ganzhi": high["ganzhi"],
                "focus": high["headline"],
                "dense_year": dense["year"],
                "dense_relations": len(dense.get("relation_details") or []),
            }
        )
    return phases


def _year_record(year: dict, cycle: dict, cycle_record: dict, facts: dict) -> dict:
    gan = _label(year.get("gan"))
    zhi = _label(year.get("zhi"))
    relations = list(year.get("relations") or [])
    parts = _score_parts(gan, zhi, relations)
    score = round(cycle_record["score"] * 0.55 + parts["score"] * 0.45)
    _, support, movement = _relation_adjustment(relations)
    gan_god, zhi_god = _label(year.get("gan_shishen")), _label(year.get("zhi_shishen"))
    stem_note, action = _stem_reading(gan)
    relation_lines = _relation_text(relations)
    relation_details = _relation_details(relations, facts)
    if not relation_lines:
        relation_lines = ["与原盘没有新增的显著冲合，主题更多来自岁运十神本身"]
    months = [_month_record(item, score, facts) for item in year.get("months") or []]
    active_months = sorted(months, key=lambda item: (item["relation_count"], abs(item["score"] - 50)), reverse=True)[:3]
    supportive_months = sorted(months, key=lambda item: item["score"], reverse=True)[:3]
    adjustment_months = sorted(months, key=lambda item: item["score"])[:3]
    return {
        "id": year.get("id"), "year": year.get("year"), "age": year.get("age"), "ganzhi": year.get("ganzhi"),
        "gan": gan, "zhi": zhi, "gan_ten_god": gan_god, "zhi_ten_god": zhi_god,
        "cycle_id": cycle.get("id"), "cycle_name": cycle.get("name"), "score": score, "band": _band(score),
        "headline": _focus(gan_god, zhi_god), "stem_note": stem_note, "action": action,
        "relations": relation_lines, "relation_details": relation_details,
        "support": support, "movement": movement,
        "ten_god_readings": _ten_god_reading(gan_god, zhi_god),
        "overlap_notes": _overlap_notes(year, cycle, facts),
        "shensha": _shensha_readings(list(year.get("shensha") or [])),
        "months": months,
        "active_months": active_months,
        "supportive_months": supportive_months,
        "adjustment_months": adjustment_months,
    }


def build_luck_analysis(facts: dict) -> dict:
    _activate_case_profiles(facts)
    pattern = build_pattern_analysis(facts)
    view = _view(facts)
    cycles: list[dict] = []
    years: list[dict] = []
    for cycle in [item for item in facts.get("luck_cycles") or [] if not item.get("is_pre_luck")]:
        cycle_record = _cycle_record(cycle, facts)
        cycle_years = [_year_record(item, cycle, cycle_record, facts) for item in cycle.get("years") or []]
        cycle_record["years"] = cycle_years
        cycle_record["peak_years"] = sorted(cycle_years, key=lambda item: item["score"], reverse=True)[:2]
        cycle_record["turning_years"] = sorted(cycle_years, key=lambda item: item["score"])[:2]
        cycle_record["phases"] = _cycle_phases(cycle_years)
        cycles.append(cycle_record)
        years.extend(cycle_years)
    tiaohou = view["tiaohou"]
    primary_gods = list(tiaohou.get("primary_gods") or [])
    primary_text = "、".join(primary_gods) or "按月令另行核对"
    chart = facts.get("chart") or {}
    day_master = str((chart.get("day_master") or {}).get("label") or "日主")
    is_xin_wu = day_master == "辛" and str(tiaohou.get("month") or "") == "午"
    preference_summary = (
        "格局从七杀主线观察，日主偏弱时，土印与金比劫负责承接压力、补足自身；调候则把壬水、己土放在前面，用水降温流通，用湿土培金并缓冲烈火。原盘壬水已透、己土藏于午未，说明所需力量并非全无，但仍要看行运是否让它们更有根、更稳定。木火继续增加时，目标和责任容易同步加重，需要做减法。"
        if is_xin_wu else
        f"格局用神与调候用神需要合看。当前调候优先关注{primary_text}，再结合日主强弱、原盘位置和岁运作用关系判断。"
    )
    elements = (
        [
            {"name": "金", "level": "扶身", "reason": "日主辛金在午月偏弱，金可补足自主判断、执行底气与边界。"},
            {"name": "土", "level": "相助", "reason": "印星可承接七杀并生金；己土又是辛生午月的调候重点之一。"},
            {"name": "水", "level": "调候", "reason": "壬水已经透出，能降温、流通并让伤官的观察和方法得到发挥；仍要避免无根之水。"},
            {"name": "木", "level": "审慎", "reason": "财星明显，但木会继续生火并消耗偏弱辛金；机会增加时要同步核对承受力。"},
            {"name": "火", "level": "谨慎", "reason": "午月火当令且七杀为最强十神，再增火会放大压力、急迫和责任负荷。"},
        ] if is_xin_wu else
        [{"name": item, "level": "结合原盘", "reason": "需结合格局、调候与实际作用关系判断。"} for item in ("木", "火", "土", "金", "水")]
    )
    return {
        "schema_version": "mingshu-luck/1.0",
        "preference": {
            "priority_basis": "balanced",
            "summary": preference_summary,
            "pattern": pattern["useful_gods"],
            "tiaohou": {"season": tiaohou.get("season"), "climate": tiaohou.get("climate"), "primary_gods": tiaohou.get("primary_gods"), "caution_gods": tiaohou.get("caution_gods")},
            "elements": elements,
            "stems": [{"name": name, **profile} for name, profile in STEM_PROFILE.items()],
        },
        "cycles": cycles,
        "years": years,
        "method": {
            "label": "结构顺势度",
            "description": "分数只比较格局用神、调候用神与原盘作用关系在不同岁运中的相对配合，不代表人生价值，也不等同于事件吉凶。",
            "cycle_formula": "以50为中线，叠加运干、运支及其与原盘关系；全部权重来自本章公开的十干与十二支取用表。",
            "year_formula": "流年分数由所在大运占55%、当年干支及原盘关系占45%合成；流月再以当年占50%、月干支及其关系占50%形成月内相对节奏。",
        },
    }
