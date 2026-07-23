"""Resumable batch generation for validated MingShu chapters."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from .contracts import ChapterDraft
from .generation import generate_chapter


PERSONALIZED_SPREAD_SLUGS = (
    "origin-overview",
    "wuxing-balance",
    "wuxing-flow",
    "strength-climate",
    "ten-gods-balance",
    "ten-gods-position",
    "origin-relations",
    "pattern",
    "luck-overview",
    "dayun-1",
    "dayun-2",
    "dayun-3",
    "dayun-4",
    "dayun-5",
    "dayun-6",
    "dayun-7",
    "luck-transitions",
    "personality",
    "talent-learning-style",
    "education",
    "career-core",
    "career-direction",
    "career-timing",
    "wealth-model",
    "wealth-risk",
    "love-pattern",
    "marriage-partner",
    "family-guiren",
    "health",
)


def chapter_path(output_dir: str | Path, slug: str) -> Path:
    return Path(output_dir) / f"{slug}.json"


def load_chapter_drafts(output_dir: str | Path) -> dict[str, ChapterDraft]:
    result: dict[str, ChapterDraft] = {}
    directory = Path(output_dir)
    if not directory.exists():
        return result
    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("_"):
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        chapter = ChapterDraft.model_validate(value)
        result[chapter.spread_slug] = chapter
    return result


def _write_status(output_dir: Path, status: dict) -> None:
    (output_dir / "_batch-status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_chapter_batch(
    facts: dict,
    blueprint: dict,
    *,
    output_dir: str | Path,
    node_outputs: dict[str, Any] | None = None,
    slugs: Iterable[str] = PERSONALIZED_SPREAD_SLUGS,
    model: str | None = None,
    node_model_overrides: dict[str, str] | None = None,
    resume: bool = True,
    limit: int | None = None,
    on_progress: Callable[[dict], None] | None = None,
) -> dict[str, ChapterDraft]:
    """Generate chapters one at a time and persist each successful result."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    by_slug = {item.get("slug"): item for item in blueprint.get("spreads") or []}
    selected = list(dict.fromkeys(str(slug) for slug in slugs))
    unknown = sorted(set(selected) - set(by_slug))
    if unknown:
        raise ValueError(f"unknown spread slugs: {', '.join(unknown)}")
    existing = load_chapter_drafts(directory) if resume else {}
    queue = [slug for slug in selected if slug not in existing]
    if limit is not None:
        queue = queue[: max(0, limit)]
    status = {
        "schema_version": "mingshu-chapter-batch/1.0",
        "started_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "requested": selected,
        "completed": sorted(existing),
        "pending": queue,
        "failed": {},
    }
    _write_status(directory, status)
    for slug in queue:
        spread = by_slug[slug]
        event = {"slug": slug, "state": "running"}
        if on_progress:
            on_progress(event)
        try:
            chapter = generate_chapter(
                spread,
                facts,
                node_outputs=node_outputs,
                model=model,
                node_model_overrides=node_model_overrides,
            )
        except Exception as exc:
            status["failed"][slug] = str(exc)
            status["pending"] = [item for item in status["pending"] if item != slug]
            _write_status(directory, status)
            if on_progress:
                on_progress({"slug": slug, "state": "failed", "error": str(exc)})
            continue
        chapter_path(directory, slug).write_text(
            json.dumps(chapter.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        existing[slug] = chapter
        status["completed"] = sorted(existing)
        status["pending"] = [item for item in status["pending"] if item != slug]
        _write_status(directory, status)
        if on_progress:
            on_progress({"slug": slug, "state": "completed"})
    status["finished_at"] = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    _write_status(directory, status)
    return existing
