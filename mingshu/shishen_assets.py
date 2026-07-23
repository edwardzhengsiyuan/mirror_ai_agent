"""Reusable visual assets for the ten-god chapter.

The imagery treats each ten god as a relationship pattern expressed through
an adult figure, a concrete action, and a small set of period-inspired props.
It deliberately avoids deities, literal fortune symbols, and deterministic
good/bad stereotypes.
"""

from __future__ import annotations


TEN_GOD_ASSETS: tuple[dict[str, str], ...] = (
    {
        "code": "SHISHEN:BIJIAN",
        "name": "比肩",
        "theme": "自我与同伴",
        "tagline": "并肩而立，各自有分寸",
        "image": "bijian-v2.png",
        "visual": "一位人物以横梁平衡两只同样的卷筒，并用垂线校准；用等重和自持表达比肩。",
    },
    {
        "code": "SHISHEN:JIECAI",
        "name": "劫财",
        "theme": "竞争与动员",
        "tagline": "力气聚得快，边界更要清楚",
        "image": "jiecai-v2.png",
        "visual": "一位人物把三股绳索收束在同一只行箱上，旁置等额筹片和分装袋；表现动员与边界。",
    },
    {
        "code": "SHISHEN:SHISHEN",
        "name": "食神",
        "theme": "表达与滋养",
        "tagline": "把积累做成可以分享的成果",
        "image": "shishen-v1.png",
        "visual": "人物从容整理蒸点与果品并将成品向外递出，表现创造、照料和稳定输出。",
    },
    {
        "code": "SHISHEN:SHANGGUAN",
        "name": "伤官",
        "theme": "突破与质疑",
        "tagline": "看见旧结构，也敢于重新设计",
        "image": "shangguan-v1.png",
        "visual": "女设计者揭开木构机关面板，以圆规校准新结构；锋利落在方法而非情绪。",
    },
    {
        "code": "SHISHEN:ZHENGCAI",
        "name": "正财",
        "theme": "稳定经营",
        "tagline": "一笔一算，把日常接稳",
        "image": "zhengcai-v1.png",
        "visual": "管事以算盘核算并把等额筹片归入分格，粮袋、钥匙与量具构成稳定经营语汇。",
    },
    {
        "code": "SHISHEN:PIANCAI",
        "name": "偏财",
        "theme": "流动资源",
        "tagline": "在流动里辨认机会与交换",
        "image": "piancai-v1.png",
        "visual": "行商一手衡量货样、一手完成交换，样品、路线图与行囊表现资源调度。",
    },
    {
        "code": "SHISHEN:ZHENGGUAN",
        "name": "正官",
        "theme": "秩序与责任",
        "tagline": "有尺度，也愿意承担尺度",
        "image": "zhengguan-v1.png",
        "visual": "文官水平持尺，文书盘左右对称；表达规则、公平和可被检验的责任。",
    },
    {
        "code": "SHISHEN:QISHA",
        "name": "七杀",
        "theme": "压力与决断",
        "tagline": "压力真实，判断因此更清楚",
        "image": "qisha-v1.png",
        "visual": "女将面对沙盘、沙漏与急件，手扶入鞘之剑；表现高压下的边界和决断。",
    },
    {
        "code": "SHISHEN:ZHENGYIN",
        "name": "正印",
        "theme": "学习与支持",
        "tagline": "先把知识接稳，再把方法传下去",
        "image": "zhengyin-v1.png",
        "visual": "女师者包护书卷并递出成册，灯与书柜表现稳定吸收、保护和传承。",
    },
    {
        "code": "SHISHEN:PIANYIN",
        "name": "偏印",
        "theme": "非线性学习",
        "tagline": "从不同材料之间找到隐秘联系",
        "image": "pianyin-v1.png",
        "visual": "独立研究者把叶片、矿石与浑仪放在同一桌面比较，表现跨界探索与直觉连接。",
    },
)


TEN_GOD_ASSET_BY_CODE = {item["code"]: item for item in TEN_GOD_ASSETS}
TEN_GOD_IMAGE_BY_CODE = {item["code"]: item["image"] for item in TEN_GOD_ASSETS}
