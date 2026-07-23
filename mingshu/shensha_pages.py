"""Print-first sample pages for the shensha chapter."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .shensha_library import SHENSHA_BY_CODE, SHENSHA_IMAGE_BY_CODE, SHENSHA_LIBRARY


PILLAR_LABELS = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
CLUSTER_ORDER = ("支持与帮助", "学习与表达", "行动与权责", "人际与机缘", "资源与生活", "关系与校准")

REAL_CASE_SHENSHA_COPY = {
    "SHENSHA:YUEDE": {
        "meaning": "月德贵人重在圆融、体谅和人情分寸。遇到意见不同时，愿意缓一步、换一种说法，通常更容易让事情保留转圜空间。",
        "impact": "月德落在月柱，影响较多体现在工作环境、日常协作和处事习惯。你在团队里容易承担缓和气氛、照顾各方处境的角色；需要作决定时，温和可以保留，但边界仍要说清楚。",
    },
    "SHENSHA:LUSHEN": {
        "meaning": "禄神与稳定所得、工作回报和生活支撑有关，强调把已经掌握的能力持续做下去，逐渐形成能够依靠的成果。",
        "impact": "禄神落在年柱，务实、可靠的印象较容易被外界看见，早期环境也可能较重视能力与实际回报。长期积累比短期冒进更能发挥这项特点。",
    },
    "SHENSHA:JIANGXING": {
        "meaning": "将星表示担当、组织和关键时刻作决定的能力。它关心的是能否把人和事安排好，并愿意对结果负责。",
        "impact": "将星落在年柱，你进入群体时容易被期待承担事情，或较早形成独立处理问题的习惯。真正发挥作用的地方，在于清楚分工并把责任落实，而不是事事都由自己掌控。",
    },
    "SHENSHA:TAOHUA": {
        "meaning": "桃花与亲和力、审美表达和被人注意的程度有关，也会增加社交往来和关系互动的机会。",
        "impact": "桃花落在年柱，较多表现为外在印象与公共场合中的亲和力。别人容易注意到你的气质、表达或审美；关系是否深入，仍取决于相处、承诺和现实选择。",
    },
    "SHENSHA:FUXINGGUIREN": {
        "meaning": "福星贵人偏向生活中的顺手与照应，常表现为遇事有人愿意搭把手，或在复杂局面里较容易找到可用的资源。",
        "impact": "福星贵人落在年柱，来自家庭、熟人网络或外部环境的善意较容易被你接到。主动维护信誉、及时回应帮助，会让这种支持形成更稳定的往来。",
    },
    "SHENSHA:DEXIUGUIREN": {
        "meaning": "德秀贵人把品行与才华放在一起看，强调做事有分寸、表达有内容，并通过长期表现赢得信任。",
        "impact": "德秀贵人同时落在月、日、时三柱，工作协作、日常相处和长期成果都容易受到这项特点影响。能力被看见以后，能否保持稳定与真诚，比一时表现更重要。",
    },
    "SHENSHA:TIANDEGUIREN": {
        "meaning": "天德贵人象征宽厚、克制和化解矛盾的能力。面对僵局时，守住原则又愿意体谅他人，事情往往更容易找到出口。",
        "impact": "天德贵人落在月柱，较多影响工作方式与现实协作。遇到制度、长辈或关键人物时，你更容易因处事稳妥而得到善意回应；这份帮助仍要靠行动和长期信誉承接。",
    },
    "SHENSHA:TIANCHUGUIREN": {
        "meaning": "天厨贵人与照料、饮食、手艺和把生活安排妥帖的能力有关，也包含愿意用具体成果照顾身边人的倾向。",
        "impact": "天厨贵人落在月柱和时柱，既影响工作中的服务与产出，也影响长期生活安排。把审美、手艺或照料能力发展成稳定专长，会比只在忙碌时临时付出更有价值。",
    },
    "SHENSHA:YINCHAYANCUO": {
        "meaning": "阴差阳错提示事情容易在时间、表达或理解上出现错位：双方并非没有诚意，却可能因为节奏不同而多走一步弯路。",
        "impact": "阴差阳错落在日柱，较多牵动日常生活与亲密关系。重要安排尽量确认时间、责任和真实想法，不把沉默当作默契，可以减少反复猜测和临时变动。",
    },
}

SHENSHA_V2_CSS = r'''
.shensha-pair h1{margin-bottom:9px}.shensha-entry-list{display:grid;grid-template-columns:1fr 1fr;gap:15px;align-items:start;border-top:1px solid var(--gold);padding-top:11px}.shensha-entry{display:flex;flex-direction:column;width:100%;height:480px;border:1px solid var(--line);background:#f8f1e3}.shensha-entry-list .shensha-entry:nth-child(2){margin-top:28px}.shensha-entry figure{flex:0 0 165px;width:100%;padding:8px;border-right:0;border-bottom:1px solid var(--line);background:#f3e8d4}.shensha-entry figure img{width:100%;height:100%;object-fit:contain;background:transparent}.shensha-entry>div{flex:1;align-self:stretch;padding:10px 12px}.shensha-entry h2{font-size:22px;margin:2px 0 6px}.shensha-entry h3{font-size:9px;margin:7px 0 2px}.shensha-entry p{font-size:8.2px;line-height:1.5}.shensha-single .shensha-entry{display:flex;width:48%;height:480px;margin:12px 0 0;border:1px solid var(--line)}.shensha-single .shensha-entry figure{flex-basis:175px}.shensha-single .shensha-entry h3{font-size:10px;margin-top:10px}.shensha-single .shensha-entry p{font-size:9px;line-height:1.6}
'''


def build_shensha_case(facts: dict) -> dict:
    raw = facts.get("analysis_facts", {}).get("shensha", {})
    placements: dict[str, list[dict]] = {}
    by_pillar: dict[str, list[dict]] = {key: [] for key in PILLAR_LABELS}
    for pillar in PILLAR_LABELS:
        for item in raw.get(pillar, []) or []:
            code = item.get("code")
            if code not in SHENSHA_BY_CODE:
                continue
            row = {
                "code": code,
                "name": item.get("name") or SHENSHA_BY_CODE[code]["name"],
                "kind": item.get("kind") or SHENSHA_BY_CODE[code]["kind"],
                "pillar": pillar,
                "pillar_label": PILLAR_LABELS[pillar],
                "source": item.get("source") or "",
            }
            by_pillar[pillar].append(row)
            placements.setdefault(code, []).append(row)

    unique = []
    for code, rows in placements.items():
        knowledge = dict(SHENSHA_BY_CODE[code])
        knowledge["image"] = SHENSHA_IMAGE_BY_CODE[code]
        knowledge["placements"] = rows
        knowledge["placement_labels"] = [row["pillar_label"] for row in rows]
        unique.append(knowledge)
    order = {item["code"]: index for index, item in enumerate(SHENSHA_LIBRARY)}
    unique.sort(key=lambda item: order[item["code"]])
    return {
        "schema_version": "mingshu-shensha-case/1.0",
        "count": len(unique),
        "by_pillar": by_pillar,
        "items": unique,
    }


def _e(value: object) -> str:
    return escape(str(value or ""))


def _bridge_page(facts: dict) -> str:
    rows = [row for row in facts.get("analysis_facts", {}).get("shishen", []) if row.get("label") != "日主"]
    rows = sorted(rows, key=lambda row: float(row.get("percent") or 0), reverse=True)[:3]
    number = ("一", "二", "三")
    descriptions = {
        "七杀": "对目标、效率和现实压力较敏感，遇事容易先判断轻重缓急。把要求拆成步骤，比一味硬撑更能发挥行动力。",
        "伤官": "观察快、表达直接，也较容易看见规则中不够合理的地方。把判断写清楚、做成作品，锋芒便更容易成为能力。",
        "偏印": "重视理解、方法和独立判断，面对陌生问题常会先在心里建立自己的解释框架。规律作息能让思考更稳定。",
        "正财": "看重秩序、兑现和可持续的安排，适合把目标落实到时间、预算与具体责任。",
        "偏财": "对机会、资源与外部变化较敏锐，擅长在流动环境里寻找可用条件，但仍需保留复核与边界。",
        "正官": "重视规则、责任与可信度，适合在清楚的标准中持续积累专业声誉。",
        "正印": "重视安全感、学习与支持系统，遇事先打好基础会更从容。",
        "食神": "讲究体验、表达与稳定产出，适合把兴趣沉淀为可重复的作品或服务。",
        "比肩": "自主意识与自我要求较强，适合明确自己的节奏和责任范围。",
        "劫财": "行动与同伴意识较强，合作时清楚分工与利益边界尤其重要。",
    }
    sections = []
    for index, row in enumerate(rows):
        label = _e(row.get("label"))
        percent = float(row.get("percent") or 0)
        text = descriptions.get(row.get("label"), "这股力量在原盘中较为醒目，宜结合它所在的位置与干支作用继续阅读。")
        sections.append(f"<section><i>{number[index]}</i><div><h2>{label} · {percent:.1f}%</h2><p>{_e(text)}</p></div></section>")
    return f"""<article class="page verso bridge-page" data-page="42">
      <header>十神 · 本章小结</header><p class="eyebrow">从力量较集中的十神，回看这张命盘的行为方式</p><h1>这张命盘的三条十神主线</h1>
      <div class="bridge-lines">{''.join(sections)}</div>
      <blockquote>下一章的神煞用于补充细节；真正的判断，仍以前面已经确认的五行、十神与干支结构为根基。</blockquote><footer>42</footer>
    </article>"""


def _intro_page(case: dict) -> str:
    return f"""<article class="page recto chapter-divider" data-page="43">
      <div class="chapter-frame"><small>第六章 · 本盘 {_e(case['count'])} 种</small><h1>神煞分析</h1><p>辨其含义<br>观其影响</p><i>神煞补充性情与经历的细节<br>仍以原盘结构为根基</i></div><footer>43</footer>
    </article>"""


def _shensha_entry(case: dict, code: str) -> str:
    item = next(row for row in case["items"] if row["code"] == code)
    copy = REAL_CASE_SHENSHA_COPY.get(code)
    placement = "、".join(item["placement_labels"])
    if copy is None:
        scope = {
            "年柱": "早年环境、家庭背景以及他人最先看见的外在印象",
            "月柱": "工作方式、社会协作与日常习惯",
            "日柱": "自我感受、日常生活与亲密关系",
            "时柱": "长期计划、成果沉淀与未来生活安排",
        }
        scopes = "；".join(scope[label] for label in item["placement_labels"])
        copy = {
            "meaning": item["summary"],
            "impact": f"{item['name']}落在{placement}，较多影响{scopes}。{item['reading']}这是一项辅助线索，仍要与十神、干支关系和现实经历合看。",
        }
    return f"""<section class="shensha-entry">
      <figure><img src="../../../assets/mingshu/shensha/{_e(item['image'])}" alt="{_e(item['name'])}国风人物插图"></figure>
      <div><p class="entry-meta">{_e(item['kind'])} · {_e(placement)}</p><h2>{_e(item['name'])}</h2>
      <h3>神煞本身的含义</h3><p>{_e(copy['meaning'])}</p>
      <h3>对命主的影响</h3><p>{_e(copy['impact'])}</p></div>
    </section>"""


def _pair_page(case: dict, codes: tuple[str, str], page: int, side: str) -> str:
    names = "与".join(next(row["name"] for row in case["items"] if row["code"] == code) for code in codes)
    return f"""<article class="page {side} shensha-pair" data-page="{page}">
      <header>神煞 · 本盘实见</header><p class="eyebrow">{_e(names)}</p><h1>含义与现实影响</h1>
      <div class="shensha-entry-list">{''.join(_shensha_entry(case, code) for code in codes)}</div><footer>{page}</footer>
    </article>"""


def _single_page(case: dict, code: str, page: int, side: str) -> str:
    item = next(row for row in case["items"] if row["code"] == code)
    return f"""<article class="page {side} shensha-single" data-page="{page}">
      <header>神煞 · 本盘实见</header><p class="eyebrow">落在{_e('、'.join(item['placement_labels']))}，与日常生活和亲密关系的位置相连</p><h1>{_e(item['name'])}</h1>
      {_shensha_entry(case, code)}<footer>{page}</footer>
    </article>"""


def _distribution_page(case: dict) -> str:
    columns = []
    for pillar, label in PILLAR_LABELS.items():
        names = []
        for item in case["by_pillar"][pillar]:
            if item["name"] not in names:
                names.append(item["name"])
        chips = "".join(f"<li>{_e(name)}</li>" for name in names)
        columns.append(f"<section><h2>{label}</h2><ul>{chips or '<li>本柱未见</li>'}</ul></section>")
    placement_count = sum(len(items) for items in case["by_pillar"].values())
    repeated = [item for item in case["items"] if len(item["placements"]) > 1]
    if repeated:
        repeated_text = "、".join(f"{item['name']}见于{'、'.join(item['placement_labels'])}" for item in repeated)
        note = f"{repeated_text}。重复出现表示它参与的生活范围更广，不等于作用被简单倍增。"
    else:
        note = "本盘神煞各有一处落点。落柱决定它更接近哪一类生活场景，但不应越过原盘结构单独判断吉凶。"
    return f"""<article class="page recto distribution" data-page="49">
      <header>神煞 · 原局分布</header><p class="eyebrow">{case['count']}种神煞，共{placement_count}处落点</p><h1>四柱中的神煞位置</h1>
      <div class="distribution-grid">{''.join(columns)}</div>
      <p class="distribution-note">{_e(note)}</p><footer>49</footer>
    </article>"""


def _reading_summary_page(case: dict, page: int, side: str) -> str:
    helpful = [item["name"] for item in case["items"] if item.get("kind") in {"神", "贵人"}]
    caution = [item["name"] for item in case["items"] if item.get("kind") == "煞"]
    return f"""<article class="page {side} guide" data-page="{page}">
      <header>神煞 · 合并阅读</header><p class="eyebrow">把名称放回现实生活，不把标签当作结论</p><h1>本盘神煞的阅读重点</h1>
      <ol>
        <li><i>一</i><div><h2>支持线索</h2><p>{_e('、'.join(helpful) or '本盘未见明显贵人类神煞')}。它们提示哪些场景更容易得到经验、资源或善意回应，前提仍是主动沟通和实际行动。</p></div></li>
        <li><i>二</i><div><h2>需要留意的地方</h2><p>{_e('、'.join(caution) or '本盘未见单列的煞类神煞')}。这类名称用于提醒节奏、边界或误差，不等于某件坏事一定发生。</p></div></li>
        <li><i>三</i><div><h2>以原盘为主</h2><p>同一神煞落在不同柱位，现实含义会不同；遇到大运流年再次引动时，也要同时核对五行、十神与合冲刑害。</p></div></li>
      </ol><p class="bottom-note"><b>阅读边界</b>神煞是补充说明，不用于替代健康、法律、财务或关系中的专业判断。</p><footer>{page}</footer>
    </article>"""


def render_shensha_sample_html(facts: dict, output_html: Path, output_data: Path) -> dict:
    case = build_shensha_case(facts)
    detail_pages = []
    codes = [item["code"] for item in case["items"]][:10]
    for index in range(0, len(codes), 2):
        page = 44 + len(detail_pages)
        side = "verso" if page % 2 == 0 else "recto"
        chunk = codes[index:index + 2]
        detail_pages.append(_pair_page(case, tuple(chunk), page, side) if len(chunk) == 2 else _single_page(case, chunk[0], page, side))
    while len(detail_pages) < 5:
        page = 44 + len(detail_pages)
        side = "verso" if page % 2 == 0 else "recto"
        detail_pages.append(_reading_summary_page(case, page, side))
    pages = (_bridge_page(facts), _intro_page(case), *detail_pages[:5], _distribution_page(case))
    spreads = "".join(f'<section class="spread">{pages[i]}{pages[i + 1]}</section>' for i in range(0, len(pages), 2))
    html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 神煞章节样例</title><style>
@font-face{{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}}@font-face{{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}}@font-face{{font-family:Calligraphy;src:url('../../../assets/fonts/MaShanZheng-Regular.ttf')}}
@page{{size:A4 landscape;margin:0}}:root{{--paper:#f5eddd;--paper2:#fbf7ec;--ink:#292821;--muted:#746b5e;--line:#d5c19d;--gold:#a77934;--jade:#315e52;--red:#974238}}*{{box-sizing:border-box}}body{{margin:0;background:#242422;color:var(--ink);font-family:BookSerif,serif}}main{{padding:28px 0 70px}}.spread{{display:flex;width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;filter:drop-shadow(0 14px 24px #111)}}.page{{position:relative;flex:0 0 50%;aspect-ratio:148/210;padding:7.5% 8%;overflow:hidden;background:linear-gradient(145deg,var(--paper2),var(--paper));contain:layout paint}}.spread>.page:first-child:after{{content:'';position:absolute;right:0;inset-block:0;width:1px;background:#cbbfae}}header{{font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px}}.recto header{{text-align:right}}h1{{font-size:29px;line-height:1.25;margin:7px 0 10px;font-weight:500}}h2{{font-weight:500}}.eyebrow{{font:9px BookSans;color:var(--gold);letter-spacing:.1em;margin:18px 0 0}}footer{{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#887d6b}}.recto footer{{text-align:right}}.bottom-note{{font:9px/1.65 BookSans;color:var(--muted);margin:10px 0 0;padding:9px 12px;border-left:2px solid var(--gold);background:rgba(255,253,247,.72)}}.bottom-note b{{color:var(--jade);margin-right:8px}}
.bridge-page h1{{margin-bottom:20px}}.bridge-lines{{border-top:1px solid var(--gold)}}.bridge-lines section{{display:grid;grid-template-columns:52px 1fr;gap:16px;padding:20px 0;border-bottom:1px solid var(--line)}}.bridge-lines i{{font:37px Calligraphy;color:var(--gold);font-style:normal;text-align:center}}.bridge-lines h2{{font-size:17px;margin:0 0 6px}}.bridge-lines p{{font:10.5px/1.75 BookSans;color:#555048;margin:0}}.bridge-page blockquote{{font:16px/1.7 BookSerif;color:var(--jade);margin:22px 0 0;padding:12px 16px;border-left:3px solid var(--gold);background:rgba(255,253,247,.58)}}
.chapter-divider{{padding:0;background:#203b34;color:#f1e6ce}}.chapter-frame{{position:absolute;inset:8%;border:1px solid #b89a60;outline:1px solid rgba(184,154,96,.45);outline-offset:-9px}}.chapter-frame small,.chapter-frame h1,.chapter-frame p,.chapter-frame i{{position:absolute;writing-mode:vertical-rl;white-space:nowrap;margin:0}}.chapter-frame small{{right:10%;bottom:10%;font:11px BookSans;letter-spacing:.25em;color:#c9ac73}}.chapter-frame h1{{right:22%;top:44%;transform:translateY(-50%);font:49px/1 Calligraphy;letter-spacing:.14em;font-weight:400}}.chapter-frame p{{right:48%;top:27%;font:20px/1.8 BookSerif;color:#e4d2ae;letter-spacing:.14em}}.chapter-frame i{{right:72%;top:13%;font:normal 10px/1.8 BookSans;color:#b9ad91;letter-spacing:.08em}}.chapter-divider footer{{color:#bda978}}
.pillar-grid{{display:grid;grid-template-columns:repeat(4,1fr);border-block:1px solid var(--gold);margin-top:20px;min-height:430px}}.pillar-grid section{{padding:18px 11px;border-right:1px solid var(--line)}}.pillar-grid section:last-child{{border:0}}.pillar-grid h2{{font-size:17px;text-align:center;margin:0 0 17px}}.pillar-grid ul{{list-style:none;padding:0;margin:0}}.pillar-grid li{{border-top:1px solid #dfd2bc;padding:10px 2px;display:flex;justify-content:space-between;gap:4px;align-items:baseline}}.pillar-grid li b{{font-size:14px;font-weight:500}}.pillar-grid li span{{font:8px BookSans;color:var(--gold)}}.pillar-grid .empty{{font:11px BookSans;color:var(--muted);justify-content:center}}
.guide ol{{list-style:none;padding:0;margin:18px 0 13px}}.guide li{{display:flex;gap:18px;border-top:1px solid var(--line);padding:16px 0}}.guide li i{{font:32px Calligraphy;color:var(--gold);font-style:normal;min-width:34px}}.guide li h2{{font-size:17px;margin:0 0 5px}}.guide li p{{font:11px/1.75 BookSans;margin:0;color:#4d4941}}.cluster-list{{display:grid;grid-template-columns:1fr 1fr;gap:0 18px;border-top:1px solid var(--line);padding-top:8px}}.cluster-list div{{padding:7px 0;border-bottom:1px solid #ded1bb}}.cluster-list b{{font:10px BookSans;color:var(--jade)}}.cluster-list p{{font:10px/1.6 BookSans;color:var(--muted);margin:2px 0}}
.shensha-pair h1{{font-size:25px;margin-bottom:11px}}.shensha-entry-list{{border-top:1px solid var(--gold)}}.shensha-entry{{display:grid;grid-template-columns:38% 62%;height:257px;border-bottom:1px solid var(--line);background:#f8f1e3;isolation:isolate}}.shensha-entry figure{{margin:0;padding:8px;overflow:hidden;display:flex;align-items:center;justify-content:center;border-right:1px solid var(--line);background:#f3e8d4}}.shensha-entry figure img{{width:100%;height:100%;object-fit:contain;mix-blend-mode:normal;background:#f3e8d4}}.shensha-entry>div{{align-self:center;padding:10px 14px;background:#f8f1e3}}.entry-meta{{font:8px BookSans!important;color:var(--gold)!important;letter-spacing:.08em;margin:0!important}}.shensha-entry h2{{font:25px Calligraphy;margin:2px 0 7px}}.shensha-entry h3{{font:10px BookSans;color:var(--jade);margin:8px 0 2px;letter-spacing:.05em}}.shensha-entry p{{font:9.3px/1.58 BookSans;color:#4d4941;margin:0}}.shensha-single .shensha-entry{{height:460px;margin-top:12px;grid-template-columns:48% 52%;border-block:1px solid var(--gold)}}.shensha-single .shensha-entry h2{{display:none}}.shensha-single .shensha-entry h3{{font-size:12px;margin-top:15px}}.shensha-single .shensha-entry p{{font-size:10.5px;line-height:1.75}}.distribution-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:20px}}.distribution-grid section{{min-height:185px;padding:17px;border:1px solid var(--line);background:rgba(255,253,247,.45)}}.distribution-grid h2{{font-size:18px;color:var(--gold);margin:0 0 10px;padding-bottom:7px;border-bottom:1px solid var(--line)}}.distribution-grid ul{{list-style:none;padding:0;margin:0;columns:2;column-gap:12px}}.distribution-grid li{{font:10px/1.75 BookSans;color:#4f4a43;break-inside:avoid}}.distribution-note{{font:10.5px/1.75 BookSans;color:var(--jade);margin:20px 0 0;padding:13px 15px;border-left:3px solid var(--gold);background:rgba(255,253,247,.58)}}
@media print{{body{{background:#fff}}main{{padding:0}}.spread{{width:296mm;height:210mm;margin:0;filter:none;break-after:page}}.page{{width:148mm;height:210mm}}}}
{SHENSHA_V2_CSS}</style></head><body><main>{spreads}</main></body></html>"""
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_data.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")
    library = [{**item, "image": SHENSHA_IMAGE_BY_CODE[item["code"]]} for item in SHENSHA_LIBRARY]
    output_data.write_text(json.dumps({"case": case, "library": library}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"html": str(output_html), "data": str(output_data), "pages": 8, "case_count": case["count"]}
