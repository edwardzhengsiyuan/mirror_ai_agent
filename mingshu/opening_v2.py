"""Second-generation opening proof driven directly by structured paipan facts."""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

from .opening_content import DAY_MASTER_PROFILES, MONTH_PROFILES, ZODIAC_PROFILES, daymaster_asset
from .ganzhi_library import BRANCH_ARCHETYPES, STEM_ARCHETYPES
from .tiaohou_content import daymaster_classic, tiaohou_combo
from .element_styles import ELEMENT_COLOR_SCRIPT


ELEMENT_COLORS = {
    "WUXING:MU": "#315f47",
    "WUXING:HUO": "#a9362b",
    "WUXING:TU": "#a5742f",
    "WUXING:JIN": "#77756e",
    "WUXING:SHUI": "#244e68",
}


def _join_cn(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return "、".join(items[:-1]) + "与" + items[-1]


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _view(facts: dict) -> dict:
    chart = facts.get("chart") or {}
    pillars = list(chart.get("pillars") or [])[:4]
    day_code = (chart.get("day_master") or {}).get("code") or "GAN:BING"
    month_code = ((pillars[1].get("zhi") or {}).get("name") if len(pillars) > 1 else None) or "ZHI:ZI"
    year_code = ((pillars[0].get("zhi") or {}).get("name") if pillars else None) or "ZHI:SI"
    day = DAY_MASTER_PROFILES[day_code]
    month = MONTH_PROFILES[month_code]
    return {
        "subject": (facts.get("subject") or {}).get("display_name") or "",
        "gender": (facts.get("subject") or {}).get("gender") or "male",
        "birth": (facts.get("subject") or {}).get("birth") or {},
        "pillars": pillars,
        "day_code": day_code,
        "month_code": month_code,
        "year_code": year_code,
        "day": day,
        "month": month,
        "classic": daymaster_classic(day["char"]),
        "tiaohou": tiaohou_combo(day["char"], month["char"]),
        "zodiac": ZODIAC_PROFILES[year_code],
        "wuxing": list((facts.get("analysis_facts") or {}).get("wuxing") or []),
        "shensha": dict((facts.get("analysis_facts") or {}).get("shensha") or {}),
        "luck": [x for x in facts.get("luck_cycles") or [] if not x.get("is_pre_luck")],
    }


def _pillar_matrix(v: dict) -> str:
    pillars = v["pillars"]
    labels = "".join(f'<div class="matrix-head">{_e(p.get("label"))}</div>' for p in pillars)

    def cells(render) -> str:
        return "".join(f'<div class="matrix-cell">{render(p, i)}</div>' for i, p in enumerate(pillars))

    rows = [
        ("天干", cells(lambda p, _i: (
            f'<b class="big-glyph" style="color:{ELEMENT_COLORS.get((p.get("gan") or {}).get("wuxing"), "#292824")}">{_e((p.get("gan") or {}).get("name_label"))}</b>'
            f'<span>{_e((p.get("gan") or {}).get("shishen_label"))}</span>'
        ))),
        ("地支", cells(lambda p, _i: (
            f'<b class="big-glyph" style="color:{ELEMENT_COLORS.get((p.get("zhi") or {}).get("wuxing"), "#292824")}">{_e((p.get("zhi") or {}).get("name_label"))}</b>'
        ))),
        ("藏干十神", cells(lambda p, _i: "<br>".join(
            f'{_e(x.get("name_label"))} {_e(x.get("shishen_label"))}' for x in (p.get("zhi") or {}).get("hidden_gans") or []
        ))),
        ("地势", cells(lambda p, _i: (
            f'日主 {_e((p.get("daygan_dishi") or {}).get("label"))}<br>自坐 {_e((p.get("zizuo_dishi") or {}).get("label"))}'
        ))),
        ("纳音", cells(lambda p, _i: _e((p.get("nayin") or {}).get("label")))),
        ("神煞", cells(lambda p, _i: "<br>".join(
            _e(x.get("name")) for x in v["shensha"].get(p.get("key"), [])[:5]
        ) or "—")),
    ]
    return f'<div class="chart-matrix"><div class="matrix-corner">四柱</div>{labels}' + "".join(
        f'<div class="row-label">{label}</div>{content}' for label, content in rows
    ) + "</div>"


def _luck_matrix(cycles: list[dict]) -> str:
    rows = []
    for cycle in cycles[:8]:
        years = list(cycle.get("years") or [])[:10]
        year_cells = "".join(
            f'<div class="year-cell"><b>{_e(y.get("ganzhi"))}</b><span>{_e(y.get("year"))}</span></div>'
            for y in years
        )
        rows.append(
            f'<div class="cycle-name"><b>{_e(cycle.get("name"))}</b><span>{_e(cycle.get("start_year"))}–{_e(cycle.get("end_year"))}</span>'
            f'<em>{_e((cycle.get("gan_shishen") or {}).get("label"))} · {_e((cycle.get("zhi_shishen") or {}).get("label"))}</em></div>'
            f'<div class="year-row">{year_cells}</div>'
        )
    return '<div class="luck-matrix">' + "".join(rows) + "</div>"


def _radar_svg(items: list[dict], texture_href: str) -> str:
    order = ["WUXING:MU", "WUXING:HUO", "WUXING:TU", "WUXING:JIN", "WUXING:SHUI"]
    names = {"WUXING:MU":"木", "WUXING:HUO":"火", "WUXING:TU":"土", "WUXING:JIN":"金", "WUXING:SHUI":"水"}
    colors = {
        "WUXING:MU": "#4f7c64",
        "WUXING:HUO": "#b84a3a",
        "WUXING:TU": "#b58b52",
        "WUXING:JIN": "#7d8992",
        "WUXING:SHUI": "#3e6176",
    }
    values = {x.get("code"): float(x.get("percent") or 0) for x in items}
    cx, cy, radius = 210, 210, 136

    def pt(index: int, scale: float) -> tuple[float, float]:
        angle = math.radians(-90 + index * 72)
        return cx + math.cos(angle) * radius * scale, cy + math.sin(angle) * radius * scale

    rings = []
    for scale in (.25, .5, .75, 1):
        rings.append(" ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, scale) for i in range(5))))
    maximum = max([values.get(x, 0) for x in order] + [0])
    # Use a stable percentage scale instead of stretching the strongest item
    # to the rim.  This keeps the polygon faithful to the underlying values.
    scale_max = max(50.0, math.ceil(maximum / 10) * 10)

    def data_scale(code: str) -> float:
        return max(0.0, min(1.0, values.get(code, 0) / scale_max))

    full_polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, 1) for i in range(5)))
    polygon = " ".join(
        f"{x:.1f},{y:.1f}" for x, y in (
            pt(i, data_scale(code)) for i, code in enumerate(order)
        )
    )
    labels = []
    nodes = []
    for i, code in enumerate(order):
        data_x, data_y = pt(i, data_scale(code))
        x, y = pt(i, 1.25)
        color = colors[code]
        nodes.append(f'<circle cx="{data_x:.1f}" cy="{data_y:.1f}" r="4.5" fill="{color}"/>')
        labels.append(
            f'<g class="radar-label"><rect x="{x - 30:.1f}" y="{y - 18:.1f}" width="60" height="46" rx="5"/>'
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle"><tspan>{names[code]}</tspan>'
            f'<tspan x="{x:.1f}" dy="20">{values.get(code, 0):.1f}%</tspan></text></g>'
        )
    return f'''<svg class="data-radar" viewBox="0 0 420 420" aria-label="五行力量图">
      <defs><clipPath id="radar-data-clip"><polygon points="{polygon}"/></clipPath></defs>
      <g class="radar-color-field" clip-path="url(#radar-data-clip)">
        <polygon class="radar-data-paper" points="{full_polygon}"/>
        <image class="radar-watercolor" href="{_e(texture_href)}" x="74" y="74" width="272" height="272" preserveAspectRatio="none"/>
      </g>
      <g class="radar-grid">{''.join(f'<polygon points="{ring}"/>' for ring in rings)}
      {''.join(f'<line x1="{cx}" y1="{cy}" x2="{pt(i,1)[0]:.1f}" y2="{pt(i,1)[1]:.1f}"/>' for i in range(5))}</g>
      <polygon class="radar-data-outline" points="{polygon}"/>{''.join(nodes)}<circle class="radar-center" cx="{cx}" cy="{cy}" r="4"/>
      <g class="radar-text">{''.join(labels)}</g></svg>'''


def _wuxing_note(items: list[dict]) -> str:
    ranked = sorted(items, key=lambda x: float(x.get("percent") or 0), reverse=True)
    if not ranked:
        return "等待五行力量数据。"
    leading = _join_cn([str(item.get("label") or "") for item in ranked[:2]])
    lighter = _join_cn([str(item.get("label") or "") for item in ranked[-2:]])
    return (
        f'{ranked[0].get("label")}最显，约 {float(ranked[0].get("percent") or 0):.1f}%；'
        f'{ranked[-1].get("label")}相对收敛，约 {float(ranked[-1].get("percent") or 0):.1f}%。'
        f"主要分量落在{leading}，{lighter}在整体中的占比较轻。"
    )


def _chart_summary(v: dict) -> str:
    visible = []
    for pillar in v["pillars"]:
        gan = pillar.get("gan") or {}
        god = gan.get("shishen_label")
        if god and god != "日主":
            visible.append(f'{pillar.get("label")}{gan.get("name_label")}{god}')
    stem_line = _join_cn(visible)
    return (
        f'{v["day"]["char"]}{v["day"]["element"]}生于{v["month"]["char"]}月，{v["month"]["tagline"]}。'
        + (f"天干另见{stem_line}，构成原盘最先显出的关系线索。" if stem_line else "")
    )


def _luck_summary(cycles: list[dict]) -> str:
    visible = cycles[:3]
    if not visible:
        return "岁运自出生之后渐次展开，十年气象与逐年变化彼此叠加。"
    first = visible[0]
    following = _join_cn([str(item.get("name") or "") for item in visible[1:]])
    tail = f"，随后{following}相承" if following else ""
    return (
        f'{first.get("name")}大运始于{first.get("start_year")}年{tail}。'
        "十年气象有其主调，流年则让具体议题在不同年份显露轻重。"
    )


TIME_CONTEXT = {
    "子": "深夜",
    "丑": "夜深将晓",
    "寅": "黎明",
    "卯": "日出前后",
    "辰": "清晨",
    "巳": "上午",
    "午": "正午",
    "未": "午后",
    "申": "傍晚前",
    "酉": "日落前后",
    "戌": "入夜",
    "亥": "夜晚",
}


def _gan_presence(v: dict, gan_name: str) -> tuple[str, str]:
    for pillar in v["pillars"]:
        if (pillar.get("gan") or {}).get("name_label") == gan_name:
            return "原盘透出", "visible"
    for pillar in v["pillars"]:
        hidden = (pillar.get("zhi") or {}).get("hidden_gans") or []
        if any(item.get("name_label") == gan_name for item in hidden):
            return "藏于地支", "hidden"
    return "原盘未见", "absent"


def _symbolic_reading(v: dict) -> dict[str, str]:
    ranked = sorted(v["wuxing"], key=lambda item: float(item.get("percent") or 0), reverse=True)
    leading = ranked[0] if ranked else {"label": "五行", "percent": 0}
    second = ranked[1] if len(ranked) > 1 else {"label": "", "percent": 0}
    finish = {"木": "成林", "火": "照野", "土": "承形", "金": "成骨", "水": "通脉"}
    title = f'{leading.get("label")}势居前，{second.get("label")}{finish.get(str(second.get("label")), "相随")}'
    pillars = "、".join(
        str(pillar.get("ganzhi") or "")
        or f'{(pillar.get("gan") or {}).get("name_label", "")}{(pillar.get("zhi") or {}).get("name_label", "")}'
        for pillar in v["pillars"]
    )
    hour = ((v["pillars"][3].get("zhi") or {}).get("name_label") if len(v["pillars"]) > 3 else "") or ""
    stems = {(pillar.get("gan") or {}).get("name_label") for pillar in v["pillars"]}
    sky_note = (
        "天干没有丙火，且巳时属于白昼，所以画面只用明亮天光表达时间，不另外画出太阳或月亮。"
        if "丙" not in stems and hour in "巳午未申"
        else "天空遵循原盘天干与出生时段取象，不额外添加无关的天体与符号。"
    )
    gods = "、".join(v["tiaohou"].get("primary_gods") or [])
    return {
        "title": title,
        "origin": (
            f"原盘{pillars}，生在{v['month']['char']}月{v['month']['season']}，时支{hour}对应{TIME_CONTEXT.get(hour, '当时天光')}。"
            f"画面因此采用{v['tiaohou']['climate_tone']}的整体气息。{sky_note}"
        ),
        "elements": (
            f'{leading.get("label")}约占{float(leading.get("percent") or 0):.1f}%，成为画面的主色与主势；'
            f'{second.get("label")}约占{float(second.get("percent") or 0):.1f}%，转化为山石的骨架。'
            "其余五行按比例退为土坡、草木与细微湿痕，不用面积相等的装饰性拼贴。"
        ),
        "balance": (
            f"此局气势偏暖偏燥，但调候并不等于简单增加水景。《穷通宝鉴》先看{gods}的配合："
            "让火有所承续、让结构能够成材；水只保留为岩隙中的微小湿意，避免喧宾夺主。"
        ),
        "aesthetic": (
            "左页以雾白、远山和宣纸肌理留出呼吸，右页让暖色矿脉、银灰山骨和一线绿意集中显形。"
            "这是一种由静入动、由气候走向结构的观看顺序。"
        ),
    }


def _tiaohou_cards(v: dict) -> str:
    cards = []
    gods = list(v["tiaohou"].get("primary_gods") or [])
    explains = list(v["tiaohou"].get("god_explanations") or [])
    for index, gan in enumerate(gods):
        status, status_class = _gan_presence(v, gan)
        explanation = explains[index] if index < len(explains) else "用于调整寒暖燥湿的先后关系。"
        cards.append(
            f'<div class="god-card {status_class}"><b>{_e(gan)}</b><div><strong>{_e(status)}</strong><p>{_e(explanation)}</p></div></div>'
        )
    return "".join(cards)


def _tiaohou_status(v: dict) -> str:
    parts = []
    for gan in list(v["tiaohou"].get("primary_gods") or []):
        status, _ = _gan_presence(v, gan)
        parts.append(f"{gan}{status}")
    cautions = []
    for gan in list(v["tiaohou"].get("caution_gods") or []):
        status, _ = _gan_presence(v, gan)
        cautions.append(f"{gan}{status}")
    result = "；".join(parts) + "。"
    if cautions:
        result += "原文提醒谨慎看待" + "、".join(cautions) + "，要结合位置与强弱，不作机械增补。"
    return result


PILLAR_REALMS = {
    "year": "年柱更接近早期家庭环境、成长底色，以及别人刚认识你时较容易看到的外层表现。",
    "month": "月柱更接近成长与工作环境，也常反映你面对规则、协作和现实任务时的习惯。",
    "day": "日柱是自我与日常生活的中心；日支还关系到亲密相处、居家节奏与身体感受。",
    "hour": "时柱更接近长期计划、成果输出、晚些时候的发展，以及你想把自己带向哪里。",
}


def _stem_case_page(pillar: dict, profile: dict, page: int, asset_prefix: str) -> str:
    gan = pillar.get("gan") or {}
    key = str(pillar.get("key") or "")
    role = "日主" if key == "day" else str(gan.get("shishen_label") or "")
    role_text = (
        "这里的丁就是日主，是整张命盘观察十神关系的参照点。"
        if key == "day"
        else f"相对本盘日主而言，它表现为{role}；这说明它在这个位置更常借由‘{role}’所代表的现实议题被看见。"
    )
    side = "verso" if page % 2 == 0 else "recto"
    return f'''<article class="page {side} ganzhi-card stem-card" data-page="{page}">
      <header>干支名片 · {_e(pillar.get('label'))}天干</header><div class="ganzhi-heading"><div><small>{_e(profile['yin_yang'])}{_e(profile['element'])}</small><h2>{_e(profile['char'])}</h2><h3>{_e(profile['title'])}</h3></div><img src="{asset_prefix}/stems/{_e(profile['slug'])}-v2.png" alt="{_e(profile['char'])}天干免抠意象插图"></div>
      <section><b>这个字在说什么</b><p>{_e(profile['essence'])}</p></section>
      <section><b>落到现实生活</b><p>{_e(profile['life'])}</p></section>
      <section class="case-position"><b>在本盘的位置</b><p>{_e(profile['char'])}落在{_e(pillar.get('label'))}天干。{_e(PILLAR_REALMS[key])}{_e(role_text)}</p></section>
      <aside><b>需要留意</b>{_e(profile['balance'])}</aside><footer>{page:02d}</footer>
    </article>'''


def _branch_case_page(pillar: dict, profile: dict, page: int, asset_prefix: str) -> str:
    zhi = pillar.get("zhi") or {}
    key = str(pillar.get("key") or "")
    hidden = list(zhi.get("hidden_gans") or [])
    hidden_text = "、".join(
        f"{item.get('name_label')}{item.get('shishen_label')}" for item in hidden if item.get("name_label")
    ) or "无藏干资料"
    main = hidden[0] if hidden else {}
    side = "verso" if page % 2 == 0 else "recto"
    return f'''<article class="page {side} ganzhi-card branch-card" data-page="{page}">
      <header>干支名片 · {_e(pillar.get('label'))}地支</header><div class="ganzhi-heading"><div><small>{_e(profile['season'])} · {_e(profile['yin_yang'])}{_e(profile['element'])}</small><h2>{_e(profile['char'])}</h2><h3>{_e(profile['title'])}</h3></div><img src="{asset_prefix}/branches/{_e(profile['slug'])}-v2.png" alt="{_e(profile['char'])}地支免抠意象插图"></div>
      <section><b>这个字在说什么</b><p>{_e(profile['essence'])}</p></section>
      <section><b>落到现实生活</b><p>{_e(profile['life'])}</p></section>
      <section class="case-position"><b>在本盘的位置</b><p>{_e(profile['char'])}落在{_e(pillar.get('label'))}地支。{_e(PILLAR_REALMS[key])}本气是{_e(main.get('name_label'))}{_e(main.get('shishen_label'))}；完整藏干为{_e(hidden_text)}。</p></section>
      <aside><b>需要留意</b>{_e(profile['balance'])}</aside><footer>{page:02d}</footer>
    </article>'''


def _ganzhi_case_spreads(v: dict, asset_prefix: str) -> str:
    pages: list[str] = []
    page_number = 10
    for pillar in v["pillars"]:
        gan_code = str((pillar.get("gan") or {}).get("name") or "")
        zhi_code = str((pillar.get("zhi") or {}).get("name") or "")
        pages.append(_stem_case_page(pillar, STEM_ARCHETYPES[gan_code], page_number, asset_prefix))
        pages.append(_branch_case_page(pillar, BRANCH_ARCHETYPES[zhi_code], page_number + 1, asset_prefix))
        page_number += 2
    return "".join(
        f'<section class="spread ganzhi-spread" data-spread="{7 + index // 2}">{pages[index]}{pages[index + 1]}</section>'
        for index in range(0, len(pages), 2)
    )


def build_opening_html_v2(
    facts: dict,
    *,
    asset_prefix: str = "../../../assets/mingshu/illustrations",
    ganzhi_asset_prefix: str = "../../../assets/mingshu/ganzhi",
    font_prefix: str = "../../../assets/fonts",
    symbolic_image: str | None = None,
) -> str:
    v = _view(facts)
    cover = f"{asset_prefix}/covers/cover-celestial-v1.png"
    usage_bg = f"{asset_prefix}/layout/reading-guide-v3.png"
    greeting_bg = f"{asset_prefix}/layout/opening-message-v3.png"
    wuxing_bg = f"{asset_prefix}/layout/wuxing-compass-v3-clear.png"
    wuxing_texture = f"{asset_prefix}/layout/wuxing-watercolor-field-v1.png"
    day_image = f"{asset_prefix}/{daymaster_asset(v['day_code'], v['gender'])}"
    month_image = f"{asset_prefix}/seasons/{v['month']['asset']}"
    zodiac_image = f"{asset_prefix}/zodiac/{v['zodiac']['slug']}-v1.png"
    symbolic_image = symbolic_image or f"{asset_prefix}/cases/ding-si-symbolic-landscape-v1.png"
    symbolic_copy = _symbolic_reading(v)
    primary_gods = "、".join(v["tiaohou"].get("primary_gods") or [])
    ganzhi_spreads = _ganzhi_case_spreads(v, ganzhi_asset_prefix)
    birth = v["birth"]
    birth_line = f'{birth.get("year", "—")}.{birth.get("month", "—"):0>2}.{birth.get("day", "—"):0>2} · {"男" if v["gender"] == "male" else "女"}'

    spreads = f'''
    <section class="spread" data-spread="1"><article class="page blank" aria-label="封面左侧留空"></article>
      <article class="page cover" data-page="cover"><img src="{cover}" alt="命书封面山水底图"><div class="cover-copy"><small>四柱 · 五行 · 岁运 · 人生专题</small><h1>命书</h1><p>以古老的时间语言，照见当下的选择</p><div class="cover-name"><span data-cover-name>{_e(v['subject'])}</span><em>{_e(birth_line)}</em></div></div></article></section>
    <section class="spread" data-spread="2"><article class="page usage toc-page" data-page="inside-cover"><img class="page-bg" src="{usage_bg}" alt="书房与线装书"><header>目录</header>
      <div class="toc-copy"><small>CONTENTS</small><h2>循序读懂这张命盘</h2>
        <ol><li><b>开篇与原盘</b><span>寄语 · 四柱 · 大运流年 · 五行 · 日主 · 月令 · 生肖</span><em>01—07</em></li>
        <li><b>干支名片</b><span>逐一认识原盘八个位置上的天干与地支</span><em>09—17</em></li>
        <li><b>调候分析</b><span>命局取象 · 古籍原文 · 寒暖燥湿 · 调候用神</span><em>19—23</em></li>
        <li><b>干支作用</b><span>合 · 冲 · 刑 · 穿害 · 暗合，以及原盘实际成立关系</span><em>24—30</em></li>
        <li><b>十神分析</b><span>十神含义 · 力量占比 · 一柱一页定位 · 冲合后的现实影响</span><em>31—42</em></li>
        <li><b>神煞分析</b><span>本盘九种神煞 · 各自含义 · 对命主的实际影响</span><em>43—50</em></li>
        <li><b>格局分析</b><span>主格局候选 · 二级结构 · 格局用神 · 大运出现时机 · 职业发挥</span><em>51—59</em></li>
        <li><b>五行喜忌</b><span>格局与调候合参 · 五行总表 · 十天干细分 · 原盘状态</span><em>61—66</em></li>
        <li><b>大运流年</b><span>九步大运总势 · 每步双页解析 · 1998—2087流年分析</span><em>67—179</em></li>
        <li><b>专项报告</b><span>性格 · 事业 · 学业 · 感情婚姻 · 身心节律 · 六亲 · 风险与应对</span><em>181—227</em></li>
        <li><b>结语</b><span>全书主线回望 · 写给命主的最后寄语</span><em>229—231</em></li></ol>
      </div><footer>目录</footer></article>
      <article class="page greeting" data-page="1"><img class="page-bg" src="{greeting_bg}" alt="山路朝日与飞鹤"><header>首页寄语</header><div class="couplet"><p>知来处而不困于来处</p><p>见天时仍自择其前程</p></div><div class="greeting-note">愿这本书帮你辨认来路，也为下一步留出自由。</div><footer>01</footer></article></section>
    <section class="spread" data-spread="3"><article class="page chart" data-page="2"><header>原盘 · 出生时刻的结构</header><h2>四柱全盘</h2><p class="deck">{_e(_chart_summary(v))}</p>{_pillar_matrix(v)}<footer>02</footer></article>
      <article class="page luck" data-page="3"><header>大运流年 · 十年与一年的叠加</header><h2>十年一程，逐年展开</h2><p class="deck">{_e(_luck_summary(v['luck']))}</p>{_luck_matrix(v['luck'])}<footer>03</footer></article></section>
    <section class="spread" data-spread="4"><article class="page wuxing" data-page="4"><img class="page-bg" src="{wuxing_bg}" alt="国风五行意象底图"><header>五行 · 力量分布</header><h2>五气各有位置</h2><div class="radar-plate">{_radar_svg(v['wuxing'], wuxing_texture)}</div><div class="wuxing-note"><b>力量重心</b><span>{_e(_wuxing_note(v['wuxing']))}</span></div><footer>04</footer></article>
      <article class="page daymaster" data-page="5"><header>日主 · 自我视角</header><div class="day-copy"><small>{_e(v['day']['element'])}之象</small><h2>{_e(v['day']['char'])}{_e(v['day']['element'])}日主</h2><h3>{_e(v['day']['metaphor'])}</h3><h4>{_e(v['day']['tagline'])}</h4><p>{_e(v['day']['intro'])}</p><div class="day-guides"><span><b>顺势</b>{_e(v['day']['strength'])}</span><span><b>平衡</b>{_e(v['day']['balance'])}</span></div><aside class="classic-note"><b>《滴天髓》</b><blockquote>{_e(v['classic']['verse'])}</blockquote><p>{_e(v['classic']['plain'])}</p></aside></div><img class="day-person" src="{day_image}" alt="{_e(v['day']['char'])}{_e(v['day']['element'])}日主人物"><footer>05</footer></article></section>
    <section class="spread" data-spread="5"><article class="page month" data-page="6"><header>月令 · 出生时的季节底色</header><div class="month-copy"><small>{_e(v['month']['season'])}</small><h2>{_e(v['month']['char'])}月</h2><h3>{_e(v['month']['tagline'])}</h3><p>{_e(v['month']['intro'])}</p><p>{_e(v['month']['reading'])}</p></div><img class="month-art" src="{month_image}" alt="{_e(v['month']['image'])}"><footer>06</footer></article>
      <article class="page zodiac" data-page="7"><header>生肖 · 年份的文化记忆</header><h2>生肖{_e(v['zodiac']['animal'])}</h2><h3>{_e(v['zodiac']['tagline'])}</h3><img src="{zodiac_image}" alt="年画风生肖{_e(v['zodiac']['animal'])}"><p>{_e(v['zodiac']['intro'])}</p><aside>生肖只占四柱中的一字，适合作为文化入口，不单独判断性格与关系。</aside><footer>07</footer></article></section>
    <section class="spread" data-spread="6"><article class="page section-blank" data-page="8" aria-label="章节扉页左侧留空"></article>
      <article class="page chapter-divider" data-page="9"><div class="chapter-frame"><small>第二章</small><h2>干支名片</h2><p>识其本象<br>再看落位</p><i>八个位置逐一展开<br>同一个字也因落点而不同</i></div><footer>09</footer></article></section>
    {ganzhi_spreads}
    <section class="spread" data-spread="11"><article class="page section-blank" data-page="18" aria-label="章节扉页左侧留空"></article>
      <article class="page chapter-divider" data-page="19"><div class="chapter-frame"><small>第三章</small><h2>调候分析</h2><p>察四时寒暖<br>观一局燥湿</p><i>气候不是吉凶<br>是理解结构的另一把尺</i></div><footer>19</footer></article></section>
    <section class="spread symbolic-spread" data-spread="12"><img class="symbolic-art" src="{symbolic_image}" alt="{_e(v['day']['char'])}日{_e(v['month']['char'])}月命局五行取象风景">
      <article class="page symbolic-copy" data-page="20"><header>调候 · 命局取象</header><div class="symbolic-panel"><small>{_e(v['month']['season'])} · {_e(TIME_CONTEXT.get(((v['pillars'][3].get('zhi') or {}).get('name_label') if len(v['pillars']) > 3 else ''), '出生时段'))}</small><h2>{_e(symbolic_copy['title'])}</h2><p>{_e(symbolic_copy['origin'])}</p><p>{_e(symbolic_copy['elements'])}</p><p>{_e(symbolic_copy['balance'])}</p><p class="aesthetic-note">{_e(symbolic_copy['aesthetic'])}</p></div><footer>20</footer></article>
      <article class="page symbolic-view" data-page="21"><footer>21</footer></article></section>
    <section class="spread" data-spread="13"><article class="page qiongtong" data-page="22"><header>调候 · 古籍原文</header><small>{_e(v['tiaohou']['season'])} · {_e(v['tiaohou']['climate_tone'])}</small><h2>{_e(v['month']['char'])}月{_e(v['day']['char'])}火</h2><p class="deck">原文保留时代语境，下面只提炼与寒暖燥湿有关的阅读线索。</p><div class="classic-columns">{_e(v['tiaohou']['source_excerpt'])}</div><aside class="plain-reading"><b>今天怎么读</b><p>{_e(v['tiaohou']['plain'])}</p></aside><footer>22</footer></article>
      <article class="page tiaohou-gods" data-page="23"><header>调候 · 用神次序</header><small>{_e(v['tiaohou']['climate'])}</small><h2>{_e(primary_gods)}为先</h2><p class="deck">这里的“用”先处理季节气候，再看原盘是否已有、是否过量。</p><div class="god-cards">{_tiaohou_cards(v)}</div><aside class="case-check"><b>本盘实际情况</b><p>{_e(_tiaohou_status(v))}</p></aside><p class="reading-boundary">调候只回答“这个季节最需要怎样的温度与湿度”。完整喜忌还要与格局、强弱及干支关系一起阅读。</p><footer>23</footer></article></section>'''
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_e(v['subject'] or '命主')} · 命书开篇</title><style>{_css(font_prefix)}</style></head>
    <body><aside class="proof-tools"><label>封面姓名（可选）<input data-testid="cover-name-input" value="{_e(v['subject'])}" placeholder="留空则隐藏"></label><span>真实 A5 跨页 · 左装</span></aside><main>{spreads}</main>
    {ELEMENT_COLOR_SCRIPT}<script>const input=document.querySelector('[data-testid="cover-name-input"]'),name=document.querySelector('[data-cover-name]');function sync(){{name.textContent=input.value;name.parentElement.classList.toggle('empty',!input.value.trim())}}input.addEventListener('input',sync);sync();</script></body></html>'''


def _css(font_prefix: str) -> str:
    return f'''
@font-face{{font-family:BookSerif;src:url('{font_prefix}/NotoSerifSC-Regular.ttf')}}
@font-face{{font-family:BookSans;src:url('{font_prefix}/NotoSansSC-Regular.ttf')}}
@font-face{{font-family:BookBrush;src:url('{font_prefix}/MaShanZheng-Regular.ttf')}}
@page{{size:296mm 210mm;margin:0}}
:root{{--paper:#f4efe4;--ink:#292824;--muted:#766d60;--gold:#a57d39;--red:#a7362b;--jade:#315d51;--line:#d5c39f}}
*{{box-sizing:border-box}}body{{margin:0;background:#282725;color:var(--ink);font-family:BookSerif,serif}}.proof-tools{{position:sticky;top:0;z-index:20;height:54px;background:#1d1d1c;color:#ddd;display:flex;align-items:center;justify-content:center;gap:36px;font:13px BookSans;padding:0 20px}}.proof-tools label{{display:flex;align-items:center;gap:12px}}.proof-tools input{{width:210px;border:0;border-bottom:1px solid #8c7b5e;background:#1d1d1c;color:#fff;padding:7px 4px;outline:none}}main{{padding:26px 0 60px}}.spread{{width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;display:flex;filter:drop-shadow(0 12px 24px #111)}}.page{{position:relative;flex:0 0 50%;overflow:clip;contain:layout paint;background:var(--paper);padding:7.5% 8%;aspect-ratio:148/210}}.spread>.page:first-child:after{{content:'';position:absolute;right:0;top:0;bottom:0;width:1px;background:#d4ccbd}}.blank{{background:#292825}}.page-bg{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}header{{position:relative;z-index:5;font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px;text-align:left}}.recto header,.page[data-page='1'] header,.page[data-page='3'] header,.page[data-page='5'] header,.page[data-page='7'] header,.page[data-page='9'] header,.page[data-page='11'] header,.page[data-page='13'] header{{text-align:right}}footer{{position:absolute;z-index:6;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#827a6d}}.recto footer{{text-align:right}}.page h2{{font-size:31px;margin:24px 0 12px}}.deck{{font-size:12px;line-height:1.8;color:var(--muted);margin:0 0 18px}}
.cover{{padding:0;color:#f4eddd;text-align:center}}.cover>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}.cover-copy{{position:absolute;inset:0;padding-top:11%}}.cover-copy small{{font:11px BookSans;letter-spacing:.24em;color:#c9aa6c}}.cover h1{{font-size:92px;letter-spacing:.18em;text-indent:.18em;margin:17% 0 0;text-shadow:0 4px 14px #1c2220}}.cover h1:after{{content:'';display:block;width:108px;height:4px;background:#aa392d;margin:10px auto}}.cover p{{margin:13% 0 0;font-size:15px;letter-spacing:.12em}}.cover-name{{position:absolute;left:50%;bottom:11%;transform:translateX(-50%);min-width:190px;padding-top:11px;border-top:1px solid #cbb278}}.cover-name span{{display:block;font-size:20px;letter-spacing:.16em}}.cover-name em{{display:block;margin-top:4px;font:normal 9px BookSans;color:#cdb67d}}.cover-name.empty span{{display:none}}
.usage{{padding-top:7.5%}}.toc-page:after{{content:'';position:absolute;inset:0;background:linear-gradient(90deg,rgba(244,239,228,.97),rgba(244,239,228,.90) 78%,rgba(244,239,228,.64));z-index:1}}.toc-page header,.toc-page footer{{z-index:4}}.toc-copy{{position:relative;z-index:3;width:84%;margin:3% auto 0}}.toc-copy>small{{font:8px BookSans;color:var(--gold);letter-spacing:.25em}}.toc-copy h2{{font:24px BookSerif;margin:3px 0 7px;color:#262923}}.toc-copy ol{{padding:0;margin:0;list-style:none;counter-reset:toc}}.toc-copy li{{counter-increment:toc;position:relative;display:grid;grid-template-columns:32px 1fr 48px;grid-template-rows:auto auto;padding:5px 0 4px;border-top:1px solid rgba(165,125,57,.45)}}.toc-copy li:before{{content:'0' counter(toc);grid-row:1/3;font:14px BookSerif;color:var(--gold)}}.toc-copy b{{font-size:10.8px;font-weight:500}}.toc-copy span{{font:7px/1.28 BookSans;color:#6d675e;margin-top:1px;padding-right:8px}}.toc-copy em{{grid-column:3;grid-row:1/3;align-self:center;text-align:right;font:normal 8.5px BookSans;color:#8b6b39}}
.greeting{{padding:7.5% 6%}}.couplet{{position:relative;z-index:3;height:70%;display:flex;flex-direction:row-reverse;justify-content:center;gap:58px;padding-top:18%}}.couplet p{{writing-mode:vertical-rl;margin:0;font:37px/1.2 BookBrush;color:#26302c;letter-spacing:.11em}}.couplet p:last-child{{color:#8f3028}}.greeting-note{{position:absolute;z-index:3;bottom:12%;left:14%;right:14%;text-align:center;font-size:11px;letter-spacing:.12em;color:#514c43}}
.chart h2,.luck h2{{margin-bottom:4px}}.chart-matrix{{display:grid;grid-template-columns:56px repeat(4,1fr);border-top:1px solid var(--gold);border-left:1px solid var(--line);font:10px/1.55 BookSans}}.chart-matrix>*{{border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:7px 5px;text-align:center;min-width:0}}.matrix-corner,.matrix-head,.row-label{{background:#e9dfcd;color:#6c5a3d}}.matrix-head{{font:13px BookSerif}}.row-label{{display:grid;place-items:center;font-size:9px}}.matrix-cell span{{display:block;color:#9b6f2e}}.big-glyph{{display:block;font:35px/1.05 BookSerif;margin-bottom:2px}}.luck-matrix{{display:grid;grid-template-columns:86px 1fr;border-top:1px solid var(--gold)}}.cycle-name,.year-row{{border-bottom:1px solid var(--line);min-height:57px}}.cycle-name{{padding:8px 8px 5px 0}}.cycle-name b,.cycle-name span,.cycle-name em{{display:block}}.cycle-name b{{font-size:18px}}.cycle-name span{{font:9px BookSans;color:#777}}.cycle-name em{{font:normal 9px BookSans;color:#a17839}}.year-row{{display:grid;grid-template-columns:repeat(10,1fr)}}.year-cell{{display:grid;place-items:center;border-left:1px solid #e1d6c2;padding:5px 1px}}.year-cell b{{font-size:12px}}.year-cell span{{font:7px BookSans;color:#817a6f}}
.wuxing{{padding:7.5% 7%}}.wuxing h2{{position:relative;z-index:4;margin:14px 0 0;font-size:29px}}.radar-plate{{position:absolute;z-index:3;left:50%;top:20.5%;width:76%;aspect-ratio:1;transform:translateX(-50%);background:transparent}}.data-radar{{display:block;width:100%;height:100%;overflow:visible}}.radar-grid polygon,.radar-grid line{{fill:none;stroke:#9d793e;stroke-width:1;stroke-opacity:.68}}.radar-data-paper{{fill:#eadbbd;fill-opacity:.18}}.radar-watercolor{{opacity:.8}}.radar-data-outline{{fill:none;stroke:#7f6235;stroke-width:2.2}}.radar-center{{fill:#7f6235}}.radar-label rect{{fill:#fffdf8;fill-opacity:.94;stroke:#b18a4d;stroke-width:.8}}.radar-label text{{font:17px BookSerif;fill:#30332f}}.radar-label tspan+tspan{{font-size:12px;fill:#775f39}}.wuxing-note{{position:absolute;z-index:4;left:12%;right:12%;bottom:9.5%;display:grid;grid-template-columns:58px 1fr;background:rgba(244,239,228,.92);border-left:3px solid var(--gold);padding:10px 12px;font:10.5px/1.65 BookSans}}.wuxing-note b{{color:#8d6a35}}
.daymaster{{background:#f2e8d7}}.day-copy{{position:relative;z-index:3;width:70%;margin-top:4%}}.day-copy small{{font:10px BookSans;color:var(--gold);letter-spacing:.16em}}.day-copy h2{{font-size:36px;margin:3px 0 0}}.day-copy h3{{font-size:18px;margin:1px 0;color:#2d554c}}.day-copy h4{{font-weight:400;color:var(--red);margin:5px 0 8px}}.day-copy>p{{font-size:10.5px;line-height:1.62;margin:6px 0}}.day-guides{{display:grid;grid-template-columns:1fr 1fr;gap:7px;width:88%;margin:8px 0}}.day-guides span{{background:rgba(255,250,240,.72);padding:7px 8px;font:9px/1.5 BookSans}}.day-guides b{{display:block;color:var(--gold);margin-bottom:2px}}.classic-note{{width:88%;background:rgba(255,252,244,.92);border:1px solid #cbb58b;border-left:3px solid var(--red);padding:9px 11px;margin-top:8px}}.classic-note>b{{font-size:11px;color:#8d3029}}.classic-note blockquote{{font:13px/1.65 BookSerif;margin:5px 0;color:#292824}}.classic-note p{{font:9.4px/1.55 BookSans;margin:0;color:#5f594f}}.day-person{{position:absolute;right:0;bottom:0;width:49%;max-height:59%;object-fit:contain;object-position:right bottom}}
.month{{padding-bottom:0;background:#f4efe4}}.month-copy{{position:relative;z-index:3;background:#f4efe4;padding-bottom:14px}}.month-copy small{{display:block;margin-top:20px;font:10px BookSans;color:var(--gold);letter-spacing:.18em}}.month-copy h2{{font-size:43px;margin:3px 0}}.month-copy h3{{font-size:18px;color:var(--red);margin:0 0 10px}}.month-copy p{{font-size:11.5px;line-height:1.68;margin:6px 0}}.month-art{{position:absolute;left:0;right:0;bottom:0;width:100%;height:42%;object-fit:cover;border-top:5px solid #e6d9c3}}.month footer{{color:#f8f1e3;text-shadow:0 1px 2px #2c302d}}
.zodiac{{text-align:center;background:#f5ecdd}}.zodiac h2{{font-size:38px;margin:20px 0 0}}.zodiac h3{{margin:2px 0;color:var(--red);font-weight:400}}.zodiac>img{{width:64%;height:43%;object-fit:contain}}.zodiac>p{{font-size:11.5px;line-height:1.72;text-align:left;margin:3px 8%}}.zodiac aside{{font:10px/1.65 BookSans;text-align:left;margin:12px 8%;padding:11px 13px;border-left:3px solid var(--red);background:#fffaf0}}
.ganzhi-card{{padding-top:6.7%;background:linear-gradient(145deg,#f9f4e8,#eee3cf)}}.ganzhi-heading{{display:grid;grid-template-columns:1fr 46%;gap:18px;align-items:center;height:37%;overflow:hidden;border-bottom:1px solid var(--gold)}}.ganzhi-heading>*{{min-width:0;min-height:0}}.ganzhi-heading small{{font:11px BookSans;color:var(--gold);letter-spacing:.16em}}.ganzhi-heading h2{{font:76px/1 BookSerif;margin:8px 0 3px}}.ganzhi-heading h3{{font-size:18px;line-height:1.45;margin:0;color:var(--jade);font-weight:500}}.ganzhi-heading img{{display:block;width:100%;height:92%;max-height:92%;object-fit:contain;mix-blend-mode:normal;align-self:center}}.branch-card .ganzhi-heading{{grid-template-columns:46% 1fr}}.branch-card .ganzhi-heading>div{{order:2}}.branch-card .ganzhi-heading img{{order:1}}.ganzhi-card section{{padding:12px 0 10px;border-bottom:1px solid var(--line)}}.ganzhi-card section>b{{display:block;font-size:13px;color:var(--jade);margin-bottom:4px}}.ganzhi-card section p{{font:11.5px/1.72 BookSans;color:#4e4942;margin:0}}.ganzhi-card .case-position{{border-left:3px solid var(--gold);padding-left:12px;background:rgba(255,252,245,.55)}}.ganzhi-card aside{{margin-top:11px;font:10.8px/1.68 BookSans;color:#5f584e}}.ganzhi-card aside b{{color:var(--red);margin-right:8px}}.ganzhi-card footer{{font-size:12px}}
.section-blank{{background:#f3eddf;padding:0}}.chapter-divider{{padding:0;background:#203b34;color:#f1e6ce}}.chapter-frame{{position:absolute;inset:8%;border:1px solid #b89a60;outline:1px solid rgba(184,154,96,.45);outline-offset:-9px}}.chapter-frame small,.chapter-frame h2,.chapter-frame p,.chapter-frame i{{position:absolute;writing-mode:vertical-rl;white-space:nowrap;margin:0}}.chapter-frame small{{right:10%;bottom:10%;font:11px BookSans;letter-spacing:.3em;color:#c9ac73}}.chapter-frame h2{{right:22%;top:44%;transform:translateY(-50%);font:49px/1 BookBrush;letter-spacing:.14em}}.chapter-frame p{{right:48%;top:27%;font:20px/1.8 BookSerif;color:#e4d2ae;letter-spacing:.14em}}.chapter-frame i{{right:72%;top:13%;font:normal 10px/1.8 BookSans;color:#b9ad91;letter-spacing:.08em}}.chapter-divider footer{{color:#bda978}}
.symbolic-spread{{position:relative;overflow:hidden;background:#e9ddc6}}.symbolic-art{{position:absolute;z-index:0;inset:0;width:100%;height:100%;object-fit:cover}}.symbolic-spread .page{{z-index:1;background:transparent}}.symbolic-spread>.page:first-of-type:after{{display:none}}.symbolic-copy header{{background:rgba(243,236,220,.82);padding:9px 10px;border-bottom-color:#b7955a}}.symbolic-panel{{width:88%;margin-top:7%;padding:18px 19px;background:rgba(248,243,231,.91);border:1px solid rgba(157,121,62,.7);box-shadow:0 8px 24px rgba(77,54,30,.09)}}.symbolic-panel small{{font:9px BookSans;color:#9b7335;letter-spacing:.16em}}.symbolic-panel h2{{font-size:27px;margin:8px 0 11px}}.symbolic-panel p{{font-size:10.5px;line-height:1.72;margin:7px 0}}.symbolic-panel .aesthetic-note{{border-top:1px solid #cdb994;padding-top:8px;color:#665d50}}.symbolic-view footer{{color:#f6ead2;text-align:right;text-shadow:0 1px 3px #4c3625}}
.qiongtong,.tiaohou-gods{{background:#f0e6d3}}.qiongtong:before,.tiaohou-gods:before{{content:'';position:absolute;inset:4.7%;border:1px solid rgba(151,111,54,.42);pointer-events:none}}.qiongtong>small,.tiaohou-gods>small{{display:block;margin-top:17px;font:9px BookSans;color:#9a743d;letter-spacing:.14em}}.qiongtong h2,.tiaohou-gods h2{{margin:5px 0 7px;font-size:32px}}.qiongtong .deck,.tiaohou-gods .deck{{font-size:10px;line-height:1.6;margin-bottom:10px}}.classic-columns{{height:45%;padding:14px 14px;border-top:1px solid #af8b50;border-bottom:1px solid #af8b50;writing-mode:vertical-rl;text-orientation:mixed;font:12.3px/1.75 BookSerif;letter-spacing:.04em;overflow:hidden;background:rgba(255,251,241,.46)}}.plain-reading{{margin-top:12px;padding:10px 12px;background:#fffaf0;border-left:3px solid #9a3a2f}}.plain-reading b{{font-size:11px;color:#94382e}}.plain-reading p{{font:9.5px/1.58 BookSans;margin:4px 0 0}}.god-cards{{display:grid;gap:9px;margin-top:11px}}.god-card{{display:grid;grid-template-columns:62px 1fr;min-height:87px;background:rgba(255,251,241,.72);border:1px solid #ccb992}}.god-card>b{{display:grid;place-items:center;font-size:38px;color:#8f352d;border-right:1px solid #ccb992}}.god-card>div{{padding:10px 12px}}.god-card strong{{font:11px BookSans;color:#8c6c3a}}.god-card p{{font:10px/1.58 BookSans;margin:4px 0 0}}.god-card.visible{{border-color:#9d6c35}}.god-card.visible strong{{color:#2e5a4e}}.god-card.hidden strong{{color:#8e6333}}.god-card.absent strong{{color:#8e4038}}.case-check{{margin-top:13px;padding:11px 13px;border-top:1px solid #a88247;border-bottom:1px solid #a88247}}.case-check b{{font-size:12px;color:#2d554c}}.case-check p{{font:10px/1.65 BookSans;margin:5px 0}}.reading-boundary{{font:9.5px/1.6 BookSans;color:#756c5f;margin:12px 0}}
@media(max-width:800px){{.spread{{display:block;width:min(560px,calc(100vw - 24px));aspect-ratio:auto}}.page{{width:100%}}.blank{{display:none}}.proof-tools{{justify-content:flex-start;overflow:auto}}.proof-tools span{{display:none}}}}
@media print{{body{{background:#fff}}.proof-tools{{display:none}}main{{padding:0}}.spread{{display:flex!important;width:296mm;height:210mm;margin:0;filter:none;break-after:page;break-inside:avoid}}.spread:last-child{{break-after:auto}}.page{{flex:0 0 147.9mm;width:147.9mm;height:210mm;aspect-ratio:auto}}.blank{{display:block}}}}
'''


def write_opening_html_v2(facts: dict, output: str | Path, **kwargs: Any) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_opening_html_v2(facts, **kwargs), encoding="utf-8")
    return path


def write_opening_manifest_v2(facts: dict, output: str | Path) -> Path:
    v = _view(facts)
    payload = {
        "schema_version": "mingshu-opening/2.0",
        "source": facts.get("source"),
        "subject": facts.get("subject"),
        "loaded_profiles": {"day_master": v["day_code"], "month": v["month_code"], "zodiac": v["year_code"]},
        "spreads": [["blank", "cover"], ["inside_cover", 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11], [12, 13], [14, 15], [16, 17], [18, 19], [20, 21], [22, 23]],
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
