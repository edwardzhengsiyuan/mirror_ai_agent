"""Print-first closing chapter for the illustrated MingShu."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .element_styles import ELEMENT_COLOR_SCRIPT


def _e(value: object) -> str:
    return escape(str(value or ""))


def _chart_summary(facts: dict) -> dict[str, object]:
    pillars = facts.get("chart", {}).get("pillars", [])
    day = next((item for item in pillars if item.get("key") == "day"), {})
    month = next((item for item in pillars if item.get("key") == "month"), {})
    wuxing = sorted(
        facts.get("analysis_facts", {}).get("wuxing", []),
        key=lambda item: float(item.get("percent", 0)),
        reverse=True,
    )
    gods = sorted(
        (
            item
            for item in facts.get("analysis_facts", {}).get("shishen", [])
            if item.get("code") != "SHISHEN:RIZHU" and float(item.get("percent", 0)) > 0
        ),
        key=lambda item: float(item.get("percent", 0)),
        reverse=True,
    )
    relations = facts.get("analysis_facts", {}).get("origin_relations", [])
    relation_labels = list(dict.fromkeys(item.get("label", "") for item in relations if item.get("label")))
    return {
        "subject": facts.get("subject", {}).get("display_name") or "你",
        "day": day.get("gan", {}).get("name_label") or "日主",
        "month": month.get("zhi", {}).get("name_label") or "月令",
        "dominant": wuxing[0] if wuxing else {"label": "", "percent": 0},
        "quiet": wuxing[-1] if wuxing else {"label": "", "percent": 0},
        "gods": gods[:3],
        "relations": relation_labels,
    }


def render_closing_html(facts: dict) -> str:
    s = _chart_summary(facts)
    dominant = s["dominant"]
    quiet = s["quiet"]
    god_names = "、".join(item["label"] for item in s["gods"])
    relation_names = "、".join(s["relations"]) or "原盘中的合冲关系"
    pages = [
        '<article class="page verso blank" data-page="228" aria-label="结语章节前留白页"></article>',
        '''<article class="page recto chapter-divider" data-page="229"><div class="chapter-frame"><small>第十一章</small><h1>结语</h1><p>知所来<br>自择所往</p><i>读到此处<br>把判断交还生活</i></div><footer>229</footer></article>''',
        f'''<article class="page verso closing-summary" data-page="230"><header>结语 · 全书回望</header><p class="eyebrow">从原盘到岁运，从专题再回到此刻</p><h1>这本命书留下的四条线索</h1>
        <div class="closing-lines">
          <section><i>一</i><div><h2>你的起点有鲜明的温度</h2><p>{_e(s['day'])}日主生于{_e(s['month'])}月，{_e(dominant['label'])}的力量约占 {_e(f"{dominant['percent']:.1f}")}%。行动、表达和推进往往来得快；真正重要的不是压住这股力量，而是为它安排方向与停顿。</p></div></section>
          <section><i>二</i><div><h2>能力要经过现实，才会成为成果</h2><p>原盘较显眼的十神是{_e(god_names)}。它们共同指向一件事：既要保持判断和行动，也要把时间、资源、责任与交付方式说清楚。</p></div></section>
          <section><i>三</i><div><h2>拉扯之处，也是需要练习的地方</h2><p>{_e(relation_names)}不是替人生下结论，而是在提醒：机会、方法、亲密关系与生活节奏相遇时，要多一次确认，少一次靠惯性推进。</p></div></section>
          <section><i>四</i><div><h2>平衡来自补上较少被使用的能力</h2><p>{_e(quiet['label'])}在五行中约占 {_e(f"{quiet['percent']:.1f}")}%。它不等于缺点，更像一项需要主动安排的能力：留出冷静、复盘、规则与恢复，才能让优势走得更久。</p></div></section>
        </div><footer>230</footer></article>''',
        f'''<article class="page recto final-letter" data-page="231"><header>结语 · 写给 {_e(s['subject'])}</header><div class="letter-mark"><span>知势</span><span>择路</span></div><h1>愿你知势，<br>不被势困</h1><div class="letter-copy">
          <p>读到这里，命盘里能说的，已经说得够多了。</p>
          <p>天时给人一个起点，经历会改变每一种力量的分量。你怎样学习，和谁同行，在什么地方停下来，又在什么时候重新出发，都会继续改写这张图。</p>
          <p>所以，把命书合上之后，仍要回到眼前这一日：把能做的事做具体，把重要的人认真对待，把真正想走的路留在自己的选择里。</p>
        </div><blockquote>命可参详，路须亲行。</blockquote><div class="closing-seal">镜<br>心</div><footer>231</footer></article>''',
    ]
    spreads = "".join(
        f'<section class="spread">{pages[index]}{pages[index + 1]}</section>'
        for index in range(0, len(pages), 2)
    )
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 结语</title><style>{_css()}</style></head><body><main>{spreads}</main>{ELEMENT_COLOR_SCRIPT}</body></html>'''


def _css() -> str:
    return r'''
@font-face{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}@font-face{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}@font-face{font-family:Brush;src:url('../../../assets/fonts/MaShanZheng-Regular.ttf')}@page{size:A4 landscape;margin:0}:root{--paper:#f6efdf;--paper2:#fbf7ed;--ink:#292821;--muted:#746b5e;--line:#d6c39f;--gold:#a77934;--jade:#315e52;--red:#974238}*{box-sizing:border-box}body{margin:0;background:#242422;color:var(--ink);font-family:BookSerif,serif}main{padding:28px 0 70px}.spread{display:flex;width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;filter:drop-shadow(0 14px 24px #111)}.page{position:relative;flex:0 0 50%;aspect-ratio:148/210;padding:7.5% 8%;overflow:hidden;background:linear-gradient(145deg,var(--paper2),var(--paper));contain:layout paint}.spread>.page:first-child:after{content:'';position:absolute;right:0;inset-block:0;width:1px;background:#cbbfae}.blank{padding:0;background:var(--paper)}header{font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px}.recto header{text-align:right}.eyebrow{font:9px BookSans;color:var(--gold);letter-spacing:.07em;margin:18px 0 0}h1{font-size:29px;line-height:1.28;margin:8px 0 18px;font-weight:500}footer{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#887d6b}.recto footer{text-align:right}.chapter-divider{padding:0;background:#203b34;color:#f1e6ce}.chapter-frame{position:absolute;inset:8%;border:1px solid #b89a60;outline:1px solid rgba(184,154,96,.45);outline-offset:-9px}.chapter-frame small,.chapter-frame h1,.chapter-frame p,.chapter-frame i{position:absolute;writing-mode:vertical-rl;white-space:nowrap;margin:0}.chapter-frame small{right:10%;bottom:10%;font:11px BookSans;letter-spacing:.25em;color:#c9ac73}.chapter-frame h1{right:36%;top:13%;font:78px Brush;font-weight:400}.chapter-frame p{right:59%;top:19%;font:21px/1.8 BookSerif}.chapter-frame i{left:12%;bottom:11%;font:normal 10px/1.7 BookSans;color:#ccb986}.closing-lines{margin-top:8px;border-top:1px solid var(--gold)}.closing-lines section{display:grid;grid-template-columns:42px 1fr;gap:13px;padding:16px 4px 15px;border-bottom:1px solid var(--line)}.closing-lines i{font:32px Brush;color:var(--gold);font-style:normal}.closing-lines h2{font-size:15px;font-weight:500;color:var(--jade);margin:0 0 7px}.closing-lines p{font:10.2px/1.72 BookSans;color:#4f4a42;margin:0}.final-letter{background:radial-gradient(circle at 74% 22%,rgba(167,121,52,.09),transparent 24%),linear-gradient(145deg,#fbf7ed,#f2e8d4)}.letter-mark{display:flex;gap:9px;margin:38px 0 16px}.letter-mark span{border:1px solid var(--gold);padding:7px 5px;writing-mode:vertical-rl;font:12px BookSans;color:var(--gold);letter-spacing:.18em}.final-letter h1{font:50px/1.28 Brush;color:var(--jade);font-weight:400;margin:0 0 28px}.letter-copy{width:86%;border-top:1px solid var(--gold);padding-top:17px}.letter-copy p{font:11px/1.92 BookSans;color:#48443d;margin:0 0 12px}.final-letter blockquote{font:27px Brush;color:var(--red);margin:23px 0 0;text-align:left}.closing-seal{position:absolute;right:10%;bottom:12%;border:1px solid var(--red);color:var(--red);font:15px/1.2 BookSerif;padding:7px;opacity:.72}@media print{body{background:#fff}main{padding:0}.spread{width:296mm;height:210mm;margin:0;filter:none;break-after:page}.spread:last-child{break-after:auto}.page{width:148mm;height:210mm}}
'''


def write_closing_sample(facts: dict, html_path: str | Path, data_path: str | Path | None = None) -> Path:
    target = Path(html_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_closing_html(facts), encoding="utf-8")
    if data_path is not None:
        data_target = Path(data_path)
        data_target.parent.mkdir(parents=True, exist_ok=True)
        data_target.write_text(json.dumps(_chart_summary(facts), ensure_ascii=False, indent=2), encoding="utf-8")
    return target
