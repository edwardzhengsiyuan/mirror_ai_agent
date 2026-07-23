"""Reusable, reader-facing knowledge cards for MingShu.

The cards explain terminology. They deliberately do not turn a single symbol
into a personal prediction; personalized conclusions must still cite chart
facts and the interpretation nodes that used them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict


@dataclass(frozen=True)
class KnowledgeCard:
    code: str
    name: str
    category: str
    tagline: str
    introduction: str
    reading_tip: str
    caveat: str

    def to_dict(self) -> dict:
        return asdict(self)


_NAYIN_DEFINITIONS = {
    "HAI_ZHONG_JIN": ("海中金", "金", "深藏待显", "像藏在海中的金属，重点意象是积累、等待条件成熟与被发现。"),
    "LU_ZHONG_HUO": ("炉中火", "火", "有源而燃", "像炉膛中的火，需要燃料、空间与持续照料，强调集中、转化与持续投入。"),
    "DA_LIN_MU": ("大林木", "木", "成片生长", "像连成一片的树林，强调环境、群体、生长空间与长期培育。"),
    "LU_PANG_TU": ("路旁土", "土", "承载往来", "像道路两旁的土，意象偏向承载、连接、秩序与日常运转。"),
    "JIAN_FENG_JIN": ("剑锋金", "金", "锋芒成器", "像经过锻炼的锋刃，强调清晰、决断、边界与经过打磨后的能力。"),
    "SHAN_TOU_HUO": ("山头火", "火", "高处可见", "像山头的火光，强调显眼、号召、传播与需要控制节奏的热度。"),
    "JIAN_XIA_SHUI": ("涧下水", "水", "循隙而行", "像山涧细流，强调顺势寻找通道、细致渗透与持续流动。"),
    "CHENG_TOU_TU": ("城头土", "土", "边界与守护", "像城墙之土，重点意象是结构、边界、防护与责任。"),
    "BAI_LA_JIN": ("白蜡金", "金", "尚待雕琢", "像仍需加工定型的金属，强调潜质、工序、耐心与逐步成形。"),
    "YANG_LIU_MU": ("杨柳木", "木", "柔韧应时", "像随风而动的杨柳，强调适应、柔韧、审美与环境感受力。"),
    "QUAN_ZHONG_SHUI": ("泉中水", "水", "由内而出", "像从地下涌出的泉水，强调内在来源、持续补给与逐渐显露。"),
    "WU_SHANG_TU": ("屋上土", "土", "覆盖与安顿", "像屋顶所用之土，意象偏向庇护、完成、归置与生活秩序。"),
    "PI_LI_HUO": ("霹雳火", "火", "骤然而发", "像雷电带来的火，强调启动、突变、强烈信号与及时应对。"),
    "SONG_BAI_MU": ("松柏木", "木", "耐久有节", "像四季常青的松柏，强调耐力、原则、长期主义与稳定生长。"),
    "CHANG_LIU_SHUI": ("长流水", "水", "绵延不息", "像持续向前的河流，强调过程、迁移、连接与长期积累。"),
    "SHA_ZHONG_JIN": ("沙中金", "金", "淘洗见质", "像藏在沙中的金，需要筛选与提炼，强调辨别、发现与去芜存菁。"),
    "SHAN_XIA_HUO": ("山下火", "火", "近地温养", "像山脚下的火光，强调具体场景中的温度、照料与实际影响。"),
    "PING_DI_MU": ("平地木", "木", "因地成材", "像平地上培育的树木，强调基础条件、规划、协作与可持续成长。"),
    "BI_SHANG_TU": ("壁上土", "土", "成面立界", "像构成墙面的土，强调界面、规则、分隔与把零散材料组织起来。"),
    "JIN_BO_JIN": ("金箔金", "金", "精细成饰", "像延展成薄片的金，强调精致、呈现、附着价值与工艺感。"),
    "FO_DENG_HUO": ("佛灯火", "火", "微光长明", "像灯盏中的火，强调专注、指引、文化意味与小而持续的影响。"),
    "TIAN_HE_SHUI": ("天河水", "水", "由上而降", "像来自天际的水，意象偏向视野、润泽、广度与超出日常的想象。"),
    "DA_YI_TU": ("大驿土", "土", "通衢承载", "像驿道与交通节点之土，强调平台、流通、组织与承接复杂往来。"),
    "CHAI_CHUAN_JIN": ("钗钏金", "金", "成器可佩", "像加工完成的首饰，强调品位、关系中的呈现、细节与完成度。"),
    "SANG_ZHE_MU": ("桑柘木", "木", "实用养成", "像可供生产与生活使用的桑柘，强调培育、实用、照料与稳定产出。"),
    "DA_XI_SHUI": ("大溪水", "水", "势成而行", "像汇聚成势的溪流，强调行动路径、变化速度与顺势疏导。"),
    "SHA_ZHONG_TU": ("沙中土", "土", "聚散之间", "像沙地中的土，强调基础的松紧、聚合能力与环境稳定度。"),
    "TIAN_SHANG_HUO": ("天上火", "火", "光照四方", "像太阳般的高空之火，强调可见度、方向感、影响范围与节律。"),
    "SHI_LIU_MU": ("石榴木", "木", "内含丰实", "像果实多籽的石榴树，强调内在丰富、成果、繁衍与阶段性成熟。"),
    "DA_HAI_SHUI": ("大海水", "水", "包容汇聚", "像汇聚百川的大海，强调容量、复杂度、开放边界与整体视角。"),
}

NAYIN_CARDS: Dict[str, KnowledgeCard] = {
    code: KnowledgeCard(
        code=f"NAYIN:{code}",
        name=name,
        category=f"纳音·{element}",
        tagline=tagline,
        introduction=introduction,
        reading_tip="命书中宜结合它所在的年、月、日、时柱来读，用作该柱气质意象的补充说明。",
        caveat="纳音不是判断命局强弱、格局或吉凶的主轴，不能脱离原盘单独下结论。",
    )
    for code, (name, element, tagline, introduction) in _NAYIN_DEFINITIONS.items()
}


_TEN_GOD_DEFINITIONS = {
    "BIJIAN": ("比肩", "自我与同伴", "代表与自己相似的力量，常用来观察自主性、同辈关系与共同承担。"),
    "JIECAI": ("劫财", "竞争与动员", "代表更主动的同类力量，常用来观察竞争、资源分配、行动号召与边界。"),
    "SHISHEN": ("食神", "表达与滋养", "代表较从容的输出方式，常用来观察创造、照料、享受过程与稳定表达。"),
    "SHANGGUAN": ("伤官", "突破与质疑", "代表更锋利的输出方式，常用来观察创新、批判、规则张力与表达强度。"),
    "PIANCAI": ("偏财", "流动资源", "代表流动性更强的资源，常用来观察机会、人脉、经营敏感度与资源调度。"),
    "ZHENGCAI": ("正财", "稳定经营", "代表可持续经营的资源，常用来观察责任、预算、日常管理与稳定关系。"),
    "QISHA": ("七杀", "压力与决断", "代表直接的约束和挑战，常用来观察行动压力、风险意识、魄力与应变。"),
    "ZHENGGUAN": ("正官", "秩序与责任", "代表制度化的约束，常用来观察规则、责任、组织角色与社会评价。"),
    "PIANYIN": ("偏印", "非线性学习", "代表偏探索型的吸收方式，常用来观察直觉、跨界、独特经验与独立研究。"),
    "ZHENGYIN": ("正印", "学习与支持", "代表较稳定的吸收和支持，常用来观察学习、资质、照顾、方法与安全感。"),
}

TEN_GOD_CARDS: Dict[str, KnowledgeCard] = {
    code: KnowledgeCard(
        code=f"SHISHEN:{code}",
        name=name,
        category="十神",
        tagline=tagline,
        introduction=introduction,
        reading_tip="十神要同时看力量、位置、是否透出，以及与其他十神和干支的作用，不能只看“有或没有”。",
        caveat="十神是关系语言，不是固定性格标签；同一十神在不同组合中会呈现不同侧面。",
    )
    for code, (name, tagline, introduction) in _TEN_GOD_DEFINITIONS.items()
}


_ZODIAC_DEFINITIONS = {
    "SHU": ("鼠", "机敏与储备", "生肖鼠常被用作机敏、观察与积累的文化意象。"),
    "NIU": ("牛", "踏实与耐力", "生肖牛常被用作稳定、耐力与循序推进的文化意象。"),
    "HU": ("虎", "行动与开拓", "生肖虎常被用作胆识、行动与开拓边界的文化意象。"),
    "TU": ("兔", "敏感与协调", "生肖兔常被用作细腻、审美与协调关系的文化意象。"),
    "LONG": ("龙", "愿景与变化", "生肖龙常被用作愿景、变化与影响力的文化意象。"),
    "SHE": ("蛇", "洞察与节奏", "生肖蛇常被用作洞察、策略与把握节奏的文化意象。"),
    "MA": ("马", "速度与远行", "生肖马常被用作行动、迁移与追求空间的文化意象。"),
    "YANG": ("羊", "温和与共感", "生肖羊常被用作温和、审美与群体共感的文化意象。"),
    "HOU": ("猴", "灵活与创造", "生肖猴常被用作灵活、学习与解决问题的文化意象。"),
    "JI": ("鸡", "秩序与表达", "生肖鸡常被用作时间感、秩序与清晰表达的文化意象。"),
    "GOU": ("狗", "守护与忠诚", "生肖狗常被用作守护、忠诚与原则感的文化意象。"),
    "ZHU": ("猪", "包容与丰足", "生肖猪常被用作包容、休养与生活丰足的文化意象。"),
}

ZODIAC_CARDS: Dict[str, KnowledgeCard] = {
    code: KnowledgeCard(
        code=f"SHENGXIAO:{code}",
        name=name,
        category="生肖",
        tagline=tagline,
        introduction=introduction,
        reading_tip="生肖来自年支，适合放在文化导读和年柱背景中，不替代四柱整体分析。",
        caveat="生肖只占八字的一部分，不能据此概括一个人的全部性格或关系结果。",
    )
    for code, (name, tagline, introduction) in _ZODIAC_DEFINITIONS.items()
}


def get_nayin_card(code: str) -> KnowledgeCard | None:
    return NAYIN_CARDS.get(str(code).split(":")[-1])


def get_ten_god_card(code: str) -> KnowledgeCard | None:
    return TEN_GOD_CARDS.get(str(code).split(":")[-1])


def get_zodiac_card(code: str) -> KnowledgeCard | None:
    return ZODIAC_CARDS.get(str(code).split(":")[-1])
