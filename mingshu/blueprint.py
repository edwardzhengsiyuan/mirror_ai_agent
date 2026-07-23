"""Editorial blueprint for the default 80-page MingShu edition."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class EditionProfile:
    code: str
    name: str
    total_pages: int
    trim_size: str
    page_budgets: dict[str, int]


@dataclass(frozen=True)
class SpreadSpec:
    slug: str
    section: str
    title: str
    purpose: str
    visuals: tuple[str, ...]
    sources: tuple[str, ...]
    knowledge_cards: tuple[str, ...] = ()
    word_budget: int = 420
    personalized_ratio: int = 70
    pages: int = 2

    def to_dict(self, page_start: int) -> dict:
        data = asdict(self)
        data["visuals"] = list(self.visuals)
        data["sources"] = list(self.sources)
        data["knowledge_cards"] = list(self.knowledge_cards)
        data["page_start"] = page_start
        data["page_end"] = page_start + self.pages - 1
        return data


STANDARD_EDITION = EditionProfile(
    code="standard-80",
    name="典藏版",
    total_pages=80,
    trim_size="A5 148×210mm",
    page_budgets={
        "front_matter": 8,
        "chart": 2,
        "origin": 24,
        "luck": 18,
        "special_topics": 24,
        "appendix": 4,
    },
)

EDITION_OPTIONS = {
    "concise-56": {
        "name": "雅简版",
        "pages": 56,
        "allocation": "前置6 + 排盘2 + 原局14 + 大运12 + 专项18 + 附录4",
    },
    "standard-80": {
        "name": "典藏版",
        "pages": 80,
        "allocation": "前置8 + 排盘2 + 原局24 + 大运18 + 专项24 + 附录4",
    },
    "deluxe-96": {
        "name": "珍藏版",
        "pages": 96,
        "allocation": "前置8 + 排盘2 + 原局30 + 大运20 + 专项32 + 附录4",
    },
}


_STANDARD_SPREADS: tuple[SpreadSpec, ...] = (
    SpreadSpec(
        "cover",
        "front_matter",
        "封面与命书题名",
        "建立个人专属感；只呈现姓名、四柱剪影与版本信息，不在封面堆叠结论。",
        ("cover_art", "four_pillar_seal"),
        ("subject", "chart.pillars"),
        word_budget=40,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "edition-note",
        "front_matter",
        "开始阅读之前",
        "说明命书如何生成、哪些是事实、哪些是解释，并提示健康和重大决策边界。",
        ("evidence_legend",),
        ("source", "subject.confidence_note"),
        word_budget=520,
        personalized_ratio=20,
    ),
    SpreadSpec(
        "contents-one",
        "front_matter",
        "目录：认识原局",
        "用读者语言展示前半册路径，让第一次接触八字的人知道每章回答什么。",
        ("chapter_map",),
        ("blueprint",),
        word_budget=240,
        personalized_ratio=10,
    ),
    SpreadSpec(
        "contents-two",
        "front_matter",
        "目录：时间与人生主题",
        "展示大运与专项章节，并提供颜色、图标和证据编号的阅读图例。",
        ("chapter_map", "visual_legend"),
        ("blueprint",),
        word_budget=300,
        personalized_ratio=10,
    ),
    SpreadSpec(
        "complete-chart",
        "chart",
        "完整排盘",
        "在一个跨页内看清四柱、藏干、十神、纳音、地势、旬空、胎元、命宫和身宫。",
        ("pillar_table", "auxiliary_pillars"),
        ("chart",),
        word_budget=180,
        personalized_ratio=100,
    ),
    SpreadSpec(
        "origin-overview",
        "origin",
        "先看整张命盘",
        "用一页总览说明日主、月令、力量重心和需要继续验证的关键矛盾。",
        ("origin_snapshot", "evidence_badges"),
        ("chart.day_master", "chart.strength", "OVERALL"),
        word_budget=520,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "wuxing-basics",
        "origin",
        "五行不是五种物质",
        "先用生活化语言解释五行的功能与相互关系，再进入个人比例。",
        ("five_element_cycle",),
        ("knowledge.wuxing",),
        ("wuxing",),
        word_budget=620,
        personalized_ratio=20,
    ),
    SpreadSpec(
        "wuxing-balance",
        "origin",
        "你的五行力量分布",
        "展示比例、排序、显著高低与证据来源，不把“少”直接写成“缺”。",
        ("wuxing_donut", "wuxing_rank"),
        ("analysis_facts.wuxing", "OVERALL"),
        word_budget=520,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "wuxing-flow",
        "origin",
        "命盘怎样流动",
        "把生、克与原盘力量放在同一张图中，解释哪里顺接、哪里需要转化。",
        ("wuxing_flow", "plain_language_callouts"),
        ("visuals.wuxing_flow", "OVERALL"),
        word_budget=560,
        personalized_ratio=85,
    ),
    SpreadSpec(
        "strength-climate",
        "origin",
        "强弱、季节与调候",
        "把身强身弱解释为承载能力与季节背景，不贴“好命/坏命”标签。",
        ("strength_scale", "season_climate"),
        ("chart.strength", "OVERALL", "guji"),
        word_budget=620,
        personalized_ratio=80,
    ),
    SpreadSpec(
        "ten-gods-basics",
        "origin",
        "十神：十种关系语言",
        "用两组关系图介绍比劫、食伤、财、官杀、印，避免术语堆砌。",
        ("ten_god_family", "relationship_arrows"),
        ("knowledge.ten_gods",),
        ("ten_gods",),
        word_budget=720,
        personalized_ratio=20,
    ),
    SpreadSpec(
        "ten-gods-balance",
        "origin",
        "你的十神力量分布",
        "展示主要与次要十神、缺席项及组合，不把单个十神写成固定人格。",
        ("shishen_bar", "top_three_cards"),
        ("analysis_facts.shishen", "SHISHEN"),
        word_budget=560,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "ten-gods-position",
        "origin",
        "十神落在哪里",
        "解释年、月、日、时的位置，以及透出、藏干和通根怎样改变表现方式。",
        ("pillar_ten_god_map", "root_map"),
        ("chart.pillars", "analysis_facts.shishen_clues", "SHISHEN"),
        word_budget=680,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "origin-relations",
        "origin",
        "干支之间的作用",
        "用节点连线图显示合、冲、刑、穿等关系，并逐条翻译为可理解的动态。",
        ("origin_relation_network", "relation_legend"),
        ("analysis_facts.origin_relations", "SHISHEN"),
        word_budget=620,
        personalized_ratio=95,
    ),
    SpreadSpec(
        "pattern",
        "origin",
        "格局：命盘的组织方式",
        "先介绍所判格局本身，再讲成格、破格、救应和层次；不展示模型内部推理草稿。",
        ("pattern_mechanism", "formation_checklist"),
        ("chart.patterns", "GEJU_ROUTER", "GEJU_ANALYSIS", "GEJU_LEVEL"),
        ("geju",),
        word_budget=760,
        personalized_ratio=75,
    ),
    SpreadSpec(
        "nayin",
        "origin",
        "纳音：四柱的补充意象",
        "补齐四柱纳音的名称、比喻和所在柱位，并明确它不是主判断轴。",
        ("nayin_four_cards", "pillar_ribbon"),
        ("chart.pillars.nayin",),
        ("nayin",),
        word_budget=640,
        personalized_ratio=55,
    ),
    SpreadSpec(
        "shensha-zodiac",
        "origin",
        "神煞与生肖",
        "只挑与本盘相关且有依据的高信号内容；生肖作为文化导读，不替代整体分析。",
        ("shensha_constellation", "zodiac_illustration"),
        ("analysis_facts.shensha", "chart.zodiac", "OVERALL"),
        ("zodiac", "shensha"),
        word_budget=680,
        personalized_ratio=70,
    ),
    SpreadSpec(
        "luck-overview",
        "luck",
        "大运总览与走势读法",
        "展示七步大运的区间、主题、分数和置信度；分数必须来自结构化喜忌结果。",
        ("dayun_trend", "score_method"),
        ("visuals.dayun_timeline", "WUXING_PREFS"),
        word_budget=640,
        personalized_ratio=90,
    ),
    *tuple(
        SpreadSpec(
            f"dayun-{index}",
            "luck",
            f"第{index}步大运",
            "左页解释这十年的主旋律、原局互动与机会成本；右页给出十年内关键年份小时间线。",
            ("dayun_score_gauge", "element_effect", "key_year_timeline"),
            (f"luck_cycles[{index}]", "WUXING_PREFS", "time_context"),
            word_budget=760,
            personalized_ratio=95,
        )
        for index in range(1, 8)
    ),
    SpreadSpec(
        "luck-transitions",
        "luck",
        "换运节点与关键年份",
        "集中展示运与运之间的交界、强触发年份和阅读不确定性，避免逐年流水账。",
        ("transition_timeline", "confidence_band"),
        ("luck_cycles", "WUXING_PREFS"),
        word_budget=620,
        personalized_ratio=95,
    ),
    SpreadSpec(
        "personality",
        "special_topics",
        "性格底色",
        "从日主、十神、强弱与作用关系归纳行为倾向，并同时写出优势与过度使用时的代价。",
        ("personality_axes", "evidence_cards"),
        ("XINGGE", "analysis_facts.shishen", "analysis_facts.origin_relations"),
        word_budget=720,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "talent-learning-style",
        "special_topics",
        "天赋与学习方式",
        "把吸收、表达、执行、协作四类能力分开，提供适合的学习和反馈方式。",
        ("talent_radar", "learning_loop"),
        ("CAREER", "SHISHEN", "chart.pillars"),
        word_budget=700,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "education",
        "special_topics",
        "学业与考试",
        "把原事业节点中的学业内容独立成章，区分长期学习、考试发挥与资格型成长。",
        ("study_strengths", "study_timeline"),
        ("CAREER", "WUXING_PREFS"),
        word_budget=700,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "career-core",
        "special_topics",
        "事业能力与工作方式",
        "说明适合怎样承担责任、解决问题与协作，不直接给出唯一职业答案。",
        ("career_compass", "role_cards"),
        ("CAREER", "GEJU_ANALYSIS", "SHISHEN"),
        word_budget=760,
        personalized_ratio=95,
    ),
    SpreadSpec(
        "career-direction",
        "special_topics",
        "行业与角色方向",
        "把行业五行翻译成工作环境和任务类型，用角色条件而非行业名单做建议。",
        ("role_environment_matrix", "career_filters"),
        ("CAREER", "WUXING_PREFS"),
        word_budget=720,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "career-timing",
        "special_topics",
        "事业阶段与转折",
        "把事业主题映射到大运区间，标注适合积累、切换、承担和复盘的阶段。",
        ("career_timeline", "transition_markers"),
        ("CAREER", "luck_cycles", "WUXING_PREFS"),
        word_budget=720,
        personalized_ratio=95,
    ),
    SpreadSpec(
        "wealth-model",
        "special_topics",
        "财富模式",
        "把正偏财、食伤、比劫与官印关系翻译成收入来源、资源管理和风险偏好。",
        ("wealth_flow", "resource_model"),
        ("OTHER", "SHISHEN", "WUXING_PREFS"),
        word_budget=720,
        personalized_ratio=90,
    ),
    SpreadSpec(
        "wealth-risk",
        "special_topics",
        "财富节奏与风险",
        "展示不同大运的资源主题与风险提醒；不提供具体投资标的或收益承诺。",
        ("wealth_timeline", "risk_matrix"),
        ("OTHER", "luck_cycles", "WUXING_PREFS"),
        word_budget=700,
        personalized_ratio=95,
    ),
    SpreadSpec(
        "love-pattern",
        "special_topics",
        "亲密关系中的你",
        "解释情感需求、表达方式、关系张力与可沟通之处，避免宿命化标签。",
        ("relationship_needs", "interaction_loop"),
        ("RELATIONSHIP", "SHISHEN", "analysis_facts.origin_relations"),
        word_budget=760,
        personalized_ratio=95,
    ),
    SpreadSpec(
        "marriage-partner",
        "special_topics",
        "婚姻与伴侣画像",
        "区分夫妻星、夫妻宫与岁运触发，给出条件式画像和时间窗而非绝对断言。",
        ("partner_profile", "relationship_timeline"),
        ("RELATIONSHIP", "LIUQIN", "luck_cycles"),
        word_budget=760,
        personalized_ratio=95,
    ),
    SpreadSpec(
        "family-guiren",
        "special_topics",
        "家庭、六亲与贵人",
        "把父母、手足、子女、支持系统和贵人来源放在一张关系地图中。",
        ("family_map", "support_network"),
        ("LIUQIN", "GUIREN", "analysis_facts.shensha"),
        word_budget=760,
        personalized_ratio=95,
    ),
    SpreadSpec(
        "health",
        "special_topics",
        "身心节律与生活方式",
        "只做传统五行视角的生活节律提示，明确不替代医学诊断、检查或治疗。",
        ("wellbeing_balance", "habit_cards"),
        ("HEALTH", "analysis_facts.wuxing"),
        word_budget=660,
        personalized_ratio=85,
    ),
    SpreadSpec(
        "glossary",
        "appendix",
        "一看就懂的术语表",
        "收录本册实际出现的术语，每条只给一句普通话解释，并回链首次出现页。",
        ("alphabetical_index",),
        ("used_terms", "knowledge"),
        word_budget=900,
        personalized_ratio=20,
    ),
    SpreadSpec(
        "evidence-colophon",
        "appendix",
        "给未来的自己留一页",
        "记录真实经历、当时的选择与后来回看时的新理解。",
        ("provenance_block", "notes_page"),
        ("source", "generation_manifest"),
        word_budget=360,
        personalized_ratio=70,
    ),
)


def _validate_blueprint(spreads: Iterable[SpreadSpec], edition: EditionProfile) -> None:
    spreads = tuple(spreads)
    total = sum(item.pages for item in spreads)
    if total != edition.total_pages:
        raise ValueError(f"blueprint has {total} pages, expected {edition.total_pages}")
    by_section: dict[str, int] = {}
    for item in spreads:
        by_section[item.section] = by_section.get(item.section, 0) + item.pages
    if by_section != edition.page_budgets:
        raise ValueError(f"section pages {by_section!r} do not match {edition.page_budgets!r}")
    if total % 4:
        raise ValueError("booklet page count must be divisible by 4")


def build_standard_blueprint() -> dict:
    _validate_blueprint(_STANDARD_SPREADS, STANDARD_EDITION)
    page = 1
    spreads = []
    for item in _STANDARD_SPREADS:
        spreads.append(item.to_dict(page))
        page += item.pages
    return {
        "schema_version": "mingshu-blueprint/1.0",
        "edition": asdict(STANDARD_EDITION),
        "edition_options": EDITION_OPTIONS,
        "spreads": spreads,
    }
