"""Localize rendered MingShu HTML without changing its print structure."""

from __future__ import annotations

import json
import html as html_module
import re
from collections.abc import Callable

from agent.tools.llm_tool import llm_report_tool


SUPPORTED_REPORT_LOCALES = {"zh-CN", "zh-TW", "en", "ja", "ko"}

_TARGETS = {
    "zh-TW": ("繁體中文", "zh-Hant"),
    "en": ("English", "en"),
    "ja": ("自然な日本語", "ja"),
    "ko": ("자연스러운 한국어", "ko"),
}
_CHINESE_RE = re.compile(r"[\u3400-\u9fff]")
_PROTECTED_RE = re.compile(
    r"(<(?:style|script)\b[^>]*>)(.*?)(</(?:style|script)>)",
    re.IGNORECASE | re.DOTALL,
)
_TEXT_RE = re.compile(r">([^<>]+)<")
_ATTR_RE = re.compile(r'\b(alt|aria-label|title)="([^"]+)"')

BatchTranslator = Callable[[list[dict[str, str]], str], dict[str, str]]


def _escape_translation(value: str, *, quote: bool) -> str:
    """Escape translated copy while preserving existing HTML entities."""
    entities: list[str] = []

    def mask(match: re.Match[str]) -> str:
        entities.append(match.group(0))
        return f"__MINGSHU_ENTITY_{len(entities) - 1}__"

    masked = re.sub(r"&(?:#[0-9]+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);", mask, value)
    escaped = html_module.escape(masked, quote=quote)
    for index, entity in enumerate(entities):
        escaped = escaped.replace(f"__MINGSHU_ENTITY_{index}__", entity)
    return escaped


def normalize_report_locale(value: object) -> str:
    locale = str(value or "zh-CN").strip()
    if locale not in SUPPORTED_REPORT_LOCALES:
        raise ValueError(f"unsupported report locale: {locale}")
    return locale


def _json_object(content: str) -> dict:
    candidate = str(content or "").strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    return json.loads(candidate)


def _validator(expected_ids: set[str]):
    def validate(content: str) -> tuple[bool, str]:
        try:
            payload = _json_object(content)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return False, f"invalid JSON: {exc}"
        rows = payload.get("translations")
        if not isinstance(rows, list):
            return False, "translations must be a list"
        actual: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                return False, "translation rows must be objects"
            row_id = row.get("id")
            text = row.get("text")
            if not isinstance(row_id, str) or not isinstance(text, str) or not text.strip():
                return False, "every translation needs a non-empty id and text"
            actual.add(row_id)
        if actual != expected_ids:
            return False, "translation ids do not match the requested batch"
        return True, ""

    return validate


def _llm_translate_batch(rows: list[dict[str, str]], locale: str) -> dict[str, str]:
    target_name, _ = _TARGETS[locale]
    system_prompt = (
        f"你是四柱八字出版物的专业译者。把输入文本翻译成{target_name}。"
        "保持甲乙丙丁、子丑寅卯、干支组合、数字、年份、百分比和事实含义准确；"
        "十神、格局、大运、流年、纳音、神煞等术语采用目标语言常用说法，必要时保留汉字术语。"
        "不要增删判断，不要解释翻译过程，不要翻译 HTML 实体。只返回指定 JSON。"
    )
    prompt = (
        "逐项翻译 text，id 原样返回，顺序不变。返回格式："
        '{"translations":[{"id":"t0","text":"..."}]}\n\n'
        f"输入：\n{json.dumps(rows, ensure_ascii=False)}"
    )
    expected_ids = {row["id"] for row in rows}
    result = llm_report_tool(
        system_prompt,
        prompt,
        node=f"MINGSHU_LOCALIZE_{locale.upper().replace('-', '_')}",
        output_validator=_validator(expected_ids),
        validation_retries=2,
    )
    if result.get("error") or result.get("stub"):
        raise RuntimeError(f"report localization unavailable for {locale}")
    payload = _json_object(result.get("content") or "")
    return {row["id"]: row["text"] for row in payload["translations"]}


def _chunks(rows: list[dict[str, str]], max_chars: int = 6500, max_items: int = 70):
    current: list[dict[str, str]] = []
    current_chars = 0
    for row in rows:
        size = len(row["text"])
        if current and (len(current) >= max_items or current_chars + size > max_chars):
            yield current
            current = []
            current_chars = 0
        current.append(row)
        current_chars += size
    if current:
        yield current


def localize_html(
    html: str,
    locale: str,
    *,
    translate_batch: BatchTranslator | None = None,
) -> str:
    """Translate visible HTML text while preserving CSS, scripts, and markup."""
    locale = normalize_report_locale(locale)
    if locale == "zh-CN":
        return html
    translator = translate_batch or _llm_translate_batch
    protected: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected.append(match.group(2))
        return f"{match.group(1)}__MINGSHU_PROTECTED_{len(protected) - 1}__{match.group(3)}"

    masked = _PROTECTED_RE.sub(protect, html)
    values: list[str] = []
    seen: set[str] = set()

    def collect(value: str) -> None:
        core = value.strip()
        if not core or core.startswith("__MINGSHU_PROTECTED_") or not _CHINESE_RE.search(core):
            return
        if core not in seen:
            seen.add(core)
            values.append(core)

    for match in _TEXT_RE.finditer(masked):
        collect(match.group(1))
    for match in _ATTR_RE.finditer(masked):
        collect(match.group(2))

    rows = [{"id": f"t{index}", "text": value} for index, value in enumerate(values)]
    translated: dict[str, str] = {}
    for batch in _chunks(rows):
        translated.update(translator(batch, locale))
    by_source = {row["text"]: translated[row["id"]] for row in rows}

    def replace_text(match: re.Match[str]) -> str:
        value = match.group(1)
        core = value.strip()
        replacement = by_source.get(core)
        if replacement is None:
            return match.group(0)
        leading = value[: len(value) - len(value.lstrip())]
        trailing = value[len(value.rstrip()) :]
        return f">{leading}{_escape_translation(replacement, quote=False)}{trailing}<"

    def replace_attr(match: re.Match[str]) -> str:
        replacement = by_source.get(match.group(2))
        return match.group(0) if replacement is None else f'{match.group(1)}="{_escape_translation(replacement, quote=True)}"'

    localized = _TEXT_RE.sub(replace_text, masked)
    localized = _ATTR_RE.sub(replace_attr, localized)
    _, html_lang = _TARGETS[locale]
    localized = re.sub(r'<html\s+lang="[^"]*"', f'<html lang="{html_lang}"', localized, count=1)
    for index, value in enumerate(protected):
        localized = localized.replace(f"__MINGSHU_PROTECTED_{index}__", value)
    return localized


def localize_html_file(path, locale: str) -> None:
    content = path.read_text(encoding="utf-8")
    path.write_text(localize_html(content, locale), encoding="utf-8")


def localize_html_files(paths, locale: str) -> None:
    """Localize a report bundle together so repeated labels translate once."""
    items = list(paths)
    if not items or normalize_report_locale(locale) == "zh-CN":
        return
    markers = [f"<!--MINGSHU_FILE_BREAK_{index}-->" for index in range(len(items) - 1)]
    combined_parts: list[str] = []
    for index, path in enumerate(items):
        combined_parts.append(path.read_text(encoding="utf-8"))
        if index < len(markers):
            combined_parts.append(markers[index])
    localized = localize_html("".join(combined_parts), locale)
    pages = [localized]
    for marker in markers:
        next_pages: list[str] = []
        for page in pages:
            next_pages.extend(page.split(marker))
        pages = next_pages
    if len(pages) != len(items):
        raise RuntimeError("localized report bundle could not be separated")
    for path, content in zip(items, pages, strict=True):
        path.write_text(content, encoding="utf-8")
