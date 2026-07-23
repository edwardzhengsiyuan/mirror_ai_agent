"""Art-directed MingShu case proof built from real structured facts.

The renderer keeps generated artwork, deterministic charts, and reader copy in
separate layers.  Background PNGs never contain text; all facts remain editable
HTML or vector/text PDF content.
"""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

from .knowledge_pages import KNOWLEDGE_PAGE_INDEX


# The normal web/test runtime does not require ReportLab.  PDF dependencies are
# loaded only when render_artbook_case_pdf() is actually called.
Canvas = Any
PrintSpec = Any
HexColor = None
ImageReader = None
mm = None
CINNABAR = GOLD = INK = JADE = MUTED = PAPER = None
_draw_text = _safe_text = register_fonts = None


def _load_pdf_runtime() -> None:
    global Canvas, PrintSpec, HexColor, ImageReader, mm
    global CINNABAR, GOLD, INK, JADE, MUTED, PAPER
    global _draw_text, _safe_text, register_fonts
    if HexColor is not None:
        return
    try:
        from reportlab.lib.colors import HexColor as _HexColor
        from reportlab.lib.units import mm as _mm
        from reportlab.lib.utils import ImageReader as _ImageReader
        from reportlab.pdfgen.canvas import Canvas as _Canvas
        from . import pdf_renderer as pdf
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised in minimal runtimes
        raise RuntimeError(
            "PDF rendering requires the bundled document runtime or reportlab installation"
        ) from exc
    Canvas = _Canvas
    HexColor = _HexColor
    ImageReader = _ImageReader
    mm = _mm
    PrintSpec = pdf.PrintSpec
    CINNABAR = pdf.CINNABAR
    GOLD = pdf.GOLD
    INK = pdf.INK
    JADE = pdf.JADE
    MUTED = pdf.MUTED
    PAPER = pdf.PAPER
    _draw_text = pdf._draw_text
    _safe_text = pdf._safe_text
    register_fonts = pdf.register_fonts


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "mingshu" / "backgrounds"

BACKGROUND_ASSETS = {
    "chart": "bazi-chart-horizon-v1.png",
    "wuxing": "wuxing-wash-v1.png",
    "qisha_opener": "qisha-ridge-v1.png",
    "qisha_text": "qisha-text-v1.png",
}

ELEMENT_COLORS = {
    "WUXING:MU": "#496f59",
    "WUXING:HUO": "#a9382b",
    "WUXING:TU": "#a97c38",
    "WUXING:JIN": "#8d8066",
    "WUXING:SHUI": "#274b67",
}


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _pillars(facts: dict) -> list[dict]:
    return list((facts.get("chart") or {}).get("pillars") or [])


def _wuxing(facts: dict) -> list[dict]:
    items = list((facts.get("analysis_facts") or {}).get("wuxing") or [])
    if items:
        return items
    return list((((facts.get("visuals") or {}).get("wuxing_ratio") or {}).get("series") or []))


def _shishen(facts: dict) -> list[dict]:
    items = list((facts.get("analysis_facts") or {}).get("shishen") or [])
    if items:
        return items
    return list((((facts.get("visuals") or {}).get("shishen_ratio") or {}).get("series") or []))


def _day_master(facts: dict) -> dict:
    return dict((facts.get("chart") or {}).get("day_master") or {})


def _asset_url(asset_prefix: str, key: str) -> str:
    return f"{asset_prefix.rstrip('/')}/{BACKGROUND_ASSETS[key]}"


def _hidden_text(pillar: dict) -> str:
    return "　".join(
        f"{item.get('name_label')}{item.get('shishen_label')}"
        for item in (pillar.get("zhi") or {}).get("hidden_gans") or []
    )


def _relation_svg(facts: dict) -> str:
    network = (facts.get("visuals") or {}).get("origin_network") or {}
    pillars = list(network.get("pillars") or [])[:4]
    relations = list(network.get("relations") or [])[:3]
    xs = [68, 202, 336, 470]
    pillar_x = {pillar.get("key"): xs[index] for index, pillar in enumerate(pillars)}
    paths: list[str] = []
    labels: list[str] = []
    for index, relation in enumerate(relations):
        members = relation.get("members") or []
        if len(members) < 2:
            continue
        x1 = pillar_x.get(members[0].get("pillar"), xs[0])
        x2 = pillar_x.get(members[1].get("pillar"), xs[-1])
        y = 15 + index * 18
        label = relation.get("label") or "作用"
        field_label = "干" if relation.get("field") == "stem" else "支"
        tension = any(word in label for word in ("冲", "刑", "穿", "害", "破"))
        color = "#9b342b" if tension else "#386555"
        mid = (x1 + x2) / 2
        paths.append(
            f'<path d="M{x1} {y + 5} Q{mid:.1f} {y - 5} {x2} {y + 5}" '
            f'fill="none" stroke="{color}" stroke-width="1.45"/>'
            f'<circle cx="{x1}" cy="{y + 5}" r="2.4" fill="{color}"/>'
            f'<circle cx="{x2}" cy="{y + 5}" r="2.4" fill="{color}"/>'
        )
        labels.append(
            f'<text x="{mid:.1f}" y="{y + 1}" text-anchor="middle" '
            f'fill="{color}">{field_label} · {_e(label)}</text>'
        )
    return f'<svg class="relation-layer" viewBox="0 0 538 62" aria-label="原局干支作用">{"".join(paths)}{"".join(labels)}</svg>'


def _bazi_page(facts: dict, asset_prefix: str) -> str:
    pillars = _pillars(facts)
    cells = []
    for index, pillar in enumerate(pillars[:4]):
        gan = pillar.get("gan") or {}
        zhi = pillar.get("zhi") or {}
        day_mark = '<span class="day-mark">日主</span>' if index == 2 else ""
        cells.append(
            f"""
            <section class="pillar-lane{' day-pillar' if index == 2 else ''}">
              <div class="pillar-label">{_e(pillar.get('label'))}</div>
              {day_mark}
              <div class="stem">{_e(gan.get('name_label'))}</div>
              <div class="ten-god">{_e(gan.get('shishen_label'))}</div>
              <div class="branch">{_e(zhi.get('name_label'))}</div>
              <div class="hidden-label">藏干</div>
              <div class="hidden-stems">{_e(_hidden_text(pillar))}</div>
              <div class="nayin">{_e((pillar.get('nayin') or {}).get('label'))}</div>
            </section>
            """
        )
    subject = (facts.get("subject") or {}).get("display_name") or "命主"
    day_master = _day_master(facts)
    return f"""
    <article class="art-page chart-page" data-page="1" data-testid="case-chart-page">
      <img class="art-layer" src="{_asset_url(asset_prefix, 'chart')}" alt="原盘山水底图">
      <header class="running-head"><span>原局 · 四柱全盘</span><span>{_e(subject)}的命书</span></header>
      <h1>八字原盘</h1>
      <p class="chart-deck">日主为{_e(day_master.get('label'))}{_e(day_master.get('wuxing_label'))}，先看四柱，再看它们之间怎样牵动。</p>
      {_relation_svg(facts)}
      <div class="pillar-map">{''.join(cells)}</div>
      <div class="chart-caption"><b>读图顺序</b><span>天干看显露，地支看根基，藏干看潜在通道；连线只表示结构关系，不直接对应某件吉凶事件。</span></div>
      <footer><span>四柱 · 藏干 · 纳音 · 干支作用</span><b>008</b></footer>
    </article>
    """


def _wuxing_map(facts: dict) -> dict[str, dict]:
    return {item.get("code"): item for item in _wuxing(facts)}


def _wuxing_conclusion(facts: dict) -> str:
    items = sorted(_wuxing(facts), key=lambda item: float(item.get("percent") or 0), reverse=True)
    if not items:
        return "五行气势尚未显出清晰重心。"
    strongest = items[0]
    second = items[1] if len(items) > 1 else {}
    weakest = items[-1]
    return (
        f"本盘{strongest.get('label')}的相对力量最高（{float(strongest.get('percent') or 0):.1f}%），"
        f"其次为{second.get('label')}（{float(second.get('percent') or 0):.1f}%）；"
        f"{weakest.get('label')}相对较少（{float(weakest.get('percent') or 0):.1f}%）。"
        "比例用于找重心，不等同喜忌，也不建议按“缺什么补什么”直接行动。"
    )


def _wuxing_page(facts: dict, asset_prefix: str) -> str:
    values = _wuxing_map(facts)
    positions = {
        "WUXING:MU": (156, 180, "wood"),
        "WUXING:HUO": (382, 172, "fire"),
        "WUXING:TU": (430, 322, "earth"),
        "WUXING:JIN": (118, 333, "metal"),
        "WUXING:SHUI": (286, 458, "water"),
    }
    labels = []
    for code, (x, y, cls) in positions.items():
        item = values.get(code, {})
        labels.append(
            f'<div class="element-label {cls}" style="left:{x}px;top:{y}px">'
            f'<span>{_e(item.get("label"))}</span><b>{float(item.get("percent") or 0):.1f}%</b></div>'
        )
    day_master = _day_master(facts)
    return f"""
    <article class="art-page wuxing-page" data-page="2" data-testid="case-wuxing-page">
      <img class="art-layer" src="{_asset_url(asset_prefix, 'wuxing')}" alt="五行矿物色底图">
      <header class="running-head"><span>原局 · 五行</span><span>结构重心与流通</span></header>
      <div class="wuxing-title"><h1>五行<br>气势</h1><p>日主 · <b>{_e(day_master.get('label'))}{_e(day_master.get('wuxing_label'))}</b></p></div>
      <svg class="cycle-lines" viewBox="0 0 538 590" aria-label="五行相生相克">
        <defs><marker id="arrow-gold" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#8c6c32"/></marker></defs>
        <path d="M168 203 Q270 118 370 194 Q456 237 422 316 Q390 418 300 465 Q185 478 128 354 Q92 268 158 210" fill="none" stroke="#8c6c32" stroke-width="1.5" marker-end="url(#arrow-gold)"/>
        <path d="M275 313 L162 218 M275 313 L384 203 M275 313 L418 328 M275 313 L291 457 M275 313 L128 342" fill="none" stroke="#4b4841" stroke-width="1.1" stroke-dasharray="5 4" opacity=".78"/>
        <circle cx="275" cy="313" r="31" fill="#f6efe3" stroke="#9b342b" stroke-width="1.6"/>
        <text x="275" y="307" text-anchor="middle" class="center-glyph">{_e(day_master.get('label'))}</text>
        <text x="275" y="329" text-anchor="middle" class="center-label">日主</text>
      </svg>
      {''.join(labels)}
      <div class="wuxing-key"><span><i class="solid"></i>相生</span><span><i class="dashed"></i>相克</span></div>
      <div class="wuxing-conclusion"><b>读者结论</b><p>{_e(_wuxing_conclusion(facts))}</p></div>
      <footer><span>比例来自原盘力量计算</span><b>012</b></footer>
    </article>
    """


def _qisha_case_summary(facts: dict) -> dict:
    qisha = next((item for item in _shishen(facts) if item.get("label") == "七杀"), {})
    zhengguan = next((item for item in _shishen(facts) if item.get("label") == "正官"), {})
    visible = []
    for pillar in _pillars(facts):
        gan = pillar.get("gan") or {}
        if gan.get("shishen_label") == "七杀":
            visible.append(f"{pillar.get('label')}{gan.get('name_label')}水")
    return {
        "qisha_percent": float(qisha.get("percent") or 0),
        "zhengguan_percent": float(zhengguan.get("percent") or 0),
        "visible": "、".join(visible) or "天干未直接透出",
    }


def _qisha_opener(facts: dict, asset_prefix: str) -> str:
    summary = _qisha_case_summary(facts)
    return f"""
    <article class="art-page qisha-opener" data-page="3" data-testid="case-qisha-opener">
      <img class="art-layer" src="{_asset_url(asset_prefix, 'qisha_opener')}" alt="官杀山势底图">
      <header class="running-head light"><span>十神 · 一页深读</span><span>压力与边界</span></header>
      <div class="qisha-hero-copy">
        <span class="category-seal">官<br>杀</span>
        <h1>七杀</h1>
        <h2>逆风成刃，临界见真章</h2>
        <p>七杀常用来观察直接压力、竞争环境、风险反应和果断行动。它不是“凶”的同义词，而是一种人在限制条件下如何判断、承担和建立边界的语言。</p>
        <p class="case-hook">在这张真实命盘里，七杀占十神力量的 <b>{summary['qisha_percent']:.1f}%</b>，并由{_e(summary['visible'])}直接显出。</p>
      </div>
      <div class="qisha-cues">
        <div><b>顺势</b><span>抓重点 · 敢承担 · 临场决断</span></div>
        <div><b>失衡</b><span>过度警觉 · 节奏过紧 · 凡事战斗化</span></div>
        <div><b>转化</b><span>规则 · 预案 · 反馈 · 恢复</span></div>
      </div>
      <footer class="light"><span>七杀出现，不等于七杀格成立</span><b>024</b></footer>
    </article>
    """


def _qisha_detail(facts: dict, asset_prefix: str) -> str:
    page = KNOWLEDGE_PAGE_INDEX["SHISHEN:QISHA"]
    summary = _qisha_case_summary(facts)
    sections = "".join(
        f'<section><h2>{_e(title)}</h2><p>{_e(text)}</p></section>'
        for title, text in page.deep_sections
    )
    case_note = (
        f"本盘七杀为 {summary['qisha_percent']:.1f}%，{summary['visible']}；"
        f"正官为 {summary['zhengguan_percent']:.1f}%。官与杀同时构成较明显的规则—压力通道。"
        "命盘也见食神、伤官与印星；是否形成有效制化，仍要结合季节、根气和柱位。"
        "这些条件尚未完全归于七杀格的成立逻辑，因此暂不以七杀格定论。"
    )
    return f"""
    <article class="art-page qisha-detail" data-page="4" data-testid="case-qisha-detail">
      <img class="art-layer" src="{_asset_url(asset_prefix, 'qisha_text')}" alt="官杀长文底图">
      <header class="running-head"><span>十神 · 七杀</span><span>从概念回到本盘</span></header>
      <div class="detail-title"><span>深读</span><h1>压力如何成为可用的力量</h1></div>
      <div class="detail-sections">{sections}</div>
      <aside class="real-case-note"><b>本盘提示</b><p>{_e(case_note)}</p></aside>
      <footer><span>概念说明与个人判断分层呈现</span><b>025</b></footer>
    </article>
    """


def _styles() -> str:
    return """
    :root{--paper:#f5eee1;--ink:#26221d;--muted:#756b5f;--red:#9b342b;--jade:#386555;--gold:#a7894f}
    *{box-sizing:border-box}html,body{margin:0;min-height:100%}body{background:#211f1c;color:var(--ink);font-family:"Noto Serif SC","Source Han Serif SC","Songti SC",SimSun,serif}
    .case-book{display:grid;grid-template-columns:repeat(auto-fit,559px);gap:34px;justify-content:center;padding:38px}
    .art-page{position:relative;width:148mm;height:210mm;overflow:hidden;background:var(--paper);box-shadow:0 24px 70px rgba(0,0,0,.42)}
    .art-layer{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;pointer-events:none}.art-page>*:not(.art-layer){position:absolute;z-index:1}
    .running-head{top:7mm;left:12mm;right:12mm;display:flex;justify-content:space-between;padding-bottom:2mm;border-bottom:1px solid rgba(38,34,29,.22);color:#655c52;font:9px/1.2 Arial,sans-serif;letter-spacing:.15em}.running-head.light{color:#6b5c4c;border-color:rgba(85,67,50,.25)}
    footer{left:12mm;right:12mm;bottom:6mm;display:flex;justify-content:space-between;align-items:center;padding-top:2mm;border-top:1px solid rgba(38,34,29,.22);color:#6d6256;font:9px/1.2 Arial,sans-serif;letter-spacing:.12em}footer b{font:15px Georgia,serif;color:var(--red)}footer.light{color:#5d5044;border-color:rgba(85,67,50,.25)}
    .chart-page>h1{top:16mm;left:0;right:0;margin:0;text-align:center;font-size:43px;font-weight:500;letter-spacing:.16em}.chart-deck{top:31mm;left:20mm;right:20mm;margin:0;text-align:center;color:#6e6256;font-size:11px;letter-spacing:.08em}
    .relation-layer{top:36mm;left:0;width:100%;height:16mm;overflow:visible}.relation-layer text{font:9px "Noto Serif SC",SimSun,serif;paint-order:stroke;stroke:#f5eee1;stroke-width:4px;stroke-linejoin:round}
    .pillar-map{top:52mm;left:11mm;right:11mm;height:116mm;display:grid;grid-template-columns:repeat(4,1fr)}
    .pillar-lane{position:relative;text-align:center;border-left:1px solid rgba(154,127,76,.52);padding-top:2mm}.pillar-lane:last-child{border-right:1px solid rgba(154,127,76,.52)}.pillar-label{display:inline-block;padding:1.2mm 4mm;border-top:1px solid rgba(154,127,76,.6);border-bottom:1px solid rgba(154,127,76,.6);font-size:11px;letter-spacing:.15em}
    .day-mark{position:absolute;top:11mm;left:50%;transform:translateX(-50%);padding:1mm 3mm;border:1px solid rgba(155,52,43,.7);border-radius:50%;color:var(--red);font-size:8px}.stem,.branch{font-size:54px;line-height:1;font-weight:500}.stem{margin-top:13mm;color:#9b342b}.branch{margin-top:11mm;color:#315f52}.pillar-lane:nth-child(1) .stem,.pillar-lane:nth-child(4) .branch{color:#9a722f}.pillar-lane:nth-child(4) .stem,.pillar-lane:nth-child(2) .branch{color:#274b67}.ten-god{margin-top:3mm;color:#5f5549;font-size:10px}.hidden-label{margin-top:7mm;color:#8f7b5d;font-size:8px;letter-spacing:.18em}.hidden-stems{min-height:14mm;margin:2mm 2mm 0;color:#554b41;font-size:9px;line-height:1.7}.nayin{margin:3mm 3mm 0;padding-top:3mm;border-top:1px solid rgba(154,127,76,.42);color:#386555;font-size:11px;letter-spacing:.08em}.chart-caption{left:16mm;right:16mm;bottom:14mm;display:grid;grid-template-columns:20mm 1fr;gap:3mm;align-items:start}.chart-caption b{color:var(--red);font-size:10px;letter-spacing:.12em}.chart-caption span{font-size:9px;line-height:1.7;color:#5f564c}
    .wuxing-title{top:18mm;left:12mm;width:35mm;padding-left:5mm;border-left:1px solid rgba(38,34,29,.34)}.wuxing-title h1{margin:0;font-size:42px;line-height:1.16;font-weight:500;letter-spacing:.12em}.wuxing-title p{margin:4mm 0 0;font-size:12px;line-height:1.8}.wuxing-title p b{color:var(--red)}.cycle-lines{top:25mm;left:0;width:100%;height:156mm}.center-glyph{fill:#9b342b;font:28px "Noto Serif SC",SimSun,serif}.center-label{fill:#7b6854;font:9px "Noto Serif SC",SimSun,serif}
    .element-label{transform:translate(-50%,-50%);width:62px;height:62px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;text-shadow:0 1px 5px rgba(0,0,0,.35)}.element-label span{font-size:25px;line-height:1}.element-label b{margin-top:3px;font:14px Georgia,serif}.element-label.metal{color:#61584b;text-shadow:none}.element-label.earth{color:#6b5127;text-shadow:none}.wuxing-key{left:17mm;bottom:38mm;display:flex;gap:5mm;color:#665b4f;font-size:9px}.wuxing-key span{display:flex;align-items:center;gap:2mm}.wuxing-key i{display:block;width:14mm;border-top:1.5px solid #8c6c32}.wuxing-key i.dashed{border-color:#4b4841;border-style:dashed}.wuxing-conclusion{left:50mm;right:13mm;bottom:15mm;padding:3mm 0 0 5mm;border-left:3px solid var(--red)}.wuxing-conclusion b{color:var(--red);font-size:9px;letter-spacing:.16em}.wuxing-conclusion p{margin:1.5mm 0 0;font-size:9px;line-height:1.75}
    .qisha-hero-copy{top:19mm;left:13mm;width:73mm}.category-seal{display:grid;place-items:center;width:13mm;height:22mm;border:1px solid var(--red);color:var(--red);font-size:11px;line-height:1.35}.qisha-hero-copy h1{margin:7mm 0 1mm;font-size:65px;line-height:1;font-weight:500;letter-spacing:.08em}.qisha-hero-copy h2{margin:3mm 0 5mm;color:var(--red);font-size:16px;font-weight:500;letter-spacing:.1em}.qisha-hero-copy p{margin:0 0 3mm;font-size:11px;line-height:1.9}.qisha-hero-copy .case-hook{padding-top:3mm;border-top:1px solid rgba(154,127,76,.45);font-size:9px}.qisha-hero-copy .case-hook b{color:var(--red);font-size:12px}.qisha-cues{left:13mm;right:13mm;bottom:16mm;display:grid;grid-template-columns:repeat(3,1fr);gap:5mm}.qisha-cues div{padding-top:3mm;border-top:1px solid rgba(154,127,76,.65)}.qisha-cues b{display:block;color:var(--red);font-size:11px;margin-bottom:1.5mm}.qisha-cues span{display:block;font-size:8.5px;line-height:1.65;color:#554b41}
    .detail-title{top:16mm;left:14mm;right:24mm}.detail-title span{color:var(--red);font-size:9px;letter-spacing:.28em}.detail-title h1{margin:2mm 0 0;font-size:28px;font-weight:500;letter-spacing:.06em}.detail-sections{top:42mm;left:14mm;width:105mm;display:grid;grid-template-columns:1fr 1fr;column-gap:7mm;row-gap:4mm}.detail-sections section:last-child{grid-column:1/-1}.detail-sections h2{margin:0 0 1.5mm;padding-bottom:1.3mm;border-bottom:1px solid rgba(154,127,76,.4);color:var(--red);font-size:12px;letter-spacing:.1em}.detail-sections p{margin:0;font-size:11px;line-height:1.72;text-align:justify}.real-case-note{left:14mm;width:105mm;bottom:14mm;padding:3.5mm 4mm;background:rgba(246,239,227,.74);border-left:3px solid var(--red)}.real-case-note b{color:var(--red);font-size:11px;letter-spacing:.16em}.real-case-note p{margin:1.5mm 0 0;font-size:10.2px;line-height:1.65}
    @page{size:A5;margin:0}@media print{body{background:#fff}.case-book{display:block;padding:0}.art-page{box-shadow:none;break-after:page}}
    """


def render_artbook_case_html(facts: dict, *, asset_prefix: str = "../../../assets/mingshu/backgrounds") -> str:
    """Render a self-contained four-page real-case art-direction proof."""
    pages = (
        _bazi_page(facts, asset_prefix),
        _wuxing_page(facts, asset_prefix),
        _qisha_opener(facts, asset_prefix),
        _qisha_detail(facts, asset_prefix),
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mirror 命书 · 真实案例艺术样张</title><style>{_styles()}</style></head>
<body><main class="case-book" data-testid="artbook-case">{''.join(pages)}</main></body></html>"""


def write_artbook_case_html(facts: dict, output_path: str | Path, *, asset_prefix: str = "../../../assets/mingshu/backgrounds") -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_artbook_case_html(facts, asset_prefix=asset_prefix), encoding="utf-8")
    return output.resolve()


def _draw_background(canvas: Canvas, spec: PrintSpec, key: str) -> None:
    path = ASSET_DIR / BACKGROUND_ASSETS[key]
    if not path.exists():
        raise FileNotFoundError(path)
    width, height = spec.page_size
    canvas.drawImage(ImageReader(str(path)), 0, 0, width, height, preserveAspectRatio=False, mask="auto")


def _pdf_frame(canvas: Canvas, spec: PrintSpec, page: int, left_label: str, right_label: str, sans: str) -> None:
    width, height = spec.page_size
    inset = spec.bleed + 12 * mm
    canvas.setStrokeColor(HexColor("#958978"))
    canvas.setLineWidth(.35)
    canvas.line(inset, height - spec.bleed - 9 * mm, width - inset, height - spec.bleed - 9 * mm)
    canvas.line(inset, spec.bleed + 9 * mm, width - inset, spec.bleed + 9 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 5.8)
    canvas.drawString(inset, height - spec.bleed - 7 * mm, _safe_text(left_label))
    canvas.drawRightString(width - inset, height - spec.bleed - 7 * mm, _safe_text(right_label))
    canvas.setFillColor(CINNABAR)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - inset, spec.bleed + 5 * mm, f"{page:03d}")


def _pdf_bazi(canvas: Canvas, spec: PrintSpec, facts: dict, sans: str, serif: str) -> None:
    _draw_background(canvas, spec, "chart")
    _pdf_frame(canvas, spec, 8, "原局 · 四柱全盘", "八字原盘", sans)
    width, height = spec.page_size
    left = spec.bleed + 12 * mm
    usable = spec.trim_width - 24 * mm
    top = spec.bleed + spec.trim_height
    canvas.setFillColor(INK)
    canvas.setFont(serif, 26)
    canvas.drawCentredString(width / 2, top - 24 * mm, "八字原盘")
    day_master = _day_master(facts)
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 6.5)
    canvas.drawCentredString(width / 2, top - 32 * mm, _safe_text(f"日主为{day_master.get('label')}{day_master.get('wuxing_label')}，先看四柱，再看结构关系"))
    lane_w = usable / 4
    for index, pillar in enumerate(_pillars(facts)[:4]):
        x0 = left + index * lane_w
        cx = x0 + lane_w / 2
        canvas.setStrokeColor(HexColor("#ad9365"))
        canvas.setLineWidth(.5)
        canvas.line(x0, top - 52 * mm, x0, top - 164 * mm)
        if index == 3:
            canvas.line(x0 + lane_w, top - 52 * mm, x0 + lane_w, top - 164 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont(sans, 6.3)
        canvas.drawCentredString(cx, top - 57 * mm, _safe_text(pillar.get("label")))
        gan = pillar.get("gan") or {}
        zhi = pillar.get("zhi") or {}
        canvas.setFillColor(CINNABAR if index in (1, 2) else GOLD)
        if index == 3:
            canvas.setFillColor(HexColor("#274b67"))
        canvas.setFont(serif, 29)
        canvas.drawCentredString(cx, top - 74 * mm, _safe_text(gan.get("name_label")))
        canvas.setFillColor(MUTED)
        canvas.setFont(sans, 5.8)
        canvas.drawCentredString(cx, top - 82 * mm, _safe_text(gan.get("shishen_label")))
        canvas.setFillColor(JADE if index not in (1, 3) else HexColor("#274b67" if index == 1 else "#9a722f"))
        canvas.setFont(serif, 29)
        canvas.drawCentredString(cx, top - 103 * mm, _safe_text(zhi.get("name_label")))
        canvas.setFillColor(GOLD)
        canvas.setFont(sans, 5.4)
        canvas.drawCentredString(cx, top - 112 * mm, "藏干")
        _draw_text(canvas, _hidden_text(pillar), x0 + 2 * mm, top - 119 * mm, lane_w - 4 * mm, font=sans, size=5.3, leading=8.3, color=INK, max_lines=3)
        canvas.setStrokeColor(HexColor("#b59b71"))
        canvas.line(x0 + 3 * mm, top - 139 * mm, x0 + lane_w - 3 * mm, top - 139 * mm)
        canvas.setFillColor(JADE)
        canvas.setFont(serif, 6.8)
        canvas.drawCentredString(cx, top - 147 * mm, _safe_text((pillar.get("nayin") or {}).get("label")))
    network = (facts.get("visuals") or {}).get("origin_network") or {}
    pillar_keys = {pillar.get("key"): left + (index + .5) * lane_w for index, pillar in enumerate((network.get("pillars") or [])[:4])}
    for index, relation in enumerate((network.get("relations") or [])[:3]):
        members = relation.get("members") or []
        if len(members) < 2:
            continue
        x1 = pillar_keys.get(members[0].get("pillar"), left + lane_w / 2)
        x2 = pillar_keys.get(members[1].get("pillar"), left + usable - lane_w / 2)
        y = top - (39 + index * 5) * mm
        label = relation.get("label") or "作用"
        field_label = "干" if relation.get("field") == "stem" else "支"
        tension = any(word in label for word in ("冲", "刑", "穿", "害", "破"))
        color = CINNABAR if tension else JADE
        canvas.setStrokeColor(color)
        canvas.setLineWidth(.75)
        path = canvas.beginPath()
        path.moveTo(x1, y)
        path.curveTo((x1 + x2) / 2, y + 3.2 * mm, (x1 + x2) / 2, y + 3.2 * mm, x2, y)
        canvas.drawPath(path, stroke=1, fill=0)
        canvas.circle(x1, y, 1.05, stroke=0, fill=1)
        canvas.circle(x2, y, 1.05, stroke=0, fill=1)
        canvas.setFillColor(color)
        canvas.setFont(sans, 4.8)
        canvas.drawCentredString((x1 + x2) / 2, y + 3.7 * mm, _safe_text(f"{field_label} · {label}"))
    _draw_text(canvas, "天干看显露，地支看根基，藏干看潜在通道；关系线只表示结构牵动，不直接对应某件吉凶事件。", left + 6 * mm, spec.bleed + 19 * mm, usable - 12 * mm, font=sans, size=6.1, leading=9.4, color=MUTED, max_lines=3)


def _pdf_wuxing(canvas: Canvas, spec: PrintSpec, facts: dict, sans: str, serif: str) -> None:
    _draw_background(canvas, spec, "wuxing")
    _pdf_frame(canvas, spec, 12, "原局 · 五行", "结构重心与流通", sans)
    width, height = spec.page_size
    top = spec.bleed + spec.trim_height
    left = spec.bleed + 12 * mm
    canvas.setFillColor(INK)
    canvas.setFont(serif, 23)
    canvas.drawString(left, top - 25 * mm, "五行气势")
    day_master = _day_master(facts)
    canvas.setFillColor(CINNABAR)
    canvas.setFont(serif, 9)
    canvas.drawString(left, top - 34 * mm, _safe_text(f"日主 · {day_master.get('label')}{day_master.get('wuxing_label')}"))
    positions = {
        "WUXING:MU": (45, 142),
        "WUXING:HUO": (103, 143),
        "WUXING:TU": (114, 99),
        "WUXING:JIN": (34, 96),
        "WUXING:SHUI": (74, 62),
    }
    items = _wuxing_map(facts)
    points = []
    order = ["WUXING:MU", "WUXING:HUO", "WUXING:TU", "WUXING:JIN", "WUXING:SHUI"]
    for code in order:
        x_mm, y_mm = positions[code]
        points.append((spec.bleed + x_mm * mm, spec.bleed + y_mm * mm))
    canvas.setStrokeColor(HexColor("#8c6c32"))
    canvas.setLineWidth(.7)
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        canvas.line(x1, y1, x2, y2)
    for code, (x, y) in zip(order, points):
        item = items.get(code, {})
        color = HexColor(ELEMENT_COLORS[code])
        canvas.setFillColor(color)
        canvas.setFont(serif, 16)
        canvas.drawCentredString(x, y + 1 * mm, _safe_text(item.get("label")))
        canvas.setFont("Helvetica", 6.7)
        canvas.drawCentredString(x, y - 5 * mm, f"{float(item.get('percent') or 0):.1f}%")
    cx = spec.bleed + 74 * mm
    cy = spec.bleed + 105 * mm
    canvas.setFillColor(PAPER)
    canvas.setStrokeColor(CINNABAR)
    canvas.circle(cx, cy, 9 * mm, stroke=1, fill=1)
    canvas.setFillColor(CINNABAR)
    canvas.setFont(serif, 13)
    canvas.drawCentredString(cx, cy + 1 * mm, _safe_text(day_master.get("label")))
    canvas.setFont(sans, 4.8)
    canvas.drawCentredString(cx, cy - 4 * mm, "日主")
    _draw_text(canvas, _wuxing_conclusion(facts), left + 31 * mm, spec.bleed + 18 * mm, spec.trim_width - 57 * mm, font=sans, size=6.1, leading=9.3, color=INK, max_lines=5)


def _pdf_qisha_opener(canvas: Canvas, spec: PrintSpec, facts: dict, sans: str, serif: str) -> None:
    _draw_background(canvas, spec, "qisha_opener")
    _pdf_frame(canvas, spec, 24, "十神 · 一页深读", "压力与边界", sans)
    top = spec.bleed + spec.trim_height
    left = spec.bleed + 13 * mm
    summary = _qisha_case_summary(facts)
    canvas.setFillColor(CINNABAR)
    canvas.rect(left, top - 43 * mm, 10 * mm, 18 * mm, stroke=1, fill=0)
    canvas.setFont(serif, 7)
    canvas.drawCentredString(left + 5 * mm, top - 32 * mm, "官")
    canvas.drawCentredString(left + 5 * mm, top - 38 * mm, "杀")
    canvas.setFillColor(INK)
    canvas.setFont(serif, 39)
    canvas.drawString(left, top - 66 * mm, "七杀")
    canvas.setFillColor(CINNABAR)
    canvas.setFont(serif, 10)
    canvas.drawString(left, top - 78 * mm, "逆风成刃，临界见真章")
    _draw_text(canvas, "七杀常用来观察直接压力、竞争环境、风险反应和果断行动。它不是“凶”的同义词，而是一种人在限制条件下如何判断、承担和建立边界的语言。", left, top - 88 * mm, 70 * mm, font=serif, size=7, leading=11, color=INK, max_lines=6)
    _draw_text(canvas, f"在这张真实命盘里，七杀占十神力量的 {summary['qisha_percent']:.1f}%，并由{summary['visible']}直接显出。", left, top - 121 * mm, 70 * mm, font=sans, size=6, leading=9.3, color=MUTED, max_lines=4)
    cues = (("顺势", "抓重点 · 敢承担 · 临场决断"), ("失衡", "过度警觉 · 节奏过紧 · 凡事战斗化"), ("转化", "规则 · 预案 · 反馈 · 恢复"))
    cue_w = (spec.trim_width - 26 * mm - 8 * mm) / 3
    y = spec.bleed + 24 * mm
    for index, (title, text) in enumerate(cues):
        x = left + index * (cue_w + 4 * mm)
        canvas.setStrokeColor(GOLD)
        canvas.line(x, y + 20 * mm, x + cue_w, y + 20 * mm)
        canvas.setFillColor(CINNABAR)
        canvas.setFont(serif, 7.4)
        canvas.drawString(x, y + 14 * mm, title)
        _draw_text(canvas, text, x, y + 8 * mm, cue_w, font=sans, size=5.2, leading=8, color=INK, max_lines=3)


def _pdf_qisha_detail(canvas: Canvas, spec: PrintSpec, facts: dict, sans: str, serif: str) -> None:
    _draw_background(canvas, spec, "qisha_text")
    _pdf_frame(canvas, spec, 25, "十神 · 七杀", "从概念回到本盘", sans)
    page = KNOWLEDGE_PAGE_INDEX["SHISHEN:QISHA"]
    top = spec.bleed + spec.trim_height
    left = spec.bleed + 14 * mm
    width = 103 * mm
    canvas.setFillColor(CINNABAR)
    canvas.setFont(sans, 6)
    canvas.drawString(left, top - 21 * mm, "深读")
    canvas.setFillColor(INK)
    canvas.setFont(serif, 18)
    canvas.drawString(left, top - 31 * mm, "压力如何成为可用的力量")
    col_gap = 7 * mm
    col_w = (width - col_gap) / 2
    y_positions = [top - 47 * mm, top - 47 * mm, top - 93 * mm, top - 93 * mm, top - 137 * mm]
    x_positions = [left, left + col_w + col_gap, left, left + col_w + col_gap, left]
    section_widths = [col_w, col_w, col_w, col_w, width]
    for index, (title, text) in enumerate(page.deep_sections):
        x = x_positions[index]
        y = y_positions[index]
        w = section_widths[index]
        canvas.setFillColor(CINNABAR)
        canvas.setFont(serif, 8)
        canvas.drawString(x, y, _safe_text(title))
        canvas.setStrokeColor(HexColor("#bba37a"))
        canvas.line(x, y - 2 * mm, x + w, y - 2 * mm)
        _draw_text(canvas, text, x, y - 6 * mm, w, font=sans, size=6.35, leading=9.3, color=INK, max_lines=8 if index < 4 else 5)
    summary = _qisha_case_summary(facts)
    case_note = (
        f"本盘七杀为 {summary['qisha_percent']:.1f}%，{summary['visible']}；正官为 {summary['zhengguan_percent']:.1f}%。"
        "官与杀同时构成较明显的规则—压力通道。命盘也见食神、伤官与印星；是否形成有效制化，仍要结合季节、根气和柱位。这些条件尚未完全归于七杀格的成立逻辑，因此暂不以七杀格定论。"
    )
    canvas.setFillColor(HexColor("#f1e4d3"))
    canvas.setFillAlpha(.82)
    canvas.rect(left, spec.bleed + 16 * mm, width, 29 * mm, stroke=0, fill=1)
    canvas.setFillAlpha(1)
    canvas.setFillColor(CINNABAR)
    canvas.setFont(serif, 7.8)
    canvas.drawString(left + 4 * mm, spec.bleed + 38 * mm, "本盘提示")
    _draw_text(canvas, case_note, left + 4 * mm, spec.bleed + 34 * mm, width - 8 * mm, font=sans, size=6.1, leading=9.1, color=INK, max_lines=7)


def render_artbook_case_pdf(facts: dict, output_path: str | Path, *, bleed_mm: float = 0.0) -> Path:
    """Render the four-page real-case proof as an A5 PDF."""
    _load_pdf_runtime()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    spec = PrintSpec(bleed_mm=bleed_mm)
    sans, serif = register_fonts()
    canvas = Canvas(str(output), pagesize=spec.page_size, pageCompression=1)
    canvas.setTitle("Mirror 命书 · 真实案例艺术样张")
    canvas.setAuthor("MirrorAI")
    for drawer in (_pdf_bazi, _pdf_wuxing, _pdf_qisha_opener, _pdf_qisha_detail):
        drawer(canvas, spec, facts, sans, serif)
        canvas.showPage()
    canvas.save()
    return output.resolve()
