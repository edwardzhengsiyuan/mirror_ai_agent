"""Compose a print-oriented MingShu document from facts and optional node output.

The composer is deliberately conservative. Deterministic chart facts can be
printed directly. LLM node text is only recorded as source material; it is not
silently copied into the reader-facing book. Validated ``ChapterDraft``
objects may replace the deterministic editorial copy later.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from copy import deepcopy
from typing import Any

from .contracts import ChapterDraft, validate_chapter_evidence


BOOK_SCHEMA_VERSION = "mingshu-book/1.0"

ELEMENT_BEHAVIOUR = {
    "木": "重视生长、连接与持续展开",
    "火": "重视表达、行动与把事物照亮",
    "土": "重视承接、稳定与把事情落到实处",
    "金": "重视边界、效率与清晰判断",
    "水": "重视观察、适应与信息流动",
}

SECTION_INTROS = {
    "front_matter": "先说明本书如何使用，再进入个人命盘。",
    "chart": "把出生信息转成一张可核对的结构图。",
    "origin": "观察命盘内部的力量、关系和组织方式。",
    "luck": "把时间视为环境变化，不把走势图当作命运判决。",
    "special_topics": "把原局与时间线翻译成可行动的人生主题。",
    "appendix": "留下术语、证据与版本信息，方便复核。",
}


def _compact_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _node_content(node_outputs: dict[str, Any] | None, node: str) -> str:
    if not node_outputs:
        return ""
    value = node_outputs.get(node)
    if isinstance(value, dict) and "output" in value:
        value = value.get("output")
    if isinstance(value, dict):
        if value.get("error") or value.get("stub"):
            return ""
        return str(value.get("content") or "").strip()
    return str(value or "").strip()


def summarize_node_sources(node_outputs: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Return a privacy-conscious manifest without storing raw LLM reasoning."""
    result: dict[str, dict[str, Any]] = {}
    if not node_outputs:
        return result
    for node in sorted(node_outputs):
        content = _node_content(node_outputs, node)
        result[node] = {
            "available": bool(content),
            "content_sha256": _compact_hash(content) if content else None,
            "characters": len(content),
        }
    return result


def _top_items(facts: dict, area: str, count: int = 3) -> list[dict]:
    items = list(((facts.get("analysis_facts") or {}).get(area) or []))
    return sorted(items, key=lambda item: float(item.get("percent") or 0), reverse=True)[:count]


def _day_master_sentence(facts: dict) -> str:
    chart = facts.get("chart") or {}
    master = chart.get("day_master") or {}
    strength = chart.get("strength") or {}
    element = master.get("wuxing_label") or "未标注"
    label = master.get("label") or "日主"
    strength_label = strength.get("label") or "强弱待核"
    return (
        f"这张命盘以日柱天干“{label}”为观察中心，五行属{element}；"
        f"综合季节与全盘助力来看，日主状态记作“{strength_label}”。"
    )


def _wuxing_sentence(facts: dict) -> str:
    items = _top_items(facts, "wuxing", 5)
    if not items:
        return "当前事实层没有可用的五行比例。"
    strongest = items[0]
    weakest = items[-1]
    behaviour = ELEMENT_BEHAVIOUR.get(strongest.get("label"), "形成命盘中较显眼的表达方式")
    return (
        f"五行比例中，{strongest.get('label')}约占{float(strongest.get('percent') or 0):.1f}%，"
        f"是当前计算中的最高项，常可先从“{behaviour}”理解；"
        f"{weakest.get('label')}约占{float(weakest.get('percent') or 0):.1f}%。"
        "比例描述的是结构，不直接等于优点、缺点或吉凶。"
    )


def _shishen_sentence(facts: dict) -> str:
    items = [item for item in _top_items(facts, "shishen", 4) if item.get("label") != "日主"]
    if not items:
        return "当前事实层没有可用的十神比例。"
    names = "、".join(
        f"{item.get('label')}（{float(item.get('percent') or 0):.1f}%）"
        for item in items[:3]
    )
    return f"按力量排序，较显眼的关系语言是{names}。后文还会结合它们落在哪一柱来读。"


def _relation_sentence(facts: dict) -> str:
    relations = list(((facts.get("analysis_facts") or {}).get("origin_relations") or []))
    if not relations:
        return "原局没有导出需要特别标注的干支组合。"
    names = "、".join(item.get("label") or item.get("relation_type") or "作用" for item in relations)
    return (
        f"原局共导出{len(relations)}组显式关系：{names}。"
        "关系表示两个位置会彼此牵动，仍需连同五行结果、距离和所在柱位一起理解。"
    )


def _nayin_sentence(facts: dict) -> str:
    pairs = []
    for pillar in (facts.get("chart") or {}).get("pillars") or []:
        nayin = pillar.get("nayin") or {}
        pairs.append(f"{pillar.get('label')}{pillar.get('ganzhi')}为{nayin.get('label') or '未标注'}")
    return "；".join(pairs) + "。纳音在本书中只承担意象补充，不作为主判断轴。"


def _zodiac_sentence(facts: dict) -> str:
    zodiac = (facts.get("chart") or {}).get("zodiac") or {}
    knowledge = zodiac.get("knowledge") or {}
    return (
        f"生肖为{zodiac.get('label') or '未标注'}。"
        f"{knowledge.get('introduction') or '生肖用于年柱文化背景的辅助阅读。'}"
        "它不能替代四柱整体分析。"
    )


def _cycle_for_slug(facts: dict, slug: str) -> dict | None:
    if not slug.startswith("dayun-"):
        return None
    try:
        target = int(slug.split("-", 1)[1])
    except (TypeError, ValueError):
        return None
    actual = [item for item in facts.get("luck_cycles") or [] if not item.get("is_pre_luck")]
    return actual[target - 1] if 0 < target <= len(actual) else None


def _cycle_activity(cycle: dict) -> int:
    """Calculate interaction activity, explicitly not a fortune score."""
    cycle_relations = len(cycle.get("relations") or [])
    year_relations = [len(item.get("relations") or []) for item in cycle.get("years") or []]
    average = (sum(year_relations) / len(year_relations)) if year_relations else 0
    return int(round(min(100, 18 + cycle_relations * 12 + average * 11)))


def _cycle_copy(cycle: dict) -> dict[str, Any]:
    relation_names = list(dict.fromkeys(item.get("label") or "作用" for item in cycle.get("relations") or []))
    relation_text = "、".join(relation_names) if relation_names else "没有导出显式关系"
    stem_god = (cycle.get("gan_shishen") or {}).get("label") or "未标注"
    branch_god = (cycle.get("zhi_shishen") or {}).get("label") or "未标注"
    activity = _cycle_activity(cycle)
    years = list(cycle.get("years") or [])
    busy_years = sorted(
        years,
        key=lambda item: len(item.get("relations") or []),
        reverse=True,
    )[:3]
    busy = "、".join(f"{item.get('year')}年{item.get('ganzhi')}" for item in busy_years)
    return {
        "deck": (
            f"{cycle.get('start_year')}—{cycle.get('end_year')}，约从{cycle.get('age_start')}岁开始；"
            f"运柱为{cycle.get('name')}。"
        ),
        "paragraphs": [
            (
                f"这一阶段的天干十神为{stem_god}，地支十神为{branch_god}。"
                "两者分别提示外在议题与更深层的环境作用，但不宜单独解释。"
            ),
            (
                f"大运与原局导出的主要作用为{relation_text}。"
                f"按关系数量计算的“结构活跃度”为{activity}/100；"
                "这个数只表示变化与牵动的密度，不表示好运或坏运。"
            ),
            (
                f"本运中作用关系相对较多的年份包括{busy or '暂无'}。"
                "这些年份更适合提前留意议题变化，再用真实经历判断它带来的是机会、压力，还是二者并存。"
            ),
        ],
        "takeaways": [
            "先看阶段主题，再看具体年份。",
            "关系多意味着议题活跃，不等于结果更差。",
            "换运前后各一年宜保留观察窗口。",
        ],
        "facts": {
            "cycle_id": cycle.get("id"),
            "activity_index": activity,
            "score": cycle.get("score"),
            "score_status": cycle.get("score_status"),
        },
    }


def _default_copy(spread: dict, facts: dict) -> dict[str, Any]:
    slug = spread.get("slug")
    section = spread.get("section")
    top_wuxing = _top_items(facts, "wuxing", 3)
    top_shishen = [item for item in _top_items(facts, "shishen", 4) if item.get("label") != "日主"][:3]
    subject = facts.get("subject") or {}
    chart = facts.get("chart") or {}
    pillars = chart.get("pillars") or []
    pillar_text = "　".join(item.get("ganzhi") or "" for item in pillars)
    if subject.get("birth_time_unknown"):
        confidence = "出生时辰尚未确定，涉及时柱的内容只能作为暂时参考。"
    else:
        confidence = "本书按所提供的出生日期与时辰排盘；若原始记录有误，相关解读也会随之改变。"
    cycle = _cycle_for_slug(facts, slug or "")
    if cycle:
        result = _cycle_copy(cycle)
        result.update(
            {
                "kicker": "阶段阅读",
                "title": f"{cycle.get('name')}大运",
                "callout_title": "放回生活里看",
                "callout": "结构活跃度只表示变化密度，不等于吉凶；请结合当时的选择与现实条件阅读。",
            }
        )
        return result

    templates: dict[str, dict[str, Any]] = {
        "cover": {
            "kicker": "MIRROR PERSONAL CHART BOOK",
            "title": "命书",
            "deck": f"{subject.get('display_name') or '命主'}的四柱阅读档案",
            "paragraphs": [pillar_text, "原局 · 大运 · 人生主题"],
            "takeaways": ["一册只对应一份出生资料。"],
        },
        "edition-note": {
            "kicker": "阅读之前",
            "title": "这本书怎样使用",
            "deck": "它是一份传统文化视角下的自我观察材料，不是不可改变的命运判决。",
            "paragraphs": [
                confidence,
                "书中先呈现可以核对的排盘，再用图解和日常语言说明其中的关系。",
                "健康、法律、投资与重大关系决定，请以专业意见和现实信息为准。",
            ],
            "takeaways": [
                "先核对出生资料。",
                "看趋势，不看宿命。",
                "把建议变成可验证的小行动。",
                "重要事项以现实信息和专业意见为准。",
            ],
        },
        "contents-one": {
            "kicker": "目录一",
            "title": "认识原局",
            "deck": "从完整排盘出发，依次看日主、五行、十神、格局和干支关系。",
            "paragraphs": [
                "先确认四柱与出生资料，再看五行如何分布、十神如何互动，以及格局怎样组织全盘。",
                "纳音、神煞与生肖作为文化意象穿插其中，帮助理解，但不代替原局的整体关系。",
            ],
            "takeaways": ["排盘", "五行", "十神", "格局", "纳音与神煞"],
        },
        "contents-two": {
            "kicker": "目录二",
            "title": "时间与人生主题",
            "deck": "从十年阶段到具体生活主题，观察环境变化与个人选择如何相遇。",
            "paragraphs": [
                "大运部分先看十年主题，再留意关键年份；专项部分分别谈学习、事业、财富、感情与家庭。",
                "同一种命盘倾向，在不同年龄与生活环境中可能呈现出不同面貌。",
            ],
            "takeaways": ["大运总览", "七步大运", "事业财富", "感情家庭", "身心节律"],
        },
        "complete-chart": {
            "kicker": "完整排盘",
            "title": "先核对，再解读",
            "deck": f"四柱为：{pillar_text}",
            "paragraphs": [
                _day_master_sentence(facts),
                "年柱常作为早期环境与社会背景的入口；月柱是季节和命盘结构的重要支点；日柱连接自我与亲密关系；时柱常用于长期愿景与后段人生观察。",
                confidence,
            ],
            "takeaways": ["四柱是否正确", "公历时间是否正确", "性别与时辰是否正确"],
        },
        "origin-overview": {
            "kicker": "原局总览",
            "title": "先看整张命盘",
            "deck": _day_master_sentence(facts),
            "paragraphs": [_wuxing_sentence(facts), _shishen_sentence(facts), _relation_sentence(facts)],
            "takeaways": ["日主是观察中心。", "比例不是吉凶。", "关系要连同柱位一起看。"],
        },
        "wuxing-basics": {
            "kicker": "通用知识",
            "title": "五行不是五种物质",
            "deck": "木、火、土、金、水是一套描述变化关系的语言。",
            "paragraphs": [
                "木偏向生长与展开，火偏向表达与显现，土偏向承接与整合，金偏向边界与收敛，水偏向流动与适应。",
                "相生表示资源如何传递，相克表示边界如何建立。两者都不是天然的好或坏。",
                "命书中的比例图帮助看结构重心；真正的喜忌还需要结合季节、格局与调候。",
            ],
            "takeaways": ["看关系，不贴标签。", "看整体，不只看缺什么。"],
        },
        "wuxing-balance": {
            "kicker": "个人结构",
            "title": "你的五行力量分布",
            "deck": _wuxing_sentence(facts),
            "paragraphs": [
                "图中的比例由命盘各处五行换算而来，适合用来比较相对重心。",
                "占比最高的元素往往更容易被本人或他人察觉；占比较低的元素不代表完全没有，也不建议简单用颜色、饰物等替代现实行动。",
            ],
            "takeaways": [f"{item.get('label')} {float(item.get('percent') or 0):.1f}%" for item in top_wuxing],
        },
        "wuxing-flow": {
            "kicker": "结构关系",
            "title": "命盘怎样流动",
            "deck": "力量不只看多少，还要看它能否顺畅传递。",
            "paragraphs": [
                _wuxing_sentence(facts),
                "图中的箭头展示相生的阅读顺序，圆的大小展示当前比例。实际命盘还要结合透干、藏干、季节和干支作用。",
                "如果某一环节很强而下一环承接不足，常表现为能量集中；如果多个环节彼此接续，则更容易形成稳定的表达路径。",
            ],
            "takeaways": ["先找起点。", "再看承接。", "最后看哪里形成回路或阻滞。"],
        },
        "strength-climate": {
            "kicker": "季节与尺度",
            "title": "强弱不是性格强弱",
            "deck": _day_master_sentence(facts),
            "paragraphs": [
                "身强身弱描述日主在出生季节与全盘支持关系中的相对状态，不等于意志、能力或身体强弱。",
                "调候关注命盘所处的寒暖燥湿，是另一条观察轴。格局、调候和力量平衡可能给出不同优先级，因此正式喜忌需要明确采用哪一种依据。",
            ],
            "takeaways": ["强弱是结构术语。", "季节决定背景。", "喜忌要说明判断依据。"],
        },
        "ten-gods-basics": {
            "kicker": "通用知识",
            "title": "十神是十种关系语言",
            "deck": "十神描述日主与其他五行之间的生克、同异与阴阳关系。",
            "paragraphs": [
                "比肩、劫财关乎同类与自主；食神、伤官关乎输出与表达；正财、偏财关乎资源与结果；正官、七杀关乎规则与压力；正印、偏印关乎吸收与支持。",
                "同一个十神在不同柱位、不同强弱和不同组合中会有不同表现，因此不能只凭一个名称概括性格。",
            ],
            "takeaways": ["同类", "输出", "资源", "规则", "支持"],
        },
        "ten-gods-balance": {
            "kicker": "个人结构",
            "title": "你的十神力量分布",
            "deck": _shishen_sentence(facts),
            "paragraphs": [
                "比例图帮助识别哪些关系语言更常出现，但仍需查看它来自天干还是藏干、落在哪一柱、是否得到季节支持。",
                "较高项可以理解为常用通道；较低项可能需要特定环境才显现。",
            ],
            "takeaways": [f"{item.get('label')} {float(item.get('percent') or 0):.1f}%" for item in top_shishen],
        },
        "ten-gods-position": {
            "kicker": "位置阅读",
            "title": "十神落在哪里",
            "deck": "同一种关系语言，落在年、月、日、时会连接不同的人生场景。",
            "paragraphs": [
                "天干较像显在表面的行为与议题，藏干更像需要条件才被看见的内在资源。",
                "本书把每一柱的天干十神与藏干十神并列呈现，方便查看某种力量是显露、扎根，还是只在局部出现。",
                _shishen_sentence(facts),
            ],
            "takeaways": ["看柱位。", "看透藏。", "看是否重复出现。"],
        },
        "origin-relations": {
            "kicker": "干支作用",
            "title": "命盘内部如何彼此牵动",
            "deck": _relation_sentence(facts),
            "paragraphs": [
                "合、冲、刑、害、穿等词描述结构之间的作用方式，不宜直接翻译成某件具体事件。",
                "距离较近的柱位通常更直接；跨柱关系则需要结合所代表的场景。关系图保留来源位置，避免只凭一个术语下结论。",
            ],
            "takeaways": ["先看哪两柱。", "再看作用类型。", "最后看结果五行和现实场景。"],
        },
        "pattern": {
            "kicker": "组织方式",
            "title": "格局不是身份等级",
            "deck": "格局用于描述命盘如何围绕月令和主要力量组织起来。",
            "paragraphs": [
                f"当前命盘较接近“{('、'.join(item.get('label') or '' for item in chart.get('patterns') or []) or '尚需结合全盘确认')}”。",
                "格局是否成立，要同时看月令、透干、根气与全盘制化，也要留意可能改变判断的条件。",
                "格局名称描述的是力量的组织方式，不代表身份高低，也不能单独保证成败。",
            ],
            "takeaways": ["说明成立条件。", "保留反证。", "不把格局等同社会层级。"],
        },
        "nayin": {
            "kicker": "补充意象",
            "title": "四柱的纳音",
            "deck": _nayin_sentence(facts),
            "paragraphs": [
                "六十甲子各有一组纳音名称，适合用来补充每一柱的文化意象。",
                "本书为每一柱提供一句通俗解释，但不会用纳音单独判断强弱、格局、职业或婚姻。",
            ],
            "takeaways": [f"{item.get('label')} · {(item.get('nayin') or {}).get('label')}" for item in pillars],
        },
        "shensha-zodiac": {
            "kicker": "辅助阅读",
            "title": "神煞与生肖",
            "deck": _zodiac_sentence(facts),
            "paragraphs": [
                "神煞来自固定查表规则，只作为个人特点的补充线索，不能用来保证具体事件。",
                "同一柱可能同时出现多个名称，甚至包含方向相反的文化意象；因此只保留与主结构能互相印证的部分。",
                _zodiac_sentence(facts),
            ],
            "takeaways": ["生肖只来自年支。", "神煞必须有查表来源。", "主结构优先于辅助标签。"],
        },
        "luck-overview": {
            "kicker": "时间轴",
            "title": "七步大运总览",
            "deck": "先看十年环境如何变化，再进入每一步大运。",
            "paragraphs": [
                "每一步大运都列出运柱、十神、与原局的关系和十个流年。",
                "走势图中的“结构活跃度”表示关系牵动的密度，并不是吉凶分。线条越高，越值得结合现实事件仔细观察。",
                "大运不是从某天突然切换，交运前后宜作为连续过渡期观察。",
            ],
            "takeaways": ["总览阶段主题。", "区分活跃度与顺逆度。", "关键年份回到现实事件验证。"],
        },
        "luck-transitions": {
            "kicker": "时间交界",
            "title": "换运节点与关键年份",
            "deck": "转换期往往比单一年份更值得观察。",
            "paragraphs": [
                "本书把每一步大运的末年、下一步大运的首年并列，形成前后各一年的观察窗口。",
                "若某个流年同时与原局和大运发生多组关系，可标记为“议题活跃”；但仍不能只凭关系数量判断结果。",
                "建议把实际发生的学习、迁移、工作、关系和健康事件记在时间轴旁，作为后续校准资料。",
            ],
            "takeaways": ["观察前后两年。", "记录现实事件。", "根据反馈更新判断。"],
        },
        "personality": {
            "kicker": "专项 · 自我",
            "title": "性格是结构与环境的共同结果",
            "deck": f"{_day_master_sentence(facts)} {_shishen_sentence(facts)}",
            "paragraphs": [
                "性格章节优先描述可观察的行为倾向，例如决策速度、表达方式、边界感和恢复节奏。",
                "命盘只提供倾向线索；家庭、教育、职业训练和个人选择都会改变它的表现方式。",
                _relation_sentence(facts),
            ],
            "takeaways": ["把标签改成行为。", "同时写优势和过度使用的代价。", "允许人在不同环境中表现不同。"],
        },
        "talent-learning-style": {
            "kicker": "专项 · 学习",
            "title": "找到更省力的输入输出循环",
            "deck": "天赋不是单点能力，而是吸收、加工、表达和反馈形成的循环。",
            "paragraphs": [
                _shishen_sentence(facts),
                "印星类线索常用于观察吸收与理解，食伤类线索用于观察表达与产出，官杀类线索用于观察目标和标准，财星类线索用于观察成果与资源。",
                "适合的学习方式应通过现实表现验证，例如先听后做、先搭框架后练习，或通过讲给别人听来巩固。",
            ],
            "takeaways": ["输入方式", "练习节奏", "反馈形式"],
        },
        "education": {
            "kicker": "专项 · 学业",
            "title": "学业看能力，也看阶段和方法",
            "deck": "把考试、学历和持续学习分开观察。",
            "paragraphs": [
                "学业判断需要同时看吸收能力、规则适应、输出稳定性和大运环境，不能只抓住一个“文昌”或一个十神。",
                "命书最终应给出具体方法：如何安排复习、怎样处理压力、什么环境更能维持专注，而不是保证某次考试结果。",
            ],
            "takeaways": ["方法比标签重要。", "阶段变化要结合现实目标。", "不预测录取保证。"],
        },
        "career-core": {
            "kicker": "专项 · 事业",
            "title": "工作方式比职业名称更稳定",
            "deck": "先识别如何解决问题，再讨论行业和岗位。",
            "paragraphs": [
                _shishen_sentence(facts),
                "事业核心关注自主与协作、探索与执行、规则与弹性、短期结果与长期积累之间的偏好。",
                "同一种能力可以出现在多个行业，因此本书用角色任务描述方向，不把八字直接映射为单一职业。",
            ],
            "takeaways": ["擅长解决什么问题", "喜欢怎样协作", "需要怎样的评价机制"],
        },
        "career-direction": {
            "kicker": "专项 · 事业",
            "title": "选择适配的角色与环境",
            "deck": "行业只是外壳，角色、组织阶段和工作节奏才决定日常体验。",
            "paragraphs": [
                "方向矩阵从工作结构、信息密度、人员协作、结果周期和自主空间五个维度筛选环境。",
                "命盘线索可用来提出假设，最终应以履历、技能、机会成本和真实反馈作决定。",
            ],
            "takeaways": ["先选问题类型。", "再选组织环境。", "最后看行业机会。"],
        },
        "career-timing": {
            "kicker": "专项 · 事业",
            "title": "事业节奏与转折窗口",
            "deck": "用大运观察环境变化，用现实条件决定是否行动。",
            "paragraphs": [
                "事业时间线应标注学习期、积累期、扩张期和调整期，同时保留不确定性。",
                "结构活跃的年份适合提前准备备选方案、技能储备和现金缓冲，不代表必须跳槽或创业。",
            ],
            "takeaways": ["提前准备。", "小步验证。", "重要决定保留现实缓冲。"],
        },
        "wealth-model": {
            "kicker": "专项 · 财富",
            "title": "财富先看创造、承接与留存",
            "deck": "财星只是资源关系的一部分，不等于财富金额。",
            "paragraphs": [
                "财富模式拆为价值创造、交换定价、资源配置、风险控制和长期留存五个环节。",
                "命盘可以提示更习惯主动开拓、稳定积累还是通过专业能力变现，但不能代替财务数据和投资分析。",
            ],
            "takeaways": ["收入来源", "现金流稳定性", "风险承受力", "长期留存机制"],
        },
        "wealth-risk": {
            "kicker": "专项 · 财富",
            "title": "把风险写成可以管理的动作",
            "deck": "不预测具体收益，不推荐具体投资品。",
            "paragraphs": [
                "风险页关注收入集中度、负债、冲动决策、合伙边界和阶段性现金压力。",
                "所谓“财运变化”应翻译成预算、合同、储备和决策流程，而不是用吉凶词替代管理。",
            ],
            "takeaways": ["建立应急金。", "重大决策设置冷静期。", "合伙与借贷保留书面边界。"],
        },
        "love-pattern": {
            "kicker": "专项 · 关系",
            "title": "亲密关系中的需要与表达",
            "deck": "关系分析描述互动模式，不给某个人下命定结论。",
            "paragraphs": [
                "本章关注靠近方式、情绪表达、冲突处理、个人空间和承诺节奏。",
                _relation_sentence(facts),
                "原局关系可以提示哪些议题容易被触发，但现实中的沟通能力和双方意愿更重要。",
            ],
            "takeaways": ["说清需要。", "区分事实与猜测。", "为冲突建立暂停和复盘机制。"],
        },
        "marriage-partner": {
            "kicker": "专项 · 婚姻",
            "title": "伴侣画像应写成相处条件",
            "deck": "不预测唯一伴侣，不承诺结婚年份，也不以八字替代双方选择。",
            "paragraphs": [
                "所谓伴侣画像，更适合翻译成价值观、生活节奏、边界、责任分配和沟通方式。",
                "时间线只标记关系议题可能更活跃的阶段，并要求回到现实关系状态验证。",
            ],
            "takeaways": ["价值观是否兼容", "冲突能否修复", "责任是否可协商"],
        },
        "family-guiren": {
            "kicker": "专项 · 支持",
            "title": "支持网络不只来自某一个人",
            "deck": "家庭、同辈、老师、伙伴和制度资源共同构成支持系统。",
            "paragraphs": [
                "六亲和贵人线索适合观察互动角色，不宜推断亲属寿命、疾病或不可改变的关系结局。",
                "真正有效的贵人关系通常建立在能力可见、互惠、信用和清晰请求之上。",
            ],
            "takeaways": ["识别已有支持。", "让能力被看见。", "把求助说具体。"],
        },
        "health": {
            "kicker": "专项 · 身心",
            "title": "关注节律，不做疾病诊断",
            "deck": _wuxing_sentence(facts),
            "paragraphs": [
                "五行在本章只用于观察工作—休息、表达—恢复、活动—安静之间的节律偏好。",
                "不根据命盘诊断疾病、器官问题或寿命。持续不适、睡眠障碍或情绪困扰应咨询合格专业人士。",
            ],
            "takeaways": ["规律睡眠", "适度活动", "定期体检", "持续不适及时就医"],
        },
        "glossary": {
            "kicker": "附录",
            "title": "一看就懂的术语",
            "deck": "只保留阅读本书真正需要的概念。",
            "paragraphs": [
                "日主：日柱天干，是全盘关系的观察中心。五行比例：命盘中五种力量的相对分布。十神：其他干支与日主的关系名称。",
                "格局：命盘围绕月令与主要力量形成的组织方式。大运：约十年一段的时间环境。流年：某一个公历年份的干支背景。",
                "神煞：按固定规则查出的辅助标签。纳音：六十甲子的文化意象分类。",
            ],
            "takeaways": ["术语服务于理解，不用于制造神秘感。"],
        },
        "evidence-colophon": {
            "kicker": "写在最后",
            "title": "给未来的自己留一页",
            "deck": "命盘提供一种观察角度，生活会不断补上新的答案。",
            "paragraphs": [
                "可以记下真实发生的重要事件、当时的选择，以及后来回看时的新理解。",
                "当经历与书中的描述不一致时，以你的真实经验为准；那正是重新认识自己的入口。",
                "愿这本书成为一份可以反复翻阅、持续补写的个人观察档案。",
            ],
            "takeaways": ["记录经历", "回看选择", "更新理解"],
        },
    }
    result = deepcopy(templates.get(slug) or {})
    if not result:
        result = {
            "kicker": spread.get("title") or "命书",
            "title": spread.get("title") or "未命名章节",
            "deck": SECTION_INTROS.get(section, "从完整命盘出发，观察这一主题如何在生活中呈现。"),
            "paragraphs": [
                SECTION_INTROS.get(section, "本章用通俗语言说明命盘中的一个侧面。"),
                "请把这一页与完整命盘和真实经历放在一起阅读，不必用单一标签定义自己。",
            ],
            "takeaways": ["看见倾向。", "联系经历。", "保留变化空间。"],
        }
    result.setdefault("callout_title", "放回生活里看")
    reader_paragraphs = list(result.get("paragraphs") or [])
    result.setdefault(
        "callout",
        reader_paragraphs[0] if reader_paragraphs else result.get("deck") or SECTION_INTROS.get(section, ""),
    )
    result.setdefault("facts", {})
    return result


def _chapter_copy(chapter: ChapterDraft) -> dict[str, Any]:
    paragraphs = [
        f"{claim.text} {claim.plain_language_reason}"
        for claim in chapter.claims
    ]
    return {
        "kicker": "个性化解读",
        "title": chapter.title,
        "deck": chapter.deck,
        "paragraphs": paragraphs,
        "takeaways": list(chapter.reader_takeaways),
        "callout_title": "放回生活里看",
        "callout": chapter.uncertainty_note or "真实表现会随环境、阶段与个人选择而变化。",
        "knowledge_card_codes": list(chapter.knowledge_card_codes),
        "evidence_ids": sorted(
            {
                evidence_id
                for claim in chapter.claims
                for evidence_id in claim.evidence_ids
            }
        ),
        "facts": {"chapter_status": "validated"},
    }


def compose_book(
    facts: dict,
    blueprint: dict,
    *,
    node_outputs: dict[str, Any] | None = None,
    chapter_drafts: dict[str, ChapterDraft] | None = None,
    generated_at: dt.datetime | None = None,
) -> dict:
    """Build a complete 80-page document manifest.

    ``chapter_drafts`` must already satisfy the strict chapter contract. Their
    evidence identifiers are checked again against the supplied facts.
    """
    if blueprint.get("edition", {}).get("total_pages") != 80:
        raise ValueError("the standard composer currently expects an 80-page blueprint")
    chapter_drafts = chapter_drafts or {}
    spreads = []
    for spread in blueprint.get("spreads") or []:
        slug = spread.get("slug")
        chapter = chapter_drafts.get(slug)
        if chapter is not None:
            if chapter.spread_slug != slug:
                raise ValueError(f"chapter spread mismatch: expected {slug}, got {chapter.spread_slug}")
            valid, message = validate_chapter_evidence(chapter, facts)
            if not valid:
                raise ValueError(message)
            copy = _chapter_copy(chapter)
            status = "validated_chapter"
        else:
            copy = _default_copy(spread, facts)
            status = "deterministic_editorial"
        spreads.append(
            {
                **deepcopy(spread),
                "copy": copy,
                "status": status,
            }
        )

    timestamp = generated_at or dt.datetime.now(dt.UTC)
    result = {
        "schema_version": BOOK_SCHEMA_VERSION,
        "generated_at": timestamp.isoformat().replace("+00:00", "Z"),
        "edition": deepcopy(blueprint.get("edition") or {}),
        "subject": deepcopy(facts.get("subject") or {}),
        "fact_source": deepcopy(facts.get("source") or {}),
        "node_source_manifest": summarize_node_sources(node_outputs),
        "spreads": spreads,
        "generation": {
            "total_pages": sum(int(item.get("pages") or 0) for item in spreads),
            "validated_chapters": sum(item["status"] == "validated_chapter" for item in spreads),
            "deterministic_editorial_spreads": sum(
                item["status"] == "deterministic_editorial" for item in spreads
            ),
            "raw_node_text_printed": False,
            "safety_note": (
                "健康、法律、投资和重大关系议题仅作传统文化视角下的自我观察，"
                "不替代专业意见。"
            ),
        },
    }
    result["manifest_sha256"] = _compact_hash(
        {
            "schema_version": result["schema_version"],
            "edition": result["edition"],
            "subject": result["subject"],
            "fact_source": result["fact_source"],
            "spreads": result["spreads"],
        }
    )
    return result
