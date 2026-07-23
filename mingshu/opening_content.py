"""Reusable reader-facing copy for the opening pages of a MingShu.

These entries are editorial assets, not generated per customer.  A real case
loads the matching record by day stem, month branch, year branch, and gender.
The language stays introductory and deliberately avoids treating a single
symbol as a complete personality verdict.
"""

from __future__ import annotations


DAY_MASTER_PROFILES = {
    "GAN:JIA": {
        "char": "甲", "element": "木", "metaphor": "向上生长的大树", "tagline": "先立方向，再舒枝叶",
        "intro": "甲木常被比作向上生长的大树。它关心方向、骨架与长期积累，遇事往往先确认什么值得坚持，再投入时间建立可依靠的结构。",
        "strength": "顺势时，甲木有开路、担当与保护他人的能力；愿意把复杂事情做成可以持续生长的系统。",
        "balance": "若过度用力，容易把坚持变成僵硬。保留修枝、转向和听取反馈的空间，成长反而更稳。",
    },
    "GAN:YI": {
        "char": "乙", "element": "木", "metaphor": "循势而上的藤蔓", "tagline": "柔中有韧，借势成形",
        "intro": "乙木像藤蔓、花草与细枝，擅长感受环境并寻找可以依附、协作和延展的位置。它的力量不在正面碰撞，而在持续调整。",
        "strength": "顺势时，乙木细腻、有审美、懂关系，也能在限制条件中找到新的连接方式。",
        "balance": "过度顾及环境时，容易迟疑或绕得太远。给自己一条明确底线，柔韧就不会失去方向。",
    },
    "GAN:BING": {
        "char": "丙", "element": "火", "metaphor": "照见万物的太阳", "tagline": "坦荡发光，也给世界温度",
        "intro": "丙火像白昼的太阳，重视清楚、坦荡和可见的行动。它通常愿意把能量带到公共空间，让周围的人知道目标在哪里。",
        "strength": "顺势时，丙火热情、直接、感染力强，适合发动事情、建立信心，并把复杂局面照得更明白。",
        "balance": "持续高亮也会消耗。允许自己有阴影、有休息、有不必立刻回应的时刻，光才会稳定。",
    },
    "GAN:DING": {
        "char": "丁", "element": "火", "metaphor": "被守护的灯火", "tagline": "把注意力照向真正重要之处",
        "intro": "丁火像灯烛与炉火，重视专注、细节和人与人之间可感知的温度。它不一定张扬，却能把光放到关键位置。",
        "strength": "顺势时，丁火敏锐、体贴、判断细致，适合需要长期打磨、审美和精确照料的工作。",
        "balance": "过度敏感时，容易把微小波动都当成信号。稳定作息与边界，能让这束光更聚焦。",
    },
    "GAN:WU": {
        "char": "戊", "element": "土", "metaphor": "承托四方的山体", "tagline": "不急于移动，先成为依靠",
        "intro": "戊土像山与高地，关注稳定、承载和长期可靠。它倾向先判断一件事是否站得住，再决定投入多少力量。",
        "strength": "顺势时，戊土沉着、守信、能扛事，适合建立秩序、守住底线并成为团队的稳定支点。",
        "balance": "过度承载会让自己难以松动。把责任分层、允许求助，山才不会被所有重量压在一处。",
    },
    "GAN:JI": {
        "char": "己", "element": "土", "metaphor": "被耕作与照料的田地", "tagline": "细细整理，让万物各得其所",
        "intro": "己土像园圃与田地，善于收纳、整理、滋养和把零散资源重新组合。它关注事情是否真正落到日常。",
        "strength": "顺势时，己土务实、周到、有整合力，能够照顾流程、关系和长期维护中的细微需求。",
        "balance": "若把所有需要都接到自己身上，容易陷入琐碎。先划清责任田，再决定哪些值得亲手照料。",
    },
    "GAN:GENG": {
        "char": "庚", "element": "金", "metaphor": "正在成形的精钢", "tagline": "直面问题，重铸结构",
        "intro": "庚金像经过锻造的钢材，重视明确、效率和纠正偏差。它往往能快速识别结构中的薄弱处，并愿意动手调整。",
        "strength": "顺势时，庚金果断、有执行力、敢于处理难题，适合改革、攻坚和建立清晰规则。",
        "balance": "太快切入会忽略人的感受。先说明目的、预留缓冲，锋利就能成为工具而不是伤害。",
    },
    "GAN:XIN": {
        "char": "辛", "element": "金", "metaphor": "细磨之后的珠玉", "tagline": "辨别分寸，把细节做到准确",
        "intro": "辛金像珠玉、针锋与精密器物，关注质感、标准和边界。它对细微差别敏感，也在意表达是否恰到好处。",
        "strength": "顺势时，辛金审美清楚、判断精细、讲究品质，适合编辑、设计、谈判和需要校准的工作。",
        "balance": "标准过密会让自己和他人都紧张。区分关键误差与无关瑕疵，精致才不会变成苛刻。",
    },
    "GAN:REN": {
        "char": "壬", "element": "水", "metaphor": "奔流入海的大江", "tagline": "先看全局，再寻找通路",
        "intro": "壬水像江河与海洋，天然关注流动、信息和更大的空间。它常从整体趋势出发，寻找跨越边界的路线。",
        "strength": "顺势时，壬水视野开阔、反应快、善整合，能够在变化中看到机会并连接不同资源。",
        "balance": "选择太多时，容易分散或不断换道。用阶段目标收束水路，广阔才会形成真正的抵达。",
    },
    "GAN:GUI": {
        "char": "癸", "element": "水", "metaphor": "润物无声的雨露", "tagline": "安静感受，也持续更新",
        "intro": "癸水像雨、露和地下水，擅长感受细微变化，理解未被说出的情绪与信息。它的影响通常温和而持续。",
        "strength": "顺势时，癸水敏锐、富有想象力、善倾听，适合研究、照料和需要长期观察的事情。",
        "balance": "吸收过多时，容易混淆自己的感受与外界压力。固定的表达出口和清晰边界尤其重要。",
    },
}


MONTH_PROFILES = {
    "ZHI:ZI": {"char":"子","season":"仲冬","image":"冰封湖面","tagline":"水气至深，万物在静处蓄势","intro":"子月位于冬季的核心，外界活动收敛，水的流动转入冰面之下。它强调储备、观察与耐心：很多事情并非停滞，而是在看不见的地方重新组织。","reading":"读月令不是给性格贴标签，而是先看命盘出生时的环境底色。子月的寒与水，会影响全盘怎样取暖、流通和寻找支点。","asset":"zi-frozen-lake-v1.png"},
    "ZHI:CHOU": {"char":"丑","season":"季冬","image":"冻土与谷仓","tagline":"寒土收纳，等待解冻","intro":"丑月像被霜封住的田地，水气仍在，土开始承担收束与储藏。它关心资源能否保存、秩序能否维持，也提示变化尚未完全显露。","reading":"分析丑月，要同时看寒湿、土性与藏干怎样参与全盘，而不是只用一个‘土’字概括。","asset":"chou-frozen-earth-v1.png"},
    "ZHI:YIN": {"char":"寅","season":"孟春","image":"破雪新林","tagline":"阳气初升，方向开始出现","intro":"寅月是春天的开端，像林木顶开残雪。行动欲与生长感被唤醒，适合启动、试探和建立新的时间表。","reading":"寅月重在生发，但能否顺利仍要看水分、温度和全盘是否提供足够承接。","asset":"yin-thawing-forest-v1.png"},
    "ZHI:MAO": {"char":"卯","season":"仲春","image":"晨光花木","tagline":"木气舒展，关系向外延伸","intro":"卯月像春日清晨的花木，生长进入稳定扩展期。它带来连接、审美与柔和推进的氛围。","reading":"卯月的重点是舒展与纯粹，仍需结合透干、根气和全局制化判断实际表现。","asset":"mao-spring-garden-v1.png"},
    "ZHI:CHEN": {"char":"辰","season":"季春","image":"春雨水库","tagline":"湿土转季，汇聚再分流","intro":"辰月处在春夏转换之间，像蓄着春雨的水库。它既收纳前一季的水木，也为下一阶段准备出口。","reading":"辰的复杂在于湿土与藏气并存，分析时要看它究竟成为蓄水、培木还是阻滞。","asset":"chen-spring-reservoir-v1.png"},
    "ZHI:SI": {"char":"巳","season":"孟夏","image":"初夏花影","tagline":"火势初盛，万物加速显形","intro":"巳月进入初夏，温度与行动速度明显上升。事情更容易被看见，也更需要管理节奏和消耗。","reading":"巳月不能只理解成热烈；其中的结构、藏干和与其他地支的作用，会决定火如何被使用。","asset":"si-early-summer-v1.png"},
    "ZHI:WU": {"char":"午","season":"仲夏","image":"盛夏高日","tagline":"阳气至盛，表达直接而明亮","intro":"午月像正午太阳，外放、清晰、快速。优势是推动力强，课题则是避免持续过热。","reading":"午月的火势需要看全盘是否有水、土或其他结构调节，不能简单等同于热情或急躁。","asset":"wu-high-summer-v1.png"},
    "ZHI:WEI": {"char":"未","season":"季夏","image":"暑后果园","tagline":"热土收成，把生长变成成果","intro":"未月位于夏末，阳光仍强，土开始承担成熟、整理与收藏。它关心如何把过程沉淀成可保留的成果。","reading":"未月兼有燥热与收藏意味，要结合水分、根气与全盘流通判断。","asset":"wei-late-summer-v1.png"},
    "ZHI:SHEN": {"char":"申","season":"孟秋","image":"山风初肃","tagline":"金气初起，开始筛选与定形","intro":"申月带来初秋的清爽与收敛，事情从扩张转向筛选、校正和建立标准。","reading":"申月的效率感来自季节转向，具体是果断还是紧张，要看全盘如何承接这股收束力。","asset":"shen-early-autumn-v1.png"},
    "ZHI:YOU": {"char":"酉","season":"仲秋","image":"月下金野","tagline":"清气成形，品质与边界变得清楚","intro":"酉月像月光下成熟的田野，强调完成度、审美与准确边界。","reading":"酉月提供的是环境基调，不能脱离日主和全盘关系直接推断职业或性格。","asset":"you-autumn-moon-v1.png"},
    "ZHI:XU": {"char":"戌","season":"季秋","image":"落日燥原","tagline":"燥土收束，为入冬做好归档","intro":"戌月处在秋冬交界，像落日后的干燥原野。它强调总结、守界与处理未完成事项。","reading":"戌的燥与库性需要结合全盘判断：可能形成秩序，也可能让流动暂时受阻。","asset":"xu-dry-autumn-v1.png"},
    "ZHI:HAI": {"char":"亥","season":"孟冬","image":"雪落大河","tagline":"水门初开，世界转向内在流动","intro":"亥月像初雪中的大河，外界渐静，水的想象、信息和迁移感增强。","reading":"亥月重在进入冬季后的流动方式，需看全盘是否有承接、温暖与明确河道。","asset":"hai-snow-river-v1.png"},
}


ZODIAC_PROFILES = {
    "ZHI:ZI": {"animal":"鼠","slug":"rat","tagline":"机敏而有余庆","intro":"生肖鼠在民俗里象征机敏、储备与发现细小机会。可把它当作年文化的第一层入口，而不是完整性格结论。"},
    "ZHI:CHOU": {"animal":"牛","slug":"ox","tagline":"踏实耕耘，厚积有成","intro":"生肖牛常被赋予勤恳、耐力与可信赖的意味。真正的行动方式仍要回到整张命盘观察。"},
    "ZHI:YIN": {"animal":"虎","slug":"tiger","tagline":"有胆有界，昂然向前","intro":"生肖虎象征勇气、保护与开路。年画中的虎可以威而不凶，表达担当而非攻击。"},
    "ZHI:MAO": {"animal":"兔","slug":"rabbit","tagline":"温和机巧，春意常新","intro":"生肖兔常与敏捷、礼貌和生机相连。它是文化取象，不等同于一个人的全部处事风格。"},
    "ZHI:CHEN": {"animal":"龙","slug":"dragon","tagline":"行云布雨，气象自成","intro":"生肖龙象征变化、志向与连接天地的想象。呈现上宜庄重舒展，不必靠凶猛制造力量。"},
    "ZHI:SI": {"animal":"蛇","slug":"snake","tagline":"灵慧蜿蜒，福意绵长","intro":"生肖蛇在传统文化中有灵性、更新与洞察的意味。这里采用喜庆年画取象，避免把蛇简单描述为阴冷或危险。"},
    "ZHI:WU": {"animal":"马","slug":"horse","tagline":"步履明快，志在远方","intro":"生肖马象征行动、远行与开阔生命力。它提供亲切的文化记忆，不替代命盘结构分析。"},
    "ZHI:WEI": {"animal":"羊","slug":"goat","tagline":"温厚有礼，和气致祥","intro":"生肖羊常与温和、审美和群体协作相关。年画取其吉庆与丰足，不把温和误读成软弱。"},
    "ZHI:SHEN": {"animal":"猴","slug":"monkey","tagline":"灵动善变，巧思常来","intro":"生肖猴象征机巧、学习与随机应变。具体如何使用聪明，仍要看全盘的目标与边界。"},
    "ZHI:YOU": {"animal":"鸡","slug":"rooster","tagline":"守时有信，鸣晓迎新","intro":"生肖鸡有报晓、秩序与守时的文化意味。画面取喜庆昂扬，避免夸张争斗感。"},
    "ZHI:XU": {"animal":"狗","slug":"dog","tagline":"忠诚守护，家宅常安","intro":"生肖狗象征守护、信任与陪伴。它是一种民俗祝愿，不直接决定人际关系模式。"},
    "ZHI:HAI": {"animal":"猪","slug":"pig","tagline":"丰足安乐，福气盈门","intro":"生肖猪常与丰足、安稳和享受生活相连。年画取其圆满亲和，也保留成熟而不幼稚的气质。"},
}


STEM_SLUGS = {
    "GAN:JIA":"jia", "GAN:YI":"yi", "GAN:BING":"bing", "GAN:DING":"ding", "GAN:WU":"wu",
    "GAN:JI":"ji", "GAN:GENG":"geng", "GAN:XIN":"xin", "GAN:REN":"ren", "GAN:GUI":"gui",
}


def daymaster_asset(code: str, gender: str) -> str:
    """Return the project-relative transparent character illustration path."""
    gender_slug = "female" if str(gender).lower() == "female" else "male"
    return f"daymasters/{STEM_SLUGS[code]}-{gender_slug}-v1.png"

