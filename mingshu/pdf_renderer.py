"""ReportLab renderer for the 80-page A5 MingShu proof.

The output uses one PDF page per physical book page. Printers can impose these
single pages for saddle stitch or perfect binding; the application does not
hard-code a printer-specific imposition scheme.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


INK = HexColor("#282622")
MUTED = HexColor("#786b5b")
PAPER = HexColor("#f7f4ed")
PAPER_DARK = HexColor("#eee8dc")
JADE = HexColor("#345e4a")
JADE_LIGHT = HexColor("#e4ebe3")
CINNABAR = HexColor("#8c261e")
CINNABAR_LIGHT = HexColor("#f1dfda")
GOLD = HexColor("#a8894f")
GOLD_LIGHT = HexColor("#e3d8c4")
WHITE = HexColor("#fffdf8")

ELEMENT_COLORS = {
    "WUXING:MU": HexColor("#4f7c64"),
    "WUXING:HUO": HexColor("#b84a3a"),
    "WUXING:TU": HexColor("#b58b52"),
    "WUXING:JIN": HexColor("#87929b"),
    "WUXING:SHUI": HexColor("#3e6176"),
}

SECTION_LABELS = {
    "front_matter": "卷首",
    "chart": "排盘",
    "origin": "原局",
    "luck": "岁运",
    "special_topics": "专项",
    "appendix": "附录",
}

_DASH_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)


@dataclass(frozen=True)
class PrintSpec:
    trim_width: float = A5[0]
    trim_height: float = A5[1]
    bleed_mm: float = 0.0

    @property
    def bleed(self) -> float:
        return self.bleed_mm * mm

    @property
    def page_size(self) -> tuple[float, float]:
        return (
            self.trim_width + self.bleed * 2,
            self.trim_height + self.bleed * 2,
        )


def _safe_text(value: Any) -> str:
    return str(value or "").translate(_DASH_TRANSLATION)


def _font_candidates() -> tuple[list[Path], list[Path]]:
    sans = [
        Path(os.environ.get("MINGSHU_FONT_SANS", "")),
        Path("assets/fonts/NotoSansSC-Regular.ttf"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ]
    serif = [
        Path(os.environ.get("MINGSHU_FONT_SERIF", "")),
        Path("assets/fonts/NotoSerifSC-Regular.ttf"),
        Path("C:/Windows/Fonts/STKAITI.TTF"),
        Path("C:/Windows/Fonts/simsunb.ttf"),
    ]
    return sans, serif


def _first_font(paths: Iterable[Path]) -> Path:
    for path in paths:
        if str(path) and path.is_file():
            return path.resolve()
    raise RuntimeError(
        "No CJK TrueType font found. Set MINGSHU_FONT_SANS and "
        "MINGSHU_FONT_SERIF or add fonts under assets/fonts/."
    )


def register_fonts() -> tuple[str, str]:
    """Register embeddable Chinese fonts and return their ReportLab names."""
    sans_name = "MingShuSans"
    serif_name = "MingShuSerif"
    registered = set(pdfmetrics.getRegisteredFontNames())
    sans_candidates, serif_candidates = _font_candidates()
    if sans_name not in registered:
        pdfmetrics.registerFont(TTFont(sans_name, str(_first_font(sans_candidates))))
    if serif_name not in registered:
        pdfmetrics.registerFont(TTFont(serif_name, str(_first_font(serif_candidates))))
    return sans_name, serif_name


def _wrap_lines(text: Any, font: str, size: float, max_width: float) -> list[str]:
    result: list[str] = []
    for paragraph in _safe_text(text).splitlines() or [""]:
        if not paragraph:
            result.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and pdfmetrics.stringWidth(candidate, font, size) > max_width:
                result.append(current.rstrip())
                current = char.lstrip()
            else:
                current = candidate
        if current or not result:
            result.append(current.rstrip())
    return result


def _draw_text(
    canvas: Canvas,
    text: Any,
    x: float,
    y: float,
    width: float,
    *,
    font: str,
    size: float,
    leading: float,
    color: Color = INK,
    max_lines: int | None = None,
) -> float:
    lines = _wrap_lines(text, font, size, width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and pdfmetrics.stringWidth(last + "...", font, size) > width:
            last = last[:-1]
        lines[-1] = last + "..."
    canvas.setFillColor(color)
    canvas.setFont(font, size)
    cursor = y
    for line in lines:
        canvas.drawString(x, cursor, line)
        cursor -= leading
    return cursor


def _round_rect(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: Color,
    stroke: Color | None = None,
    radius: float = 6,
    line_width: float = 0.7,
) -> None:
    canvas.setFillColor(fill)
    canvas.setStrokeColor(stroke or fill)
    canvas.setLineWidth(line_width)
    canvas.roundRect(x, y, width, height, radius, stroke=1 if stroke else 0, fill=1)


def _page_background(canvas: Canvas, spec: PrintSpec, page_number: int, section: str) -> None:
    width, height = spec.page_size
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    canvas.saveState()
    # Restrained ink-wash contours sit outside the reading area.  They echo the
    # reference slide language without turning every page into a decorative card.
    canvas.setStrokeColor(INK if page_number % 2 else GOLD)
    canvas.setStrokeAlpha(0.055)
    canvas.setLineWidth(0.7)
    bx = spec.bleed - 8 * mm
    by = spec.bleed + 5 * mm
    canvas.bezier(bx, by, bx + 16 * mm, by + 22 * mm, bx + 30 * mm, by - 2 * mm, bx + 47 * mm, by + 16 * mm)
    canvas.bezier(bx - 2 * mm, by - 3 * mm, bx + 12 * mm, by + 11 * mm, bx + 32 * mm, by - 8 * mm, bx + 55 * mm, by + 9 * mm)
    canvas.setStrokeColor(JADE)
    canvas.setStrokeAlpha(0.045)
    rx = width - spec.bleed - 10 * mm
    canvas.setLineWidth(1.0)
    canvas.line(rx, height - spec.bleed - 2 * mm, rx - 5 * mm, height - spec.bleed - 36 * mm)
    canvas.line(rx - 8 * mm, height - spec.bleed - 1 * mm, rx - 11 * mm, height - spec.bleed - 25 * mm)
    for offset in (8, 17, 27):
        y = height - spec.bleed - offset * mm
        canvas.bezier(rx - 3 * mm, y, rx - 10 * mm, y + 4 * mm, rx - 13 * mm, y + 2 * mm, rx - 16 * mm, y + 6 * mm)
    canvas.restoreState()
    if spec.bleed:
        _draw_crop_marks(canvas, spec)


def _draw_crop_marks(canvas: Canvas, spec: PrintSpec) -> None:
    bleed = spec.bleed
    width, height = spec.page_size
    trim_x1, trim_y1 = bleed, bleed
    trim_x2, trim_y2 = width - bleed, height - bleed
    canvas.saveState()
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(0.35)
    mark = min(7 * mm, bleed * 0.75)
    gap = 1.2 * mm
    for x in (trim_x1, trim_x2):
        canvas.line(x, trim_y1 - gap, x, trim_y1 - gap - mark)
        canvas.line(x, trim_y2 + gap, x, trim_y2 + gap + mark)
    for y in (trim_y1, trim_y2):
        canvas.line(trim_x1 - gap, y, trim_x1 - gap - mark, y)
        canvas.line(trim_x2 + gap, y, trim_x2 + gap + mark, y)
    canvas.restoreState()


def _running_frame(
    canvas: Canvas,
    spec: PrintSpec,
    page_number: int,
    spread: dict,
    sans: str,
) -> None:
    bleed = spec.bleed
    left = bleed + 14 * mm
    right = bleed + spec.trim_width - 14 * mm
    top = bleed + spec.trim_height - 10 * mm
    bottom = bleed + 9 * mm
    section = SECTION_LABELS.get(spread.get("section"), spread.get("section") or "")
    canvas.setStrokeColor(HexColor("#b8b2a7"))
    canvas.setLineWidth(0.45)
    canvas.line(left, top - 2.5 * mm, right, top - 2.5 * mm)
    canvas.line(left, bottom + 2.5 * mm, right, bottom + 2.5 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 6.5)
    canvas.drawString(left, top, _safe_text(section))
    canvas.drawRightString(right, top, "MIRROR · PERSONAL CHART BOOK")
    canvas.drawString(left, bottom, _safe_text(spread.get("title")))
    canvas.setFillColor(CINNABAR)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(right, bottom, f"{page_number:02d}")


def _content_bounds(spec: PrintSpec) -> tuple[float, float, float, float]:
    bleed = spec.bleed
    left = bleed + 14 * mm
    bottom = bleed + 16 * mm
    width = spec.trim_width - 28 * mm
    height = spec.trim_height - 34 * mm
    return left, bottom, width, height


def _draw_cover(canvas: Canvas, spec: PrintSpec, book: dict, facts: dict, sans: str, serif: str) -> None:
    width, height = spec.page_size
    bleed = spec.bleed
    canvas.setFillColor(JADE)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    cx = width / 2
    cy = height / 2 + 22 * mm
    canvas.saveState()
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.8)
    canvas.setDash(3, 4)
    canvas.circle(cx, cy, 48 * mm, stroke=1, fill=0)
    canvas.setDash()
    canvas.setLineWidth(0.35)
    canvas.circle(cx, cy, 38 * mm, stroke=1, fill=0)
    canvas.restoreState()
    pillars = (facts.get("chart") or {}).get("pillars") or []
    seal = "".join(item.get("ganzhi") or "" for item in pillars)[:2] or "命书"
    _round_rect(canvas, cx - 13 * mm, cy - 13 * mm, 26 * mm, 26 * mm, fill=CINNABAR)
    canvas.setFillColor(WHITE)
    canvas.setFont(serif, 23)
    canvas.drawCentredString(cx, cy - 3 * mm, _safe_text(seal))
    canvas.setFillColor(GOLD_LIGHT)
    canvas.setFont("Helvetica", 6.8)
    canvas.drawCentredString(cx, cy - 31 * mm, "MIRROR PERSONAL CHART BOOK")
    canvas.setFillColor(WHITE)
    canvas.setFont(serif, 42)
    canvas.drawCentredString(cx, cy - 54 * mm, "命 书")
    name = (book.get("subject") or {}).get("display_name") or "命主"
    canvas.setFont(sans, 9)
    canvas.drawCentredString(cx, cy - 69 * mm, _safe_text(name))
    canvas.setStrokeColor(GOLD)
    canvas.line(cx - 12 * mm, cy - 77 * mm, cx + 12 * mm, cy - 77 * mm)
    canvas.setFillColor(GOLD_LIGHT)
    canvas.setFont(sans, 6.5)
    canvas.drawCentredString(cx, bleed + 18 * mm, "原局 · 岁运 · 人生主题")


def _draw_title_page(
    canvas: Canvas,
    spec: PrintSpec,
    book: dict,
    facts: dict,
    sans: str,
    serif: str,
) -> None:
    left, bottom, width, height = _content_bounds(spec)
    top = bottom + height
    canvas.setFillColor(CINNABAR)
    canvas.setFont(sans, 7)
    canvas.drawString(left, top - 8 * mm, "PERSONAL EDITION")
    canvas.setFillColor(INK)
    canvas.setFont(serif, 34)
    canvas.drawString(left, top - 26 * mm, "一张命盘")
    canvas.drawString(left, top - 41 * mm, "一本可以复核的书")
    pillars = (facts.get("chart") or {}).get("pillars") or []
    y = top - 67 * mm
    cell_w = (width - 9 * mm) / 4
    for index, pillar in enumerate(pillars[:4]):
        x = left + index * (cell_w + 3 * mm)
        _round_rect(canvas, x, y - 34 * mm, cell_w, 34 * mm, fill=WHITE, stroke=GOLD_LIGHT)
        canvas.setFillColor(MUTED)
        canvas.setFont(sans, 6.5)
        canvas.drawCentredString(x + cell_w / 2, y - 7 * mm, _safe_text(pillar.get("label")))
        canvas.setFillColor(JADE)
        canvas.setFont(serif, 22)
        canvas.drawCentredString(x + cell_w / 2, y - 22 * mm, _safe_text(pillar.get("ganzhi")))
    subject = book.get("subject") or {}
    note = (
        "出生时辰尚未确定，涉及时柱的内容只能作为暂时参考。"
        if subject.get("birth_time_unknown")
        else "本书按所提供的出生日期与时辰排盘；若原始记录有误，相关解读也会随之改变。"
    )
    _round_rect(canvas, left, bottom + 16 * mm, width, 31 * mm, fill=JADE_LIGHT)
    _draw_text(
        canvas,
        note,
        left + 5 * mm,
        bottom + 35 * mm,
        width - 10 * mm,
        font=sans,
        size=7.5,
        leading=12,
        color=JADE,
        max_lines=4,
    )
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 5.8)
    canvas.drawString(left, bottom + 7 * mm, "愿这本书陪你在经历中认识自己。")


def _draw_copy_page(
    canvas: Canvas,
    spec: PrintSpec,
    spread: dict,
    page_number: int,
    sans: str,
    serif: str,
) -> None:
    left, bottom, width, height = _content_bounds(spec)
    top = bottom + height
    copy = spread.get("copy") or {}
    canvas.setFillColor(CINNABAR)
    canvas.setFont(sans, 7)
    canvas.drawString(left, top - 7 * mm, _safe_text(copy.get("kicker") or SECTION_LABELS.get(spread.get("section"))))
    title_y = top - 20 * mm
    title_y = _draw_text(
        canvas,
        copy.get("title") or spread.get("title"),
        left,
        title_y,
        width,
        font=serif,
        size=22,
        leading=28,
        max_lines=2,
    )
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.4)
    canvas.line(left, title_y - 2 * mm, left + 17 * mm, title_y - 2 * mm)
    deck_y = title_y - 10 * mm
    deck_y = _draw_text(
        canvas,
        copy.get("deck"),
        left,
        deck_y,
        width,
        font=serif,
        size=10.5,
        leading=17,
        color=JADE,
        max_lines=4,
    )
    cursor = deck_y - 4 * mm
    paragraphs = list(copy.get("paragraphs") or [])[:4]
    for paragraph in paragraphs:
        cursor = _draw_text(
            canvas,
            paragraph,
            left,
            cursor,
            width,
            font=sans,
            size=7.6,
            leading=12.2,
            color=INK,
            max_lines=6,
        )
        cursor -= 2.8 * mm
        if cursor < bottom + 62 * mm:
            break
    takeaways = list(copy.get("takeaways") or [])[:3]
    if takeaways:
        y = bottom + 49 * mm
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.65)
        canvas.line(left, y + 5 * mm, left + 12 * mm, y + 5 * mm)
        for index, item in enumerate(takeaways):
            canvas.setFillColor(CINNABAR if index == 0 else GOLD)
            canvas.setFont(serif, 11)
            canvas.drawString(left, y, ("一", "二", "三")[index])
            _draw_text(
                canvas,
                item,
                left + 9 * mm,
                y + 1,
                width - 9 * mm,
                font=sans,
                size=7.1,
                leading=10.5,
                color=INK,
                max_lines=2,
            )
            y -= 11 * mm
    else:
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.65)
        canvas.line(left, bottom + 39 * mm, left + 12 * mm, bottom + 39 * mm)
        _draw_text(
            canvas,
            copy.get("callout"),
            left,
            bottom + 32 * mm,
            width,
            font=sans,
            size=7.1,
            leading=11,
            color=MUTED,
            max_lines=3,
        )


def _visual_title(
    canvas: Canvas,
    spec: PrintSpec,
    spread: dict,
    sans: str,
    serif: str,
    subtitle: str = "",
) -> tuple[float, float, float, float]:
    left, bottom, width, height = _content_bounds(spec)
    top = bottom + height
    canvas.setFillColor(CINNABAR)
    canvas.setFont(sans, 7)
    canvas.drawString(left, top - 7 * mm, "图解")
    _draw_text(
        canvas,
        spread.get("title"),
        left,
        top - 20 * mm,
        width,
        font=serif,
        size=20,
        leading=25,
        max_lines=2,
    )
    if subtitle:
        _draw_text(
            canvas,
            subtitle,
            left,
            top - 38 * mm,
            width,
            font=sans,
            size=6.8,
            leading=10,
            color=MUTED,
            max_lines=2,
        )
    return left, bottom, width, height


def _draw_pillar_chart(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(
        canvas,
        spec,
        spread,
        sans,
        serif,
        "天干、地支、藏干和纳音放在同一张表里核对。",
    )
    pillars = (facts.get("chart") or {}).get("pillars") or []
    gap = 2.3 * mm
    cell_w = (width - gap * 3) / 4
    y = bottom + 28 * mm
    card_h = 109 * mm
    for index, pillar in enumerate(pillars[:4]):
        x = left + index * (cell_w + gap)
        _round_rect(canvas, x, y, cell_w, card_h, fill=WHITE, stroke=GOLD_LIGHT, radius=5)
        canvas.setFillColor(MUTED)
        canvas.setFont(sans, 6.2)
        canvas.drawCentredString(x + cell_w / 2, y + card_h - 9 * mm, _safe_text(pillar.get("label")))
        canvas.setFillColor(CINNABAR)
        canvas.setFont(serif, 26)
        canvas.drawCentredString(
            x + cell_w / 2,
            y + card_h - 28 * mm,
            _safe_text((pillar.get("gan") or {}).get("name_label")),
        )
        canvas.setFont(sans, 6)
        canvas.setFillColor(GOLD)
        canvas.drawCentredString(
            x + cell_w / 2,
            y + card_h - 36 * mm,
            _safe_text((pillar.get("gan") or {}).get("shishen_label")),
        )
        canvas.setFillColor(JADE)
        canvas.setFont(serif, 26)
        canvas.drawCentredString(
            x + cell_w / 2,
            y + card_h - 55 * mm,
            _safe_text((pillar.get("zhi") or {}).get("name_label")),
        )
        hidden = " ".join(
            f"{item.get('name_label')}{item.get('shishen_label')}"
            for item in (pillar.get("zhi") or {}).get("hidden_gans") or []
        )
        _draw_text(
            canvas,
            hidden,
            x + 2 * mm,
            y + card_h - 68 * mm,
            cell_w - 4 * mm,
            font=sans,
            size=5.4,
            leading=8,
            color=MUTED,
            max_lines=4,
        )
        canvas.setStrokeColor(GOLD_LIGHT)
        canvas.line(x + 2 * mm, y + 22 * mm, x + cell_w - 2 * mm, y + 22 * mm)
        _draw_text(
            canvas,
            (pillar.get("nayin") or {}).get("label") or "未标注",
            x + 2 * mm,
            y + 15 * mm,
            cell_w - 4 * mm,
            font=serif,
            size=7,
            leading=9,
            color=INK,
            max_lines=2,
        )


def _draw_wuxing_donut(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(canvas, spec, spread, sans, serif, "圆环表示五行相对力量，不表示吉凶。")
    series = list(((facts.get("analysis_facts") or {}).get("wuxing") or []))
    cx = left + 47 * mm
    cy = bottom + 92 * mm
    radius = 39 * mm
    start = 90.0
    for item in series:
        extent = -360.0 * float(item.get("percent") or 0) / 100.0
        canvas.setFillColor(ELEMENT_COLORS.get(item.get("code"), GOLD))
        canvas.wedge(cx - radius, cy - radius, cx + radius, cy + radius, start, extent, stroke=0, fill=1)
        start += extent
    canvas.setFillColor(PAPER)
    canvas.circle(cx, cy, 23 * mm, stroke=0, fill=1)
    strongest = max(series, key=lambda item: item.get("percent", 0), default={})
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 6)
    canvas.drawCentredString(cx, cy + 4 * mm, "力量重心")
    canvas.setFillColor(INK)
    canvas.setFont(serif, 18)
    canvas.drawCentredString(cx, cy - 5 * mm, _safe_text(strongest.get("label")))
    x = left + 94 * mm
    y = bottom + 126 * mm
    for item in sorted(series, key=lambda value: value.get("percent", 0), reverse=True):
        color = ELEMENT_COLORS.get(item.get("code"), GOLD)
        canvas.setFillColor(color)
        canvas.circle(x, y + 1.8, 2.3, stroke=0, fill=1)
        canvas.setFillColor(INK)
        canvas.setFont(sans, 7.2)
        canvas.drawString(x + 5 * mm, y, _safe_text(item.get("label")))
        canvas.setFont("Helvetica-Bold", 7.2)
        canvas.drawRightString(left + width, y, f"{float(item.get('percent') or 0):.1f}%")
        y -= 11 * mm
    _round_rect(canvas, left, bottom + 18 * mm, width, 23 * mm, fill=JADE_LIGHT)
    _draw_text(
        canvas,
        "少不等于没有，多不等于有利。正式喜忌还要结合季节、格局与调候。",
        left + 5 * mm,
        bottom + 33 * mm,
        width - 10 * mm,
        font=sans,
        size=7,
        leading=11,
        color=JADE,
        max_lines=3,
    )


def _draw_wuxing_flow(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(canvas, spec, spread, sans, serif, "圆的大小对应比例，箭头表示相生的阅读顺序。")
    items = {
        item.get("code"): item
        for item in ((facts.get("analysis_facts") or {}).get("wuxing") or [])
    }
    order = ["WUXING:MU", "WUXING:HUO", "WUXING:TU", "WUXING:JIN", "WUXING:SHUI"]
    cx = left + width / 2
    cy = bottom + 92 * mm
    points = []
    for index, code in enumerate(order):
        angle = math.radians(90 - index * 72)
        points.append((code, cx + math.cos(angle) * 45 * mm, cy + math.sin(angle) * 42 * mm))
    canvas.setLineWidth(1.2)
    canvas.setStrokeColor(HexColor("#8ca097"))
    for index, (_, x1, y1) in enumerate(points):
        _, x2, y2 = points[(index + 1) % len(points)]
        canvas.line(x1, y1, x2, y2)
        angle = math.atan2(y2 - y1, x2 - x1)
        ax = x2 - math.cos(angle) * 11
        ay = y2 - math.sin(angle) * 11
        canvas.line(ax, ay, ax - math.cos(angle - 0.55) * 7, ay - math.sin(angle - 0.55) * 7)
        canvas.line(ax, ay, ax - math.cos(angle + 0.55) * 7, ay - math.sin(angle + 0.55) * 7)
    for code, x, y in points:
        item = items.get(code, {})
        percent = float(item.get("percent") or 0)
        radius = (8 + min(7, percent / 6)) * mm
        canvas.setFillColor(ELEMENT_COLORS.get(code, GOLD))
        canvas.circle(x, y, radius, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont(serif, 12)
        canvas.drawCentredString(x, y + 1 * mm, _safe_text(item.get("label")))
        canvas.setFont("Helvetica", 5.5)
        canvas.drawCentredString(x, y - 4 * mm, f"{percent:.1f}%")
    _round_rect(canvas, left + 13 * mm, bottom + 17 * mm, width - 26 * mm, 18 * mm, fill=WHITE, stroke=GOLD_LIGHT)
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 6.5)
    canvas.drawCentredString(left + width / 2, bottom + 27 * mm, "木 → 火 → 土 → 金 → 水 → 木")


def _draw_shishen_bars(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(canvas, spec, spread, sans, serif, "长度按十神力量比例排序。")
    series = [
        item
        for item in ((facts.get("analysis_facts") or {}).get("shishen") or [])
        if item.get("label") != "日主"
    ]
    series = sorted(series, key=lambda item: item.get("percent", 0), reverse=True)[:10]
    top = bottom + 137 * mm
    label_w = 21 * mm
    value_w = 15 * mm
    track_w = width - label_w - value_w
    max_pct = max([float(item.get("percent") or 0) for item in series] or [1])
    for index, item in enumerate(series):
        y = top - index * 10.5 * mm
        canvas.setFillColor(CINNABAR if index < 3 else INK)
        canvas.setFont(sans, 6.8)
        canvas.drawString(left, y, _safe_text(item.get("label")))
        _round_rect(canvas, left + label_w, y - 1.3 * mm, track_w, 4 * mm, fill=PAPER_DARK, radius=4)
        bar_width = track_w * float(item.get("percent") or 0) / max_pct
        _round_rect(
            canvas,
            left + label_w,
            y - 1.3 * mm,
            max(2, bar_width),
            4 * mm,
            fill=JADE if index >= 3 else CINNABAR,
            radius=4,
        )
        canvas.setFont("Helvetica-Bold", 6.3)
        canvas.drawRightString(left + width, y, f"{float(item.get('percent') or 0):.1f}%")


def _draw_relation_network(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(canvas, spec, spread, sans, serif, "连线保留柱位和关系名称。")
    network = (facts.get("visuals") or {}).get("origin_network") or {}
    pillars = network.get("pillars") or []
    relations = network.get("relations") or []
    xs = [left + 15 * mm + index * ((width - 30 * mm) / 3) for index in range(4)]
    pillar_x = {pillar.get("key"): xs[index] for index, pillar in enumerate(pillars[:4])}
    node_y = bottom + 49 * mm
    for index, relation in enumerate(relations[:7]):
        members = relation.get("members") or []
        if len(members) < 2:
            continue
        x1 = pillar_x.get(members[0].get("pillar"), xs[0])
        x2 = pillar_x.get(members[1].get("pillar"), xs[-1])
        curve_y = bottom + 78 * mm + index * 12 * mm
        label = relation.get("label") or "作用"
        tension = any(word in label for word in ("冲", "刑", "穿", "害", "破"))
        color = CINNABAR if tension else JADE
        canvas.setStrokeColor(color)
        canvas.setLineWidth(1.4)
        path = canvas.beginPath()
        path.moveTo(x1, node_y + 8 * mm)
        path.curveTo(x1, curve_y, x2, curve_y, x2, node_y + 8 * mm)
        canvas.drawPath(path, stroke=1, fill=0)
        _round_rect(
            canvas,
            (x1 + x2) / 2 - 9 * mm,
            curve_y - 3 * mm,
            18 * mm,
            6 * mm,
            fill=PAPER,
        )
        canvas.setFillColor(color)
        canvas.setFont(sans, 6.1)
        canvas.drawCentredString((x1 + x2) / 2, curve_y - 1.5, _safe_text(label))
    for index, pillar in enumerate(pillars[:4]):
        x = xs[index]
        canvas.setFillColor(WHITE)
        canvas.setStrokeColor(JADE)
        canvas.setLineWidth(1)
        canvas.circle(x, node_y, 9 * mm, stroke=1, fill=1)
        canvas.setFillColor(INK)
        canvas.setFont(serif, 12)
        canvas.drawCentredString(x, node_y + 1 * mm, _safe_text(pillar.get("ganzhi")))
        canvas.setFillColor(MUTED)
        canvas.setFont(sans, 5.5)
        canvas.drawCentredString(x, node_y - 5 * mm, _safe_text(pillar.get("label")))
    canvas.setFillColor(JADE)
    canvas.setFont(sans, 6.3)
    canvas.drawString(left + 18 * mm, bottom + 23 * mm, "绿色：连接与汇合类")
    canvas.setFillColor(CINNABAR)
    canvas.drawString(left + 78 * mm, bottom + 23 * mm, "红色：张力与牵动类")


def _draw_nayin_cards(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(canvas, spec, spread, sans, serif, "纳音只作柱位意象补充。")
    pillars = (facts.get("chart") or {}).get("pillars") or []
    gap = 4 * mm
    card_w = (width - gap) / 2
    card_h = 57 * mm
    top_y = bottom + 139 * mm
    for index, pillar in enumerate(pillars[:4]):
        col = index % 2
        row = index // 2
        x = left + col * (card_w + gap)
        y = top_y - row * (card_h + gap) - card_h
        _round_rect(canvas, x, y, card_w, card_h, fill=WHITE, stroke=GOLD_LIGHT)
        nayin = pillar.get("nayin") or {}
        knowledge = nayin.get("knowledge") or {}
        canvas.setFillColor(MUTED)
        canvas.setFont(sans, 5.8)
        canvas.drawString(x + 4 * mm, y + card_h - 8 * mm, _safe_text(f"{pillar.get('label')} · {pillar.get('ganzhi')}"))
        canvas.setFillColor(INK)
        canvas.setFont(serif, 16)
        canvas.drawString(x + 4 * mm, y + card_h - 20 * mm, _safe_text(nayin.get("label")))
        canvas.setFillColor(CINNABAR)
        canvas.setFont(sans, 6.5)
        canvas.drawString(x + 4 * mm, y + card_h - 29 * mm, _safe_text(knowledge.get("tagline")))
        _draw_text(
            canvas,
            knowledge.get("introduction"),
            x + 4 * mm,
            y + card_h - 39 * mm,
            card_w - 8 * mm,
            font=sans,
            size=5.8,
            leading=8.2,
            color=MUTED,
            max_lines=4,
        )


def _actual_luck_cycles(facts: dict) -> list[dict]:
    return [item for item in facts.get("luck_cycles") or [] if not item.get("is_pre_luck")]


def _activity_index(cycle: dict) -> int:
    cycle_relations = len(cycle.get("relations") or [])
    yearly = [len(item.get("relations") or []) for item in cycle.get("years") or []]
    average = sum(yearly) / len(yearly) if yearly else 0
    return int(round(min(100, 18 + cycle_relations * 12 + average * 11)))


def _draw_luck_overview(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(
        canvas,
        spec,
        spread,
        sans,
        serif,
        "曲线表示关系牵动的密度；它不是吉凶分，请结合真实经历阅读。",
    )
    cycles = _actual_luck_cycles(facts)[:7]
    chart_x = left + 7 * mm
    chart_y = bottom + 54 * mm
    chart_w = width - 14 * mm
    chart_h = 76 * mm
    canvas.setStrokeColor(HexColor("#c8c0b4"))
    canvas.setLineWidth(0.45)
    for step in (0, 25, 50, 75, 100):
        y = chart_y + chart_h * step / 100
        canvas.line(chart_x, y, chart_x + chart_w, y)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 5.2)
        canvas.drawRightString(chart_x - 2 * mm, y - 1.5, str(step))
    points = []
    for index, cycle in enumerate(cycles):
        x = chart_x + index * (chart_w / max(1, len(cycles) - 1))
        activity = _activity_index(cycle)
        y = chart_y + chart_h * activity / 100
        points.append((x, y, cycle, activity))
    canvas.setStrokeColor(JADE)
    canvas.setLineWidth(2)
    for first, second in zip(points, points[1:]):
        canvas.line(first[0], first[1], second[0], second[1])
    for x, y, cycle, activity in points:
        canvas.setFillColor(CINNABAR if cycle.get("score") is not None else JADE)
        canvas.circle(x, y, 2.5 * mm, stroke=0, fill=1)
        canvas.setFillColor(INK)
        canvas.setFont(serif, 7)
        canvas.drawCentredString(x, chart_y - 7 * mm, _safe_text(cycle.get("name")))
        canvas.setFont("Helvetica", 5.2)
        canvas.drawCentredString(x, y + 4 * mm, str(activity))
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(x, chart_y - 13 * mm, str(cycle.get("start_year")))
    _round_rect(canvas, left, bottom + 18 * mm, width, 22 * mm, fill=CINNABAR_LIGHT)
    _draw_text(
        canvas,
        "活跃度只计算原局与岁运之间的作用密度。它帮助找“需要多观察”的阶段，不用于判断成败。",
        left + 5 * mm,
        bottom + 32 * mm,
        width - 10 * mm,
        font=sans,
        size=6.8,
        leading=10.5,
        color=CINNABAR,
        max_lines=3,
    )


def _draw_dayun_detail(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    cycles = _actual_luck_cycles(facts)
    try:
        index = int(spread.get("slug", "").split("-", 1)[1]) - 1
    except (ValueError, IndexError):
        index = -1
    cycle = cycles[index] if 0 <= index < len(cycles) else {}
    left, bottom, width, height = _visual_title(
        canvas,
        spec,
        spread,
        sans,
        serif,
        f"{cycle.get('start_year', '')}-{cycle.get('end_year', '')} · 结构活跃度，不是吉凶分。",
    )
    activity = _activity_index(cycle) if cycle else 0
    cx = left + 37 * mm
    cy = bottom + 100 * mm
    radius = 29 * mm
    canvas.setStrokeColor(PAPER_DARK)
    canvas.setLineWidth(8)
    canvas.arc(cx - radius, cy - radius, cx + radius, cy + radius, 210, 120)
    canvas.setStrokeColor(JADE)
    canvas.arc(cx - radius, cy - radius, cx + radius, cy + radius, 210, 120 * activity / 100)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 21)
    canvas.drawCentredString(cx, cy - 1 * mm, str(activity))
    canvas.setFont(sans, 6)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(cx, cy - 9 * mm, "结构活跃度")
    _round_rect(canvas, left + 78 * mm, bottom + 81 * mm, width - 78 * mm, 45 * mm, fill=WHITE, stroke=GOLD_LIGHT)
    canvas.setFillColor(CINNABAR)
    canvas.setFont(serif, 20)
    canvas.drawString(left + 83 * mm, bottom + 111 * mm, _safe_text(cycle.get("name")))
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 6.3)
    canvas.drawString(left + 83 * mm, bottom + 101 * mm, _safe_text(f"天干十神 · {(cycle.get('gan_shishen') or {}).get('label') or '未标注'}"))
    canvas.drawString(left + 83 * mm, bottom + 92 * mm, _safe_text(f"地支十神 · {(cycle.get('zhi_shishen') or {}).get('label') or '未标注'}"))
    years = list(cycle.get("years") or [])
    max_rel = max([len(item.get("relations") or []) for item in years] or [1])
    timeline_y = bottom + 39 * mm
    canvas.setStrokeColor(GOLD_LIGHT)
    canvas.line(left + 3 * mm, timeline_y, left + width - 3 * mm, timeline_y)
    for idx, year in enumerate(years):
        x = left + 3 * mm + idx * ((width - 6 * mm) / max(1, len(years) - 1))
        count = len(year.get("relations") or [])
        r = (2.2 + 2.8 * count / max_rel) * mm
        canvas.setFillColor(CINNABAR if count == max_rel else GOLD)
        canvas.circle(x, timeline_y, r, stroke=0, fill=1)
        canvas.saveState()
        canvas.translate(x + 1, timeline_y - 8 * mm)
        canvas.rotate(55)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 4.7)
        canvas.drawString(0, 0, str(year.get("year")))
        canvas.restoreState()
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 5.6)
    canvas.drawString(left, bottom + 17 * mm, "圆越大，表示该流年导出的作用关系越多；需结合现实事件复核。")


def _draw_shensha_zodiac(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(canvas, spec, spread, sans, serif, "辅助标签只在与主结构互证时采用。")
    zodiac = (facts.get("chart") or {}).get("zodiac") or {}
    cx = left + 34 * mm
    cy = bottom + 101 * mm
    canvas.setFillColor(JADE)
    canvas.circle(cx, cy, 26 * mm, stroke=0, fill=1)
    canvas.setFillColor(WHITE)
    canvas.setFont(serif, 29)
    canvas.drawCentredString(cx, cy - 3 * mm, _safe_text(zodiac.get("label")))
    canvas.setFont(sans, 6)
    canvas.drawCentredString(cx, cy - 12 * mm, "生肖文化意象")
    shensha = (facts.get("analysis_facts") or {}).get("shensha") or {}
    names = []
    for items in shensha.values():
        for item in items:
            name = item.get("name")
            if name and name not in names:
                names.append(name)
    x0 = left + 71 * mm
    y = bottom + 135 * mm
    for index, name in enumerate(names[:12]):
        col = index % 2
        row = index // 2
        x = x0 + col * 33 * mm
        yy = y - row * 14 * mm
        _round_rect(canvas, x, yy, 29 * mm, 8 * mm, fill=WHITE, stroke=GOLD_LIGHT, radius=7)
        canvas.setFillColor(CINNABAR if "煞" in name else JADE)
        canvas.setFont(sans, 5.8)
        canvas.drawCentredString(x + 14.5 * mm, yy + 2.5 * mm, _safe_text(name))
    _round_rect(canvas, left, bottom + 19 * mm, width, 24 * mm, fill=GOLD_LIGHT)
    _draw_text(
        canvas,
        "神煞名称来自固定查表规则。名称听起来强烈，不等于现实中一定发生对应事件。",
        left + 5 * mm,
        bottom + 34 * mm,
        width - 10 * mm,
        font=sans,
        size=6.8,
        leading=10,
        color=INK,
        max_lines=3,
    )


def _draw_notes_page(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    left, bottom, width, height = _visual_title(
        canvas,
        spec,
        {**spread, "title": "复核记录"},
        sans,
        serif,
        "把真实事件、疑问和修订意见留在这里。",
    )
    _round_rect(canvas, left, bottom + 124 * mm, width, 18 * mm, fill=JADE_LIGHT)
    canvas.setFillColor(JADE)
    canvas.setFont(sans, 6.2)
    canvas.drawString(left + 4 * mm, bottom + 134 * mm, "记录真实发生的事，也记录当时的感受与选择。")
    canvas.setStrokeColor(HexColor("#cfc5b7"))
    canvas.setLineWidth(0.5)
    y = bottom + 111 * mm
    for index in range(11):
        canvas.line(left, y, left + width, y)
        if index in (0, 4, 8):
            canvas.setFillColor(CINNABAR)
            canvas.setFont(sans, 5.8)
            canvas.drawString(
                left,
                y + 2 * mm,
                ["日期与事件", "与书中判断的对应", "需要修订的地方"][index // 4],
            )
        y -= 9 * mm
    canvas.setFillColor(MUTED)
    canvas.setFont(sans, 5.8)
    canvas.drawRightString(left + width, bottom + 12 * mm, "这本书允许被现实经验修订。")


def _draw_concept_visual(canvas: Canvas, spec: PrintSpec, spread: dict, facts: dict, sans: str, serif: str) -> None:
    copy = spread.get("copy") or {}
    left, bottom, width, height = _visual_title(
        canvas,
        spec,
        spread,
        sans,
        serif,
        copy.get("deck") or copy.get("callout") or "",
    )
    takeaways = list(copy.get("takeaways") or [])
    labels = takeaways[:4]
    while len(labels) < 4:
        labels.append(["观察", "依据", "行动", "复核"][len(labels)])
    top = bottom + 116 * mm
    node_x = left + 23 * mm
    text_x = left + 46 * mm
    accents = [JADE, GOLD, CINNABAR, INK]
    canvas.saveState()
    canvas.setFillColor(GOLD_LIGHT)
    canvas.setFillAlpha(0.34)
    canvas.circle(left + width - 7 * mm, top + 4 * mm, 31 * mm, stroke=0, fill=1)
    canvas.restoreState()
    canvas.setStrokeColor(GOLD_LIGHT)
    canvas.setLineWidth(1.0)
    path = canvas.beginPath()
    path.moveTo(node_x, top + 2 * mm)
    path.curveTo(node_x - 8 * mm, top - 30 * mm, node_x + 9 * mm, top - 58 * mm, node_x, top - 91 * mm)
    canvas.drawPath(path, stroke=1, fill=0)
    for index, label in enumerate(labels[:4]):
        y = top - index * 31 * mm
        accent = accents[index]
        canvas.setFillColor(WHITE)
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1.0)
        canvas.circle(node_x, y, 6.5 * mm, stroke=1, fill=1)
        canvas.setFillColor(accent)
        canvas.setFont(serif, 10)
        canvas.drawCentredString(node_x, y - 1.7 * mm, ("一", "二", "三", "四")[index])
        canvas.setStrokeColor(GOLD_LIGHT)
        canvas.setLineWidth(0.6)
        canvas.line(node_x + 8 * mm, y, text_x - 4 * mm, y)
        _draw_text(
            canvas,
            label,
            text_x,
            y + 2 * mm,
            width - (text_x - left),
            font=serif,
            size=9.2,
            leading=13.5,
            color=INK,
            max_lines=2,
        )


def _draw_visual_page(
    canvas: Canvas,
    spec: PrintSpec,
    spread: dict,
    facts: dict,
    sans: str,
    serif: str,
) -> None:
    slug = spread.get("slug")
    visuals = set(spread.get("visuals") or [])
    if slug == "complete-chart" or "pillar_table" in visuals:
        _draw_pillar_chart(canvas, spec, spread, facts, sans, serif)
    elif "wuxing_donut" in visuals:
        _draw_wuxing_donut(canvas, spec, spread, facts, sans, serif)
    elif "wuxing_flow" in visuals or "five_element_cycle" in visuals:
        _draw_wuxing_flow(canvas, spec, spread, facts, sans, serif)
    elif "shishen_bar" in visuals:
        _draw_shishen_bars(canvas, spec, spread, facts, sans, serif)
    elif "origin_relation_network" in visuals:
        _draw_relation_network(canvas, spec, spread, facts, sans, serif)
    elif "nayin_four_cards" in visuals:
        _draw_nayin_cards(canvas, spec, spread, facts, sans, serif)
    elif "shensha_constellation" in visuals:
        _draw_shensha_zodiac(canvas, spec, spread, facts, sans, serif)
    elif slug == "luck-overview":
        _draw_luck_overview(canvas, spec, spread, facts, sans, serif)
    elif slug and slug.startswith("dayun-"):
        _draw_dayun_detail(canvas, spec, spread, facts, sans, serif)
    elif slug == "evidence-colophon":
        _draw_notes_page(canvas, spec, spread, facts, sans, serif)
    else:
        _draw_concept_visual(canvas, spec, spread, facts, sans, serif)


def render_book_pdf(
    book: dict,
    facts: dict,
    output_path: str | Path,
    *,
    bleed_mm: float = 0.0,
) -> Path:
    """Render and return the final PDF path."""
    sans, serif = register_fonts()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    spec = PrintSpec(bleed_mm=bleed_mm)
    canvas = Canvas(str(output), pagesize=spec.page_size, pageCompression=1)
    subject_name = (book.get("subject") or {}).get("display_name") or "命主"
    canvas.setTitle(_safe_text(f"{subject_name} · Mirror 命书"))
    canvas.setAuthor("MirrorAI")
    canvas.setSubject("八字原局、岁运与人生主题的结构化编辑样书")
    canvas.setKeywords("MirrorAI, MingShu, Bazi, A5")

    expected_page = 1
    for spread in book.get("spreads") or []:
        page_start = int(spread.get("page_start") or expected_page)
        if page_start != expected_page:
            raise ValueError(f"page manifest is discontinuous at {spread.get('slug')}")
        for side in (0, 1):
            page_number = page_start + side
            _page_background(canvas, spec, page_number, spread.get("section") or "")
            if page_number == 1:
                _draw_cover(canvas, spec, book, facts, sans, serif)
            elif page_number == 2:
                _draw_title_page(canvas, spec, book, facts, sans, serif)
            else:
                _running_frame(canvas, spec, page_number, spread, sans)
                if side == 0:
                    _draw_copy_page(canvas, spec, spread, page_number, sans, serif)
                else:
                    _draw_visual_page(canvas, spec, spread, facts, sans, serif)
            canvas.showPage()
        expected_page += 2

    if expected_page - 1 != int((book.get("edition") or {}).get("total_pages") or 0):
        raise ValueError("rendered page count does not match edition manifest")
    canvas.save()
    return output.resolve()
