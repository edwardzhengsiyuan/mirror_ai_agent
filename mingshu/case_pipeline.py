"""End-to-end generation of the integrated, print-ready MingShu PDF."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from copy import copy
from pathlib import Path
from typing import Any, Callable

from pypdf import PdfReader, PdfWriter, Transformation

from agent.tools.paipan_tool import paipan_tool
from mingshu import build_book_facts
from mingshu.closing_pages import write_closing_sample
from mingshu.integrated_bridge import write_integrated_bridge
from mingshu.luck_pages import write_luck_sample
from mingshu.localization import localize_html_files, normalize_report_locale
from mingshu.opening_v2 import write_opening_html_v2, write_opening_manifest_v2
from mingshu.pattern_pages import write_pattern_sample
from mingshu.relation_pages import write_relation_sample
from mingshu.shensha_pages import render_shensha_sample_html
from mingshu.shishen_pages import write_shishen_sample
from mingshu.topics_pages import write_topics_sample


ROOT = Path(__file__).resolve().parents[1]
Progress = Callable[[int, str], None]


def _browser_binary() -> Path:
    configured = (os.environ.get("MINGSHU_BROWSER_BIN") or "").strip()
    candidates = [
        configured,
        shutil.which("msedge") or "",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
        shutil.which("chromium-browser") or "",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise RuntimeError(
        "没有找到用于排版的 Chrome/Edge。请设置 MINGSHU_BROWSER_BIN。"
    )


def _render_html_pdf(html_path: Path, pdf_path: Path, expected_spreads: int) -> None:
    browser = _browser_binary()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="mingshu-browser-", dir=str(pdf_path.parent)))
    args = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={profile}",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path.resolve()}",
        html_path.resolve().as_uri(),
    ]
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
        args.insert(1, "--no-sandbox")
    try:
        completed = subprocess.run(
            args,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(os.environ.get("MINGSHU_RENDER_TIMEOUT", "180")),
            check=False,
        )
        if completed.returncode != 0 or not pdf_path.is_file():
            detail = (completed.stdout or "").strip()[-1000:]
            raise RuntimeError(f"章节排版失败（{completed.returncode}）：{detail}")
        pages = len(PdfReader(str(pdf_path)).pages)
        if pages != expected_spreads:
            raise RuntimeError(
                f"{html_path.parent.name} 应为 {expected_spreads} 个跨页，实际为 {pages}"
            )
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _assemble(bundle: dict[str, Any], segment_dir: Path, target: Path) -> None:
    writer = PdfWriter()
    for segment in bundle["segments"]:
        source = segment_dir / f"{segment['name']}.pdf"
        reader = PdfReader(str(source))
        expected = int(segment["spreads"])
        if len(reader.pages) != expected:
            raise RuntimeError(f"{source.name} 页数不符")
        for page in reader.pages:
            writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": f"MirrorAI 命书 · {bundle['case_id']}",
            "/Author": "MirrorAI",
            "/Subject": "八字命书个案",
        }
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        writer.write(handle)


def _split_a5(source: Path, target: Path) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for spread_index, spread in enumerate(reader.pages):
        width, height = float(spread.mediabox.width), float(spread.mediabox.height)
        half = width / 2
        sides = ("right",) if spread_index == 0 else ("left", "right")
        for side in sides:
            page = writer.add_blank_page(width=half, height=height)
            source_page = copy(spread)
            if side == "right":
                source_page.add_transformation(Transformation().translate(tx=-half, ty=0))
            page.merge_page(source_page)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        writer.write(handle)


def _generate_bundle(
    job_id: str,
    profile: dict[str, Any],
    job_dir: Path,
    progress: Progress,
) -> tuple[dict[str, Any], dict[str, Any]]:
    progress(7, "排出四柱与大运")
    facts = build_book_facts(paipan_tool(profile), profile)
    facts_path = job_dir / "facts.json"
    facts_path.write_text(
        json.dumps(facts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    progress(15, "组织原局、岁运与专项内容")

    prototypes = ROOT / "docs" / "prototypes"

    def segment_dir(slug: str) -> Path:
        target = prototypes / f"mingshu-job-{job_id}-{slug}"
        target.mkdir(parents=True, exist_ok=True)
        return target

    opening = segment_dir("opening")
    case_image = ROOT / "assets" / "mingshu" / "illustrations" / "cases" / (
        f"{profile['birth']['year']:04d}{profile['birth']['month']:02d}"
        f"{profile['birth']['day']:02d}-{profile['birth']['hour']:02d}"
        f"{profile['birth'].get('minute', 0):02d}-{profile['gender']}"
        "-symbolic-landscape-v1.png"
    )
    symbolic_url = (
        f"../../../assets/mingshu/illustrations/cases/{case_image.name}"
        if case_image.is_file()
        else "../../../assets/mingshu/illustrations/layout/wuxing-watercolor-field-v1.png"
    )
    write_opening_html_v2(
        facts,
        opening / "index.html",
        symbolic_image=symbolic_url,
    )
    write_opening_manifest_v2(facts, opening / "manifest.json")

    relations = segment_dir("relations")
    write_relation_sample(facts, relations / "index.html")
    bridge = segment_dir("bridge")
    write_integrated_bridge(bridge / "index.html")
    shishen = segment_dir("shishen")
    write_shishen_sample(facts, shishen / "index.html", shishen / "data.json")
    shensha = segment_dir("shensha")
    render_shensha_sample_html(facts, shensha / "index.html", shensha / "data.json")
    pattern = segment_dir("pattern")
    write_pattern_sample(facts, pattern / "index.html", pattern / "data.json")
    luck = segment_dir("luck")
    write_luck_sample(facts, luck / "index.html", luck / "data.json")
    topics = segment_dir("topics")
    write_topics_sample(facts, topics / "index.html", topics / "data.json")
    closing = segment_dir("closing")
    write_closing_sample(facts, closing / "index.html", closing / "data.json")

    segments = [
        ("01-opening", opening / "index.html", 13),
        ("02-relations", relations / "index.html", 3),
        ("03-bridge", bridge / "index.html", 1),
        ("04-shishen", shishen / "index.html", 5),
        ("05-shensha", shensha / "index.html", 4),
        ("06-pattern", pattern / "index.html", 5),
        ("07-luck", luck / "index.html", 60),
        ("08-topics", topics / "index.html", 24),
        ("09-closing", closing / "index.html", 2),
    ]
    case_id = (
        f"{profile['birth']['year']:04d}{profile['birth']['month']:02d}"
        f"{profile['birth']['day']:02d}-{profile['birth']['hour']:02d}"
        f"{profile['birth'].get('minute', 0):02d}-{profile['gender']}-{job_id[:8]}"
    )
    bundle = {
        "schema_version": "mingshu-case-bundle/1.0",
        "case_id": case_id,
        "profile": profile,
        "facts": str(facts_path),
        "segments": [
            {"name": name, "html": str(path), "spreads": spreads}
            for name, path, spreads in segments
        ],
        "spread_count": sum(item[2] for item in segments),
        "a5_page_count": sum(item[2] for item in segments) * 2 - 1,
    }
    (job_dir / "bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    progress(22, "章节内容准备完成")
    return facts, bundle


def generate_mingshu_job(
    job_id: str,
    request_payload: dict[str, Any],
    job_dir: Path,
    progress: Progress,
) -> dict[str, Any]:
    """Default runner used by the asynchronous job service."""
    job_dir.mkdir(parents=True, exist_ok=True)
    birth = dict(request_payload["birth"])
    birth.setdefault("minute", 0)
    birth.setdefault("second", 0)
    locale = normalize_report_locale(request_payload.get("locale"))
    profile = {
        "display_name": request_payload.get("name", ""),
        "birthplace": request_payload.get("birthplace", ""),
        "calendar": "solar",
        "birth": birth,
        "gender": request_payload["gender"],
        "birth_time_unknown": False,
        "locale": locale,
    }
    facts, bundle = _generate_bundle(job_id, profile, job_dir, progress)

    if locale != "zh-CN":
        progress(23, f"正在准备 {locale} 报告文本")
        localize_html_files(
            [Path(segment["html"]) for segment in bundle["segments"]],
            locale,
        )

    segment_dir = job_dir / "segments"
    segment_dir.mkdir(parents=True, exist_ok=True)
    total = len(bundle["segments"])
    for index, segment in enumerate(bundle["segments"], start=1):
        progress(
            24 + round(index / total * 50),
            f"排版章节 {index}/{total}：{segment['name']}",
        )
        _render_html_pdf(
            Path(segment["html"]),
            segment_dir / f"{segment['name']}.pdf",
            int(segment["spreads"]),
        )

    downloads = job_dir / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    slug = bundle["case_id"]
    spreads = downloads / f"mirror-mingshu-{slug}-spreads.pdf"
    a5 = downloads / f"mirror-mingshu-{slug}-a5.pdf"
    progress(80, "合订完整命书")
    _assemble(bundle, segment_dir, spreads)
    progress(90, "生成 A5 印刷拆页")
    _split_a5(spreads, a5)

    spread_pages = len(PdfReader(str(spreads)).pages)
    a5_pages = len(PdfReader(str(a5)).pages)
    if spread_pages != bundle["spread_count"] or a5_pages != bundle["a5_page_count"]:
        raise RuntimeError("成品页数校验失败")
    progress(97, "核对页数与下载文件")

    pillars = [
        item.get("ganzhi")
        for item in facts.get("chart", {}).get("pillars", [])
        if item.get("ganzhi")
    ]
    # Segment PDFs and generated HTML are intermediate build artifacts.  The
    # final two books live under downloads/; removing the intermediates keeps
    # the persistent volume from growing by another full copy per report.
    shutil.rmtree(segment_dir, ignore_errors=True)
    for segment in bundle["segments"]:
        try:
            shutil.rmtree(Path(segment["html"]).parent, ignore_errors=True)
        except (OSError, TypeError, ValueError):
            pass
    localized_titles = {
        "zh-CN": f"{profile.get('display_name') or '个人'}的命书",
        "zh-TW": f"{profile.get('display_name') or '個人'}的命書",
        "en": f"{profile.get('display_name') or 'Personal'} MingShu Report",
        "ja": f"{profile.get('display_name') or '個人'}の命書",
        "ko": f"{profile.get('display_name') or '개인'} 명서",
    }
    time_basis = {
        "zh-CN": "北京时间",
        "zh-TW": "北京時間",
        "en": "Beijing Time",
        "ja": "北京時間",
        "ko": "베이징 시간",
    }
    return {
        "case_id": bundle["case_id"],
        "title": localized_titles[locale],
        "locale": locale,
        "birthplace": profile.get("birthplace", ""),
        "time_basis": time_basis[locale],
        "pillars": pillars,
        "spread_count": spread_pages,
        "a5_page_count": a5_pages,
        "downloads": {
            "spreads": spreads.name,
            "a5": a5.name,
        },
    }
