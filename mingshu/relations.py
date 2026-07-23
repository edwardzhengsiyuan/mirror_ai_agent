"""Complete, position-aware relationships for the four original pillars.

The force analyser intentionally keeps only the relations that survive its
strength/conflict resolution.  A printed chart also needs structural branch
relations such as 半合 and 拱合, while still avoiding candidate stem matches
that the analyser did not establish.
"""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations, product


SANHE = (
    (("ZHI:HAI", "ZHI:MAO", "ZHI:WEI"), "WUXING:MU"),
    (("ZHI:YIN", "ZHI:WU", "ZHI:XU"), "WUXING:HUO"),
    (("ZHI:SI", "ZHI:YOU", "ZHI:CHOU"), "WUXING:JIN"),
    (("ZHI:SHEN", "ZHI:ZI", "ZHI:CHEN"), "WUXING:SHUI"),
)
SANHUI = (
    (("ZHI:YIN", "ZHI:MAO", "ZHI:CHEN"), "WUXING:MU"),
    (("ZHI:SI", "ZHI:WU", "ZHI:WEI"), "WUXING:HUO"),
    (("ZHI:SHEN", "ZHI:YOU", "ZHI:XU"), "WUXING:JIN"),
    (("ZHI:HAI", "ZHI:ZI", "ZHI:CHOU"), "WUXING:SHUI"),
)
SANXING = (
    ("ZHI:YIN", "ZHI:SI", "ZHI:SHEN"),
    ("ZHI:CHOU", "ZHI:WEI", "ZHI:XU"),
)
LIUHE = {
    frozenset(("ZHI:ZI", "ZHI:CHOU")), frozenset(("ZHI:YIN", "ZHI:HAI")),
    frozenset(("ZHI:MAO", "ZHI:XU")), frozenset(("ZHI:CHEN", "ZHI:YOU")),
    frozenset(("ZHI:SI", "ZHI:SHEN")), frozenset(("ZHI:WU", "ZHI:WEI")),
}
LIUCHONG = {
    frozenset(("ZHI:ZI", "ZHI:WU")), frozenset(("ZHI:CHOU", "ZHI:WEI")),
    frozenset(("ZHI:YIN", "ZHI:SHEN")), frozenset(("ZHI:MAO", "ZHI:YOU")),
    frozenset(("ZHI:CHEN", "ZHI:XU")), frozenset(("ZHI:SI", "ZHI:HAI")),
}
CHUAN = {
    frozenset(("ZHI:ZI", "ZHI:WEI")), frozenset(("ZHI:CHOU", "ZHI:WU")),
    frozenset(("ZHI:YIN", "ZHI:SI")), frozenset(("ZHI:MAO", "ZHI:CHEN")),
    frozenset(("ZHI:SHEN", "ZHI:HAI")), frozenset(("ZHI:YOU", "ZHI:XU")),
}
XIANGPO = {
    frozenset(("ZHI:ZI", "ZHI:YOU")), frozenset(("ZHI:YIN", "ZHI:HAI")),
    frozenset(("ZHI:CHEN", "ZHI:CHOU")), frozenset(("ZHI:WU", "ZHI:MAO")),
    frozenset(("ZHI:SHEN", "ZHI:SI")), frozenset(("ZHI:XU", "ZHI:WEI")),
}
XING = {
    frozenset(("ZHI:YIN", "ZHI:SI")), frozenset(("ZHI:SI", "ZHI:SHEN")),
    frozenset(("ZHI:SHEN", "ZHI:YIN")), frozenset(("ZHI:CHOU", "ZHI:WEI")),
    frozenset(("ZHI:WEI", "ZHI:XU")), frozenset(("ZHI:XU", "ZHI:CHOU")),
    frozenset(("ZHI:ZI", "ZHI:MAO")),
}
ZIXING = {"ZHI:CHEN", "ZHI:WU", "ZHI:YOU", "ZHI:HAI"}
ANHE = {
    frozenset(("ZHI:YIN", "ZHI:CHOU")),
    frozenset(("ZHI:WU", "ZHI:HAI")),
    frozenset(("ZHI:MAO", "ZHI:SHEN")),
}


def _member(pillar: dict, index: int, field: str) -> dict:
    item = pillar["gan"] if field == "stem" else pillar["zhi"]
    return {
        "pillar": pillar["key"],
        "pillar_index": index,
        "pillar_label": pillar["label"],
        "field": field,
        "code": item["name"],
        "label": item["name_label"],
        "wuxing": item["wuxing"],
        "wuxing_label": item["wuxing_label"],
    }


def _category(relation_type: str) -> str:
    upper = relation_type.upper()
    if "CHONG" in upper:
        return "chong"
    if upper in {"XING", "SANXING", "ZIXING"}:
        return "xing"
    if upper in {"CHUAN", "LIUHAI"}:
        return "chuan"
    if upper in {"ANHE"}:
        return "anhe"
    if upper in {"XIANGPO"}:
        return "po"
    return "he"


def collect_established_relations(pillars: list[dict], effective_relations: list[dict]) -> list[dict]:
    """Return resolved stem forces plus every structural branch relationship."""
    result: list[dict] = []
    seen: set[tuple] = set()

    def add(item: dict) -> None:
        members = item.get("members") or []
        key = (
            item.get("relation_type"),
            tuple((member.get("pillar_index"), member.get("field")) for member in members),
        )
        if key in seen:
            return
        seen.add(key)
        item["category"] = _category(str(item.get("relation_type") or ""))
        result.append(item)

    # Only keep stem relations that survived the existing force analysis.  This
    # is why a merely visible 乙、庚 pair is not automatically called a 合.
    for raw in effective_relations or []:
        if raw.get("field") != "stem":
            continue
        item = deepcopy(raw)
        suffix = "冲" if "Chong" in str(item.get("relation_type")) else "合"
        item["label"] = "".join(member.get("label", "") for member in item.get("members") or []) + suffix
        item["source"] = "resolved_force"
        add(item)

    branches = [(index, pillar, (pillar.get("zhi") or {}).get("name")) for index, pillar in enumerate(pillars)]
    positions: dict[str, list[int]] = {}
    for index, _pillar, code in branches:
        positions.setdefault(str(code), []).append(index)

    def branch_relation(rel_type: str, indexes: tuple[int, ...], suffix: str, **extra: object) -> None:
        members = [_member(pillars[index], index, "branch") for index in indexes]
        add(
            {
                "relation_type": rel_type,
                "label": "".join(member["label"] for member in members) + suffix,
                "field": "branch",
                "members": members,
                "distance": max(indexes) - min(indexes),
                "strength": None,
                "source": "structural_rule",
                **extra,
            }
        )

    # Full three-branch structures take precedence over their partial forms.
    full_sanhe: set[tuple[str, str, str]] = set()
    for group, wuxing in SANHE:
        if all(positions.get(code) for code in group):
            full_sanhe.add(group)
            for indexes in product(*(positions[code] for code in group)):
                if len(set(indexes)) == 3:
                    branch_relation("SANHE", tuple(sorted(indexes)), "三合", result_wuxing=wuxing)
        else:
            first, center, last = group
            if positions.get(first) and positions.get(last) and not positions.get(center):
                for left, right in product(positions[first], positions[last]):
                    branch_relation(
                        "GONGHE", tuple(sorted((left, right))), "拱合",
                        result_wuxing=wuxing, missing_member=center,
                        **({"label": "巳丑拱合"} if {first, last} == {"ZHI:SI", "ZHI:CHOU"} else {}),
                    )
            if positions.get(center):
                for endpoint in (first, last):
                    if positions.get(endpoint):
                        for left, right in product(positions[endpoint], positions[center]):
                            branch_relation(
                                "BANHE", tuple(sorted((left, right))), "半合",
                                result_wuxing=wuxing,
                                missing_member=last if endpoint == first else first,
                            )

    for group, wuxing in SANHUI:
        if all(positions.get(code) for code in group):
            for indexes in product(*(positions[code] for code in group)):
                if len(set(indexes)) == 3:
                    branch_relation("SANHUI", tuple(sorted(indexes)), "三会", result_wuxing=wuxing)

    full_sanxing: set[frozenset[str]] = set()
    for group in SANXING:
        if all(positions.get(code) for code in group):
            full_sanxing.add(frozenset(group))
            for indexes in product(*(positions[code] for code in group)):
                if len(set(indexes)) == 3:
                    branch_relation("SANXING", tuple(sorted(indexes)), "三刑")

    for (left_index, left_pillar, left_code), (right_index, right_pillar, right_code) in combinations(branches, 2):
        pair = frozenset((str(left_code), str(right_code)))
        indexes = (left_index, right_index)
        if pair in LIUHE:
            branch_relation("LIUHE", indexes, "六合")
        if pair in LIUCHONG:
            branch_relation("LIUCHONG", indexes, "冲")
        if pair in CHUAN:
            branch_relation("CHUAN", indexes, "穿")
        if pair in XIANGPO:
            branch_relation("XIANGPO", indexes, "破")
        if pair in ANHE:
            branch_relation("ANHE", indexes, "暗合")
        if pair in XING and not any(pair.issubset(group) for group in full_sanxing):
            branch_relation("XING", indexes, "刑")
        if left_code == right_code and left_code in ZIXING:
            branch_relation("ZIXING", indexes, "自刑")

    order = {"he": 0, "chong": 1, "xing": 2, "chuan": 3, "po": 4, "anhe": 5}
    result.sort(
        key=lambda item: (
            order.get(item.get("category", ""), 9),
            min((member.get("pillar_index", 9) for member in item.get("members") or []), default=9),
            item.get("relation_type", ""),
        )
    )
    for index, item in enumerate(result, 1):
        item["id"] = f"origin_relation_{index:02d}"
    return result
