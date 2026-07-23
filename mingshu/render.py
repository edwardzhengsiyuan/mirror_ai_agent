"""Dependency-free A5 editorial proof renderer.

This is intentionally a proof of the page system, not a final narrative
generator. Deterministic chart facts are rendered as real visuals; sections
that still require validated LLM copy are shown as clearly labelled content
slots.
"""

from __future__ import annotations

import html
import math
from typing import Any, Iterable


ELEMENT_COLORS = {
    "WUXING:MU": "#4F7C64",
    "WUXING:HUO": "#B84A3A",
    "WUXING:TU": "#B58B52",
    "WUXING:JIN": "#87929B",
    "WUXING:SHUI": "#3E6176",
}

INK = "#18221f"
MUTED = "#6c736e"
PAPER = "#f5f0e6"
JADE = "#315f52"
CINNABAR = "#a64032"
GOLD = "#ad8750"

SECTION_LABELS = {
    "front_matter": "卷首",
    "chart": "排盘",
    "origin": "原局",
    "luck": "岁运",
    "special_topics": "专项",
    "appendix": "附录",
}


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _pillars(facts: dict) -> list[dict]:
    return list((facts.get("chart") or {}).get("pillars") or [])


def _wuxing_series(facts: dict) -> list[dict]:
    return list((((facts.get("visuals") or {}).get("wuxing_ratio") or {}).get("series") or []))


def _shishen_series(facts: dict) -> list[dict]:
    return list((((facts.get("visuals") or {}).get("shishen_ratio") or {}).get("series") or []))


def _cover_visual(facts: dict) -> str:
    pillars = _pillars(facts)
    chars = "".join(item.get("ganzhi", "") for item in pillars)
    display_name = ((facts.get("subject") or {}).get("display_name") or "命主")
    return f"""
      <div class="cover-art">
        <div class="cover-orbit orbit-one"></div>
        <div class="cover-orbit orbit-two"></div>
        <div class="cover-seal">{_e(chars[:2] or "命书")}</div>
        <div class="cover-kicker">MIRROR · PERSONAL CHART BOOK</div>
        <div class="cover-title">命书</div>
        <div class="cover-name">{_e(display_name)} · {_e(" · ".join(p.get("ganzhi", "") for p in pillars))}</div>
        <div class="cover-rule"></div>
        <div class="cover-caption">八字原局 · 大运流年 · 人生专项</div>
      </div>
    """


def _pillar_table(facts: dict) -> str:
    cells = []
    for pillar in _pillars(facts):
        hidden = " · ".join(
            f"{item.get('name_label')}{item.get('shishen_label')}"
            for item in (pillar.get("zhi") or {}).get("hidden_gans") or []
        )
        nayin = (pillar.get("nayin") or {}).get("label") or "—"
        cells.append(
            f"""
            <div class="pillar-card">
              <div class="pillar-label">{_e(pillar.get("label"))}</div>
              <div class="stem">{_e((pillar.get("gan") or {}).get("name_label"))}</div>
              <div class="ten-god">{_e((pillar.get("gan") or {}).get("shishen_label"))}</div>
              <div class="branch">{_e((pillar.get("zhi") or {}).get("name_label"))}</div>
              <div class="hidden">{_e(hidden)}</div>
              <div class="nayin">{_e(nayin)}</div>
            </div>
            """
        )
    return f"""
      <div class="visual-title">四柱结构</div>
      <div class="pillar-grid">{''.join(cells)}</div>
      <div class="visual-note">天干显于外，地支藏于内；十神标示关系，纳音补充每一柱的文化意象。</div>
    """


def _donut(facts: dict) -> str:
    series = _wuxing_series(facts)
    circles = []
    offset = 0.0
    legend = []
    for item in series:
        pct = float(item.get("percent") or 0)
        color = ELEMENT_COLORS.get(item.get("code"), GOLD)
        circles.append(
            f'<circle cx="120" cy="120" r="82" pathLength="100" '
            f'fill="none" stroke="{color}" stroke-width="28" '
            f'stroke-dasharray="{pct:.2f} {100-pct:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" />'
        )
        offset += pct
        legend.append(
            f'<div class="legend-row"><i style="background:{color}"></i>'
            f'<span>{_e(item.get("label"))}</span><b>{pct:.1f}%</b></div>'
        )
    strongest = max(series, key=lambda item: item.get("percent", 0), default={})
    return f"""
      <div class="visual-title">五行力量比例</div>
      <div class="donut-wrap">
        <svg viewBox="0 0 240 240" class="donut-svg">
          <circle cx="120" cy="120" r="82" fill="none" stroke="#ded6c8" stroke-width="28" />
          <g transform="rotate(-90 120 120)">{''.join(circles)}</g>
          <text x="120" y="112" text-anchor="middle" class="donut-small">力量重心</text>
          <text x="120" y="142" text-anchor="middle" class="donut-big">{_e(strongest.get("label"))}</text>
        </svg>
        <div class="chart-legend">{''.join(legend)}</div>
      </div>
      <div class="visual-note">比例来自脚本力量计算；“少”不等于“没有”，也不直接等于忌或凶。</div>
    """


def _bars(facts: dict) -> str:
    series = sorted(_shishen_series(facts), key=lambda item: item.get("percent", 0), reverse=True)
    rows = []
    for index, item in enumerate(series):
        pct = float(item.get("percent") or 0)
        cls = " emphasis" if index < 3 else ""
        rows.append(
            f"""
            <div class="bar-row{cls}">
              <span>{_e(item.get("label"))}</span>
              <div class="bar-track"><i style="width:{min(pct * 3.2, 100):.2f}%"></i></div>
              <b>{pct:.1f}%</b>
            </div>
            """
        )
    return f"""
      <div class="visual-title">十神力量排序</div>
      <div class="bar-chart">{''.join(rows)}</div>
      <div class="visual-note">横条按本盘力量排序；解读还要结合位置、透藏与相互作用。</div>
    """


def _relation_network(facts: dict) -> str:
    network = ((facts.get("visuals") or {}).get("origin_network") or {})
    pillars = network.get("pillars") or []
    relations = network.get("relations") or []
    x_positions = [66, 176, 286, 396]
    pillar_x = {p.get("key"): x_positions[index] for index, p in enumerate(pillars[:4])}
    paths = []
    chips = []
    for index, relation in enumerate(relations):
        members = relation.get("members") or []
        if len(members) < 2:
            continue
        x1 = pillar_x.get(members[0].get("pillar"), 66)
        x2 = pillar_x.get(members[1].get("pillar"), 396)
        y = 90 + index * 44
        color = CINNABAR if any(k in relation.get("label", "") for k in ("冲", "刑", "穿")) else JADE
        paths.append(
            f'<path d="M{x1} 210 C{x1} {y}, {x2} {y}, {x2} 210" '
            f'fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
        )
        chips.append(
            f'<text x="{(x1+x2)/2:.1f}" y="{y-5}" text-anchor="middle" '
            f'class="relation-label" fill="{color}">{_e(relation.get("label"))}</text>'
        )
    nodes = []
    for index, pillar in enumerate(pillars[:4]):
        x = x_positions[index]
        nodes.append(
            f'<circle cx="{x}" cy="230" r="28" fill="{PAPER}" stroke="{JADE}" stroke-width="2"/>'
            f'<text x="{x}" y="227" text-anchor="middle" class="node-gz">{_e(pillar.get("ganzhi"))}</text>'
            f'<text x="{x}" y="247" text-anchor="middle" class="node-label">{_e(pillar.get("label"))}</text>'
        )
    return f"""
      <div class="visual-title">原局干支作用图</div>
      <svg viewBox="0 0 460 300" class="relation-svg">
        {''.join(paths)}
        {''.join(chips)}
        {''.join(nodes)}
      </svg>
      <div class="relation-key"><span class="positive">合 / 会 / 半合</span><span class="tension">冲 / 刑 / 穿</span></div>
      <div class="visual-note">合会多见承接，冲刑穿多见张力；同一种关系落在不同柱位，也会连接不同的人生场景。</div>
    """


def _flow(facts: dict) -> str:
    series = _wuxing_series(facts)
    values = {item.get("code"): item for item in series}
    order = ["WUXING:MU", "WUXING:HUO", "WUXING:TU", "WUXING:JIN", "WUXING:SHUI"]
    points = []
    for index, code in enumerate(order):
        angle = math.radians(-90 + index * 72)
        x = 230 + math.cos(angle) * 116
        y = 150 + math.sin(angle) * 100
        item = values.get(code, {})
        points.append((code, x, y, item))
    arrows = []
    for index in range(5):
        _, x1, y1, _ = points[index]
        _, x2, y2, _ = points[(index + 1) % 5]
        arrows.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#82948b" stroke-width="2.2" marker-end="url(#arrow)"/>'
        )
    nodes = []
    for code, x, y, item in points:
        color = ELEMENT_COLORS[code]
        radius = 28 + min(float(item.get("percent") or 0), 40) * 0.28
        nodes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" opacity=".92"/>'
            f'<text x="{x:.1f}" y="{y-2:.1f}" text-anchor="middle" class="flow-name">{_e(item.get("label"))}</text>'
            f'<text x="{x:.1f}" y="{y+16:.1f}" text-anchor="middle" class="flow-value">{float(item.get("percent") or 0):.1f}%</text>'
        )
    return f"""
      <div class="visual-title">五行流通示意</div>
      <svg viewBox="0 0 460 300" class="flow-svg">
        <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#82948b"/></marker></defs>
        {''.join(arrows)}
        {''.join(nodes)}
      </svg>
      <div class="visual-note">圆的大小对应力量比例；箭头只表示相生阅读顺序，实际喜忌需结合格局与调候。</div>
    """


def _nayin_cards(facts: dict) -> str:
    cards = []
    for pillar in _pillars(facts):
        nayin = pillar.get("nayin") or {}
        knowledge = nayin.get("knowledge") or {}
        cards.append(
            f"""
            <div class="nayin-card">
              <div class="nayin-pillar">{_e(pillar.get("label"))} · {_e(pillar.get("ganzhi"))}</div>
              <h3>{_e(nayin.get("label"))}</h3>
              <div class="nayin-tag">{_e(knowledge.get("tagline"))}</div>
              <p>{_e(knowledge.get("introduction"))}</p>
            </div>
            """
        )
    return f"""
      <div class="visual-title">四柱纳音意象</div>
      <div class="nayin-grid">{''.join(cards)}</div>
      <div class="visual-note">纳音作为柱位意象的补充，不单独决定命局强弱、格局或吉凶。</div>
    """


def _timeline(facts: dict) -> str:
    series = list((((facts.get("visuals") or {}).get("dayun_timeline") or {}).get("series") or []))[:7]
    if not series:
        return '<div class="empty-state">暂无大运数据</div>'
    start = min(item.get("start_year") or 0 for item in series)
    end = max(item.get("end_year") or start for item in series)
    span = max(1, end - start + 1)
    bands = []
    labels = []
    for index, item in enumerate(series):
        x = 30 + ((item.get("start_year") - start) / span) * 400
        width = max(42, (((item.get("end_year") - item.get("start_year") + 1) / span) * 400))
        color = [JADE, "#4b756c", GOLD, "#a87643", CINNABAR, "#735d67", "#465b6a"][index % 7]
        bands.append(
            f'<rect x="{x:.1f}" y="{80 + index%2*36}" width="{width:.1f}" height="28" rx="14" fill="{color}" opacity=".92"/>'
        )
        labels.append(
            f'<text x="{x+width/2:.1f}" y="{99 + index%2*36}" text-anchor="middle" class="timeline-name">{_e(item.get("name"))}</text>'
            f'<text x="{x+width/2:.1f}" y="{158 + index%2*22}" text-anchor="middle" class="timeline-year">{_e(item.get("start_year"))}</text>'
        )
    return f"""
      <div class="visual-title">七步大运总览</div>
      <svg viewBox="0 0 460 230" class="timeline-svg">
        <line x1="30" y1="146" x2="430" y2="146" stroke="#b8aea0" stroke-width="2"/>
        {''.join(bands)}
        {''.join(labels)}
      </svg>
      <div class="score-pending"><b>十年一程</b><span>运柱给出一段时间的环境主调，具体年份仍会因流年与现实选择呈现不同轻重。</span></div>
    """


def _generic_visual(spread: dict) -> str:
    labels = ("看见倾向", "联系经历", "保留变化", "落到行动")
    blocks = "".join(
        f'<div class="wire-block"><i>{index:02d}</i><span>{_e(label)}</span></div>'
        for index, label in enumerate(labels, start=1)
    )
    return f"""
      <div class="visual-title">{_e(spread.get("title"))}</div>
      <div class="wire-grid">{blocks}</div>
      <div class="editorial-slot">
        <b>把理解带回生活</b>
        <p>命盘提供一种观察角度；真实经历、环境变化和每一次选择，会继续补写它的含义。</p>
      </div>
    """


def _visual_for(spread: dict, facts: dict) -> str:
    names = set(spread.get("visuals") or [])
    if "cover_art" in names:
        return _cover_visual(facts)
    if "pillar_table" in names:
        return _pillar_table(facts)
    if "wuxing_donut" in names:
        return _donut(facts)
    if "wuxing_flow" in names:
        return _flow(facts)
    if "shishen_bar" in names:
        return _bars(facts)
    if "origin_relation_network" in names:
        return _relation_network(facts)
    if "nayin_four_cards" in names:
        return _nayin_cards(facts)
    if "dayun_trend" in names:
        return _timeline(facts)
    return _generic_visual(spread)


def _source_chips(sources: Iterable[str]) -> str:
    return "".join(f"<span>{_e(source)}</span>" for source in sources)


def _page_shell(
    page_number: int,
    spread: dict,
    body: str,
    side: str,
    extra_class: str = "",
) -> str:
    section = SECTION_LABELS.get(spread.get("section"), spread.get("section"))
    return f"""
      <article class="book-page {side} {extra_class}" data-page="{page_number}">
        <div class="grain"></div>
        <header class="running-head"><span>{_e(section)}</span><b>MIRROR 命书</b></header>
        <main>{body}</main>
        <footer><span>{_e(spread.get("title"))}</span><b>{page_number:02d}</b></footer>
      </article>
    """


def _left_page(spread: dict) -> str:
    title = spread.get("title") or "命书"
    return f"""
      <div class="section-kicker">{_e(SECTION_LABELS.get(spread.get("section")))}</div>
      <h1>{_e(title)}</h1>
      <div class="title-rule"></div>
      <p class="purpose">这一章从“{_e(title)}”展开，观察它在命盘中的位置、力量与相互关系，也留意这些倾向在不同阶段如何改变表达方式。</p>
      <section class="proof-card">
        <h2>理解这一章</h2>
        <p>同一个命理名称，在不同柱位、季节和组合中会呈现不同面貌；它描述的是关系与倾向，不是固定不变的身份标签。</p>
      </section>
      <section class="source-card">
        <h2>带着三个问题阅读</h2>
        <div class="chips"><span>它在何处出现</span><span>由什么承接</span><span>怎样回到生活</span></div>
      </section>
    """


def _styles() -> str:
    return f"""
      :root {{
        --ink: {INK}; --muted: {MUTED}; --paper: {PAPER};
        --jade: {JADE}; --cinnabar: {CINNABAR}; --gold: {GOLD};
      }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; min-height: 100%; }}
      body {{
        background: #d8d4cc;
        color: var(--ink);
        font-family: "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
      }}
      .book {{ display: flex; flex-direction: column; align-items: center; gap: 18px; padding: 28px; }}
      .book-page {{
        position: relative; width: 148mm; height: 210mm; overflow: hidden;
        padding: 15mm 12mm 13mm 14mm; background:
          radial-gradient(circle at 90% 5%, rgba(173,135,80,.10), transparent 27%),
          linear-gradient(135deg, rgba(49,95,82,.035), transparent 38%), var(--paper);
        box-shadow: 0 14px 34px rgba(31,38,35,.18);
        break-after: page; page-break-after: always;
      }}
      .book-page.right {{ padding-left: 12mm; padding-right: 14mm; }}
      .grain {{
        position: absolute; inset: 0; opacity: .07; pointer-events: none;
        background-image: repeating-linear-gradient(0deg, transparent 0 3px, rgba(24,34,31,.08) 4px);
      }}
      .running-head, footer {{
        position: absolute; left: 12mm; right: 12mm; display: flex; justify-content: space-between;
        text-transform: uppercase; letter-spacing: .12em; font-size: 7.5px; color: var(--muted);
      }}
      .running-head {{ top: 7mm; border-bottom: 1px solid rgba(24,34,31,.18); padding-bottom: 2mm; }}
      footer {{ bottom: 6mm; border-top: 1px solid rgba(24,34,31,.18); padding-top: 2mm; }}
      footer b {{ color: var(--cinnabar); font-family: Georgia, serif; font-size: 11px; }}
      main {{ position: relative; z-index: 1; height: 100%; }}
      h1 {{
        margin: 7mm 0 3mm; font-family: "Noto Serif SC", "Source Han Serif SC", SimSun, serif;
        font-size: 27px; line-height: 1.2; letter-spacing: .04em; font-weight: 650;
      }}
      h2 {{ margin: 0 0 2mm; font-size: 11px; color: var(--jade); letter-spacing: .08em; }}
      p {{ line-height: 1.8; }}
      .section-kicker {{ margin-top: 11mm; color: var(--cinnabar); letter-spacing: .3em; font-size: 9px; }}
      .title-rule {{ width: 18mm; height: 2px; background: var(--gold); margin: 4mm 0 6mm; }}
      .purpose {{ font-family: "Noto Serif SC", SimSun, serif; font-size: 13px; line-height: 1.9; color: #303b37; }}
      .spec-grid {{ display: grid; grid-template-columns: repeat(3,1fr); gap: 2mm; margin: 8mm 0 6mm; }}
      .spec-grid div {{ padding: 4mm 3mm; border: 1px solid rgba(49,95,82,.25); background: rgba(255,255,255,.35); }}
      .spec-grid span {{ display: block; font-size: 7px; color: var(--muted); margin-bottom: 2mm; }}
      .spec-grid b {{ font-size: 11px; color: var(--jade); }}
      .proof-card, .source-card {{ margin-top: 4mm; padding: 4mm; background: rgba(255,255,255,.42); border-left: 2px solid var(--jade); }}
      .proof-card p {{ margin: 0; font-size: 10px; color: #49514d; }}
      .chips {{ display: flex; flex-wrap: wrap; gap: 1.6mm; }}
      .chips span {{ padding: 1.2mm 2mm; border-radius: 8mm; background: var(--jade); color: white; font-size: 7.5px; }}
      .chips.pale span {{ background: rgba(173,135,80,.16); color: #685335; border: 1px solid rgba(173,135,80,.35); }}
      .visual-title {{ margin: 11mm 0 5mm; font-family: "Noto Serif SC", SimSun, serif; font-size: 21px; color: var(--ink); }}
      .visual-note {{ margin-top: 5mm; padding-top: 3mm; border-top: 1px solid rgba(24,34,31,.2); font-size: 8px; line-height: 1.7; color: var(--muted); }}
      .cover-art {{ height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
      .cover-orbit {{ position: absolute; border: 1px solid rgba(173,135,80,.38); border-radius: 50%; }}
      .orbit-one {{ width: 78mm; height: 78mm; }}
      .orbit-two {{ width: 104mm; height: 104mm; border-style: dashed; transform: rotate(16deg); }}
      .cover-seal {{ z-index: 1; width: 23mm; height: 23mm; display: grid; place-items: center; background: var(--cinnabar); color: #f7eee0; font-family: SimSun, serif; font-size: 22px; letter-spacing: .1em; border: 2px solid #f7eee0; outline: 1px solid var(--cinnabar); }}
      .cover-kicker {{ z-index: 1; margin-top: 12mm; font-size: 7px; letter-spacing: .26em; color: var(--jade); }}
      .cover-title {{ z-index: 1; font-family: "Noto Serif SC", SimSun, serif; font-size: 54px; letter-spacing: .22em; margin-left: .22em; }}
      .cover-name {{ z-index: 1; margin-top: 3mm; font-size: 9px; letter-spacing: .11em; }}
      .cover-rule {{ z-index: 1; width: 22mm; height: 1px; background: var(--gold); margin: 5mm; }}
      .cover-caption {{ z-index: 1; font-size: 8px; color: var(--muted); letter-spacing: .18em; }}
      .pillar-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 2.6mm; margin-top: 8mm; }}
      .pillar-card {{ text-align: center; border: 1px solid rgba(49,95,82,.25); background: rgba(255,255,255,.4); padding: 3mm 1.5mm; min-height: 112mm; }}
      .pillar-label {{ font-size: 8px; color: var(--muted); letter-spacing: .18em; margin-bottom: 4mm; }}
      .stem, .branch {{ font-family: "Noto Serif SC", SimSun, serif; font-size: 37px; line-height: 1.25; }}
      .stem {{ color: var(--cinnabar); }} .branch {{ color: var(--jade); margin-top: 5mm; }}
      .ten-god {{ font-size: 8px; color: var(--gold); }}
      .hidden {{ min-height: 18mm; margin-top: 4mm; font-size: 7px; line-height: 1.7; color: var(--muted); }}
      .nayin {{ padding-top: 3mm; border-top: 1px solid rgba(24,34,31,.16); font-family: SimSun, serif; font-size: 9px; }}
      .donut-wrap {{ display: grid; grid-template-columns: 58% 42%; align-items: center; margin-top: 8mm; }}
      .donut-svg {{ width: 100%; }} .donut-small {{ font-size: 10px; fill: var(--muted); }} .donut-big {{ font-size: 24px; fill: var(--ink); font-family: SimSun, serif; }}
      .chart-legend {{ display: grid; gap: 4mm; }}
      .legend-row {{ display: grid; grid-template-columns: 4mm 1fr auto; gap: 2mm; align-items: center; font-size: 10px; }}
      .legend-row i {{ width: 3mm; height: 3mm; border-radius: 50%; }} .legend-row b {{ font-family: Georgia, serif; }}
      .bar-chart {{ display: grid; gap: 3mm; margin-top: 7mm; }}
      .bar-row {{ display: grid; grid-template-columns: 18mm 1fr 13mm; gap: 2mm; align-items: center; font-size: 8px; }}
      .bar-row.emphasis span, .bar-row.emphasis b {{ color: var(--cinnabar); font-weight: 700; }}
      .bar-track {{ height: 3.2mm; border-radius: 3mm; background: #ded6c8; overflow: hidden; }}
      .bar-track i {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg,var(--jade),#6f9488); }}
      .relation-svg, .flow-svg, .timeline-svg {{ width: 100%; margin-top: 2mm; overflow: visible; }}
      .relation-label {{ font-size: 9px; font-weight: 700; }} .node-gz {{ font-size: 15px; font-family: SimSun, serif; fill: var(--ink); }} .node-label {{ font-size: 7px; fill: var(--muted); }}
      .relation-key {{ display: flex; gap: 3mm; justify-content: center; font-size: 8px; }} .relation-key span {{ padding: 1.5mm 3mm; border-radius: 9mm; }}
      .relation-key .positive {{ color: var(--jade); background: rgba(49,95,82,.1); }} .relation-key .tension {{ color: var(--cinnabar); background: rgba(166,64,50,.1); }}
      .flow-name {{ font-size: 17px; fill: white; font-family: SimSun, serif; }} .flow-value {{ font-size: 8px; fill: white; }}
      .nayin-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }}
      .nayin-card {{ min-height: 57mm; padding: 4mm; border: 1px solid rgba(173,135,80,.35); background: rgba(255,255,255,.35); }}
      .nayin-card h3 {{ font-family: SimSun, serif; font-size: 20px; margin: 3mm 0 1mm; }}
      .nayin-pillar {{ font-size: 7px; color: var(--muted); letter-spacing: .12em; }}
      .nayin-tag {{ color: var(--cinnabar); font-size: 9px; }} .nayin-card p {{ font-size: 8px; line-height: 1.7; }}
      .timeline-name {{ fill: white; font-size: 9px; font-family: SimSun, serif; }} .timeline-year {{ fill: var(--muted); font-size: 7px; }}
      .score-pending {{ margin-top: 6mm; padding: 4mm; border: 1px solid rgba(166,64,50,.25); background: rgba(166,64,50,.06); }}
      .score-pending b {{ display: block; color: var(--cinnabar); margin-bottom: 2mm; }} .score-pending span {{ font-size: 8px; line-height: 1.7; }}
      .wire-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; margin-top: 8mm; }}
      .wire-block {{ min-height: 36mm; padding: 4mm; display: flex; flex-direction: column; justify-content: space-between; border: 1px dashed rgba(49,95,82,.35); background: rgba(255,255,255,.28); }}
      .wire-block i {{ font-family: Georgia,serif; font-size: 19px; color: var(--gold); }} .wire-block span {{ font-size: 9px; text-transform: uppercase; letter-spacing: .08em; color: var(--jade); }}
      .editorial-slot {{ margin-top: 5mm; padding: 5mm; background: var(--jade); color: white; }}
      .editorial-slot b {{ font-family: SimSun,serif; font-size: 16px; }} .editorial-slot p {{ margin: 2mm 0 0; font-size: 8px; opacity: .8; }}
      @page {{ size: A5; margin: 0; }}
      @media print {{
        body {{ background: none; }}
        .book {{ display: block; padding: 0; }}
        .book-page {{ margin: 0; box-shadow: none; }}
      }}
    """


def render_editorial_proof(facts: dict, blueprint: dict) -> str:
    """Render one physical A5 page per manifest page."""
    pages = []
    for spread in blueprint.get("spreads") or []:
        page_start = int(spread["page_start"])
        left_body = _left_page(spread)
        visual_body = _visual_for(spread, facts)
        special = "cover-page" if spread.get("slug") == "cover" else ""
        pages.append(_page_shell(page_start, spread, left_body, "left", special))
        pages.append(_page_shell(page_start + 1, spread, visual_body, "right", special))

    title = f"{((facts.get('subject') or {}).get('display_name') or '命主')} · 命书"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{_e(title)}</title>
  <style>{_styles()}</style>
</head>
<body>
  <div class="book">{''.join(pages)}</div>
</body>
</html>
"""
