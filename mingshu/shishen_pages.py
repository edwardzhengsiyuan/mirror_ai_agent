"""Print-first ten-god sample pages driven by real chart facts."""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

from .shishen import build_ten_god_analysis
from .shishen_assets import TEN_GOD_ASSETS
from .element_styles import ELEMENT_COLOR_SCRIPT


FAMILY_CLASS = {
    "SHISHEN:BIJIAN": "peer",
    "SHISHEN:JIECAI": "peer",
    "SHISHEN:SHISHEN": "output",
    "SHISHEN:SHANGGUAN": "output",
    "SHISHEN:ZHENGCAI": "wealth",
    "SHISHEN:PIANCAI": "wealth",
    "SHISHEN:ZHENGGUAN": "authority",
    "SHISHEN:QISHA": "authority",
    "SHISHEN:ZHENGYIN": "resource",
    "SHISHEN:PIANYIN": "resource",
}

PILLAR_X = {"year": 66, "month": 196, "day": 326, "hour": 456}
PALACE_COPY = {
    "year": "年柱更接近早期环境、家族背景与进入社会时的外层印象。",
    "month": "月柱更接近成长及工作环境，也常承接规则习惯与现实协作。",
    "day": "日柱是自我与日常生活的中心，日支也是亲密关系的重要位置。",
    "hour": "时柱更接近长期计划、成果输出以及面向未来的安排。",
}

TEN_GOD_PLAIN = {
    "比肩": "代表自主、并肩做事和坚持自己的判断。它不是固执，而是遇事先想自己能不能上手。",
    "劫财": "代表竞争、抢进度、动员伙伴和分配边界。它不等于破财，更像人多事急时的推进力量。",
    "食神": "代表把想法做成成果，也关乎表达、照顾感受和生活舒展度。",
    "伤官": "代表发现问题、提出不同意见和改造旧方法。用得好是改进能力，太急时容易话说得过满。",
    "正财": "代表稳定、可核算的资源，以及把日常责任落实、把事情长期经营下去的能力。",
    "偏财": "代表流动机会、外部资源和临场调度。它重视判断时机，不等同于意外之财。",
    "正官": "代表规则、责任和可被检验的标准。",
    "七杀": "代表压力、挑战和需要迅速决断的情境。",
    "正印": "代表稳定学习、支持、保护和把经验系统化。",
    "偏印": "代表独立学习、跨领域联想和不按常规寻找方法。",
    "日主": "就是命盘中的自己，是所有十神关系的参照点。",
}

PILLAR_SCOPE = {
    "year": "年柱更接近早期环境、家庭留下的做事底色，以及别人初识你时较容易看到的一面。",
    "month": "月柱更接近成长和工作环境，也反映你在现实协作、规则与资源面前的常用反应。",
    "day": "日柱是自己与日常生活的中心，日支还对应亲密关系中最常见的相处节奏。",
    "hour": "时柱更接近长期计划、成果输出、后续发展，以及你想把自己带向哪里。",
}

STEM_POSITION_COPY = {
    ("year", "正财"): "正财落在年干，别人较先看到的是你重实际、重兑现、愿意把资源算清楚的一面；早期环境也容易强调稳定与责任。",
    ("month", "偏财"): "偏财落在月干，工作与现实环境会不断训练你判断机会、安排资源和临场调整；你对‘值不值得做’通常较敏感。",
    ("day", "日主"): "日干丁火就是你自己。丁火像灯火，关注细节、氛围和人与人之间的感受，也希望把光用在真正重要的位置。",
    ("hour", "偏印"): "偏印落在时干，说明你面向未来时更愿意独立研究、跨领域寻找方法，不太满足于照搬现成答案。",
}

BRANCH_POSITION_COPY = {
    "year": "年支午以比肩为本气，早年环境与外在交往里，自主、亲自参与和与同伴并肩做事的色彩较重；其中还藏食神，说明这种投入往往希望做出具体成果。",
    "month": "月支巳以劫财为本气，工作环境和现实协作的底层节奏偏快，常要动员伙伴、处理竞争和临时变化；巳中同时藏正财与伤官，资源核算和改进方法也会参与其中。",
    "day": "日支丑以食神为本气，日常生活与亲密相处需要稳定表达、具体照料和看得见的成果；其中还藏七杀与偏财，压力、机会和生活节奏会在这个位置相遇。",
    "hour": "时支巳同样以劫财为本气，长期计划一旦确定，往往会很快进入行动和协作；藏干中的正财与伤官，使未来成果同时受到资源安排和方法改进的影响。",
}

SEAT_COPY = {
    ("正财", "比肩"): "外在目标偏务实，底层动力却来自自己上手与同伴协作。好处是能把资源落地；需要留意凡事自己扛，或在分配问题上和同伴较真。",
    ("偏财", "劫财"): "机会与资源往往从团队、人群和快速变化中出现；你容易在行动中发现机会，也更容易遇到竞争、临时分配或计划被别人打乱。",
    ("日主", "食神"): "你在日常和亲密关系中需要舒展、可表达、能照顾感受的节奏。你更习惯通过做出成果、解决具体问题，让生活与关系变舒服。",
    ("偏印", "劫财"): "长期想法偏独立，真正执行时又需要迅速行动或借助伙伴。灵感和推进力都不弱，但要避免方向太多、学到一半又换题。",
}

PILLAR_TAKEAWAY = {
    "year": "别人先看到你的务实与责任感，而这份务实多半靠亲自投入和并肩协作来兑现。",
    "month": "工作中的机会不少来自人和变化；越是机会密集，越需要提前讲清分工、成本和边界。",
    "day": "你真正需要的是能表达、能产出、也能喘口气的生活；但外界节奏常会牵动这个位置。",
    "hour": "你对未来有自己的方法，适合边研究边推进；关键是给想法排顺序，不让行动把学习打散。",
}


def _e(value: object) -> str:
    return escape(str(value or ""))


def _polar(cx: float, cy: float, radius: float, index: float, count: int = 10) -> tuple[float, float]:
    angle = math.radians(-90 + 360 * index / count)
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def _points(values: list[float], scale: float, radius: float, cx: float, cy: float) -> str:
    return " ".join(
        f"{_polar(cx, cy, radius * value / scale, index)[0]:.1f},{_polar(cx, cy, radius * value / scale, index)[1]:.1f}"
        for index, value in enumerate(values)
    )


def _radar_svg(analysis: dict) -> str:
    radar = analysis["radar"]
    values = [float(item["percent"]) for item in radar]
    scale = max(25, int(math.ceil(max(values or [0]) / 5.0) * 5))
    cx, cy, radius = 260.0, 252.0, 164.0
    data_points = _points(values, scale, radius, cx, cy)
    outer_points = _points([scale] * 10, scale, radius, cx, cy)
    grids = "".join(
        f'<polygon class="radar-grid" points="{_points([scale * step] * 10, scale, radius, cx, cy)}"/>'
        for step in (0.25, 0.5, 0.75, 1.0)
    )
    axes = "".join(
        f'<line class="radar-axis" x1="{cx}" y1="{cy}" x2="{_polar(cx, cy, radius, i)[0]:.1f}" y2="{_polar(cx, cy, radius, i)[1]:.1f}"/>'
        for i in range(10)
    )
    family_glows = []
    family_positions = ((0.5, "peer"), (2.5, "output"), (4.5, "wealth"), (6.5, "authority"), (8.5, "resource"))
    for index, family in family_positions:
        x, y = _polar(cx, cy, radius * 0.7, index)
        family_glows.append(f'<circle class="wash {family}" cx="{x:.1f}" cy="{y:.1f}" r="88"/>')
    labels = []
    for index, item in enumerate(radar):
        x, y = _polar(cx, cy, 198, index)
        labels.append(
            f"""<g class="radar-label {FAMILY_CLASS[item['code']]}" transform="translate({x:.1f},{y:.1f})">
              <rect x="-34" y="-22" width="68" height="44" rx="5"/>
              <text class="name" y="-3">{_e(item['label'])}</text><text class="value" y="14">{item['percent']:.1f}%</text>
            </g>"""
        )
    return f"""
    <svg class="ten-radar" viewBox="0 0 520 500" role="img" aria-label="十神力量雷达图，十项合计为百分之百">
      <title>十神力量雷达图</title><desc>最高为劫财百分之二十一点六，其次为正财百分之十八点五。</desc>
      <defs>
        <clipPath id="ten-radar-mask"><polygon points="{data_points}"/></clipPath>
        <filter id="wash-blur" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="24"/></filter>
      </defs>
      <circle class="radar-halo" cx="260" cy="252" r="190"/>
      {grids}{axes}
      <g clip-path="url(#ten-radar-mask)">
        <polygon class="radar-base" points="{outer_points}"/>
        <g filter="url(#wash-blur)">{''.join(family_glows)}</g>
      </g>
      <polygon class="radar-shape" points="{data_points}"/>
      <circle class="radar-center" cx="260" cy="252" r="4"/>
      {''.join(labels)}
      <text class="scale-note" x="260" y="492">刻度上限 {scale}% · 十神合计 100%</text>
    </svg>"""


def _family_strip(analysis: dict) -> str:
    parts = []
    for family in analysis["families"]:
        member_names = " · ".join(f"{item['label']} {item['percent']:.1f}%" for item in family["members"])
        parts.append(
            f"""<div class="family-line {family['code']}"><div class="family-name"><b>{_e(family['label'])}</b><strong>{family['percent']:.1f}%</strong></div><div class="family-rule"><i style="width:{min(family['percent'] / 40 * 100, 100):.1f}%"></i></div><p>{_e(member_names)}</p></div>"""
        )
    return "".join(parts)


def _radar_page(analysis: dict) -> str:
    return f"""<article class="page verso radar-page" data-page="34">
      <header>十神 · 力量分布</header><p class="eyebrow">先看十种关系语言各自占了多少位置</p><h1>十神力量，不只看次数</h1>
      {_radar_svg(analysis)}
      <p class="bottom-note"><b>日主作为参照</b> 日主原始占比为 {analysis['basis']['rizhu_reference_percent']:.2f}%，故不计入十神百分比。</p><footer>34</footer>
    </article>"""


def _strength_page(analysis: dict) -> str:
    top = analysis["rankings"]["top"]
    top_lines = "".join(
        f'<div class="top-god {FAMILY_CLASS[item["code"]]}"><span>{index}</span><b>{_e(item["label"])}</b><strong>{item["percent"]:.1f}%</strong></div>'
        for index, item in enumerate(top, start=1)
    )
    absent = "、".join(item["label"] for item in analysis["rankings"]["absent"])
    return f"""<article class="page recto focus-page" data-page="35">
      <header>十神 · 力量重心</header><p class="eyebrow">强弱说明参与度，不直接等于好坏</p><h1>劫财在内，财星在外</h1>
      <p class="lead">推动事情、召集伙伴和抢进度的劲头，主要藏在地支内部。别人较先看到的，是你重结果、会安排资源，也希望事情能够稳定落地的一面。</p>
      <div class="top-gods">{top_lines}</div>
      <div class="family-stack">{_family_strip(analysis)}</div>
      <div class="absence"><b>低值与未见</b><p>七杀只占 {next(item['percent'] for item in analysis['radar'] if item['code']=='SHISHEN:QISHA'):.1f}%；{_e(absent)}在原局未直接形成力量。它们不是人格缺口，是否成为阶段主题，要留待大运流年观察。</p></div>
      <footer>35</footer>
    </article>"""


def _ten_god_intro_page(items: tuple[dict[str, str], ...], page: int, side: str, title: str) -> str:
    cards = "".join(
        f"""<section class="god-primer-card {FAMILY_CLASS[item['code']]}">
          <figure><img src="../../../assets/mingshu/shishen/{_e(item['image'])}" alt="{_e(item['name'])}意象插图"></figure>
          <div><p>{_e(item['theme'])}</p><h2>{_e(item['name'])}</h2><span>{_e(TEN_GOD_PLAIN[item['name']])}</span></div>
        </section>"""
        for item in items
    )
    return f"""<article class="page {side} primer-page" data-page="{page}">
      <header>十神 · 基础含义</header><p class="eyebrow">十个名称，描述人与资源、表达、规则和学习的十种关系</p><h1>{_e(title)}</h1>
      <div class="god-primer-list">{cards}</div><footer>{page}</footer>
    </article>"""


def _position_page(facts: dict, analysis: dict, pillar_keys: tuple[str, str], page: int, side: str) -> str:
    pillars = {str(item.get("key")): item for item in (facts.get("chart") or {}).get("pillars") or []}
    blocks = []
    for pillar_key in pillar_keys:
        pillar = pillars[pillar_key]
        stem = next(item for item in analysis["placements"] if item["pillar"] == pillar_key and item["layer"] == "stem")
        hidden = [item for item in analysis["placements"] if item["pillar"] == pillar_key and item["layer"] == "hidden"]
        god = stem["ten_god_label"]
        stem_label = "日干" if pillar_key == "day" else f"{pillar.get('label', '')[:1]}干"
        branch = pillar.get("zhi") or {}
        hidden_line = " · ".join(
            f"{item['source_label']}{item['ten_god_label']}（{item['hidden_rank_label']}）" for item in hidden
        )
        blocks.append(f"""<section class="layer-analysis-card">
          <div class="layer-glyph"><small>{_e(pillar.get('label'))}</small><b>{_e(stem['source_label'])}</b><span>{_e(god)}</span></div>
          <div class="position-copy"><h2>{_e(stem_label)}{_e(stem['source_label'])}是{_e(god)}</h2><p>{_e(STEM_POSITION_COPY[(pillar_key, god)])}</p>
          <div class="branch-position"><b>地支{_e(branch.get('name_label'))}｜{_e(hidden[0]['ten_god_label'])}为本气</b><p>{_e(BRANCH_POSITION_COPY[pillar_key])}</p><small>藏干：{_e(hidden_line)}</small></div></div>
        </section>""")
    return f"""<article class="page {side} layered-page" data-page="{page}">
      <header>十神定位 · 第一层</header><p class="eyebrow">先看十神落在哪一柱，它的作用范围才会清楚</p><h1>十神与位置：{_e(pillars[pillar_keys[0]]['label'])}、{_e(pillars[pillar_keys[1]]['label'])}</h1>
      <div class="layer-analysis-list">{''.join(blocks)}</div>
      <p class="layer-closing">天干说明较容易显露的表达，地支及藏干说明更深的行动底色；两层都确认以后，组合与冲合才有落脚点。</p><footer>{page}</footer>
    </article>"""


def _combination_page(facts: dict, analysis: dict, pillar_keys: tuple[str, str], page: int, side: str) -> str:
    pillars = {str(item.get("key")): item for item in (facts.get("chart") or {}).get("pillars") or []}
    blocks = []
    for pillar_key in pillar_keys:
        pillar = pillars[pillar_key]
        stem = next(item for item in analysis["placements"] if item["pillar"] == pillar_key and item["layer"] == "stem")
        main = next(item for item in analysis["placements"] if item["pillar"] == pillar_key and item["layer"] == "hidden")
        gan_god, main_god = stem["ten_god_label"], main["ten_god_label"]
        combination = f"{gan_god}坐{main_god}" if gan_god != "日主" else f"日主坐{main_god}"
        blocks.append(f"""<section class="seat-analysis-card">
          <div class="seat-pair"><small>{_e(pillar.get('label'))}</small><b>{_e(gan_god)}</b><i>坐</i><b>{_e(main_god)}</b></div>
          <div><h2>{_e(combination)}</h2><p>{_e(SEAT_COPY[(gan_god, main_god)])}</p><small>{_e((pillar.get('zhi') or {}).get('name_label'))}的本气为{_e(main['source_label'])}{_e(main_god)}，与天干{_e(stem['source_label'])}{_e(gan_god)}合看。</small></div>
        </section>""")
    return f"""<article class="page {side} layered-page seat-page" data-page="{page}">
      <header>十神定位 · 第二层</header><p class="eyebrow">天干是较容易显露的一面，地支本气是更深的行动底色</p><h1>同柱组合：{_e(pillars[pillar_keys[0]]['label'])}、{_e(pillars[pillar_keys[1]]['label'])}</h1>
      <div class="layer-analysis-list">{''.join(blocks)}</div>
      <p class="layer-closing">“坐”不是吉凶标签。它说明同一个位置里，上层的表现方式和下层的动力如何配合，也可能在哪里彼此牵制。</p><footer>{page}</footer>
    </article>"""


def _relation_plain(label: str, pillar_key: str) -> str:
    if label == "辛乙冲":
        return (
            "月干辛偏财与时干乙偏印相冲：眼前的资源、机会与成本，常会逼着你修正长期学习和个人方法；"
            "反过来，新方法也会让你重新判断哪些机会值得接。"
        )
    if label == "巳丑拱合":
        return (
            "巳与丑有向酉金靠拢的趋势。对丁火而言，金是财星，所以工作行动、日常产出和实际结果容易互相牵引；"
            "但酉并未出现，只能理解为倾向，不能当成已经合成财局。"
        )
    if label == "午丑穿":
        return (
            "年支午与日支丑有隐性摩擦：外界或早期环境的节奏，与自己的日常和亲密关系节奏不总一致。"
            "它表示需要磨合，不等于家庭或关系一定出问题。"
        )
    return f"本柱参与{label}，需要结合另一端所在位置一起理解，不单凭一个名称下结论。"


def _pillar_reading_page(facts: dict, analysis: dict, pillar_key: str, page: int, side: str) -> str:
    pillars = {str(item.get("key")): item for item in (facts.get("chart") or {}).get("pillars") or []}
    pillar = pillars[pillar_key]
    stem = next(item for item in analysis["placements"] if item["pillar"] == pillar_key and item["layer"] == "stem")
    hidden = [item for item in analysis["placements"] if item["pillar"] == pillar_key and item["layer"] == "hidden"]
    main = hidden[0]
    extras = hidden[1:]
    zhi = pillar.get("zhi") or {}
    gan_god = stem["ten_god_label"]
    main_god = main["ten_god_label"]
    title = f'{pillar.get("label")}｜{gan_god}坐{main_god}' if gan_god != "日主" else f'{pillar.get("label")}｜日主坐{main_god}'
    stem_copy = STEM_POSITION_COPY.get(
        (pillar_key, gan_god),
        f'{TEN_GOD_PLAIN.get(gan_god, "这是一种十神关系。")}{PILLAR_SCOPE[pillar_key]}',
    )
    seat_copy = SEAT_COPY.get(
        (gan_god, main_god),
        f'上层的{gan_god}负责对外表达，地支本气{main_god}提供更深层的动力。两者要合起来读，不能只看一个名称。',
    )
    extras_html = "".join(
        f'<li><b>{_e(item["source_label"])} · {_e(item["ten_god_label"])}</b><span>{_e(TEN_GOD_PLAIN.get(item["ten_god_label"], "补充这一柱的内在层次。"))}</span></li>'
        for item in extras
    ) or '<li><b>本柱藏气较单纯</b><span>主要围绕本气展开，不另外增加次层主题。</span></li>'
    related = []
    seen: set[str] = set()
    for relation in analysis["relations"]:
        if not any(str(member.get("pillar")) == pillar_key for member in relation.get("members") or []):
            continue
        label = str(relation.get("label") or "")
        key = f'{label}:{_relation_plain(label, pillar_key)}'
        if key in seen:
            continue
        seen.add(key)
        related.append(f'<li><b>{_e(label)}</b><span>{_e(_relation_plain(label, pillar_key))}</span></li>')
    relations_html = "".join(related) or '<li><b>本柱没有额外冲合</b><span>阅读重点放在天干、地支本气与藏干层次。</span></li>'
    stem_label = "日干" if pillar_key == "day" else f'{pillar.get("label", "")[:1]}干'
    return f"""<article class="page {side} pillar-story" data-page="{page}">
      <header>十神定位 · {_e(pillar.get('label'))}</header><p class="eyebrow">宫位界定之后，再看它怎样进入现实生活</p><h1>{_e(title)}</h1><p class="scope">{_e(PILLAR_SCOPE[pillar_key])}</p>
      <section class="story-card"><i>一</i><div><h2>{_e(stem_label)}{_e(stem['source_label'])}是{_e(gan_god)}</h2><p>{_e(stem_copy)}</p></div></section>
      <section class="story-card"><i>二</i><div><h2>“{_e(gan_god)}坐{_e(main_god)}”是什么意思</h2><p>地支{_e(zhi.get('name_label'))}的本气是{_e(main['source_label'])}{_e(main_god)}。{_e(seat_copy)}</p></div></section>
      <section class="story-card compact"><i>三</i><div><h2>{_e(zhi.get('name_label'))}中还藏着什么</h2><ul>{extras_html}</ul></div></section>
      <section class="story-card compact relation-card"><i>四</i><div><h2>这一柱在原盘里怎样被牵动</h2><ul>{relations_html}</ul></div></section>
      <p class="takeaway">{_e(PILLAR_TAKEAWAY[pillar_key])}</p><footer>{page}</footer>
    </article>"""


def _interaction_page(analysis: dict, relations: list[dict], page: int, side: str) -> str:
    relation_copy = {
        "六合": "两处位置彼此靠近，现实中常表现为事务更容易绑定、协作或互相迁就；连接变紧以后，也要避免一方长期替另一方承担。",
        "拱合": "两处位置朝同一方向牵引，但所缺条件并未完全到位。它表示潜在路径，不等于已经合成一局。",
        "自刑": "同一类要求在内部重复，容易出现反复催促自己、越忙越难停下的情况。记录、复盘和明确完成标准能减少空转。",
        "暗合": "联系不一定摆在明面，常通过习惯、默契或未说出口的需要彼此影响。重要事项仍应说清，不把猜测当作共识。",
        "冲": "两种要求正面相遇，需要明确排序；它表示调整与选择，不等于某件坏事必然发生。",
        "穿": "两处生活领域容易在细节上互相侵入，需要用日程、职责和边界减少长期磨损。",
    }
    cards = []
    for relation in relations:
        members = relation.get("members") or []
        left = members[0] if members else {}
        right = members[1] if len(members) > 1 else {}
        relation_type = str(relation.get("relation_type") or "")
        kind = "拱合" if "GONGHE" in relation_type else "六合" if "LIUHE" in relation_type else "自刑" if "ZIXING" in relation_type else "暗合" if "ANHE" in relation_type else "冲" if "CHONG" in relation_type else "穿" if "CHUAN" in relation_type else str(relation.get("label") or "作用")
        locations = f"{left.get('pillar_label', '')}{left.get('label', '')}（{left.get('ten_god_label', '')}）与{right.get('pillar_label', '')}{right.get('label', '')}（{right.get('ten_god_label', '')}）"
        cards.append(f"<section><b>{_e(relation.get('label'))}｜{_e(locations)}</b><p>{_e(relation_copy.get(kind, '这两处位置形成结构联系，需要结合所在宫位观察它在现实中的表现。'))}</p></section>")
    return f"""<article class="page {side} interaction-story" data-page="{page}">
      <header>十神定位 · 第三层</header><p class="eyebrow">从关系两端所在宫位，理解它会牵动哪些现实事务</p><h1>原盘作用关系 · 第{('一' if page == 40 else '二')}组</h1>
      {''.join(cards)}<aside>关系线说明两处位置怎样互相牵动；它不能越过五行强弱、十神层次和现实经历，直接翻译成具体事件。</aside><footer>{page}</footer>
    </article>"""


def _placement_column(pillar: dict, placements: list[dict]) -> str:
    stem = next(item for item in placements if item["pillar"] == pillar["key"] and item["layer"] == "stem")
    hidden = [item for item in placements if item["pillar"] == pillar["key"] and item["layer"] == "hidden"]
    hidden_html = "".join(
        f'<div class="hidden-row {FAMILY_CLASS.get(item["ten_god"], "rizhu")}"><small>{_e(item["hidden_rank_label"])}</small><b>{_e(item["source_label"])}</b><span>{_e(item["ten_god_label"])}</span></div>'
        for item in hidden
    )
    zhi = pillar.get("zhi") or {}
    return f"""<div class="placement-column">
      <b class="pillar-name">{_e(pillar.get('label'))}</b>
      <div class="stem-god {FAMILY_CLASS.get(stem['ten_god'], 'rizhu')}"><small>天干 · 透出</small><strong>{_e(stem['source_label'])}</strong><span>{_e(stem['ten_god_label'])}</span></div>
      <div class="branch-glyph"><small>地支</small><strong>{_e(zhi.get('name_label'))}</strong></div>
      <div class="hidden-list">{hidden_html}</div>
    </div>"""


def _page24(facts: dict, analysis: dict) -> str:
    pillars = (facts.get("chart") or {}).get("pillars") or []
    columns = "".join(_placement_column(pillar, analysis["placements"]) for pillar in pillars[:4])
    return f"""<article class="page verso placement-page" data-page="24">
      <header>十神 · 落位</header><p class="eyebrow">透在天干，和藏在地支，是两种不同的表达层</p><h1>同样的力量，出现位置不同</h1>
      <div class="placement-board"><div class="layer-tag stem-tag">显</div><div class="layer-tag hidden-tag">藏</div>{columns}</div>
      <div class="placement-legend"><span><i class="dot main"></i>本气：地支主轴</span><span><i class="dot middle"></i>中气：次层参与</span><span><i class="dot residual"></i>余气：潜藏线索</span></div>
      <p class="bottom-note">这一页先看位置与层级；强弱结论请结合前页的力量分布阅读。</p><footer>24</footer>
    </article>"""


def _page25(facts: dict, analysis: dict) -> str:
    pillars = (facts.get("chart") or {}).get("pillars") or []
    sections = []
    for pillar in pillars[:4]:
        stem = next(item for item in analysis["placements"] if item["pillar"] == pillar["key"] and item["layer"] == "stem")
        hidden = [item for item in analysis["placements"] if item["pillar"] == pillar["key"] and item["layer"] == "hidden"]
        evidence = "，".join(f"{item['hidden_rank_label']}{item['ten_god_label']}" for item in hidden)
        sections.append(
            f"""<section class="palace-section"><div class="palace-index">{_e(pillar.get('label'))}</div><div><h2>{_e(stem['source_label'])} · {_e(stem['ten_god_label'])}透出</h2><p>{_e(PALACE_COPY[pillar['key']])}</p><small>地支 {_e((pillar.get('zhi') or {}).get('name_label'))}：{_e(evidence)}</small></div></section>"""
        )
    return f"""<article class="page recto palace-page" data-page="25">
      <header>十神 · 宫位阅读</header><p class="eyebrow">先确认落点，再决定它更容易在哪个领域被看见</p><h1>四个位置，四种关注范围</h1>
      <div class="palace-sections">{''.join(sections)}</div>
      <p class="closing-line">本盘的关键差别是：劫财虽强却藏，正财不但透出，而且在月、时两支重复出现；强度与可见度必须分开阅读。</p><footer>25</footer>
    </article>"""


def _relation_rail(x1: float, x2: float, y: float, left: str, right: str, label: str, kind: str) -> str:
    mid = (x1 + x2) / 2
    width = max(64, len(label) * 15 + 18)
    return f"""<g class="ss-rail {kind}"><line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/><circle cx="{x1}" cy="{y}" r="14"/><circle cx="{x2}" cy="{y}" r="14"/><text x="{x1}" y="{y+5}">{_e(left)}</text><text x="{x2}" y="{y+5}">{_e(right)}</text><g class="ss-caption" transform="translate({mid},{y-24})"><rect x="{-width/2}" y="-13" width="{width}" height="25" rx="5"/><text y="5">{_e(label)}</text></g></g>"""


def _page26(facts: dict, analysis: dict) -> str:
    pillars = (facts.get("chart") or {}).get("pillars") or []
    nodes = []
    for pillar in pillars[:4]:
        x = PILLAR_X[pillar["key"]]
        gan, zhi = pillar.get("gan") or {}, pillar.get("zhi") or {}
        main_hidden = (zhi.get("hidden_gans") or [{}])[0]
        nodes.append(f"""<g class="ss-node" transform="translate({x},0)"><text class="pillar" y="95">{_e(pillar.get('label'))}</text><text class="gan" y="154">{_e(gan.get('name_label'))}</text><text class="gan-ss" y="178">{_e(gan.get('shishen_label'))}</text><text class="zhi" y="262">{_e(zhi.get('name_label'))}</text><text class="zhi-ss" y="286">{_e(main_hidden.get('shishen_label'))} · 本气</text></g>""")
    rails = [
        _relation_rail(PILLAR_X["month"], PILLAR_X["hour"], 54, "偏财", "偏印", "辛乙冲", "clash"),
        _relation_rail(PILLAR_X["month"], PILLAR_X["day"], 342, "劫财", "食神", "巳丑拱合", "combine"),
        _relation_rail(PILLAR_X["day"], PILLAR_X["hour"], 342, "食神", "劫财", "巳丑拱合", "combine"),
        _relation_rail(PILLAR_X["year"], PILLAR_X["day"], 410, "比肩", "食神", "午丑穿", "harm"),
    ]
    return f"""<article class="page verso ss-relation-page" data-page="26">
      <header>十神 · 作用关系</header><p class="eyebrow">关系发生在干支，十神说明被牵动的主题</p><h1>把十神放回原盘，看清张力</h1>
      <svg class="ss-relation-map" viewBox="0 0 522 450" role="img" aria-label="原盘十神作用关系图">{''.join(nodes)}{''.join(rails)}</svg>
      <div class="relation-key"><span><i class="clash"></i>冲：直接校准</span><span><i class="combine"></i>拱合：结构牵引</span><span><i class="harm"></i>穿：宫位摩擦</span></div>
      <p class="bottom-note">地支以本气作简写，完整解读仍会保留全部藏气。</p><footer>26</footer>
    </article>"""


def _page27(analysis: dict) -> str:
    return f"""<article class="page recto relation-reading-page" data-page="27">
      <header>十神 · 关系解读</header><p class="eyebrow">每一条都从命盘事实出发，再说明它牵动的生活领域</p><h1>三种作用，牵动三个现实问题</h1>
      <section class="relation-reading clash"><b>冲</b><div><h2>偏财与偏印：资源和方法反复校准</h2><p>月干辛为偏财，时干乙为偏印，两者相冲。可以理解为当下的资源调度、机会判断，与长期学习、独立方法之间容易互相修正。</p><small>这是原局中已经成立的天干作用；不直接翻译成破财或学业不利。</small></div></section>
      <section class="relation-reading combine"><b>拱</b><div><h2>两组巳丑拱酉：日支同时承接月、时牵引</h2><p>月支巳与日支丑、日支丑与时支巳分别拱酉。巳以劫财为本气，丑以食神为本气，结构共同指向酉金，对丁日主属于财星方向。</p><small>中神酉未出现，因此只论拱意，不作三合成局，也不另计财星力量。</small></div></section>
      <section class="relation-reading harm"><b>穿</b><div><h2>比肩与食神：外层环境牵动日常位置</h2><p>年支午与日支丑相穿。若先看本气，是比肩与食神所在的两个宫位形成持续摩擦；进一步分析仍须保留双方其他藏气。</p><small>穿强调关系中的隐性牵扯，不等于一个必然发生的具体事件。</small></div></section>
      <p class="chapter-thesis">这一盘的十神主线由此变得清楚：劫财深藏、财星外显，日支食神又处在多条关系交汇处。</p><footer>27</footer>
    </article>"""


def render_shishen_sample_html(facts: dict) -> str:
    analysis = build_ten_god_analysis(facts)
    relations = analysis.get("relations") or []
    midpoint = max(1, (len(relations) + 1) // 2)
    pages = [
        _ten_god_intro_page(TEN_GOD_ASSETS[:5], 32, "verso", "从同伴到资源"),
        _ten_god_intro_page(TEN_GOD_ASSETS[5:], 33, "recto", "从机会到学习"),
        _radar_page(analysis),
        _strength_page(analysis),
        _pillar_reading_page(facts, analysis, "year", 36, "verso"),
        _pillar_reading_page(facts, analysis, "month", 37, "recto"),
        _pillar_reading_page(facts, analysis, "day", 38, "verso"),
        _pillar_reading_page(facts, analysis, "hour", 39, "recto"),
        _interaction_page(analysis, relations[:midpoint], 40, "verso"),
        _interaction_page(analysis, relations[midpoint:], 41, "recto"),
    ]
    spreads = "".join(f'<section class="spread">{pages[i]}{pages[i+1]}</section>' for i in range(0, len(pages), 2))
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 十神分析样例</title><style>
@font-face{{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}}
@font-face{{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}}
@font-face{{font-family:BookBrush;src:url('../../../assets/fonts/MaShanZheng-Regular.ttf')}}
@page{{size:A4 landscape;margin:0}}:root{{--paper:#f5eddd;--paper2:#fbf7ec;--ink:#282721;--muted:#70695d;--line:#d7c7aa;--gold:#a77b37;--jade:#315f52;--red:#994438;--peer:#a84c3d;--output:#c09645;--wealth:#b58948;--authority:#53758a;--resource:#4f7964}}*{{box-sizing:border-box}}body{{margin:0;background:#242422;color:var(--ink);font-family:BookSerif,serif}}main{{padding:28px 0 70px}}.spread{{display:flex;width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;filter:drop-shadow(0 14px 24px #111)}}.page{{position:relative;flex:0 0 50%;aspect-ratio:148/210;padding:7.5% 8%;overflow:hidden;background:linear-gradient(145deg,var(--paper2),var(--paper));contain:layout paint}}.spread>.page:first-child:after{{content:'';position:absolute;right:0;inset-block:0;width:1px;background:#cbbfae}}header{{font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px}}.recto header{{text-align:right}}h1{{font-size:29px;line-height:1.25;margin:7px 0 10px;font-weight:500}}h2{{font-weight:500}}.eyebrow{{font:9px BookSans;color:var(--gold);letter-spacing:.11em;margin:18px 0 0}}footer{{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#887d6b}}.recto footer{{text-align:right}}.bottom-note{{font:9px/1.65 BookSans;color:var(--muted);margin:8px 0 0;padding:9px 12px;border-left:2px solid var(--gold);background:rgba(255,253,247,.65)}}.bottom-note b{{color:var(--jade);margin-right:8px}}
.ten-radar{{display:block;width:100%;height:auto;margin-top:-3px}}.radar-halo{{fill:#f7f0e3;stroke:#d8c6a4;stroke-width:1}}.radar-grid,.radar-axis{{fill:none;stroke:#baa57d;stroke-width:1;opacity:.65}}.radar-base{{fill:#eadcc3;opacity:.72}}.wash{{opacity:.68}}.wash.peer{{fill:var(--peer)}}.wash.output{{fill:var(--output)}}.wash.wealth{{fill:var(--wealth)}}.wash.authority{{fill:var(--authority)}}.wash.resource{{fill:var(--resource)}}.radar-shape{{fill:none;stroke:#8e6934;stroke-width:2.2;stroke-linejoin:round}}.radar-center{{fill:#8e6934}}.radar-label rect{{fill:#fffdf7;stroke:#d5c4a6;stroke-width:1}}.radar-label text{{text-anchor:middle}}.radar-label .name{{font:14px BookSerif;fill:var(--ink)}}.radar-label .value{{font:10px BookSans;fill:#6c655a}}.radar-label.peer rect{{stroke:var(--peer)}}.radar-label.output rect{{stroke:var(--output)}}.radar-label.wealth rect{{stroke:var(--wealth)}}.radar-label.authority rect{{stroke:var(--authority)}}.radar-label.resource rect{{stroke:var(--resource)}}.scale-note{{font:9px BookSans;fill:#81735f;text-anchor:middle;letter-spacing:.08em}}
.focus-page .lead{{font:12px/1.8 BookSans;color:#554f46;margin:12px 0 16px}}.top-gods{{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.top-god{{padding:13px 9px;display:grid;grid-template-columns:20px 1fr;gap:2px 6px;border-right:1px solid var(--line)}}.top-god:last-child{{border-right:0}}.top-god span{{grid-row:1/3;font:18px BookSerif;color:#b39a72}}.top-god b{{font-size:14px}}.top-god strong{{font:11px BookSans;color:var(--muted)}}.family-stack{{margin-top:17px}}.family-line{{margin:0 0 12px}}.family-name{{display:flex;justify-content:space-between;align-items:baseline}}.family-name b{{font-size:13px}}.family-name strong{{font:11px BookSans}}.family-rule{{height:5px;background:rgba(180,160,125,.18);margin:5px 0}}.family-rule i{{display:block;height:100%;background:currentColor}}.family-line p{{font:9px BookSans;color:var(--muted);margin:0}}.family-line.peer{{color:var(--peer)}}.family-line.output{{color:var(--output)}}.family-line.wealth{{color:var(--wealth)}}.family-line.authority{{color:var(--authority)}}.family-line.resource{{color:var(--resource)}}.absence{{margin-top:15px;padding-top:12px;border-top:1px solid var(--line)}}.absence b{{color:var(--jade);font-size:12px}}.absence p{{font:10px/1.7 BookSans;color:#5f594f;margin:5px 0}}
.placement-board{{position:relative;display:grid;grid-template-columns:repeat(4,1fr);height:470px;margin-top:15px;border-top:1px solid var(--gold);border-bottom:1px solid var(--gold);background:rgba(255,253,247,.38)}}.placement-column{{text-align:center;border-right:1px solid rgba(182,158,117,.35);padding:21px 9px 10px}}.placement-column:last-child{{border-right:0}}.pillar-name{{font-size:11px}}.stem-god{{margin:13px 0 8px;padding-bottom:13px;border-bottom:1px solid var(--line)}}.stem-god small,.branch-glyph small{{display:block;font:8px BookSans;color:#8b7653}}.stem-god strong{{display:block;font-size:42px;line-height:1.3}}.stem-god span{{font-size:12px}}.branch-glyph{{margin:7px 0 12px}}.branch-glyph strong{{display:block;font-size:36px;line-height:1.3;color:#82622f}}.hidden-list{{border-top:1px solid var(--line)}}.hidden-row{{display:grid;grid-template-columns:32px 24px 1fr;align-items:center;padding:8px 0;border-bottom:1px solid rgba(190,169,133,.32);text-align:left}}.hidden-row small{{font:8px BookSans;color:#927d59}}.hidden-row b{{font-size:14px}}.hidden-row span{{font:9px BookSans;color:#5f594e;text-align:right}}.stem-god.peer,.hidden-row.peer{{color:var(--peer)}}.stem-god.output,.hidden-row.output{{color:var(--output)}}.stem-god.wealth,.hidden-row.wealth{{color:var(--wealth)}}.stem-god.authority,.hidden-row.authority{{color:var(--authority)}}.stem-god.resource,.hidden-row.resource{{color:var(--resource)}}.stem-god.rizhu{{color:var(--red)}}.layer-tag{{position:absolute;left:-28px;writing-mode:vertical-rl;font:9px BookSans;color:#9a7b47;letter-spacing:.15em}}.stem-tag{{top:102px}}.hidden-tag{{top:325px}}.placement-legend{{display:flex;justify-content:center;gap:17px;font:8px BookSans;color:var(--muted);margin-top:10px}}.dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;background:#a67c3f}}.dot.middle{{opacity:.65}}.dot.residual{{opacity:.35}}
.palace-sections{{margin-top:15px;border-top:1px solid var(--line)}}.palace-section{{display:grid;grid-template-columns:72px 1fr;gap:14px;padding:17px 0;border-bottom:1px solid var(--line)}}.palace-index{{font-size:17px;color:var(--gold);padding-top:2px}}.palace-section h2{{font-size:15px;margin:0 0 5px}}.palace-section p{{font:10px/1.65 BookSans;color:#5c564d;margin:0 0 6px}}.palace-section small{{font:8.5px BookSans;color:#8a7656}}.closing-line{{font:11px/1.75 BookSans;color:var(--jade);margin:17px 0 0;padding-left:13px;border-left:3px solid var(--gold)}}
.ss-relation-map{{display:block;width:100%;height:auto;margin-top:5px;background:rgba(255,253,247,.25);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.ss-node text{{text-anchor:middle}}.ss-node .pillar{{font:11px BookSerif;fill:#625a4e}}.ss-node .gan,.ss-node .zhi{{font:42px BookSerif;fill:var(--ink)}}.ss-node .gan-ss,.ss-node .zhi-ss{{font:10px BookSans;fill:#866f4a}}.ss-rail line{{stroke:currentColor;stroke-width:1.8}}.ss-rail circle{{fill:#fffaf0;stroke:currentColor;stroke-width:1.4}}.ss-rail>text,.ss-caption text{{font:10px BookSerif;fill:currentColor;text-anchor:middle}}.ss-caption rect{{fill:#fffaf0;stroke:none}}.ss-rail.clash{{color:var(--red)}}.ss-rail.combine{{color:var(--jade)}}.ss-rail.harm{{color:#8d6536}}.ss-rail.harm line{{stroke-dasharray:7 5}}.relation-key{{display:flex;justify-content:center;gap:19px;font:8px BookSans;color:var(--muted);margin-top:9px}}.relation-key i{{display:inline-block;width:21px;height:2px;vertical-align:middle;margin-right:5px;background:currentColor}}.relation-key i.clash{{color:var(--red)}}.relation-key i.combine{{color:var(--jade)}}.relation-key i.harm{{color:#8d6536;background:repeating-linear-gradient(90deg,currentColor 0 5px,transparent 5px 8px)}}
.relation-reading-page h1{{margin-bottom:16px}}.relation-reading{{display:grid;grid-template-columns:55px 1fr;gap:14px;padding:18px 0;border-top:1px solid var(--line)}}.relation-reading>b{{font:34px BookBrush;color:currentColor;text-align:center}}.relation-reading h2{{font-size:15px;margin:0 0 6px}}.relation-reading p{{font:10px/1.7 BookSans;color:#575149;margin:0 0 6px}}.relation-reading small{{font:8.5px/1.55 BookSans;color:#88775c}}.relation-reading.clash{{color:var(--red)}}.relation-reading.combine{{color:var(--jade)}}.relation-reading.harm{{color:#8d6536;border-bottom:1px solid var(--line)}}.relation-reading p,.relation-reading h2{{color:var(--ink)}}.chapter-thesis{{font:12px/1.75 BookSerif;color:var(--jade);margin:17px 0 0;padding-left:14px;border-left:3px solid var(--gold)}}
.pillar-story{{padding:5.8% 8% 5.4%}}.pillar-story h1{{font-size:29px;margin-bottom:5px}}.scope{{font:11.2px/1.65 BookSans;color:#5e584f;margin:0 0 7px;padding-bottom:8px;border-bottom:1px solid var(--gold)}}.story-card{{display:grid;grid-template-columns:38px 1fr;gap:11px;padding:9px 0;border-bottom:1px solid var(--line)}}.story-card>i{{font:28px BookBrush;color:var(--gold);font-style:normal;text-align:center}}.story-card h2{{font-size:15px;margin:0 0 4px;color:var(--jade)}}.story-card p{{font:10.5px/1.6 BookSans;color:#45413b;margin:0}}.story-card ul{{list-style:none;margin:0;padding:0}}.story-card li{{margin-top:4px}}.story-card li:first-child{{margin-top:0}}.story-card li b{{display:inline;color:#7e6033;font:10px BookSans;margin-right:6px}}.story-card li span{{font:10px/1.52 BookSans;color:#4e4942}}.story-card.compact{{padding-block:8px}}.relation-card{{border-bottom:0}}.takeaway{{font:10.6px/1.58 BookSans;color:var(--jade);margin:7px 0 0;padding:9px 11px;border-left:3px solid var(--gold);background:rgba(255,253,247,.72)}}.takeaway b{{margin-right:7px;color:var(--red)}}.pillar-story[data-page='37'] .story-card{{padding-block:7px}}.pillar-story[data-page='37'] .story-card p,.pillar-story[data-page='37'] .story-card li span{{line-height:1.48}}.pillar-story[data-page='37'] .takeaway{{margin-top:4px;padding-block:7px}}
.interaction-story h1{{font-size:28px;margin-bottom:15px}}.interaction-story section{{padding:15px 0;border-top:1px solid var(--line)}}.interaction-story section>b{{display:block;font-size:14px;color:var(--jade);margin-bottom:6px}}.interaction-story section p,.interaction-story section li{{font:10px/1.72 BookSans;color:#514c44}}.interaction-story section p{{margin:0}}.interaction-story section ul{{margin:0;padding-left:19px}}.interaction-story section li{{margin:4px 0}}.interaction-story strong{{font-weight:500;color:var(--red)}}.interaction-story aside{{margin-top:11px;padding:11px 13px;border-left:3px solid var(--gold);background:rgba(255,253,247,.7);font:10px/1.68 BookSans;color:#564f45}}.interaction-story aside b{{color:var(--red);margin-right:7px}}
.primer-page h1{{margin-bottom:13px}}.god-primer-list{{border-top:1px solid var(--gold)}}.god-primer-card{{display:grid;grid-template-columns:88px 1fr;gap:13px;height:103px;padding:8px 0;border-bottom:1px solid var(--line);align-items:center}}.god-primer-card figure{{height:86px;margin:0;overflow:hidden;background:rgba(255,253,247,.5);border-left:3px solid currentColor}}.god-primer-card img{{width:100%;height:100%;object-fit:contain;mix-blend-mode:multiply}}.god-primer-card div>p{{font:8px BookSans;color:var(--gold);margin:0 0 1px;letter-spacing:.08em}}.god-primer-card h2{{font-size:17px;margin:0 0 3px;color:var(--ink)}}.god-primer-card span{{display:block;font:9.2px/1.58 BookSans;color:#514c44}}.god-primer-card.peer{{color:var(--peer)}}.god-primer-card.output{{color:var(--output)}}.god-primer-card.wealth{{color:var(--wealth)}}.god-primer-card.authority{{color:var(--authority)}}.god-primer-card.resource{{color:var(--resource)}}
.layered-page h1{{font-size:27px;margin-bottom:13px}}.layer-analysis-list{{border-top:1px solid var(--gold)}}.layer-analysis-card,.seat-analysis-card{{display:grid;grid-template-columns:92px 1fr;gap:16px;min-height:228px;padding:16px 0;border-bottom:1px solid var(--line);align-items:center}}.layer-glyph,.seat-pair{{text-align:center;padding:15px 8px;border:1px solid var(--line);background:rgba(255,253,247,.55)}}.layer-glyph small,.seat-pair small{{display:block;font:9px BookSans;color:var(--gold);margin-bottom:5px}}.layer-glyph b{{display:block;font:43px BookSerif;color:var(--red);line-height:1.2}}.layer-glyph span{{font-size:13px;color:var(--jade)}}.layer-analysis-card h2,.seat-analysis-card h2{{font-size:17px;margin:0 0 5px}}.layer-analysis-card p,.seat-analysis-card p{{font:9.4px/1.58 BookSans;color:#4f4a43;margin:0 0 7px}}.layer-analysis-card div>small,.seat-analysis-card div>small{{font:8px/1.48 BookSans;color:#89785c}}.branch-position{{margin-top:7px;padding-top:7px;border-top:1px solid var(--line)}}.branch-position>b{{display:block;font:10px BookSans;color:var(--jade);margin-bottom:3px}}.branch-position p{{font-size:8.8px;line-height:1.52;margin-bottom:4px}}.branch-position small{{display:block;font:7.7px/1.4 BookSans;color:#8a7656}}.layer-closing{{font:9px/1.55 BookSans;color:var(--jade);padding:8px 11px;margin:10px 0 0;border-left:3px solid var(--gold);background:rgba(255,253,247,.58)}}.seat-pair b{{display:block;font-size:18px;color:var(--ink)}}.seat-pair i{{display:block;font:23px BookBrush;color:var(--gold);font-style:normal;line-height:1}}.seat-analysis-card{{grid-template-columns:112px 1fr;min-height:225px;padding:22px 0}}.seat-analysis-card p{{font-size:10.3px;line-height:1.72}}.seat-page .layer-closing{{font-size:10px;line-height:1.7;padding:11px 13px;margin-top:16px}}
.pillar-story[data-page='37'] .takeaway{{margin-top:3px;padding-top:6px;padding-bottom:6px}}
@media print{{body{{background:#fff}}main{{padding:0}}.spread{{width:296mm;height:210mm;margin:0;filter:none;break-after:page}}.page{{width:148mm;height:210mm}}}}</style></head><body><main>{spreads}</main>{ELEMENT_COLOR_SCRIPT}</body></html>"""


def write_shishen_sample(facts: dict, destination: str | Path, data_destination: str | Path | None = None) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_shishen_sample_html(facts), encoding="utf-8")
    if data_destination is not None:
        data_path = Path(data_destination)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(json.dumps(build_ten_god_analysis(facts), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
