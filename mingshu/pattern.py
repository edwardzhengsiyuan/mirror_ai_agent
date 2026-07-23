"""Structured, evidence-backed pattern analysis for the printed MingShu layer."""

from __future__ import annotations

from typing import Any


PATTERN_BY_TEN_GOD = {
    "正财": "财格",
    "偏财": "财格",
    "食神": "食神格",
    "伤官": "伤官格",
    "正官": "正官格",
    "七杀": "七杀格",
    "正印": "印格",
    "偏印": "印格",
}


def _ten_god_percent(facts: dict, *labels: str) -> float:
    wanted = set(labels)
    return round(
        sum(float(item.get("percent") or 0) for item in facts.get("analysis_facts", {}).get("shishen", []) if item.get("label") in wanted),
        2,
    )


def _locations(facts: dict, labels: set[str]) -> list[str]:
    result: list[str] = []
    rank_names = ("本气", "中气", "余气")
    for pillar in facts.get("chart", {}).get("pillars", [])[:4]:
        gan = pillar.get("gan") or {}
        if gan.get("shishen_label") in labels:
            result.append(f"{pillar.get('label')}天干{gan.get('name_label')}{gan.get('shishen_label')}")
        for index, hidden in enumerate((pillar.get("zhi") or {}).get("hidden_gans") or []):
            if hidden.get("shishen_label") in labels:
                rank = rank_names[index] if index < len(rank_names) else "藏气"
                result.append(f"{pillar.get('label')}地支{(pillar.get('zhi') or {}).get('name_label')}藏{hidden.get('name_label')}{hidden.get('shishen_label')}（{rank}）")
    return result


def _primary_candidate(facts: dict) -> dict[str, Any]:
    patterns = [
        item for item in facts.get("chart", {}).get("patterns", [])
        if "进一步分析" not in str(item.get("label") or "")
    ]
    if patterns:
        return {
            "name": patterns[0].get("label") or "格局候选",
            "status": "脚本已判定",
            "confidence": "high",
            "basis": ["基础排盘脚本已返回明确格局代码。"],
        }

    pillars = facts.get("chart", {}).get("pillars", [])[:4]
    if len(pillars) < 2:
        return {"name": "尚待确认", "status": "资料不足", "confidence": "low", "basis": []}
    visible = {str((pillar.get("gan") or {}).get("name")) for pillar in pillars}
    month_hidden = (pillars[1].get("zhi") or {}).get("hidden_gans") or []
    for hidden in month_hidden:
        god = str(hidden.get("shishen_label") or "")
        if god in PATTERN_BY_TEN_GOD and str(hidden.get("name")) in visible:
            return {
                "name": PATTERN_BY_TEN_GOD[god],
                "status": "命书层候选",
                "confidence": "medium",
                "basis": [
                    f"月令{(pillars[1].get('zhi') or {}).get('name_label')}所藏{hidden.get('name_label')}{god}在天干透出。",
                    "基础脚本只返回“需要进一步分析”，因此本书保留候选标记，不把它写成毫无分歧的定论。",
                ],
            }
    if month_hidden:
        main = month_hidden[0]
        god = str(main.get("shishen_label") or "")
        if god in PATTERN_BY_TEN_GOD:
            return {
                "name": PATTERN_BY_TEN_GOD[god],
                "status": "月令主气候选",
                "confidence": "medium",
                "basis": [
                    f"月令{(pillars[1].get('zhi') or {}).get('name_label')}以{main.get('name_label')}{god}为本气，格局先从{god}立意。",
                    f"{main.get('name_label')}{god}没有透在天干，因此保留“候选”二字，并继续观察相制、相化与日主承受力。",
                ],
            }
    return {
        "name": "尚待确认",
        "status": "需要进一步分析",
        "confidence": "low",
        "basis": ["月令藏干、透干和地支气势尚未形成足够清晰的单一主线。"],
    }


def _relation_labels(facts: dict) -> set[str]:
    return {str(item.get("label") or "") for item in facts.get("analysis_facts", {}).get("origin_relations", [])}


def build_pattern_analysis(facts: dict) -> dict[str, Any]:
    primary = _primary_candidate(facts)
    food = _ten_god_percent(facts, "食神")
    output = _ten_god_percent(facts, "食神", "伤官")
    wealth = _ten_god_percent(facts, "正财", "偏财")
    authority = _ten_god_percent(facts, "正官", "七杀")
    resource = _ten_god_percent(facts, "正印", "偏印")
    strength = str((facts.get("chart", {}).get("strength") or {}).get("label") or "")
    relations = _relation_labels(facts)

    killing = _ten_god_percent(facts, "七杀")
    hurting = _ten_god_percent(facts, "伤官")
    secondary = [
        {
            "name": "财生杀",
            "status": "结构清楚" if wealth >= 15 and killing >= 10 else "有线索",
            "summary": "财星会继续生助七杀，使资源、目标和现实压力连在一起。",
            "evidence": f"财星合计约 {wealth:.1f}%，七杀约 {killing:.1f}%；两者同时有力时，机会越多，责任与时间要求也往往随之增加。",
            "effect": "适合承接有明确目标和资源配置的任务，但不能只加目标，不补足权限、时间与支持。",
        },
        {
            "name": "伤官制杀",
            "status": "结构清楚" if hurting >= 10 and killing >= 10 else "有线索",
            "summary": "伤官用分析、表达和改进方法回应七杀的期限与压力。",
            "evidence": f"伤官约 {hurting:.1f}%，七杀约 {killing:.1f}%；两股力量都进入原盘，形成“以方法处理压力”的路径。",
            "effect": "越是复杂任务，越需要先拆问题、改流程、明确判断依据，避免只靠硬撑。",
        },
        {
            "name": "杀印相生",
            "status": "藏支线索" if killing >= 10 and resource >= 8 else "条件不足",
            "summary": "印星承接七杀，把外部压力转成学习、资质、方法与稳定支持。",
            "evidence": f"七杀约 {killing:.1f}%，印星约 {resource:.1f}%，日主为{strength or '强弱待定'}；印星是否透出、能否贴身承接，决定这条路径的稳定程度。",
            "effect": "建立专业体系、固定复盘和可信赖的支持网络，比不断提高强度更有帮助。",
        },
    ]

    luck_windows = []
    for cycle in facts.get("luck_cycles", []):
        name = str(cycle.get("name") or "")
        gan_god = (cycle.get("gan_shishen") or {}).get("label")
        zhi_god = (cycle.get("zhi_shishen") or {}).get("label")
        if gan_god in {"正印", "偏印", "比肩", "劫财", "食神", "伤官"} or zhi_god in {"正印", "偏印", "比肩", "劫财", "食神", "伤官"}:
            luck_windows.append({
                "name": name,
                "start_year": cycle.get("start_year"),
                "end_year": cycle.get("end_year"),
                "gan_ten_god": gan_god,
                "zhi_ten_god": zhi_god,
                "reading": f"{gan_god}与{zhi_god}进入十年主题。重点看它们能否扶助日主、承接七杀压力，并把方法落实为稳定行动。",
            })

    return {
        "schema_version": "mingshu-pattern/1.0",
        "engine_result": [item.get("label") for item in facts.get("chart", {}).get("patterns", [])],
        "primary": primary,
        "secondary": secondary,
        "structure": {
            "day_master": facts.get("chart", {}).get("day_master"),
            "strength": facts.get("chart", {}).get("strength"),
            "output_percent": output,
            "wealth_percent": wealth,
            "authority_percent": authority,
            "resource_percent": resource,
            "output_locations": _locations(facts, {"食神", "伤官"}),
            "wealth_locations": _locations(facts, {"正财", "偏财"}),
            "authority_locations": _locations(facts, {"正官", "七杀"}),
            "resource_locations": _locations(facts, {"正印", "偏印"}),
            "relations": sorted(relations),
        },
        "useful_gods": {
            "pattern_center": {"name": f"{primary['name']}的主轴", "state": f"官杀合计约 {authority:.1f}%，其中七杀约 {killing:.1f}%；先确认压力、规则与责任如何落地。"},
            "supporting": {"name": "印星（土）", "state": f"约 {resource:.1f}%，用于承接七杀、扶助偏弱日主，把压力转成方法与支持。"},
            "further_flow": {"name": "比劫（金）", "state": f"日主与比劫合计力量有限，金运可补足执行底气与自我边界。"},
            "caution": {"name": "财星（木）", "state": f"约 {wealth:.1f}%，资源意识明显，但木会继续生火；目标与责任过多时需要做减法。"},
        },
        "luck_windows": luck_windows,
        "career": [
            {"name": "专业判断与风险管理", "examples": "合规、审计、风控、质量管理、法务协同、项目治理", "reason": "七杀格候选重视标准、时限和责任；伤官又提供发现问题与改进流程的能力。"},
            {"name": "复杂项目与运营", "examples": "项目管理、运营统筹、供应链、交付管理、应急协调", "reason": "财生杀让资源与责任相连，适合处理目标清楚、需要协调多方的工作。"},
            {"name": "研究与解决方案", "examples": "行业研究、咨询、策略、数据分析、产品解决方案", "reason": "伤官与偏印并见，适合把观察和方法转成可执行方案。"},
            {"name": "专业服务与培训", "examples": "专业顾问、课程研发、知识产品、技术支持", "reason": "印星承压、伤官输出的路径，适合在持续学习后向外提供清楚的方法。"},
        ],
    }
