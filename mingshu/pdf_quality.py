"""Programmatic checks for generated MingShu PDFs."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


FORBIDDEN_MARKERS = (
    "[LLM_PLACEHOLDER:",
    "[LLM_ERROR:",
    "[NODE_ERROR:",
    "[SKIPPED:",
    "正文内容槽",
)


def inspect_pdf(path: str | Path, *, expected_pages: int = 80) -> dict:
    pdf_path = Path(path)
    reader = PdfReader(str(pdf_path))
    page_sizes: list[tuple[float, float]] = []
    text_counts: list[int] = []
    marker_hits: list[dict[str, object]] = []
    nearly_blank_pages: list[int] = []
    for page_number, page in enumerate(reader.pages, start=1):
        box = page.mediabox
        page_sizes.append((round(float(box.width), 2), round(float(box.height), 2)))
        text = page.extract_text() or ""
        text_counts.append(len(text.strip()))
        if len(text.strip()) < 4:
            nearly_blank_pages.append(page_number)
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                marker_hits.append({"page": page_number, "marker": marker})
    unique_sizes = sorted(set(page_sizes))
    errors: list[str] = []
    if len(reader.pages) != expected_pages:
        errors.append(f"expected {expected_pages} pages, got {len(reader.pages)}")
    if len(unique_sizes) != 1:
        errors.append(f"inconsistent page sizes: {unique_sizes}")
    if marker_hits:
        errors.append("forbidden placeholder or error markers found")
    if nearly_blank_pages:
        errors.append(f"nearly blank pages: {nearly_blank_pages}")
    return {
        "path": str(pdf_path.resolve()),
        "bytes": pdf_path.stat().st_size,
        "pages": len(reader.pages),
        "page_sizes_points": unique_sizes,
        "minimum_extracted_characters": min(text_counts) if text_counts else 0,
        "maximum_extracted_characters": max(text_counts) if text_counts else 0,
        "nearly_blank_pages": nearly_blank_pages,
        "forbidden_marker_hits": marker_hits,
        "errors": errors,
        "passed": not errors,
    }
