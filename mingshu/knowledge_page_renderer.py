"""Render reusable MingShu knowledge pages to A5 PDF and browser HTML."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from .knowledge_pages import KnowledgePage
from .pdf_renderer import (
    CINNABAR,
    GOLD,
    GOLD_LIGHT,
    INK,
    JADE,
    MUTED,
    PAPER,
    PAPER_DARK,
    WHITE,
    PrintSpec,
    _draw_crop_marks,
    _draw_text,
    _safe_text,
    register_fonts,
)


TONE_COLORS = {
    "jade": (JADE, HexColor("#dfe9e1")),
    "cinnabar": (CINNABAR, HexColor("#f1dfda")),
    "gold": (GOLD, HexColor("#eee4d2")),
    "water": (HexColor("#344d63"), HexColor("#e0e6e8")),
}


def _set_alpha(canvas: Canvas, *, fill: float | None = None, stroke: float | None = None) -> None:
    if fill is not None:
        canvas.setFillAlpha(fill)
    if stroke is not None:
        canvas.setStrokeAlpha(stroke)


def _paper(canvas: Canvas, spec: PrintSpec, accent: Color, page_number: int) -> None:
    width, height = spec.page_size
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    canvas.saveState()
    canvas.setFillColor(PAPER_DARK)
    _set_alpha(canvas, fill=0.42)
    canvas.circle(width - spec.bleed + 10 * mm, height - spec.bleed + 8 * mm, 34 * mm, stroke=0, fill=1)
    canvas.setStrokeColor(accent)
    _set_alpha(canvas, stroke=0.06)
    canvas.setLineWidth(0.75)
    x0 = spec.bleed - 9 * mm
    y0 = spec.bleed + 3 * mm
    canvas.bezier(x0, y0, x0 + 17 * mm, y0 + 24 * mm, x0 + 29 * mm, y0 - 3 * mm, x0 + 47 * mm, y0 + 13 * mm)
    canvas.bezier(x0 - 2 * mm, y0 - 3 * mm, x0 + 13 * mm, y0 + 12 * mm, x0 + 35 * mm, y0 - 7 * mm, x0 + 58 * mm, y0 + 8 * mm)
    if page_number % 2 == 0:
        canvas.line(width - spec.bleed - 7 * mm, height - spec.bleed, width - spec.bleed - 14 * mm, height - spec.bleed - 30 * mm)
    canvas.restoreState()
    if spec.bleed:
        _draw_crop_marks(canvas, spec)


def _motif_waves(canvas: Canvas, x: float, y: float, w: float, accent: Color) -> None:
    canvas.setStrokeColor(accent)
    canvas.setLineWidth(1.0)
    for offset in (0, 6, 12):
        yy = y + offset * mm
        canvas.bezier(x, yy, x + w * 0.22, yy + 7 * mm, x + w * 0.31, yy - 6 * mm, x + w * 0.5, yy)
        canvas.bezier(x + w * 0.5, yy, x + w * 0.69, yy + 6 * mm, x + w * 0.79, yy - 7 * mm, x + w, yy)


def _motif_mountains(canvas: Canvas, x: float, y: float, w: float, h: float, accent: Color) -> None:
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1.05)
    path = canvas.beginPath()
    path.moveTo(x, y)
    path.lineTo(x + w * 0.18, y + h * 0.36)
    path.lineTo(x + w * 0.31, y + h * 0.15)
    path.lineTo(x + w * 0.52, y + h * 0.72)
    path.lineTo(x + w * 0.67, y + h * 0.29)
    path.lineTo(x + w * 0.82, y + h * 0.51)
    path.lineTo(x + w, y)
    canvas.drawPath(path, stroke=1, fill=0)
    canvas.setStrokeColor(accent)
    canvas.setLineWidth(0.7)
    canvas.line(x + w * 0.52, y + h * 0.72, x + w * 0.48, y + h * 0.43)


def _draw_motif(
    canvas: Canvas,
    motif: str,
    x: float,
    y: float,
    width: float,
    height: float,
    accent: Color,
    wash: Color,
) -> None:
    cx, cy = x + width / 2, y + height / 2
    canvas.saveState()
    canvas.setFillColor(wash)
    _set_alpha(canvas, fill=0.72)
    canvas.circle(cx, cy, min(width, height) * 0.45, stroke=0, fill=1)
    _set_alpha(canvas, fill=1, stroke=1)

    if motif in {"spring", "pages"}:
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1.0)
        for delta in (-8, 0, 8):
            path = canvas.beginPath()
            path.moveTo(cx, y + 8 * mm)
            path.curveTo(cx + delta * 0.22 * mm, cy - 3 * mm, cx + delta * mm, cy + 3 * mm, cx + delta * mm, y + height - 8 * mm)
            canvas.drawPath(path, stroke=1, fill=0)
        canvas.setFillColor(GOLD)
        canvas.circle(cx, y + 9 * mm, 2.2 * mm, stroke=0, fill=1)
    elif motif in {"ridge", "blade", "edge"}:
        _motif_mountains(canvas, x + 8 * mm, y + 7 * mm, width - 16 * mm, height - 14 * mm, accent)
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(2.1)
        canvas.line(cx - 4 * mm, y + 8 * mm, cx + 10 * mm, y + height - 8 * mm)
    elif motif in {"orchard", "forest"}:
        canvas.setStrokeColor(INK)
        canvas.setLineWidth(0.9)
        trunks = 5 if motif == "forest" else 3
        for index in range(trunks):
            tx = x + width * (index + 1) / (trunks + 1)
            top = y + height * (0.57 + (index % 2) * 0.12)
            canvas.line(tx, y + 8 * mm, tx, top)
            canvas.setStrokeColor(accent)
            canvas.line(tx, top - 5 * mm, tx - 6 * mm, top + 2 * mm)
            canvas.line(tx, top - 1 * mm, tx + 6 * mm, top + 6 * mm)
            canvas.setStrokeColor(INK)
            canvas.setFillColor(accent if index % 2 == 0 else GOLD)
            canvas.circle(tx + (3 if index % 2 else -3) * mm, top + 5 * mm, 1.6 * mm, stroke=0, fill=1)
    elif motif == "ripple":
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(0.8)
        for radius in (7, 14, 22, 30):
            canvas.circle(cx, cy, radius * mm, stroke=1, fill=0)
        canvas.setFillColor(GOLD)
        canvas.circle(cx, cy, 2.5 * mm, stroke=0, fill=1)
    elif motif == "bridge":
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1.4)
        path = canvas.beginPath()
        path.moveTo(x + 9 * mm, y + 12 * mm)
        path.curveTo(cx - 12 * mm, y + height - 4 * mm, cx + 12 * mm, y + height - 4 * mm, x + width - 9 * mm, y + 12 * mm)
        canvas.drawPath(path, stroke=1, fill=0)
        canvas.setFillColor(GOLD)
        for sx, sy in ((0.31, 0.66), (0.5, 0.82), (0.69, 0.66)):
            canvas.circle(x + width * sx, y + height * sy, 1.6 * mm, stroke=0, fill=1)
    elif motif == "moon":
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1.1)
        canvas.circle(cx, cy + 5 * mm, 19 * mm, stroke=1, fill=0)
        _motif_waves(canvas, x + 7 * mm, y + 7 * mm, width - 14 * mm, accent)
    elif motif == "sea-metal":
        _motif_waves(canvas, x + 4 * mm, y + 8 * mm, width - 8 * mm, accent)
        canvas.setFillColor(GOLD)
        canvas.circle(cx, cy - 2 * mm, 8 * mm, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.circle(cx - 2 * mm, cy + 1 * mm, 2.2 * mm, stroke=0, fill=1)
    elif motif == "mountain-fire":
        _motif_mountains(canvas, x + 5 * mm, y + 5 * mm, width - 10 * mm, height - 10 * mm, accent)
        canvas.setStrokeColor(CINNABAR)
        canvas.setLineWidth(1.2)
        for delta in (-6, 0, 6):
            path = canvas.beginPath()
            path.moveTo(cx + delta * mm, y + height * 0.66)
            path.curveTo(cx + (delta - 4) * mm, y + height * 0.76, cx + (delta + 5) * mm, y + height * 0.84, cx + delta * mm, y + height * 0.94)
            canvas.drawPath(path, stroke=1, fill=0)
    else:
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(0.9)
        canvas.circle(cx, cy, 23 * mm, stroke=1, fill=0)
        canvas.line(cx - 25 * mm, cy, cx + 25 * mm, cy)
    canvas.restoreState()


def _draw_section(
    canvas: Canvas,
    label: str,
    title: str,
    text: str,
    x: float,
    y: float,
    width: float,
    sans: str,
    serif: str,
    accent: Color,
) -> None:
    canvas.setFillColor(accent)
    canvas.setFont(serif, 12)
    canvas.drawString(x, y, label)
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 5.6)
    canvas.drawString(x + 9 * mm, y + 1.2 * mm, title)
    _draw_text(
        canvas,
        text,
        x + 9 * mm,
        y - 3.5 * mm,
        width - 9 * mm,
        font=sans,
        size=6.7,
        leading=9.4,
        color=INK,
        max_lines=3,
    )


def _draw_page(
    canvas: Canvas,
    page: KnowledgePage,
    page_number: int,
    page_count: int,
    spec: PrintSpec,
    sans: str,
    serif: str,
) -> None:
    accent, wash = TONE_COLORS.get(page.tone, TONE_COLORS["gold"])
    _paper(canvas, spec, accent, page_number)
    bleed = spec.bleed
    left = bleed + 15 * mm
    right = bleed + spec.trim_width - 15 * mm
    width = right - left
    top = bleed + spec.trim_height

    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 6.3)
    canvas.drawString(left, top - 10 * mm, f"{page_number:02d} / {page_count:02d}")
    canvas.drawRightString(right, top - 10 * mm, "MIRROR · MINGSHU NOTES")

    kicker_y = top - 25 * mm
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.55)
    canvas.line(left + 30 * mm, kicker_y + 1.2 * mm, left + 43 * mm, kicker_y + 1.2 * mm)
    canvas.line(right - 43 * mm, kicker_y + 1.2 * mm, right - 30 * mm, kicker_y + 1.2 * mm)
    canvas.setFillColor(GOLD)
    canvas.setFont(sans, 6.5)
    canvas.drawCentredString((left + right) / 2, kicker_y, _safe_text(f"{page.category} · 一页读懂"))

    canvas.setFillColor(INK)
    canvas.setFont(serif, 28)
    canvas.drawCentredString((left + right) / 2, top - 41 * mm, _safe_text(page.name))
    canvas.setFillColor(accent)
    canvas.setFont(serif, 9.3)
    canvas.drawCentredString((left + right) / 2, top - 51 * mm, _safe_text(page.tagline))

    motif_y = top - 101 * mm
    _draw_motif(canvas, page.motif, left + 10 * mm, motif_y, width - 20 * mm, 40 * mm, accent, wash)

    _draw_text(
        canvas,
        page.lead,
        left + 2 * mm,
        top - 110 * mm,
        width - 4 * mm,
        font=serif,
        size=8.1,
        leading=12.4,
        color=INK,
        max_lines=3,
    )

    _draw_section(canvas, "顺", "顺势时", page.flowing, left, top - 132 * mm, width, sans, serif, accent)
    _draw_section(canvas, "偏", "过度时", page.overdrive, left, top - 153 * mm, width, sans, serif, accent)
    _draw_section(canvas, "用", "怎么用", page.practice, left, top - 174 * mm, width, sans, serif, accent)

    note_y = bleed + 20 * mm
    canvas.setStrokeColor(accent)
    canvas.setLineWidth(1.1)
    canvas.line(left, note_y - 1 * mm, left, note_y + 10 * mm)
    canvas.setFillColor(accent)
    canvas.setFont(sans, 5.5)
    canvas.drawString(left + 4 * mm, note_y + 7 * mm, "放回命盘里看")
    _draw_text(
        canvas,
        page.chart_note,
        left + 4 * mm,
        note_y + 2 * mm,
        width - 4 * mm,
        font=sans,
        size=5.8,
        leading=8.2,
        color=MUTED,
        max_lines=3,
    )

    footer_y = bleed + 8 * mm
    canvas.setStrokeColor(GOLD_LIGHT)
    canvas.setLineWidth(0.45)
    canvas.line(left, footer_y + 3 * mm, right, footer_y + 3 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 5.2)
    canvas.drawString(left, footer_y, _safe_text(page.category))
    canvas.drawRightString(right, footer_y, _safe_text(f"一页读懂 · {page.name}"))


def render_knowledge_pages_pdf(
    pages: Iterable[KnowledgePage],
    output_path: str | Path,
    *,
    bleed_mm: float = 0.0,
) -> Path:
    pages = tuple(pages)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    spec = PrintSpec(bleed_mm=bleed_mm)
    sans, serif = register_fonts()
    canvas = Canvas(str(output), pagesize=spec.page_size, pageCompression=1)
    canvas.setTitle("Mirror 命书固定知识页样张")
    canvas.setAuthor("Mirror AI Agent")
    for index, page in enumerate(pages, 1):
        _draw_page(canvas, page, index, len(pages), spec, sans, serif)
        canvas.showPage()
    canvas.save()
    return output.resolve()


def _svg_motif(page: KnowledgePage) -> str:
    accent = {
        "jade": "#345e4a",
        "cinnabar": "#8c261e",
        "gold": "#a8894f",
        "water": "#344d63",
    }.get(page.tone, "#a8894f")
    common = f'fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
    if page.motif in {"ridge", "blade", "edge"}:
        drawing = f'<path d="M40 150 L95 86 L132 125 L196 42 L245 124 L292 78 L360 150" {common}/><path d="M190 151 L222 44" stroke="{accent}" stroke-width="5"/>'
    elif page.motif in {"orchard", "forest"}:
        drawing = "".join(
            f'<path d="M{x} 154 V{70 + (i % 2) * 16} M{x} {90 + (i % 2) * 12} l-18 -15 M{x} {82 + (i % 2) * 12} l20 -18" {common}/><circle cx="{x + (8 if i % 2 else -8)}" cy="{58 + (i % 2) * 14}" r="6" fill="{accent}" opacity=".78"/>'
            for i, x in enumerate((82, 132, 182, 232, 282))
        )
    elif page.motif in {"spring", "pages"}:
        drawing = f'<path d="M180 158 C176 118 150 98 132 48 M180 158 C180 112 180 86 180 36 M180 158 C184 118 210 98 228 48" {common}/><circle cx="180" cy="158" r="8" fill="#a8894f"/>'
    elif page.motif in {"ripple", "moon"}:
        drawing = "".join(f'<circle cx="180" cy="92" r="{r}" {common} opacity="{0.9-r/170:.2f}"/>' for r in (24, 46, 70))
    elif page.motif == "bridge":
        drawing = f'<path d="M48 148 Q180 10 312 148" {common}/><circle cx="120" cy="72" r="6" fill="#a8894f"/><circle cx="180" cy="42" r="7" fill="#a8894f"/><circle cx="240" cy="72" r="6" fill="#a8894f"/>'
    elif page.motif == "sea-metal":
        drawing = f'<path d="M30 70 Q75 35 120 70 T210 70 T330 70 M30 104 Q75 69 120 104 T210 104 T330 104 M30 138 Q75 103 120 138 T210 138 T330 138" {common}/><circle cx="180" cy="106" r="34" fill="#a8894f"/><circle cx="168" cy="94" r="9" fill="#fffdf8"/>'
    elif page.motif == "mountain-fire":
        drawing = f'<path d="M32 150 L100 82 L148 124 L210 50 L260 118 L310 88 L340 150" {common}/><path d="M186 60 C170 38 194 26 184 8 M210 52 C198 32 220 22 214 2 M232 62 C218 42 244 34 236 14" stroke="#8c261e" stroke-width="3" fill="none"/>'
    else:
        drawing = f'<circle cx="180" cy="92" r="64" {common}/>'
    return f'<svg viewBox="0 0 360 175" aria-hidden="true"><circle cx="180" cy="90" r="78" fill="{accent}" opacity=".075"/>{drawing}</svg>'


def render_knowledge_pages_html(pages: Iterable[KnowledgePage]) -> str:
    pages = tuple(pages)
    articles = []
    for index, page in enumerate(pages, 1):
        e = html.escape
        articles.append(
            f"""
            <article class="knowledge-page" id="page-{index}">
              <header class="runhead"><span>{index:02d} / {len(pages):02d}</span><span>MIRROR · MINGSHU NOTES</span></header>
              <div class="kicker"><i></i><span>{e(page.category)} · 一页读懂</span><i></i></div>
              <h1>{e(page.name)}</h1>
              <p class="tagline">{e(page.tagline)}</p>
              <div class="motif">{_svg_motif(page)}</div>
              <p class="lead">{e(page.lead)}</p>
              <div class="reading-row"><b>顺</b><div><small>顺势时</small><p>{e(page.flowing)}</p></div></div>
              <div class="reading-row"><b>偏</b><div><small>过度时</small><p>{e(page.overdrive)}</p></div></div>
              <div class="reading-row"><b>用</b><div><small>怎么用</small><p>{e(page.practice)}</p></div></div>
              <aside><strong>放回命盘里看</strong><p>{e(page.chart_note)}</p></aside>
              <footer><span>{e(page.category)}</span><span>一页读懂 · {e(page.name)}</span></footer>
            </article>"""
        )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mirror 命书固定知识页样张</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700;900&display=swap');
:root{{--paper:#f7f4ed;--ink:#282622;--muted:#786b5b;--red:#8c261e;--gold:#a8894f;--line:#e3d8c4}}
*{{box-sizing:border-box}} body{{margin:0;background:#2a2825;color:var(--ink);font-family:"Noto Serif SC",SimSun,serif}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,559px));gap:34px;justify-content:center;padding:38px}}
.knowledge-page{{width:148mm;height:210mm;position:relative;overflow:hidden;padding:15mm;background:radial-gradient(75% 48% at 106% -4%,rgba(52,94,74,.045),transparent 60%),radial-gradient(80% 45% at -5% 105%,rgba(40,38,34,.055),transparent 58%),var(--paper);box-shadow:0 22px 60px rgba(0,0,0,.38)}}
.runhead{{display:flex;justify-content:space-between;color:var(--muted);font:10px Georgia,serif;letter-spacing:.12em}}
.kicker{{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:25px;color:var(--gold);font-size:11px;letter-spacing:.2em}} .kicker i{{width:48px;height:1px;background:var(--gold);opacity:.65}}
h1{{margin:12px 0 5px;text-align:center;font-size:45px;letter-spacing:.18em}} .tagline{{margin:0;text-align:center;color:var(--red);font-size:15px;letter-spacing:.12em}}
.motif{{height:166px;display:grid;place-items:center;margin:2px 20px 0}} .motif svg{{width:100%;height:100%}}
.lead{{margin:0 8px 13px;font-size:13px;line-height:1.8}}
.reading-row{{display:grid;grid-template-columns:34px 1fr;gap:12px;margin:8px 0}} .reading-row>b{{color:var(--gold);font-size:22px;font-weight:500}} .reading-row small{{color:var(--muted);letter-spacing:.15em}} .reading-row p{{margin:2px 0 0;font-size:11px;line-height:1.65}}
aside{{position:absolute;left:15mm;right:15mm;bottom:19mm;border-left:3px solid var(--red);padding-left:11px}} aside strong{{color:var(--red);font-size:10px;letter-spacing:.15em}} aside p{{margin:3px 0 0;color:var(--muted);font-size:9px;line-height:1.55}}
footer{{position:absolute;left:15mm;right:15mm;bottom:8mm;display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:7px;color:var(--muted);font-size:8px;letter-spacing:.1em}}
@page{{size:A5;margin:0}} @media print{{body{{background:white}}.gallery{{display:block;padding:0}}.knowledge-page{{box-shadow:none;break-after:page}}}}
</style></head><body><main class="gallery">{''.join(articles)}</main></body></html>"""


def write_knowledge_pages_html(pages: Iterable[KnowledgePage], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_knowledge_pages_html(pages), encoding="utf-8")
    return output.resolve()
