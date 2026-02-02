# Prompt Organization

Template management and prompt building for nodes and responses.

---

## Template Directories

- `agent/prompts/templates/` - General node templates
- `agent/prompts/geju/` - GEJU multi-stage workflow templates

## Fixed Template Mapping

| Node | Template File |
|------|---------------|
| `OVERALL` | `templates/init_analysis.md` |
| `SHISHEN` | `templates/shishen.md` |
| `WUXING_PREFS` | `templates/inter.md` |
| `RESPONSE_PROMPT` | `templates/final_answer.md` |

## GEJU Multi-Stage Templates

The GEJU analysis uses a 3-stage workflow with prompts in `agent/prompts/geju/`:

| Node | Template File | Description |
|------|---------------|-------------|
| `GEJU_ROUTER` | `# 格局判断路由.md` | Classifies pattern type, outputs JSON |
| `GEJU_ANALYSIS` | (dynamic selection) | Detailed analysis based on pattern |
| `GEJU_LEVEL` | `# 格局层次分析.md` | Evaluates pattern quality |

### GEJU_ANALYSIS Prompt Selection

Based on GEJU_ROUTER output:

| Router Category | Pattern Name | Template File |
|-----------------|--------------|---------------|
| `NORMAL` | 正官格 | `# 正格_正官格.md` |
| `NORMAL` | 财格 | `# 正格_财格.md` |
| `NORMAL` | 印格 | `# 正格_印格.md` |
| `NORMAL` | 食神格 | `# 正格_食神格.md` |
| `NORMAL` | 七杀格 | `# 正格_七杀格.md` |
| `NORMAL` | 伤官格 | `# 正格_伤官格.md` |
| `NORMAL` | 建禄格 | `# 正格_建禄格.md` |
| `NORMAL` | 羊刃格 | `# 正格_羊刃格.md` |
| `SPECIAL_1` | - | `# 特殊格局_专旺从格.md` |
| `SPECIAL_2` | - | `# 特殊格局_杂格.md` |
| `NONE` | - | `# 杂气无格.md` |

## Configuration Sets

`PROMPT_CONFIGS["lingyun_cat"]` maps domain nodes to corresponding `*_lym.md` templates.

`prompt_config` can be switched in profile (default `"lingyun_cat"`).

## Context Injection (`prompt_builder.py`)

Reads from cache and injects into user prompt:
- `PAIPAN` text (paipan/guji)
- `OVERALL`/`SHISHEN` `output.content`
- `GEJU_ROUTER`/`GEJU_ANALYSIS`/`GEJU_LEVEL` `output.content` (based on node dependencies)
- `WUXING_PREFS` `output.content`

## Response Prompt

Built using `build_response_prompt()` function:
- `time_context` passed as parameter (not read from cache)
- Combines all 3 GEJU stage outputs into a single "格局" section
- Additionally concatenates domain node reports
- User question
- Recent conversation rounds (`history_rounds`)

## year_data Injection

`TIME_CONTEXT` returns `year_data` containing dayun/liunian/liuyue details for each target year (from `find_yun_liu_nian_liuyue`), which is injected into the Response prompt.

## Fallback

Missing upstream content inserts empty string without throwing errors. For stronger prompts, add explicit missing content hints in `prompt_builder.py`.
