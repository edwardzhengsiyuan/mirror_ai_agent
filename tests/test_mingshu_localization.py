from __future__ import annotations

from mingshu.localization import localize_html, normalize_report_locale


def _fake_translate(rows, locale):
    prefix = {"en": "EN", "ja": "JA", "ko": "KO", "zh-TW": "TW"}[locale]
    return {row["id"]: f"{prefix}:{row['text']}" for row in rows}


def test_localize_html_translates_visible_text_and_attributes() -> None:
    source = '''<!doctype html><html lang="zh-CN"><head>
    <title>命书</title><style>.x:after{content:"中文样式"}</style>
    <script>const label = "中文脚本";</script></head>
    <body><h1 aria-label="命书标题">个人命书</h1><p>认识自己的命盘</p></body></html>'''

    localized = localize_html(source, "ja", translate_batch=_fake_translate)

    assert '<html lang="ja"' in localized
    assert "JA:命书" in localized
    assert 'aria-label="JA:命书标题"' in localized
    assert "JA:个人命书" in localized
    assert "JA:认识自己的命盘" in localized
    assert 'content:"中文样式"' in localized
    assert 'const label = "中文脚本"' in localized


def test_localize_html_keeps_simplified_chinese_unchanged() -> None:
    source = '<html lang="zh-CN"><body><p>命书</p></body></html>'
    assert localize_html(source, "zh-CN", translate_batch=_fake_translate) == source


def test_report_locale_validation() -> None:
    assert normalize_report_locale("ko") == "ko"
    assert normalize_report_locale(None) == "zh-CN"
    try:
        normalize_report_locale("fr")
    except ValueError as exc:
        assert "unsupported report locale" in str(exc)
    else:
        raise AssertionError("unsupported locale must be rejected")


def test_localization_escapes_translated_markup_and_preserves_entities() -> None:
    def translator(rows, _locale):
        return {row["id"]: 'A & B < C &nbsp; "quoted"' for row in rows}

    localized = localize_html(
        '<html lang="zh-CN"><body><p title="中文">中文</p></body></html>',
        "ja",
        translate_batch=translator,
    )

    assert 'A &amp; B &lt; C &nbsp; "quoted"' in localized
    assert 'title="A &amp; B &lt; C &nbsp; &quot;quoted&quot;"' in localized
