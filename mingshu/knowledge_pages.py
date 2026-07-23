"""Reusable reader-facing knowledge-page assets for MingShu.

These pages explain one concept at a time.  They are intentionally generic:
the same asset can be reused in many books, while the surrounding chapter is
responsible for saying whether and how strongly the concept appears in a
particular chart.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KnowledgePage:
    code: str
    category: str
    name: str
    tagline: str
    lead: str
    flowing: str
    overdrive: str
    practice: str
    chart_note: str
    motif: str
    tone: str
    deep_sections: tuple[tuple[str, str], ...] = ()
    art_asset: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


QISHA_DEEP_SECTIONS = (
    (
        "它真正描述什么",
        "七杀首先是一条“压力如何抵达我”的关系通道。它可能表现为期限、规则、竞争、风险，或必须迅速承担的责任。它不等于脾气凶，也不自动指向危险；更值得观察的是：人在限制条件下，会怎样判断、行动与保护边界。",
    ),
    (
        "顺势时的力量",
        "当日主能够承受，且全盘有印星承接、食伤制化或其他稳定结构时，七杀较容易转化为目标感、执行力与临场决断。面对复杂局面，能够先抓关键、再定次序，并愿意为决定承担后果。",
    ),
    (
        "用得过度时",
        "若压力长期没有出口，七杀也可能让人保持过高警觉：凡事先按风险处理，节奏一再加快，把协商误认为软弱，把休息误认为退步。此时真正需要的不是继续用力，而是恢复信息、身体和关系中的缓冲。",
    ),
    (
        "怎样把它用好",
        "把高压任务拆成规则、权限、截止时间和退出条件；重要决定准备备选方案；结束后安排复盘与恢复。七杀适合处理真正困难的事情，但不必让所有日常都维持战斗强度。",
    ),
    (
        "放回完整命盘",
        "先看七杀是否透干、落在哪一柱、是否得令有根，再看日主承受、印星承接与食伤制化。命盘里出现七杀，不等于构成七杀格；格局仍需围绕月令、透干、根气和全盘组织方式单独判断。",
    ),
)


SAMPLE_KNOWLEDGE_PAGES = (
    KnowledgePage(
        code="PATTERN:ZHENGYIN",
        category="格局",
        name="正印格",
        tagline="把复杂之物，化成可依循的方法",
        lead="正印格像一套稳定的吸收系统：先接住信息，再理解、归纳，并把经验变成可以传承的方法。",
        flowing="愿意学习，也善于照顾整体；做事讲来路、重方法，常能给人安定感。",
        overdrive="若过度依赖熟悉的方法，容易准备太久、顾虑太多，或把安全感放在行动之前。",
        practice="每完成一轮输入，就留下一个可见成果：一页笔记、一次讲解，或一个真正解决问题的步骤。",
        chart_note="格局看的是全盘怎样组织，不是“出现正印”就一定成格；仍要结合月令、透干、根气与制化。",
        motif="spring",
        tone="jade",
    ),
    KnowledgePage(
        code="PATTERN:QISHA",
        category="格局",
        name="七杀格",
        tagline="把外在压力，炼成清晰的决断",
        lead="七杀格关注挑战、边界与行动速度。它像一段陡坡：压力真实存在，也因此逼人练出判断与担当。",
        flowing="目标明确、临场反应快，越在需要承担和解决问题的场景里，越容易显出魄力。",
        overdrive="节奏过紧时，容易把每件事都当成战斗，对自己和他人都缺少缓冲。",
        practice="先分清真正的风险与想象中的风险，再为高压任务设置边界、备选方案和恢复时间。",
        chart_note="七杀并不天然代表危险。能否化为执行力，要看日主承受、印星承接、食伤制化与全局配合。",
        motif="ridge",
        tone="cinnabar",
        deep_sections=QISHA_DEEP_SECTIONS,
        art_asset="qisha-ridge-v1.png",
    ),
    KnowledgePage(
        code="PATTERN:SHISHEN",
        category="格局",
        name="食神格",
        tagline="让天赋从容生长，并结成作品",
        lead="食神格像一条有余地的生长路径：把内在积累转成表达、创造、照料与可持续的产出。",
        flowing="能把复杂的事讲得顺畅，也重视体验与节奏；适合通过作品、服务或长期手艺建立影响。",
        overdrive="只顾舒适时，可能回避必要的竞争与约束；表达很多，却迟迟没有落成结果。",
        practice="给兴趣配一个稳定容器：固定频率、明确交付和真实反馈，让好感受慢慢成为好作品。",
        chart_note="格局能否成立，要看食神是否得令、是否有根，以及财星承接、枭印干扰等整体关系。",
        motif="orchard",
        tone="gold",
    ),
    KnowledgePage(
        code="SHISHEN:ZHENGYIN",
        category="十神",
        name="正印",
        tagline="接住、理解，再形成自己的方法",
        lead="正印是日主所受的同类生助，常用来观察学习、保护、资质、方法感与稳定支持。",
        flowing="遇到新事物时，倾向先理解来龙去脉，再稳稳推进；也愿意为他人提供经验与照顾。",
        overdrive="可能过分等待认可或完备条件，把“我还要再准备”当成推迟行动的理由。",
        practice="把所学压缩成自己的三句话，并马上用一次；能用出来的知识，才真正成为你的支持。",
        chart_note="十神是一条关系通道。正印落在哪一柱、是否透出、力量如何，会决定它具体连接哪类生活场景。",
        motif="pages",
        tone="jade",
    ),
    KnowledgePage(
        code="SHISHEN:QISHA",
        category="十神",
        name="七杀",
        tagline="在限制之中，练出反应与担当",
        lead="七杀是日主所受的同阴阳克制，常用来观察直接压力、风险感、竞争环境与果断行动。",
        flowing="面对时间限制或突发状况时，往往能迅速抓住重点，敢于承担别人不愿接的难题。",
        overdrive="长期紧绷会让判断变得非黑即白，也可能把效率放在关系与身体感受之前。",
        practice="把压力拆成“必须处理、可以协商、无需承担”三类，让力量用在真正重要的地方。",
        chart_note="七杀的表现取决于日主能否承受，以及印、食伤等力量如何配合；不能仅凭一个名称判断好坏。",
        motif="blade",
        tone="cinnabar",
        deep_sections=QISHA_DEEP_SECTIONS,
        art_asset="qisha-ridge-v1.png",
    ),
    KnowledgePage(
        code="SHISHEN:SHISHEN",
        category="十神",
        name="食神",
        tagline="以舒服而稳定的方式，向外生长",
        lead="食神是日主所生的同阴阳之力，常用来观察表达、创造、照料、享受过程与稳定产出。",
        flowing="表达有温度，做事愿意留出余地；当节奏稳定时，往往能把兴趣打磨成长期能力。",
        overdrive="容易追求顺手与愉悦，避开枯燥但必要的训练，或在细节体验里忘了交付。",
        practice="保留从容，也给产出一个截止点：先完成，再优化，让好品味有机会进入现实。",
        chart_note="食神落在不同柱位，会连接不同的表达场景；还要看是否受制、是否有财星承接以及整体强弱。",
        motif="ripple",
        tone="gold",
    ),
    KnowledgePage(
        code="SHENSHA:TIANYI",
        category="神煞",
        name="天乙贵人",
        tagline="关键处出现的帮助，也来自平日积累",
        lead="天乙贵人常被视作援助与转圜的提示词。它更像一座桥：有人愿意伸手，也需要你能够识别并走上去。",
        flowing="容易在关键处接上合适的资源、建议或协作关系，也懂得借助制度与专业网络解决问题。",
        overdrive="若把它理解成“总有人来救”，就可能低估准备、信用和主动求助的重要性。",
        practice="让能力可见，把请求说具体，并在得到帮助后形成互惠；贵人关系往往由长期信任长成。",
        chart_note="神煞来自固定查表，只是辅助提示。是否真的形成支持，还要看它所在柱位与全盘关系。",
        motif="bridge",
        tone="jade",
    ),
    KnowledgePage(
        code="SHENSHA:YANGREN",
        category="神煞",
        name="羊刃",
        tagline="强劲的驱动力，需要清楚的边界",
        lead="羊刃常用来提示一股直接、坚决而不易退让的力量。它像锋刃：能够开路，也需要知道何时收住。",
        flowing="面对阻力时不容易松手，执行坚决，适合处理需要勇气、体力或明确立场的任务。",
        overdrive="在疲惫或受激时，容易动作过猛、争强或忽略风险，让本可协商的事变成对抗。",
        practice="为高强度行动增加规则：事前预案、当下暂停信号，以及事后的恢复与复盘。",
        chart_note="羊刃不能单独解释为事故或凶险；应与日主强弱、官杀、食伤及具体柱位一同阅读。",
        motif="edge",
        tone="cinnabar",
    ),
    KnowledgePage(
        code="SHENSHA:TIANYUEDE",
        category="神煞",
        name="天月德",
        tagline="在锋利处，保留缓和与转圜",
        lead="天德、月德常被并提，用来提示温厚、缓冲与化解的文化意象。它像月光，为紧张关系留下一点余地。",
        flowing="较愿意顾及他人处境，在冲突中寻找不伤根本的处理方式，也容易珍惜信誉与善意。",
        overdrive="一味求和可能压下真实需求，或把“体谅”变成没有边界的承担。",
        practice="温和不等于含糊：先说清事实与底线，再给双方留出可执行的台阶。",
        chart_note="天德与月德各有查法，书中可合并讲其共同意象；具体命盘仍应分别核对落点。",
        motif="moon",
        tone="water",
    ),
    KnowledgePage(
        code="NAYIN:HAI_ZHONG_JIN",
        category="纳音",
        name="海中金",
        tagline="深藏于水，等待被看见的时机",
        lead="海中金像藏在海里的金属，意象落在积累、等待条件成熟，以及从复杂环境中辨认真正价值。",
        flowing="适合先沉潜、打磨，再在合适的环境里显露；价值不一定第一眼就被看见。",
        overdrive="若长期只藏不露，容易错过被理解和被使用的机会，也可能把谨慎变成封闭。",
        practice="为积累设置一次温和的出水：展示一个阶段成果，接受反馈，再继续精炼。",
        chart_note="纳音用来补充某一柱的文化意象，不是判断命局强弱、格局、职业或婚姻的主轴。",
        motif="sea-metal",
        tone="water",
    ),
    KnowledgePage(
        code="NAYIN:SHAN_TOU_HUO",
        category="纳音",
        name="山头火",
        tagline="高处有光，也要懂得守住火候",
        lead="山头火像山顶可见的火光，意象落在传播、号召、方向感与被许多人看见的热度。",
        flowing="容易点亮主题、聚拢注意力，让人迅速明白方向；适合承担需要可见度与推动力的角色。",
        overdrive="热度太急时，会消耗燃料，也可能让表达盖过内容；高处的光尤其需要稳定来源。",
        practice="在发声之前先问：这束光要照见什么？再为持续输出准备节奏、材料与休息。",
        chart_note="纳音的意义要放回它所在的年、月、日、时柱中理解，不宜脱离原盘单独下结论。",
        motif="mountain-fire",
        tone="cinnabar",
    ),
    KnowledgePage(
        code="NAYIN:DA_LIN_MU",
        category="纳音",
        name="大林木",
        tagline="不是一棵树，而是一片共同生长的林",
        lead="大林木像成片的树林，意象落在环境、群体、成长空间，以及不同个体彼此支撑形成的生态。",
        flowing="在有协作、有空间的环境里更容易展开；长期培育、连接资源，往往比单点爆发更有力量。",
        overdrive="枝叶过密时，方向容易分散；一味扩张，也可能忽略修剪、边界与根部承载。",
        practice="确定一条主干，再决定哪些关系值得长期养护；好的生态同时需要连接与取舍。",
        chart_note="大林木提供的是柱位意象。判断个人结构时，仍以五行、十神、格局与干支作用为主。",
        motif="forest",
        tone="jade",
    ),
)


KNOWLEDGE_PAGE_INDEX = {page.code: page for page in SAMPLE_KNOWLEDGE_PAGES}
