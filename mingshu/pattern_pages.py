"""Print-first pages for the pattern chapter."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .pattern import build_pattern_analysis
from .element_styles import ELEMENT_COLOR_SCRIPT
from .page_numbering import page_offset_script


def _e(value: object) -> str:
    return escape(str(value or ""))


def _bridge_page(facts: dict) -> str:
    names = []
    for rows in facts.get("analysis_facts", {}).get("shensha", {}).values():
        for item in rows:
            if item.get("name") not in names:
                names.append(item.get("name"))
    groups = [names[:3], names[3:6], names[6:]]
    titles = ("支持与回应", "能力与责任", "节奏与边界")
    sections = "".join(f"<section><i>{'一二三'[i]}</i><div><h2>{titles[i]}</h2><p>{_e('、'.join(group) or '本盘未见单列项目')}为本盘补充线索；应放回所在柱位理解，不单凭名称判断结果。</p></div></section>" for i, group in enumerate(groups))
    return f"""<article class="page verso bridge-page" data-page="40">
      <header>神煞 · 本章小结</header><p class="eyebrow">本盘实见神煞补充人际、行动、资源和生活细节</p><h1>辅助线索，回到命盘主结构</h1>
      <div class="bridge-lines">{sections}</div>
      <blockquote>接下来进入格局：观察月令与主要力量怎样组织全盘，以及这种组织方式如何在大运中被加强或改写。</blockquote><footer>40</footer>
    </article>"""


def _intro_page() -> str:
    return """<article class="page recto chapter-divider" data-page="41"><div class="chapter-frame"><small>第七章</small><h1>格局分析</h1><p>辨其主线<br>观其成用</p><i>从月令、透干与根气出发<br>再看二级结构与行运</i></div><footer>41</footer></article>"""


def _classification_page(data: dict) -> str:
    primary = data["primary"]
    structure = data["structure"]
    strongest = max((structure["output_percent"], "食伤"), (structure["wealth_percent"], "财星"), (structure["authority_percent"], "官杀"), (structure["resource_percent"], "印星"))
    reasons = "".join(f"<li>{_e(item)}</li>" for item in primary["basis"])
    return f"""<article class="page verso classification" data-page="42">
      <header>格局 · 大类判定</header><p class="eyebrow">基础脚本保留待分析状态，命书层继续核对月令藏干与透干</p><h1>{_e(primary['name'])} · {_e(primary['status'])}</h1>
      <div class="decision-path"><section><b>特殊格</b><span>未直接采用</span><p>原盘仍有多种五行参与，不把单一力量直接写成专旺或从格。</p></section><i>↓</i><section class="active"><b>正格候选</b><span>{_e(primary['name'])}</span><p>{_e(primary['basis'][0] if primary['basis'] else '从月令主气与透干继续判断。')}</p></section><i>↓</i><section><b>保留分歧</b><span>{_e(primary['status'])}</span><p>当前力量最高的是{_e(strongest[1])}，约{strongest[0]:.1f}%；格名仍要与日主强弱、制化路径一起阅读。</p></section></div>
      <ul class="evidence-list">{reasons}</ul><footer>42</footer>
    </article>"""


def _primary_page(data: dict) -> str:
    structure = data["structure"]
    primary = data["primary"]
    primary_name = str(primary["name"])
    if "七杀" in primary_name:
        image = "qisha-v1.png"; focus = "目标、责任、时限与压力怎样被转化为清楚行动"; watch = "日主偏弱而七杀有力时，不能只加要求；印星支持、同类协助和明确权限同样重要。"
    elif "财" in primary_name:
        image = "zhengcai-v1.png"; focus = "价值判断、资源安排与成果怎样持续兑现"; watch = "机会越多，越要确认成本、边界和长期承接。"
    else:
        image = "pianyin-v1.png"; focus = "月令主气怎样组织全盘，并在现实中形成稳定做事方式"; watch = "候选格局尚需结合制化、透干与行运继续验证。"
    return f"""<article class="page recto primary-pattern" data-page="43">
      <header>格局 · 主候选</header><p class="eyebrow">从月令主气出发，再核对力量与制化路径</p><h1>{_e(primary_name)}：{_e(focus)}</h1>
      <div class="primary-layout"><div class="wealth-portraits"><figure><img src="../../../assets/mingshu/shishen/{image}" alt="{_e(primary_name)}意象"></figure><figure><img src="../../../assets/mingshu/shishen/pianyin-v1.png" alt="支持力量意象"></figure></div><div class="primary-copy"><section><h2>这个格局关注什么</h2><p>{_e(focus)}。格局不是职业或命运标签，而是一张命盘最常用的组织方式。</p></section><section><h2>本盘为什么列为候选</h2><p>{_e(' '.join(primary['basis']))} 官杀合计约 {structure['authority_percent']:.1f}%，印星约 {structure['resource_percent']:.1f}%。</p></section><section><h2>需要留意的地方</h2><p>{_e(watch)}</p></section></div></div>
      <p class="page-conclusion">这一页确定的是主候选与证据强度；格局是否发挥顺畅，还要继续看食伤、官杀和印星怎样配合。</p><footer>43</footer>
    </article>"""


def _secondary_page(data: dict) -> str:
    cards = "".join(f"""<section class="secondary-card"><div><b>{_e(item['name'])}</b><span class="status {('weak' if item['status'] == '条件不足' else 'mid' if item['status'] == '藏支线索' else 'strong')}">{_e(item['status'])}</span></div><p>{_e(item['summary'])}</p><small>{_e(item['evidence'])}</small></section>""" for item in data["secondary"])
    return f"""<article class="page verso secondary-overview" data-page="44"><header>格局 · 二级结构</header><p class="eyebrow">同一主格之下，还会出现相生、相制与条件不足的组合</p><h1>三条二级结构，强弱不同</h1><div class="secondary-list">{cards}</div><div class="status-key"><span><i class="strong"></i>结构清楚</span><span><i class="mid"></i>藏支线索</span><span><i class="weak"></i>条件不足</span></div><footer>44</footer></article>"""


def _secondary_detail_page(data: dict) -> str:
    items = data["secondary"]
    sections = "".join(f"<section class=\"mechanism {'main' if i == 0 else 'muted' if item['status'] == '条件不足' else ''}\"><div><b>{_e(item['name'])}</b></div><p>{_e(item['effect'])} {_e(item['evidence'])}</p></section>" for i, item in enumerate(items))
    return f"""<article class="page recto secondary-detail" data-page="45"><header>格局 · 二级结构</header><p class="eyebrow">成立的写成立，只有线索的保留强弱，条件不足的不抬高</p><h1>{_e(items[0]['name'])}，是本盘较清楚的配合</h1>{sections}<footer>45</footer></article>"""


def _useful_flow_page(data: dict) -> str:
    useful = data["useful_gods"]
    return f"""<article class="page verso useful-flow" data-page="46"><header>格局 · 用神与相神</header><p class="eyebrow">把“格局中心”和“帮助格局运转的力量”分开说明</p><h1>主轴、承接、扶助与边界</h1>
      <div class="useful-copy"><section><h2>{_e(useful['pattern_center']['name'])}</h2><p>{_e(useful['pattern_center']['state'])}</p></section><section><h2>{_e(useful['supporting']['name'])}</h2><p>{_e(useful['supporting']['state'])}</p></section><section><h2>{_e(useful['further_flow']['name'])}</h2><p>{_e(useful['further_flow']['state'])}</p></section><section><h2>{_e(useful['caution']['name'])}</h2><p>{_e(useful['caution']['state'])}</p></section></div>
      <p class="page-conclusion">这里采用格局法说明结构如何运转；调候用神处理季节寒暖燥湿。两套用神可以互相参照，但不能混成同一个概念。</p><footer>46</footer></article>"""


def _state_page(data: dict) -> str:
    s = data["structure"]
    rows = (("食伤 · 方法与表达", s["output_percent"], "观察它如何处理压力、提出改进并形成输出"), ("财星 · 资源与目标", s["wealth_percent"], "资源越多，也越要核对是否继续生助压力"), ("官杀 · 规则与责任", s["authority_percent"], "格局主线是否有力，需看能否得到制化和承接"), ("印星 · 学习与支持", s["resource_percent"], "印星可化杀生身，把外部要求转成方法与稳定支撑"))
    bars = "".join(f"<section><div><b>{_e(name)}</b><strong>{value:.1f}%</strong></div><i><em style=\"width:{min(value/30*100,100):.1f}%\"></em></i><p>{_e(note)}</p></section>" for name, value, note in rows)
    return f"""<article class="page recto useful-state" data-page="47"><header>格局 · 原盘状态</header><p class="eyebrow">比例说明参与度，透干和根气说明能否稳定发挥</p><h1>主轴有力，更要看承接方式</h1><div class="state-bars">{bars}</div><div class="state-summary"><b>当前结构</b><p>官杀与财星都较有力，目标、资源和责任容易彼此相连；日主偏弱时，印星的学习支持与比劫的自主边界尤其重要。伤官能够提出办法，但表达仍要落回规则与可执行步骤。</p></div><footer>47</footer></article>"""


def _luck_page(data: dict) -> str:
    rows = "".join(f"""<section><time>{_e(item['start_year'])}<small>—{_e(item['end_year'])}</small></time><div><h2>{_e(item['name'])}<span>{_e(item['gan_ten_god'])} · {_e(item['zhi_ten_god'])}</span></h2><p>{_e(item['reading'])}</p></div></section>""" for item in data["luck_windows"])
    return f"""<article class="page verso luck-pattern" data-page="48"><header>格局 · 大运引动</header><p class="eyebrow">大运不会替换原盘，但会让某一条结构在十年中更突出</p><h1>哪些大运会加强这套格局</h1><div class="luck-list">{rows}</div><footer>48</footer></article>"""


def _career_page(data: dict) -> str:
    cards = "".join(f"""<section><h2>{_e(item['name'])}</h2><p>{_e(item['reason'])}</p><small>{_e(item['examples'])}</small></section>""" for item in data["career"])
    return f"""<article class="page recto career-pattern" data-page="49"><header>格局 · 职业与天赋</header><p class="eyebrow">职业方向看的是能力如何被使用，不是由格局名称限定行业</p><h1>把判断、产出与资源连接起来</h1><div class="career-grid">{cards}</div><div class="talent-line"><b>较值得发挥的天赋</b><p>判断一件事是否值得投入；把复杂经验变成产品或服务；协调人、预算与进度；让研究和创意接受现实反馈。选择工作时，能同时接触“价值判断”和“成果落地”的岗位，更容易形成长期优势。</p></div><footer>49</footer></article>"""


def render_pattern_html(facts: dict) -> str:
    data = build_pattern_analysis(facts)
    pages = (_bridge_page(facts), _intro_page(), _classification_page(data), _primary_page(data), _secondary_page(data), _secondary_detail_page(data), _useful_flow_page(data), _state_page(data), _luck_page(data), _career_page(data))
    spreads = "".join(f'<section class="spread">{pages[i]}{pages[i + 1]}</section>' for i in range(0, len(pages), 2))
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 格局分析</title><style>
@font-face{{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}}@font-face{{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}}@font-face{{font-family:Calligraphy;src:url('../../../assets/fonts/MaShanZheng-Regular.ttf')}}@page{{size:A4 landscape;margin:0}}:root{{--paper:#f5eddd;--paper2:#fbf7ec;--ink:#292821;--muted:#746b5e;--line:#d5c19d;--gold:#a77934;--jade:#315e52;--red:#974238;--earth:#b88b4a;--metal:#8b7658;--water:#557487}}*{{box-sizing:border-box}}body{{margin:0;background:#242422;color:var(--ink);font-family:BookSerif,serif}}main{{padding:28px 0 70px}}.spread{{display:flex;width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;filter:drop-shadow(0 14px 24px #111)}}.page{{position:relative;flex:0 0 50%;aspect-ratio:148/210;padding:7.5% 8%;overflow:hidden;background:linear-gradient(145deg,var(--paper2),var(--paper));contain:layout paint}}.spread>.page:first-child:after{{content:'';position:absolute;right:0;inset-block:0;width:1px;background:#cbbfae}}header{{font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px}}.recto header{{text-align:right}}h1{{font-size:29px;line-height:1.25;margin:7px 0 10px;font-weight:500}}h2{{font-weight:500}}.eyebrow{{font:9px BookSans;color:var(--gold);letter-spacing:.1em;margin:18px 0 0}}footer{{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#887d6b}}.recto footer{{text-align:right}}.page-conclusion{{font:10px/1.7 BookSans;color:var(--jade);margin:15px 0 0;padding:10px 13px;border-left:3px solid var(--gold);background:#faf5e9}}
.bridge-page h1{{margin-bottom:20px}}.bridge-lines{{border-top:1px solid var(--gold)}}.bridge-lines section{{display:grid;grid-template-columns:52px 1fr;gap:16px;padding:20px 0;border-bottom:1px solid var(--line)}}.bridge-lines i{{font:37px Calligraphy;color:var(--gold);font-style:normal;text-align:center}}.bridge-lines h2{{font-size:17px;margin:0 0 6px}}.bridge-lines p{{font:10.5px/1.75 BookSans;color:#555048;margin:0}}.bridge-page blockquote{{font:15px/1.7 BookSerif;color:var(--jade);margin:20px 0 0;padding:12px 16px;border-left:3px solid var(--gold);background:#faf5e9}}
.chapter-divider{{padding:0;background:#203b34;color:#f1e6ce}}.chapter-frame{{position:absolute;inset:8%;border:1px solid #b89a60;outline:1px solid rgba(184,154,96,.45);outline-offset:-9px}}.chapter-frame small,.chapter-frame h1,.chapter-frame p,.chapter-frame i{{position:absolute;writing-mode:vertical-rl;white-space:nowrap;margin:0}}.chapter-frame small{{right:10%;bottom:10%;font:11px BookSans;letter-spacing:.25em;color:#c9ac73}}.chapter-frame h1{{right:22%;top:44%;transform:translateY(-50%);font:49px/1 Calligraphy;letter-spacing:.14em;font-weight:400}}.chapter-frame p{{right:48%;top:27%;font:20px/1.8 BookSerif;color:#e4d2ae;letter-spacing:.14em}}.chapter-frame i{{right:72%;top:13%;font:normal 10px/1.8 BookSans;color:#b9ad91;letter-spacing:.08em}}.chapter-divider footer{{color:#bda978}}
.decision-path{{margin-top:18px}}.decision-path section{{display:grid;grid-template-columns:92px 1fr;gap:5px 12px;padding:14px 16px;border:1px solid var(--line);background:#faf5e9}}.decision-path section.active{{border-color:var(--gold);box-shadow:inset 4px 0 var(--gold)}}.decision-path b{{font-size:15px}}.decision-path span{{font:12px BookSans;color:var(--jade);text-align:right}}.decision-path p{{grid-column:1/-1;font:9.5px/1.65 BookSans;color:#575149;margin:2px 0 0}}.decision-path>i{{display:block;text-align:center;font-style:normal;color:var(--gold);height:20px;line-height:20px}}.evidence-list{{margin:16px 0 0;padding:10px 12px 10px 28px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.evidence-list li{{font:9px/1.65 BookSans;color:#5b554c;margin:3px 0}}
.primary-layout{{display:grid;grid-template-columns:38% 62%;border-block:1px solid var(--gold);margin-top:15px;min-height:470px}}.wealth-portraits{{border-right:1px solid var(--line);display:grid;grid-template-rows:1fr 1fr;background:#f3e8d4}}.wealth-portraits figure{{margin:0;padding:8px;border-bottom:1px solid var(--line);overflow:hidden}}.wealth-portraits figure:last-child{{border:0}}.wealth-portraits img{{width:100%;height:100%;object-fit:contain;display:block;background:#f3e8d4}}.primary-copy{{align-self:center;padding:5px 16px}}.primary-copy section{{padding:12px 0;border-bottom:1px solid var(--line)}}.primary-copy section:last-child{{border:0}}.primary-copy h2{{font-size:14px;color:var(--jade);margin:0 0 5px}}.primary-copy p{{font:9.6px/1.7 BookSans;color:#4d4941;margin:0}}.primary-pattern .page-conclusion{{margin-top:10px}}
.secondary-list{{margin-top:18px;border-top:1px solid var(--gold)}}.secondary-card{{padding:20px 16px;border-bottom:1px solid var(--line);background:#faf5e9}}.secondary-card>div{{display:flex;justify-content:space-between;align-items:center}}.secondary-card b{{font-size:18px}}.status{{font:9px BookSans;padding:4px 9px;border:1px solid currentColor;border-radius:12px}}.status.strong{{color:var(--jade)}}.status.mid{{color:var(--gold)}}.status.weak{{color:#867b6c}}.secondary-card p{{font:10.5px/1.7 BookSans;color:#4e4941;margin:7px 0}}.secondary-card small{{font:8.5px/1.55 BookSans;color:#88785f}}.status-key{{display:flex;gap:20px;margin-top:14px;font:8px BookSans;color:var(--muted)}}.status-key i{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}}.status-key i.strong{{background:var(--jade)}}.status-key i.mid{{background:var(--gold)}}.status-key i.weak{{background:#a59b8a}}
.secondary-detail h1{{font-size:27px;margin-bottom:17px}}.mechanism{{display:grid;grid-template-columns:150px 1fr;gap:18px;padding:19px 0;border-top:1px solid var(--line);align-items:center}}.mechanism:last-of-type{{border-bottom:1px solid var(--line)}}.mechanism>div{{display:flex;align-items:center;justify-content:center;gap:9px;padding:12px;background:#faf5e9;border:1px solid var(--line)}}.mechanism.main>div{{border-color:var(--gold)}}.mechanism b{{font-size:16px}}.mechanism i{{font:20px Calligraphy;color:var(--gold);font-style:normal}}.mechanism p{{font:10px/1.7 BookSans;color:#4f4a43;margin:0}}.mechanism.muted{{opacity:.72}}
.flow-diagram{{display:flex;align-items:center;justify-content:space-between;margin:25px 0 22px}}.flow-node{{width:105px;height:118px;border:1px solid var(--line);background:#faf5e9;text-align:center;padding:12px 5px}}.flow-node small{{font:8px BookSans;color:var(--muted)}}.flow-node b{{display:block;font:34px Calligraphy;margin:5px 0;color:var(--red)}}.flow-node span{{font:9px BookSans}}.flow-node.active{{border-color:var(--earth)}}.flow-node.core{{border:2px solid var(--gold);box-shadow:0 0 0 5px rgba(167,121,52,.1)}}.flow-diagram>i{{font:18px Calligraphy;color:var(--gold);font-style:normal}}.useful-copy{{border-top:1px solid var(--gold)}}.useful-copy section{{display:grid;grid-template-columns:120px 1fr;gap:15px;padding:15px 0;border-bottom:1px solid var(--line)}}.useful-copy h2{{font-size:14px;color:var(--jade);margin:0}}.useful-copy p{{font:9.7px/1.65 BookSans;margin:0;color:#514c44}}
.state-bars{{margin-top:20px}}.state-bars section{{margin-bottom:20px}}.state-bars section>div{{display:flex;justify-content:space-between;align-items:baseline}}.state-bars b{{font-size:14px}}.state-bars strong{{font:12px BookSans;color:var(--gold)}}.state-bars i{{display:block;height:8px;background:#e7dbc5;margin:6px 0 5px}}.state-bars em{{display:block;height:100%;background:linear-gradient(90deg,var(--jade),var(--gold))}}.state-bars p{{font:9px BookSans;color:var(--muted);margin:0}}.state-summary{{margin-top:18px;padding:15px;border:1px solid var(--line);background:#faf5e9}}.state-summary b{{font-size:15px;color:var(--jade)}}.state-summary p{{font:10px/1.75 BookSans;color:#4d4941;margin:6px 0 0}}
.luck-list{{margin-top:10px;border-top:1px solid var(--gold)}}.luck-list section{{display:grid;grid-template-columns:58px 1fr;gap:9px;padding:6px 0;border-bottom:1px solid var(--line)}}.luck-list time{{font:12px BookSerif;color:var(--gold)}}.luck-list time small{{display:block;font:7px BookSans;color:var(--muted)}}.luck-list h2{{font-size:12px;margin:0 0 2px}}.luck-list h2 span{{float:right;font:7px BookSans;color:var(--jade)}}.luck-list p{{font:7.4px/1.35 BookSans;color:#514c44;margin:0}}
.career-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:20px}}.career-grid section{{min-height:150px;padding:16px;border:1px solid var(--line);background:#faf5e9}}.career-grid h2{{font-size:16px;color:var(--jade);margin:0 0 7px}}.career-grid p{{font:9.5px/1.65 BookSans;color:#4d4941;margin:0 0 9px}}.career-grid small{{font:8px/1.5 BookSans;color:#8a7656}}.talent-line{{margin-top:18px;padding:14px 16px;border-left:3px solid var(--gold);background:#faf5e9}}.talent-line b{{font-size:14px}}.talent-line p{{font:10px/1.7 BookSans;color:#4d4941;margin:5px 0 0}}
@media print{{body{{background:#fff}}main{{padding:0}}.spread{{width:296mm;height:210mm;margin:0;filter:none;break-after:page}}.page{{width:148mm;height:210mm}}}}</style></head><body><main>{spreads}</main>{ELEMENT_COLOR_SCRIPT}{page_offset_script(10)}</body></html>"""


def write_pattern_sample(facts: dict, html_path: str | Path, data_path: str | Path | None = None) -> Path:
    target = Path(html_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_pattern_html(facts), encoding="utf-8")
    if data_path is not None:
        data_target = Path(data_path)
        data_target.parent.mkdir(parents=True, exist_ok=True)
        data_target.write_text(json.dumps(build_pattern_analysis(facts), ensure_ascii=False, indent=2), encoding="utf-8")
    return target
