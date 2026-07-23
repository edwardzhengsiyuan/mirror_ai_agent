"""Evidence-bound special-topic analysis for the printed MingShu.

The legacy agent prompts contain useful symbolic mappings, but also a number of
deterministic claims.  This module deliberately works from structured chart
facts and rewrites the result as observable tendencies, choices and boundaries.
"""

from __future__ import annotations

from .luck_analysis import build_luck_analysis
from .pattern import build_pattern_analysis


PALACE_MEANING = {
    "year": "早年环境、家族外缘与他人最先看到的一面",
    "month": "成长方式、工作场域与日常运行习惯",
    "day": "自我核心、亲密关系与共同生活",
    "hour": "长期计划、个人作品与未来安排",
}


def _pillar(facts: dict, key: str) -> dict:
    return next(item for item in facts["chart"]["pillars"] if item["key"] == key)


def _hidden(pillar: dict) -> list[str]:
    return [item["shishen_label"] for item in pillar["zhi"].get("hidden_gans") or []]


def _relation(facts: dict, label: str) -> dict:
    return next(item for item in facts["analysis_facts"]["origin_relations"] if item["label"] == label)


def _top_cycles(luck: dict, *, reverse: bool = True, count: int = 3) -> list[dict]:
    return sorted(luck["cycles"], key=lambda item: item["score"], reverse=reverse)[:count]


def _cycle_cards(luck: dict) -> list[dict]:
    return [
        {
            "name": item["name"],
            "years": f'{item["start_year"]}—{item["end_year"]}',
            "score": item["score"],
            "band": item["band"],
            "focus": item["headline"],
        }
        for item in luck["cycles"]
    ]


def build_topics_analysis(facts: dict) -> dict:
    """Build the seven special reports from actual structured chart output."""

    year = _pillar(facts, "year")
    month = _pillar(facts, "month")
    day = _pillar(facts, "day")
    hour = _pillar(facts, "hour")
    luck = build_luck_analysis(facts)
    pattern = build_pattern_analysis(facts)
    wuxing = {item["label"]: item["percent"] for item in facts["analysis_facts"]["wuxing"]}
    shishen = {item["label"]: item["percent"] for item in facts["analysis_facts"]["shishen"]}
    shensha = {
        place: [item["name"] for item in rows]
        for place, rows in facts["analysis_facts"]["shensha"].items()
    }

    pillars = []
    for pillar in facts["chart"]["pillars"]:
        pillars.append(
            {
                "key": pillar["key"],
                "label": pillar["label"],
                "ganzhi": pillar["ganzhi"],
                "gan_god": pillar["gan"]["shishen_label"],
                "hidden": _hidden(pillar),
                "palace": PALACE_MEANING[pillar["key"]],
            }
        )

    best = _top_cycles(luck)
    demanding = _top_cycles(luck, reverse=False)
    if facts["chart"]["day_master"]["label"] == "辛" and month["zhi"]["name_label"] == "午":
        relation_names = [item["label"] for item in facts["analysis_facts"]["origin_relations"]]
        return {
            "schema_version": "mingshu-topics/1.0",
            "chart": {"ganzhi": "｜".join(item["ganzhi"] for item in facts["chart"]["pillars"]), "day_master": "辛", "strength": facts["chart"]["strength"]["label"], "pillars": pillars, "relations": relation_names},
            "personality": {
                "topic": "性格", "title": "细致有判断，压力越大越需要清楚次序",
                "summary": "辛金日主重视分寸、品质和准确；生于午月，七杀成为最强十神，使做事带有时限感和责任感。壬伤官透在月干，又让你不只是照章执行，而会主动发现问题、提出更有效的方法。",
                "layers": [
                    {"name": "外在表现", "evidence": f'七杀{shishen["七杀"]:.2f}%', "reading": "遇到明确任务时反应快、责任感强，容易先把问题接住。"},
                    {"name": "价值尺度", "evidence": f'正偏财合计{shishen["正财"]+shishen["偏财"]:.2f}%', "reading": "看重投入是否形成真实结果，也会留意资源、成本与长期兑现。"},
                    {"name": "思考方式", "evidence": f'伤官{shishen["伤官"]:.2f}%', "reading": "习惯从差异和问题入手，适合分析、改进与清楚表达。"},
                    {"name": "压力反应", "evidence": "午午自刑、日主偏弱", "reading": "忙碌时容易反复催促自己；把优先级、完成标准和休息时间写清楚更有效。"},
                ],
                "strengths": ["辨别细节和质量", "能在压力下抓住重点", "善于发现流程问题", "对资源与结果保持现实感"],
                "watch": ["要求过多时容易持续紧绷", "替目标投入过量资源", "观点正确却表达过急", "休息时仍在心里反复推演"],
            },
            "career": {
                "topic": "事业", "title": "把判断力用于复杂任务，把压力变成专业标准",
                "summary": "七杀格候选强调目标、责任和时限；伤官透出，说明你的优势不只是执行，还包括发现问题和改进方法。印星藏支可承接压力，适合通过专业体系、资质和复盘形成长期壁垒。",
                "structure": [
                    {"step": "识别问题", "gods": "伤官", "fact": "壬伤官透月干", "reading": "先看见规则、流程或产品中真正需要调整的地方。"},
                    {"step": "承担目标", "gods": "七杀", "fact": "午中丁七杀当令", "reading": "把复杂问题落到期限、责任人和可验证标准。"},
                    {"step": "建立方法", "gods": "偏印", "fact": "午未藏己偏印", "reading": "用知识体系、模板和复盘降低长期承压成本。"},
                ],
                "roles": [{"name": "项目与运营治理", "fit": "目标明确、需要多方协调与风险预案"}, {"name": "风控与质量管理", "fit": "需要标准、细节判断和持续改进"}, {"name": "研究与咨询", "fit": "把复杂问题整理成可执行方案"}, {"name": "产品与解决方案", "fit": "兼顾用户问题、资源边界和交付结果"}],
                "boundaries": ["职责增加时同步确认权限和资源", "不要用持续加班替代流程改进", "表达异议时先给证据和替代方案", "把复盘、文档与培训沉淀为团队资产"],
                "cycles": _cycle_cards(luck), "best": best, "demanding": demanding, "pattern": pattern,
            },
            "study": {
                "topic": "学业", "title": "适合先发现问题，再用体系和输出完成掌握",
                "summary": "伤官透干带来问题意识和表达欲，偏印藏于午未，适合通过自己的理解框架消化知识。最有效的路径不是只背结论，而是提出问题、查证依据、做出案例，再用讲解或作品检验。",
                "method": [{"name": "从问题进入", "why": "伤官透月", "how": "先写清要解决的问题，再选择资料。"}, {"name": "搭建框架", "why": "偏印藏支", "how": "把概念组织成自己的图表、索引和方法。"}, {"name": "用案例检验", "why": "财星明显", "how": "让知识进入真实任务，验证能否产生结果。"}, {"name": "定期复盘", "why": "午午自刑", "how": "用记录打断反复推演，按阶段收束分支。"}],
                "advantages": ["问题意识强", "能辨别差异与漏洞", "适合案例驱动", "能够形成自己的解释框架"], "friction": ["容易对不严谨处过度较真", "压力大时学习变成任务堆积", "同时研究太多分支", "缺少输出时难以判断掌握程度"],
                "support": [name for names in shensha.values() for name in names if name in {"天乙贵人", "太极贵人", "天厨贵人"}],
            },
            "relationship": {
                "topic": "感情", "title": "需要可靠回应，也需要减少没有说出口的猜测",
                "summary": "日支未以偏印为本气，同时藏七杀与偏财，亲密关系既需要理解和私人空间，也会认真面对责任与现实安排。月支、时支两午都与日支未相合，工作节奏、未来计划和共同生活容易彼此绑定。",
                "needs": [{"name": "理解与空间", "evidence": "日支未本气偏印", "reading": "需要能交流想法，也允许各自保留安静思考时间。"}, {"name": "可靠承担", "evidence": "未中藏七杀", "reading": "承诺最好落到时间、责任与具体行动。"}, {"name": "现实共建", "evidence": "财星透年时", "reading": "会关注两个人如何安排资源、生活和未来目标。"}, {"name": "表达确认", "evidence": "亥午暗合", "reading": "默契很重要，但关键决定仍需明确说出，不靠猜测。"}],
                "interactions": [{"fact": "午未六合", "meaning": "工作环境与未来计划都会靠近日支的共同生活位置，关系容易和现实事务绑定。", "action": "共同目标之外，也保留不以任务为目的的相处时间。"}, {"fact": "午午自刑", "meaning": "双方压力或计划增多时，容易在心里反复、越想解决越紧绷。", "action": "先暂停升级争论，约定一个具体问题和复盘时间。"}, {"fact": "天乙贵人", "meaning": "传统上提示关键处较容易得到帮助，也表示愿意求助时支持更容易接上。", "action": "关系卡住时及时寻求可信赖的朋友或专业帮助。"}, {"fact": "空亡在年柱", "meaning": "外界印象或早期经验不一定等于真实的亲密需求。", "action": "用当下相处事实判断关系，不让旧期待替你做决定。"}],
            },
            "health": {
                "topic": "身心", "title": "重点是降温、恢复与减少持续紧绷",
                "summary": f'午月气候炎热，火约{wuxing["火"]:.2f}%，金约{wuxing["金"]:.2f}%。传统取象提示高压和燥热环境下更要重视恢复；这只能用于生活方式观察，不能判断疾病或寿命。',
                "signals": [{"name": "节奏", "fact": "七杀最强", "reading": "容易把任务当成必须立即解决，需明确真正的优先级。"}, {"name": "反复", "fact": "午午自刑", "reading": "工作结束后头脑仍可能继续运转，固定收尾仪式有帮助。"}, {"name": "调候", "fact": "辛午取壬己", "reading": "规律饮水、睡眠、安静时间与稳定饮食，比临时补偿更重要。"}, {"name": "就医边界", "fact": "命理不是医学工具", "reading": "持续不适、异常指标或情绪困扰应交由合格专业人员处理。"}],
                "routine": ["固定睡眠与结束工作的时间", "连续高压后安排完整恢复段", "用任务清单减少脑内反复", "保留体检记录，用医学数据判断健康"],
            },
            "family": {
                "topic": "六亲", "title": "把家庭影响读成关系角色，不替任何亲属定性",
                "summary": "四柱宫位帮助观察你在家庭与支持网络中的惯常角色，但不能替代真实家史。这里重点看责任、沟通和边界，不推断亲属的寿命、品行或必然遭遇。",
                "palaces": [{"name": f'{x["label"]}·{x["ganzhi"]}', "role": x["palace"], "reading": f'{x["gan_god"]}透于天干，地支还藏{"、".join(x["hidden"])}；这一位置常围绕这些角色语言展开，仍需用真实经历核对。'} for x in pillars],
                "support": [{"name": "外部帮助", "facts": "天德、天乙、太极、国印、金舆", "reading": "愿意求助、守信用并把事情说明白时，更容易接到经验与资源。"}, {"name": "日常照料", "facts": "天厨贵人见月时", "reading": "具体照料、饮食和把生活安排妥帖，是重要的支持方式。"}, {"name": "亲密支持", "facts": "日支未承接两组午未合", "reading": "支持与共同生活、工作节奏和未来安排紧密相连，需要主动沟通负荷。"}],
            },
            "risk": {
                "topic": "风险", "title": "不预言灾祸，只管理反复出现的压力结构",
                "summary": "本节不预测事故、疾病、破产或生死。所谓风险，只指可以观察的压力来源：持续高压、目标过量、内在反复、默契代替沟通，以及责任与资源不匹配。",
                "matrix": [{"level": "较高", "name": "持续高压", "source": f'七杀{shishen["七杀"]:.2f}%', "signal": "所有任务都被当作紧急", "response": "每周只保留少数最高优先级，并确认可用资源。"}, {"level": "较高", "name": "内在反复", "source": "午午自刑", "signal": "结束后仍不断复盘和自责", "response": "设定收尾时间，用书面复盘替代脑内循环。"}, {"level": "中等", "name": "目标过量", "source": f'财星{shishen["正财"]+shishen["偏财"]:.2f}%生杀', "signal": "机会越多，责任同步增加", "response": "新增目标前先删减旧目标，核对权限、预算和退出条件。"}, {"level": "中等", "name": "沟通错位", "source": "亥午暗合", "signal": "彼此以为已经说清，其实理解不同", "response": "重要安排复述时间、责任和交付标准。"}, {"level": "基础", "name": "恢复不足", "source": "仲夏炎热、日主偏弱", "signal": "靠紧张维持效率", "response": "把睡眠、饮食、运动与求助纳入固定计划。"}],
                "cycle_watch": demanding, "cycle_support": best,
            },
            "boundaries": ["所有结论都来自结构化排盘、五行、十神、干支作用、神煞与大运计算。", "专项报告描述倾向和可观察条件，不保证事件必然发生。", "健康、法律、投资和安全问题应由相应专业人员与现实证据判断。"],
        }
    return {
        "schema_version": "mingshu-topics/1.0",
        "chart": {
            "ganzhi": "｜".join(item["ganzhi"] for item in facts["chart"]["pillars"]),
            "day_master": facts["chart"]["day_master"]["label"],
            "strength": facts["chart"]["strength"]["label"],
            "pillars": pillars,
            "relations": [item["label"] for item in facts["analysis_facts"]["origin_relations"]],
        },
        "personality": {
            "topic": "性格",
            "title": "热心而务实，敏锐但不愿空转",
            "summary": "丁火日主生于巳月，火的行动感很强；正偏财同时透出，又把注意力拉回结果、资源与兑现。时干偏印让你保留自己的研究路径，因此你并非只凭热情做事，而是会不断寻找更聪明的办法。",
            "layers": [
                {"name": "外在表现", "evidence": f'火占{wuxing["火"]:.2f}%，年支又见午', "reading": "进入状态快，愿意带头推进；别人通常先感受到你的反应速度和投入感。"},
                {"name": "价值尺度", "evidence": f'正财{shishen["正财"]:.2f}%、偏财{shishen["偏财"]:.2f}%，均有透干', "reading": "很难长期满足于只有概念、没有成果的事情，更在意投入最终能否形成作品、收入或可复用资源。"},
                {"name": "思考方式", "evidence": "时干乙偏印，且乙辛相冲", "reading": "习惯独立研究、跨领域联想；但个人兴趣和现实回报有时会拉扯，需要明确哪些探索值得继续。"},
                {"name": "压力反应", "evidence": f'劫财{shishen["劫财"]:.2f}%，两见巳火', "reading": "忙碌或竞争加剧时容易加速、亲自上手。有效的做法不是继续提速，而是先划分权限、时间和完成标准。"},
            ],
            "strengths": ["对机会与资源变化较敏感", "能把抽象想法推到实际结果", "独立学习与临场调整能力较强", "愿意承担并带动周围的人"],
            "watch": ["任务越多越容易同时开线", "现实回报与个人兴趣可能互相牵动", "合作中需要提前说清投入与分配", "恢复时间不足时判断会变得急促"],
        },
        "career": {
            "topic": "事业",
            "title": "用专业产出连接资源与结果",
            "summary": "格局脚本没有给出确定主格，书中只把财格列为中等可信度候选；更明确的是食神、伤官能够生财。适合你的并不是某一个固定职业名，而是“把知识或方法做成成果，再让成果进入真实交换”的工作结构。",
            "structure": [
                {"step": "方法与表达", "gods": "食神·伤官", "fact": "戊己土藏于午、巳、丑", "reading": "先把经验整理成产品、流程、内容或解决方案。"},
                {"step": "资源与回报", "gods": "正财·偏财", "fact": "庚辛透干，且在巳丑有根", "reading": "成果需要清晰报价、交付标准和长期复用方式。"},
                {"step": "长期壁垒", "gods": "偏印", "fact": "乙偏印落时干", "reading": "持续研究和独到方法，是后期拉开差异的部分。"},
            ],
            "roles": [
                {"name": "产品与项目", "fit": "把需求、资源、进度和交付串成闭环"},
                {"name": "咨询与解决方案", "fit": "把复杂问题拆解为客户能采用的方法"},
                {"name": "内容与知识产品", "fit": "研究—表达—复用—变现的链条与原盘相合"},
                {"name": "商务与资源整合", "fit": "适合有专业门槛、需要判断机会质量的岗位"},
            ],
            "boundaries": ["不宜只有灵感、没有交付定义", "合伙前先写清决策权与收益分配", "避免为了短期机会频繁改动长期主线", "用数据和成品检验方向，不用忙碌感代替进展"],
            "cycles": _cycle_cards(luck),
            "best": best,
            "demanding": demanding,
            "pattern": pattern,
        },
        "study": {
            "topic": "学业",
            "title": "适合带着问题学，再把知识做出来",
            "summary": "乙偏印透在时干，说明独立研究和非标准路径很重要；食神、伤官藏在地支，则提示真正掌握常发生在讲解、制作、演示或解决实际问题之后。纯背诵并非不能做，但不是最省力的入口。",
            "method": [
                {"name": "从问题进入", "why": "偏印透时", "how": "先提出一个真实问题，再围绕它搭建知识地图。"},
                {"name": "用作品检验", "why": "食伤生财", "how": "每个学习周期都留下文章、模型、案例或可演示成品。"},
                {"name": "建立主线", "why": "乙辛相冲", "how": "探索可以分叉，但要保留一个可长期累积的核心领域。"},
                {"name": "同伴反馈", "why": "比劫与劫财有力", "how": "用讨论、共创和公开讲解校正理解，同时设定比较的边界。"},
            ],
            "advantages": ["跨领域联想", "案例驱动理解", "快速形成个人方法", "把知识转成可用表达"],
            "friction": ["兴趣过多导致主线分散", "过早追求回报打断基础积累", "快节奏下跳过复盘", "只输入不输出时不易确认掌握程度"],
            "support": [name for names in shensha.values() for name in names if name in {"德秀贵人", "天厨贵人", "月德贵人"}],
        },
        "relationship": {
            "topic": "感情",
            "title": "需要可靠的日常，也需要清楚的边界",
            "summary": "日支丑中以食神为先，亲密关系更容易通过照顾、陪伴和具体生活安排建立安全感。财星透出使你在关系里愿意承担现实责任；但午丑穿和乙辛冲也说明，外部节奏、资源选择与私人生活可能互相挤压。",
            "needs": [
                {"name": "稳定回应", "evidence": "日支丑藏食神", "reading": "关心最好落实到时间、行动和可以依赖的日常。"},
                {"name": "共同建设", "evidence": "正偏财透干", "reading": "比起只有情绪浓度，更看重两个人能否共同安排现实生活。"},
                {"name": "个人空间", "evidence": "时干偏印", "reading": "需要保留独处、研究和形成自己判断的时间。"},
                {"name": "规则透明", "evidence": "劫财较有力", "reading": "金钱、时间、人情和社交边界越早谈清楚，关系越轻松。"},
            ],
            "interactions": [
                {"fact": "午丑穿", "meaning": "外界期待或工作节奏容易进入共同生活，形成小事反复磨损。", "action": "遇到摩擦时先谈具体安排，不把一次失约扩大成性格判断。"},
                {"fact": "乙辛冲", "meaning": "个人想法与现实资源之间会出现选择题，也可能表现为一方想探索、一方更看重确定性。", "action": "把分歧拆成目标、预算和时限，给探索设置可回看节点。"},
                {"fact": "桃花在年支", "meaning": "在外部社交中较容易被注意，也容易因积极、能推进而形成吸引力。", "action": "吸引力不等于长期适配，仍要观察价值观和日常节奏。"},
                {"fact": "阴差阳错在日柱", "meaning": "传统神煞提醒关系中容易有时机、表达或理解的错位。", "action": "重要决定不要依赖猜测；确认对方听见的，是否就是自己想表达的。"},
            ],
        },
        "health": {
            "topic": "身心",
            "title": "重点不在预言疾病，而在管理热、燥与恢复",
            "summary": f'五行数据显示火约{wuxing["火"]:.2f}%，水约{wuxing["水"]:.2f}%。在传统取象里，这是一幅偏暖、偏燥、节奏容易加快的图景。它只能用来提醒生活方式，不能据此判断疾病或寿命。',
            "signals": [
                {"name": "节奏", "fact": "火势明显、劫财有力", "reading": "连续推进时容易忽略疲劳信号，需要主动安排停顿。"},
                {"name": "恢复", "fact": "水的结构占比较低", "reading": "睡眠、补水、安静时间和规律作息应成为固定配置。"},
                {"name": "饮食", "fact": "巳月暖燥、天厨贵人两见", "reading": "比追求复杂补法更重要的是规律、适量和观察身体真实反应。"},
                {"name": "就医边界", "fact": "命理不是医学工具", "reading": "持续不适、异常指标或情绪困扰应交由合格医生与专业人员处理。"},
            ],
            "routine": ["把睡眠时间当作日程中的硬边界", "高强度工作每周至少安排完整恢复段", "少用兴奋感判断自己是否仍有余力", "保留体检记录，用医学数据而非命理猜测健康"],
        },
        "family": {
            "topic": "六亲",
            "title": "把六亲读成关系角色，不替现实中的人贴标签",
            "summary": "六亲映射是传统命理的角色语言，能帮助观察“你在家人面前通常怎样行动”，却不能替代真实家史。这里按四个宫位说明责任、支持和边界，不推断某位亲属的寿命、品行或必然遭遇。",
            "palaces": [
                {"name": "年柱·庚午", "role": PALACE_MEANING["year"], "reading": "正财透于年干，家族外缘常强调可靠、兑现和做成事情；午中比肩食神，也容易形成主动承担、用行动表达关心的习惯。"},
                {"name": "月柱·辛巳", "role": PALACE_MEANING["month"], "reading": "偏财坐巳，成长与工作环境容易重视机会、效率和资源调动。月柱与时柱相冲，早期形成的现实标准会持续影响后来的个人规划。"},
                {"name": "日柱·丁丑", "role": PALACE_MEANING["day"], "reading": "丑中食神、七杀、偏财并见，亲密生活同时需要照顾、责任和现实安排；事情多时尤其要避免把责任全部揽到自己身上。"},
                {"name": "时柱·乙巳", "role": PALACE_MEANING["hour"], "reading": "偏印透于时干，未来安排和个人作品需要自主空间。若家人对选择有不同意见，适合用阶段成果沟通，而不是只争论理念。"},
            ],
            "support": [
                {"name": "外部提携", "facts": "月德、天德、福星、德秀", "reading": "较容易在守信用、能交付之后获得长辈、前辈或专业网络的继续支持。"},
                {"name": "同辈协作", "facts": "比肩、劫财均有力", "reading": "同辈既能带来速度和机会，也会带来比较与分配问题，规则比人情更能保护关系。"},
                {"name": "亲密支持", "facts": "日支食神为先", "reading": "真正有效的支持往往很具体：共同吃饭、分担事务、如期出现，以及让生活可预期。"},
            ],
        },
        "risk": {
            "topic": "风险",
            "title": "没有“必然之灾”，只有需要提前管理的结构性压力",
            "summary": "本节不预测事故、疾病、破产或生死。所谓风险，只指原盘中重复出现的拉扯：速度与恢复、探索与兑现、合作与分配、外部责任与私人生活。识别得越早，越能通过制度和选择降低代价。",
            "matrix": [
                {"level": "较高", "name": "过度并行", "source": "火47.82%，劫财17.53%", "signal": "同时开启多项任务、休息仍在处理工作", "response": "限制在制品数量；没有退出条件，不新增项目。"},
                {"level": "较高", "name": "合作分配", "source": "比劫有力、财星透干", "signal": "贡献、决策权与收益口径不一致", "response": "合作前写清投入、版权、分配和退出机制。"},
                {"level": "中等", "name": "方向拉扯", "source": "乙辛冲", "signal": "研究兴趣频繁被短期机会打断", "response": "给探索设预算和验证周期，达标再扩大。"},
                {"level": "中等", "name": "生活磨损", "source": "午丑穿", "signal": "工作、人情或外界期待持续侵入私人时间", "response": "把共同生活的时间、职责和不可占用时段写进日程。"},
                {"level": "基础", "name": "恢复不足", "source": "暖燥明显、水占比较低", "signal": "靠兴奋维持效率，疲惫后仍继续加速", "response": "用睡眠、体检和稳定运动记录替代主观硬撑。"},
            ],
            "cycle_watch": demanding,
            "cycle_support": best,
        },
        "boundaries": [
            "所有结论都来自结构化排盘、十神、五行、冲合穿拱、神煞与大运评分。",
            "专项报告描述倾向和可观察条件，不保证事件必然发生。",
            "健康、法律、投资和安全问题应由相应专业人员与现实证据判断。",
        ],
    }
