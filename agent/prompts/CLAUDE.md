# Prompt Organization

Template management and prompt building for nodes and responses.

---

## Template Directory

`agent/prompts/templates/`

## Fixed Template Mapping

| Node | Template File |
|------|---------------|
| `OVERALL` | `init_analysis.md` |
| `SHISHEN` | `shishen.md` |
| `GEJU` | `geju.md` |
| `WUXING_PREFS` | `inter.md` |
| `RESPONSE_PROMPT` | `final_answer.md` |

## Configuration Sets

`PROMPT_CONFIGS["lingyun_cat"]` maps domain nodes to corresponding `*_lym.md` templates.

`prompt_config` can be switched in profile (default `"lingyun_cat"`).

## Context Injection (`prompt_builder.py`)

Reads from cache and injects into user prompt:
- `PAIPAN` text (paipan/guji)
- `OVERALL`/`SHISHEN`/`GEJU`/`WUXING_PREFS` `output.content`

## Response Prompt

Built using `build_response_prompt()` function:
- `time_context` passed as parameter (not read from cache)
- Additionally concatenates domain node reports
- User question
- Recent conversation rounds (`history_rounds`)

## year_data Injection

`TIME_CONTEXT` returns `year_data` containing dayun/liunian/liuyue details for each target year (from `find_yun_liu_nian_liuyue`), which is injected into the Response prompt.

## Fallback

Missing upstream content inserts empty string without throwing errors. For stronger prompts, add explicit missing content hints in `prompt_builder.py`.
