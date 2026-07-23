"""Print-first sample pages for stem/branch relationship explanations."""

from __future__ import annotations

from html import escape
from pathlib import Path

from .element_styles import ELEMENT_COLOR_SCRIPT


# The SVG viewBox is 522 units wide, exactly matching four equal pillar columns.
# Keep every relationship endpoint on the mathematical centre of its pillar.
PILLAR_X = {"year": 65.25, "month": 195.75, "day": 326.25, "hour": 456.75}
ELEMENT_CLASS = {
    "WUXING:MU": "wood",
    "WUXING:HUO": "fire",
    "WUXING:TU": "earth",
    "WUXING:JIN": "metal",
    "WUXING:SHUI": "water",
}


def _e(value: object) -> str:
    return escape(str(value or ""))


def _pillar_card(pillar: dict) -> str:
    gan = pillar.get("gan") or {}
    zhi = pillar.get("zhi") or {}
    hidden = " · ".join(item.get("name_label", "") for item in zhi.get("hidden_gans") or [])
    return f"""
      <div class="pillar" data-pillar="{_e(pillar.get('key'))}">
        <b class="pillar-label">{_e(pillar.get('label'))}</b>
        <span class="ten-god">{_e(gan.get('shishen_label'))}</span>
        <strong class="glyph {ELEMENT_CLASS.get(gan.get('wuxing'), '')}">{_e(gan.get('name_label'))}</strong>
        <strong class="glyph branch {ELEMENT_CLASS.get(zhi.get('wuxing'), '')}">{_e(zhi.get('name_label'))}</strong>
        <span class="hidden">{_e(hidden)}</span>
      </div>"""


def _relation_path(relation: dict, ordinal: int = 0) -> str:
    members = relation.get("members") or []
    if len(members) < 2:
        return ""
    x1 = PILLAR_X.get(members[0].get("pillar"), 65.25)
    x2 = PILLAR_X.get(members[1].get("pillar"), 456.75)
    if x1 > x2:
        x1, x2 = x2, x1
        members = [members[1], members[0], *members[2:]]
    label = _e(relation.get("label"))
    left_label = _e(members[0].get("label") or members[0].get("name_label"))
    right_label = _e(members[1].get("label") or members[1].get("name_label"))
    relation_type = str(relation.get("relation_type") or "")
    category = relation.get("category")
    tag_width = max(58, len(str(relation.get("label") or "")) * 14 + 18)
    mid = (x1 + x2) / 2

    def rail(y: int, kind: str) -> str:
        return f"""
          <g class="relation-rail {kind}">
            <line class="rail-line" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/>
            <circle class="rail-end" cx="{x1}" cy="{y}" r="12"/><text class="rail-char" x="{x1}" y="{y + 5}">{left_label}</text>
            <circle class="rail-end" cx="{x2}" cy="{y}" r="12"/><text class="rail-char" x="{x2}" y="{y + 5}">{right_label}</text>
            <g class="rail-caption" transform="translate({mid},{y - 20})"><rect x="{-tag_width/2}" y="-12" width="{tag_width}" height="23" rx="4"/><text y="4">{label}</text></g>
          </g>"""

    if relation.get("field") == "stem" and category == "chong":
        return rail(15, "clash")
    if relation_type == "GONGHE":
        return rail(355, "combine")
    return rail(420, "harm")


def _overall_page(facts: dict) -> str:
    pillars = (facts.get("chart") or {}).get("pillars") or []
    network = (facts.get("visuals") or {}).get("origin_network") or {}
    relations = network.get("relations") or []
    cards = "".join(_pillar_card(pillar) for pillar in pillars[:4])
    counters: dict[str, int] = {}
    path_parts = []
    for relation in relations:
        category = str(relation.get("category") or relation.get("relation_type") or "")
        path_parts.append(_relation_path(relation, counters.get(category, 0)))
        counters[category] = counters.get(category, 0) + 1
    paths = "".join(path_parts)
    relation_names = "、".join(str(item.get("label") or "") for item in relations) or "原局未见成立关系"
    return f"""
    <article class="page overview" data-page="24">
      <header>原局 · 干支关系</header>
      <p class="eyebrow">先看字，再看字与字之间如何牵动</p>
      <h1>命盘里的牵引与碰撞</h1>
      <p class="deck">天干关系列在上方，地支关系列在下方。每条线的端点都与对应字列居中对齐，名称写在线段中央。</p>
      <div class="relation-board">
        <div class="lane lane-stem">天干</div><div class="lane lane-branch">地支</div>
        <div class="pillars">{cards}</div>
        <svg viewBox="0 0 522 430" aria-label="本命四柱原局作用关系图">
          {paths}
        </svg>
      </div>
      <div class="case-summary"><b>本盘成立</b><span>{_e(relation_names)}</span><i>线条只表达作用方式，不直接替代吉凶判断。</i></div>
      <footer>24</footer>
    </article>"""


def _pair(x1: int, x2: int, left: str, right: str, kind: str, label: str) -> str:
    mid = (x1 + x2) / 2
    path = f"M{x1} 164 C{x1} 78,{x2} 78,{x2} 164"
    if kind == "hidden":
        path = f"M{x1} 164 C{x1} 92,{x2} 92,{x2} 164"
    return f"""
      <circle class="pair-node" cx="{x1}" cy="176" r="38"/><text class="pair-glyph" x="{x1}" y="189">{left}</text>
      <circle class="pair-node" cx="{x2}" cy="176" r="38"/><text class="pair-glyph" x="{x2}" y="189">{right}</text>
      <path class="pair-line {kind}" d="{path}"/><g class="pair-label" transform="translate({mid},74)"><rect x="-35" y="-17" width="70" height="30" rx="15"/><text y="5">{label}</text></g>"""


def _he_page(facts: dict) -> str:
    relations = ((facts.get("visuals") or {}).get("origin_network") or {}).get("relations") or []
    gonghe = [item for item in relations if item.get("relation_type") == "GONGHE"]
    count = len(gonghe)
    return f"""
    <article class="page relation-detail he" data-page="25">
      <header>作用之一 · 合</header>
      <p class="eyebrow">本盘不是天干五合，而是地支首尾相见</p><h1>合，在本盘表现为两组拱合</h1>
      <svg class="hero-diagram gonghe-diagram" viewBox="0 0 520 270" aria-label="月支巳、日支丑、时支巳形成两组巳丑拱合">
        <circle class="ghost-node" cx="260" cy="55" r="31"/><text class="ghost-glyph" x="260" y="66">酉</text><text class="ghost-note" x="260" y="105">中神未见</text>
        <path class="pair-line combine" d="M120 178 C120 103,260 103,260 178"/>
        <path class="pair-line combine" d="M260 178 C260 103,400 103,400 178"/>
        <g class="pair-label" transform="translate(190,116)"><rect x="-35" y="-17" width="70" height="30" rx="15"/><text y="5">拱合</text></g>
        <g class="pair-label" transform="translate(330,116)"><rect x="-35" y="-17" width="70" height="30" rx="15"/><text y="5">拱合</text></g>
        <circle class="pair-node fire-fill" cx="120" cy="188" r="36"/><text class="pair-glyph" x="120" y="201">巳</text><text class="node-note" x="120" y="246">月支</text>
        <circle class="pair-node earth-fill" cx="260" cy="188" r="36"/><text class="pair-glyph" x="260" y="201">丑</text><text class="node-note" x="260" y="246">日支</text>
        <circle class="pair-node fire-fill" cx="400" cy="188" r="36"/><text class="pair-glyph" x="400" y="201">巳</text><text class="node-note" x="400" y="246">时支</text>
      </svg>
      <div class="reading"><b>怎样读</b><p>拱合是三合局的首尾两支相见，而中神尚未出现。本盘巳、丑向金气靠拢，但不能直接写成“巳酉丑三合金局”，也不能写成合化成功。</p></div>
      <div class="mini-map"><b>实际位置</b><span>月支巳—日支丑</span><span>日支丑—时支巳</span><span>所缺中神：酉</span></div>
      <div class="case-note"><strong>本盘所见｜{count}组巳丑拱合</strong><p>同一个日支丑，分别承接月支巳与时支巳。两条拱合同时指向金，读作结构上的牵引；是否在大运流年中补足酉，还要另页观察。</p></div>
      <footer>25</footer>
    </article>"""


def _chong_page() -> str:
    return f"""
    <article class="page relation-detail chong" data-page="26">
      <header>作用之二 · 冲</header>
      <p class="eyebrow">两股方向相反的力量，彼此推动改变</p><h1>冲，是一次正面改道</h1>
      <svg class="hero-diagram" viewBox="0 0 520 250" aria-label="辛乙相冲示意">
        <circle class="pair-node metal-fill" cx="150" cy="176" r="38"/><text class="pair-glyph" x="150" y="189">辛</text>
        <circle class="pair-node wood-fill" cx="370" cy="176" r="38"/><text class="pair-glyph" x="370" y="189">乙</text>
        <path class="opposing" d="M204 176 H300"/><path class="opposing" d="M316 176 H220"/>
        <g class="pair-label clash-label" transform="translate(260,92)"><rect x="-35" y="-17" width="70" height="30" rx="15"/><text y="5">相冲</text></g>
      </svg>
      <div class="reading"><b>怎样读</b><p>冲常对应方向变化、位置移动或原有秩序被打开。它不是天然的坏事：需要改变时，冲也可能成为启动。</p></div>
      <div class="case-note emphasized"><strong>本盘关系｜月干辛 ↔ 时干乙</strong><p>月柱偏向当下环境与行动方式，时柱偏向后续表达与长远安排。两者相冲，像现实要求与个人构想不断校准。</p></div>
      <footer>26</footer>
    </article>"""


def _xing_page() -> str:
    return """
    <article class="page relation-detail xing" data-page="27">
      <header>作用之三 · 刑</header>
      <p class="eyebrow">不是迎面相撞，而是结构内部反复牵扯</p><h1>刑，像结绳处的内在张力</h1>
      <svg class="tri-diagram" viewBox="0 0 520 270" aria-label="地支相刑类型示意">
        <path class="triangle-line" d="M260 54 L118 220 L402 220 Z"/>
        <g class="tri-node"><circle cx="260" cy="54" r="34"/><text x="260" y="66">寅</text></g>
        <g class="tri-node"><circle cx="118" cy="220" r="34"/><text x="118" y="232">巳</text></g>
        <g class="tri-node"><circle cx="402" cy="220" r="34"/><text x="402" y="232">申</text></g>
        <text class="center-label" x="260" y="170">无恩之刑</text>
      </svg>
      <div class="type-lines"><span><b>三刑</b>寅巳申、丑戌未</span><span><b>相刑</b>子卯</span><span><b>自刑</b>辰、午、酉、亥重见</span></div>
      <div class="case-note quiet"><strong>本盘所见</strong><p>原局没有判定成立的刑。这里保留一页，是为了让读者知道“没有出现”本身也是清晰的信息。</p></div>
      <footer>27</footer>
    </article>"""


def _hai_page() -> str:
    return """
    <article class="page relation-detail hai" data-page="28">
      <header>作用之四 · 穿害</header>
      <p class="eyebrow">表面未必剧烈，内里却容易别扭或耗损</p><h1>穿，是藏在结构里的摩擦</h1>
      <svg class="hero-diagram" viewBox="0 0 520 250" aria-label="午丑相穿示意">
        <circle class="pair-node fire-fill" cx="150" cy="176" r="38"/><text class="pair-glyph" x="150" y="189">午</text>
        <circle class="pair-node earth-fill" cx="370" cy="176" r="38"/><text class="pair-glyph" x="370" y="189">丑</text>
        <path class="pierce-line" d="M202 176 H318"/>
        <path class="pierce-notch" d="M232 165 l14 22 l14-22 l14 22 l14-22"/>
        <g class="pair-label harm-label" transform="translate(260,92)"><rect x="-39" y="-17" width="78" height="30" rx="15"/><text y="5">相穿</text></g>
      </svg>
      <div class="reading"><b>怎样读</b><p>穿也称害，强调并非正面碰撞，而是关系中的隐性干扰。仍要看被作用的是喜神还是忌神、落在哪一柱。</p></div>
      <div class="case-note emphasized"><strong>本盘关系｜年支午 — 日支丑</strong><p>年支与日支相穿，连接早年环境和更贴近自己的日常位置。它更像长期磨合，不宜直接翻译成单一事件。</p></div>
      <footer>28</footer>
    </article>"""


def _anhe_page() -> str:
    return """
    <article class="page relation-detail anhe" data-page="29">
      <header>作用之五 · 暗合</header>
      <p class="eyebrow">不在表层相接，而由地支内部的藏干相牵</p><h1>暗合，是看不见的靠近</h1>
      <svg class="hidden-diagram empty-diagram" viewBox="0 0 520 275" aria-label="原局未见成立的暗合">
        <path class="screen" d="M110 34 V238 M410 34 V238"/>
        <circle class="empty-node fire-fill" cx="90" cy="174" r="31"/><text x="90" y="185">午</text>
        <circle class="empty-node fire-fill" cx="203" cy="174" r="31"/><text x="203" y="185">巳</text>
        <circle class="empty-node earth-fill" cx="317" cy="174" r="31"/><text x="317" y="185">丑</text>
        <circle class="empty-node fire-fill" cx="430" cy="174" r="31"/><text x="430" y="185">巳</text>
        <g class="empty-seal" transform="translate(260,75)"><circle r="43"/><text y="7">未见</text></g>
      </svg>
      <div class="reading"><b>怎样读</b><p>暗合强调隐性的吸引与牵制。它常需要通过藏干关系才能看见，因此比明合更适合用半透明线和“帘后”结构表现。</p></div>
      <div class="case-note quiet"><strong>本盘所见</strong><p>原局未见本书口径下成立的暗合。本页不再放入其他命盘的寅丑示例；阅读重点回到两组巳丑拱合、辛乙冲与午丑穿。</p></div>
      <footer>29</footer>
    </article>"""


def _category_page(facts: dict, page: int, header: str, title: str, relation_types: set[str], explanation: str) -> str:
    relations = (
        (facts.get("analysis_facts") or {}).get("origin_relations")
        or ((facts.get("visuals") or {}).get("origin_network") or {}).get("relations")
        or []
    )
    selected = [item for item in relations if str(item.get("relation_type") or "") in relation_types]
    if selected:
        first = selected[0]
        members = first.get("members") or []
        left = str((members[0] if members else {}).get("label") or "")
        right = str((members[1] if len(members) > 1 else {}).get("label") or "")
        diagram = f'<svg class="hero-diagram" viewBox="0 0 520 250" aria-label="{_e(first.get("label"))}示意">{_pair(150, 370, _e(left), _e(right), "combine", _e(first.get("label")))}</svg>'
        cards = []
        branch_chars = {
            "ZHI:ZI": "子", "ZHI:CHOU": "丑", "ZHI:YIN": "寅", "ZHI:MAO": "卯",
            "ZHI:CHEN": "辰", "ZHI:SI": "巳", "ZHI:WU": "午", "ZHI:WEI": "未",
            "ZHI:SHEN": "申", "ZHI:YOU": "酉", "ZHI:XU": "戌", "ZHI:HAI": "亥",
        }
        for item in selected:
            members = item.get("members") or []
            positions = " ↔ ".join(
                f"{member.get('pillar_label') or ''}{member.get('label') or ''}"
                for member in members[:2]
            )
            missing_code = item.get("missing_member")
            missing = f"；所缺中神为{branch_chars.get(missing_code, missing_code)}" if missing_code else ""
            cards.append(f'<div class="case-note"><strong>{_e(item.get("label"))}｜{_e(positions)}</strong><p>{_e(explanation + missing)} 这条线只表示结构怎样牵动，不单独替代吉凶判断。</p></div>')
        content = diagram + "".join(cards)
    else:
        content = f'<div class="case-note quiet"><strong>本盘未见</strong><p>原局没有判定成立的{_e(header)}。这里保留页面，明确“未见”本身也是信息，不放入其他命盘的示意关系。</p></div>'
    side = "verso" if page % 2 == 0 else "recto"
    return f"""<article class="page relation-detail {side}" data-page="{page}"><header>{_e(header)}</header><p class="eyebrow">只呈现本盘实际成立的关系</p><h1>{_e(title)}</h1><div class="reading"><b>怎样读</b><p>{_e(explanation)}</p></div>{content}<footer>{page}</footer></article>"""


def render_relation_sample_html(facts: dict) -> str:
    pages = [
        _overall_page(facts),
        _category_page(facts, 25, "作用之一 · 合", "合，是连接与牵引", {"WUHE", "LIUHE", "SANHE", "BANHE", "GONGHE"}, "合表示两处位置更容易连接、绑定或朝同一方向靠拢；拱合仍缺条件，不能直接写成已经合化。"),
        _category_page(facts, 26, "作用之二 · 冲", "冲，是一次正面改道", {"CHONG", "LIUCHONG"}, "冲表示两种要求正面相遇，常带来调整、移动或重新排序；需要改变时，它也可能成为启动。"),
        _category_page(facts, 27, "作用之三 · 刑", "刑，是内部反复出现的压力", {"XING", "ZIXING"}, "刑强调规则、步骤或心理压力的反复；自刑尤其像同一问题在内部循环，适合用记录和复盘打断惯性。"),
        _category_page(facts, 28, "作用之四 · 穿害", "穿害，是细节里的摩擦", {"CHUAN", "HAI", "LIUHAI"}, "穿害不一定正面爆发，常表现为信息落差、误解或日常安排互相侵入，需要靠边界与确认减少消耗。"),
        _category_page(facts, 29, "作用之五 · 暗合", "暗合，是没有摆在明面的靠近", {"ANHE"}, "暗合常通过习惯、默契或未说出口的需要彼此影响；越重要的安排，越不能只靠猜测。"),
    ]
    spreads = "".join(f'<section class="spread">{pages[i]}{pages[i+1]}</section>' for i in range(0, 6, 2))
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 干支作用关系样例</title><style>
@font-face{{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}}
@font-face{{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}}
@font-face{{font-family:BookBrush;src:url('../../../assets/fonts/MaShanZheng-Regular.ttf')}}
@page{{size:A4 landscape;margin:0}}
:root{{--paper:#f3ead8;--paper2:#faf5e9;--ink:#292823;--muted:#6f695e;--gold:#a77d3c;--line:#d3c2a3;--jade:#315c50;--red:#9a3d32;--wood:#4e7860;--fire:#a84636;--earth:#a67c3e;--metal:#717a78;--water:#41677b}}
*{{box-sizing:border-box}}body{{margin:0;background:#242422;color:var(--ink);font-family:BookSerif,serif}}main{{padding:28px 0 70px}}.spread{{display:flex;width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;filter:drop-shadow(0 14px 24px #111)}}.page{{position:relative;flex:0 0 50%;aspect-ratio:148/210;padding:7.5% 8%;overflow:hidden;background:linear-gradient(135deg,var(--paper2),var(--paper));contain:layout paint}}.spread>.page:first-child:after{{content:'';position:absolute;right:0;inset-block:0;width:1px;background:#cbbfae}}header{{font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px}}.page:nth-child(even) header{{text-align:right}}h1{{font-size:31px;line-height:1.25;margin:7px 0 10px;font-weight:500}}.eyebrow{{font:9px BookSans;color:var(--gold);letter-spacing:.12em;margin:19px 0 0}}.deck{{font:11px/1.75 BookSans;color:var(--muted);margin:0}}footer{{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#887d6b}}.page:nth-child(even) footer{{text-align:right}}
.relation-board{{position:relative;height:445px;margin-top:13px;border-top:1px solid #b69358;border-bottom:1px solid #b69358;background:rgba(255,252,243,.5)}}.relation-board svg{{position:absolute;inset:0;width:100%;height:100%;z-index:3;overflow:visible;pointer-events:none}}.pillars{{position:absolute;inset:0;display:grid;grid-template-columns:repeat(4,1fr);z-index:2}}.pillar{{text-align:center;border-right:1px solid rgba(180,156,116,.32);padding-top:81px}}.pillar:last-child{{border-right:0}}.pillar-label,.ten-god,.hidden,.nayin{{display:block}}.pillar-label{{font-size:12px}}.ten-god{{font:9px BookSans;color:#8b7652;margin:8px 0 2px}}.glyph{{display:block;font-size:42px;line-height:1.28;font-weight:500}}.glyph.branch{{margin-top:29px}}.hidden{{font:9px BookSans;color:#746e64;margin-top:8px}}.nayin{{font-size:10px;color:#90754b;border-top:1px solid rgba(180,156,116,.32);margin:13px 12px 0;padding-top:9px}}.lane{{position:absolute;left:-31px;z-index:5;writing-mode:vertical-rl;font:9px BookSans;color:#9a7c48;letter-spacing:.14em}}.lane-stem{{top:145px}}.lane-branch{{top:277px}}.wood{{color:var(--wood)}}.fire{{color:var(--fire)}}.earth{{color:var(--earth)}}.metal{{color:var(--metal)}}.water{{color:var(--water)}}.relation-rail{{color:#8e6333}}.relation-rail.combine{{color:var(--jade)}}.relation-rail.clash{{color:var(--red)}}.rail-line{{stroke:currentColor;stroke-width:1.7}}.relation-rail.harm .rail-line{{stroke-dasharray:6 4}}.rail-end{{fill:#fffaf0;stroke:currentColor;stroke-width:1.35}}.rail-char{{font:13px BookSerif;fill:currentColor;text-anchor:middle}}.rail-caption rect{{fill:#fffaf0;stroke:none;opacity:.96}}.rail-caption text{{font:12px BookSerif;fill:currentColor;text-anchor:middle;letter-spacing:.04em}}.pair-label rect{{fill:#fffaf0;stroke:currentColor}}.pair-label text{{text-anchor:middle;font:13px BookSerif;fill:currentColor}}.case-summary{{display:grid;grid-template-columns:80px 1fr;gap:7px 13px;margin-top:13px;padding:11px 13px;border-left:3px solid var(--gold);background:rgba(255,252,244,.72);font:10px/1.55 BookSans}}.case-summary b{{color:var(--jade)}}.case-summary i{{grid-column:2;font-style:normal;color:var(--muted)}}
.relation-detail{{background:linear-gradient(160deg,#f8f1e3,#eee1cb)}}.relation-detail:before{{content:'';position:absolute;inset:4.7%;border:1px solid rgba(163,126,67,.34);pointer-events:none}}.hero-diagram,.tri-diagram,.hidden-diagram{{display:block;width:100%;height:auto;margin:13px 0 8px;overflow:visible}}.pair-node{{fill:#fbf5e8;stroke:#a98348;stroke-width:1.6}}.pair-glyph{{font:45px BookSerif;fill:var(--ink);text-anchor:middle}}.pair-line{{fill:none;stroke-width:3;stroke-linecap:round}}.pair-line.combine{{stroke:var(--jade)}}.pair-line.hidden{{stroke:#846f50;stroke-dasharray:4 7}}.pair-label{{color:var(--jade)}}.clash-label{{color:var(--red)}}.harm-label{{color:#8e6333}}.hidden-label{{color:#846f50}}.soft-orbit{{fill:none;stroke:#bca26f;stroke-width:1.5;stroke-dasharray:3 6}}.metal-fill{{fill:#e2e5e0}}.wood-fill{{fill:#dfe9df}}.fire-fill{{fill:#eedbd0}}.earth-fill{{fill:#eadfc8}}.opposing{{fill:none;stroke:var(--red);stroke-width:4;marker-end:url(#none)}}.pierce-line{{stroke:#8e6333;stroke-width:3}}.pierce-notch{{fill:none;stroke:#8e6333;stroke-width:2}}.reading,.case-note{{position:relative;padding:11px 13px;background:rgba(255,252,244,.74);border-left:3px solid var(--gold);margin-top:9px}}.reading b,.case-note strong{{display:block;font-size:11px;color:var(--jade);margin-bottom:4px}}.reading p,.case-note p{{font:10px/1.65 BookSans;margin:0;color:#57534d}}.case-note.emphasized{{border-color:var(--red)}}.case-note.quiet{{border-left-width:1px;background:transparent;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.mini-map{{display:grid;grid-template-columns:88px repeat(3,1fr);align-items:center;margin:10px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);font:9px BookSans}}.mini-map>*{{padding:8px 4px;text-align:center}}.mini-map b{{color:#876a3d}}.mini-map.compact{{grid-template-columns:88px repeat(3,1fr)}}.triangle-line{{fill:none;stroke:#9b563d;stroke-width:2.2;stroke-dasharray:8 5}}.tri-node circle{{fill:#fbf5e8;stroke:#9b563d;stroke-width:1.5}}.tri-node text{{font:36px BookSerif;text-anchor:middle;fill:var(--ink)}}.center-label{{font:13px BookSans;text-anchor:middle;fill:#8b5d43;letter-spacing:.12em}}.type-lines{{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:-3px}}.type-lines span{{padding:8px 9px;border-top:1px solid var(--line);font:9px/1.55 BookSans}}.type-lines span:first-child{{grid-column:1/-1}}.type-lines b{{display:block;color:#8d563d}}.screen{{fill:none;stroke:#b9a782;stroke-width:9;stroke-opacity:.3}}.hidden-glow{{fill:none;stroke:#a98a5d;stroke-width:16;opacity:.35}}.ghost-node{{fill:rgba(255,250,240,.45);stroke:#8b7652;stroke-width:1.4;stroke-dasharray:4 5}}.ghost-glyph{{font:32px BookSerif;fill:#8b7652;text-anchor:middle}}.ghost-note,.node-note{{font:9px BookSans;fill:#8c7651;text-anchor:middle;letter-spacing:.1em}}.empty-node{{stroke:#bba77e;stroke-width:1.2;opacity:.48}}.empty-node+text,.empty-diagram>.empty-node~text{{font:31px BookSerif;fill:#756d60;text-anchor:middle;opacity:.62}}.empty-seal circle{{fill:none;stroke:#957d56;stroke-width:1.5;stroke-dasharray:3 5}}.empty-seal text{{font:17px BookBrush;fill:#806d4f;text-anchor:middle}}
@media print{{body{{background:#fff}}main{{padding:0}}.spread{{width:296mm;height:210mm;margin:0;filter:none;break-after:page}}.page{{width:148mm;height:210mm}}}}
</style></head><body><main>{spreads}</main>{ELEMENT_COLOR_SCRIPT}</body></html>"""


def write_relation_sample(facts: dict, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_relation_sample_html(facts), encoding="utf-8")
    return path
