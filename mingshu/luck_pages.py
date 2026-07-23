"""Print-first pages for five-element preferences, luck cycles, and annual readings."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .luck_analysis import build_luck_analysis
from .element_styles import ELEMENT_COLOR_SCRIPT
from .page_numbering import page_offset_script


ANNUAL_CSS = r'''
.year-title{display:flex;align-items:flex-end;justify-content:space-between;margin-top:4px}.year-title h1{font:34px Calligraphy;margin:0;color:var(--ink)}.year-title p{font:9px BookSans;color:var(--gold);margin:0}.year-score{text-align:right}.year-score b{display:block;font:28px BookSerif;color:var(--jade)}.year-score span{font:7.5px BookSans;color:var(--gold)}.year-overlap{font:7.5px/1.45 BookSans;color:#5c554b;margin:5px 0 7px;padding:5px 8px;border-left:2px solid var(--gold);background:#faf5e9}.year-gods{display:grid;grid-template-columns:1fr 1fr;border-block:1px solid var(--gold)}.year-gods section{padding:7px 9px 6px;min-height:92px}.year-gods section+section{border-left:1px solid var(--line)}.year-gods small{font:7px BookSans;color:var(--gold)}.year-gods h2{font-size:11px;color:var(--jade);margin:2px 0 3px}.year-gods p,.year-gods em{display:block;font:7.1px/1.42 BookSans;color:#4e4941;margin:0;font-style:normal}.year-gods em{margin-top:3px;color:#776e61}.month-head{display:flex;justify-content:space-between;align-items:baseline;margin:7px 0 4px}.month-head h2{font-size:11px;color:var(--jade);margin:0}.month-head span{font:6.5px BookSans;color:var(--muted)}.month-rhythm{display:grid;grid-template-columns:repeat(12,1fr);gap:2px}.month-rhythm section{min-width:0;min-height:52px;padding:3px 1px;text-align:center;border:1px solid #ddd0b9;background:linear-gradient(to top,rgba(49,94,82,.16) calc((var(--month-score) - 25)*1.75%),rgba(250,245,233,.82) 0)}.month-rhythm small,.month-rhythm b,.month-rhythm i,.month-rhythm span{display:block}.month-rhythm small{font:5.8px BookSans;color:var(--muted)}.month-rhythm b{font-size:8px;margin:2px 0}.month-rhythm i{font:normal 6px BookSans;color:var(--gold)}.month-rhythm span{font:5.2px/1.15 BookSans;color:#5f584e;white-space:nowrap;overflow:hidden}.month-notes{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:4px}.month-notes span{font:6.2px/1.35 BookSans;color:#625a50;padding:4px 5px;background:#faf5e9}.month-notes b{display:block;color:var(--gold);font-weight:400}.year-evidence{display:grid;grid-template-columns:1.6fr 1fr;gap:7px;margin-top:7px}.relation-reading{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--gold)}.relation-reading section{padding:6px 7px;border-bottom:1px solid var(--line)}.relation-reading section+section{border-left:1px solid var(--line)}.relation-reading h2,.year-evidence aside h2{font-size:9px;color:var(--jade);margin:0 0 3px}.relation-reading p{font:6.7px/1.4 BookSans;color:#504b43;margin:0}.year-evidence aside{padding:6px 7px;border-top:1px solid var(--gold);background:#faf5e9}.year-evidence aside>span{display:block;font:6.4px/1.35 BookSans;color:#625a50;margin-bottom:3px}.year-evidence aside b{color:var(--gold);margin-right:4px}.annual-boundary{font:6.4px/1.35 BookSans;color:var(--muted);margin:6px 0 0}
'''

ANNUAL_CSS += r'''
.year-overlap{font-size:8.2px;padding:6px 9px;margin-block:6px 8px}.year-gods section{padding:9px 11px 8px;min-height:108px}.year-gods small{font-size:7.6px}.year-gods h2{font-size:12px;margin-block:3px 4px}.year-gods p,.year-gods em{font-size:7.8px;line-height:1.48}.month-head{margin-block:9px 5px}.month-head h2{font-size:12px}.month-head span{font-size:7px}.month-rhythm section{min-height:60px;padding:4px 1px}.month-rhythm small{font-size:6.3px}.month-rhythm b{font-size:9px}.month-rhythm i{font-size:6.5px}.month-rhythm span{font-size:5.8px}.month-notes span{font-size:6.8px;padding:5px 6px}.year-evidence{margin-top:9px}.relation-reading section{padding:8px}.relation-reading h2,.year-evidence aside h2{font-size:10px}.relation-reading p{font-size:7.4px;line-height:1.46}.year-evidence aside{padding:8px}.year-evidence aside>span{font-size:7px;line-height:1.42}.annual-boundary{font-size:6.8px;margin-top:7px}
'''

ANNUAL_CSS += r'''
.year-gods section{min-height:122px;padding:10px 12px}.year-gods small{font-size:8px}.year-gods h2{font-size:13px}.year-gods p,.year-gods em{font-size:8.6px;line-height:1.5}.month-rhythm section{min-height:64px}.month-rhythm small{font-size:6.7px}.month-rhythm b{font-size:9.5px}.month-rhythm i{font-size:7px}.month-rhythm span{font-size:6px}.month-notes span{font-size:7.2px;line-height:1.4}.relation-reading section{padding:9px}.relation-reading h2,.year-evidence aside h2{font-size:10.5px}.relation-reading p{font-size:8.2px;line-height:1.48}.year-evidence aside{padding:9px}.year-evidence aside>span{font-size:7.8px;line-height:1.45}.annual-boundary{font-size:7.2px}
'''

LUCK_V2_CSS = r'''
.heat-head,.cycle-heat section{grid-template-columns:52px repeat(3,minmax(0,1fr)) 32px;gap:10px}.heat-head{padding:6px 3px}.cycle-heat section{min-height:47px;padding:0 3px}.cycle-heat b{font-size:13px}.cycle-heat i{position:relative;height:22px;overflow:hidden;background:#faf6ec;border-color:#d9c9ad;display:grid;place-items:center}.cycle-heat i:before{content:'';position:absolute;left:0;top:0;bottom:0;width:calc(var(--v)*1%);background:linear-gradient(90deg,#d8ccb5,#c2d0c5)}.cycle-heat i span{position:relative;z-index:1;font:8.5px/20px BookSans;color:#3f4d47}.cycle-heat strong{text-align:center}.cycle-compare h1{margin-bottom:4px}.cycle-compare .method-note{font-size:8.2px;line-height:1.45;margin-top:8px;padding:7px 10px}
.cycle-heading{display:flex;justify-content:space-between;align-items:flex-end;margin-top:5px}.cycle-heading h1{font:38px Calligraphy;margin:0}.cycle-heading p{font:9px BookSans;color:var(--gold);margin:2px 0}.cycle-mark{text-align:right}.cycle-mark b{display:block;font:31px BookSerif;color:var(--jade)}.cycle-mark span{font:8px BookSans;color:var(--gold)}.cycle-lead{font:9.3px/1.6 BookSans;color:#514c44;margin:8px 0;padding:7px 10px;border-left:3px solid var(--gold);background:#faf5e9}.cycle-gods{display:grid;grid-template-columns:1fr 1fr;border-block:1px solid var(--gold)}.cycle-gods section{padding:9px 11px;min-height:118px}.cycle-gods section+section{border-left:1px solid var(--line)}.cycle-gods small{font:7.5px BookSans;color:var(--gold)}.cycle-gods h2{font-size:12px;color:var(--jade);margin:3px 0 5px}.cycle-gods p,.cycle-gods em{display:block;font:7.8px/1.48 BookSans;color:#504b43;margin:0;font-style:normal}.cycle-gods em{margin-top:4px;color:#776e61}.cycle-evidence{display:grid;grid-template-columns:1.55fr 1fr;gap:8px;margin-top:9px}.cycle-relations{border-top:1px solid var(--gold)}.cycle-relations section{padding:7px 8px;border-bottom:1px solid var(--line)}.cycle-relations h2,.cycle-evidence aside h2{font-size:10px;color:var(--jade);margin:0 0 3px}.cycle-relations p{font:7.4px/1.45 BookSans;color:#504b43;margin:0}.cycle-evidence aside{padding:8px 9px;border-top:1px solid var(--gold);background:#faf5e9}.cycle-evidence aside>span{display:block;font:7px/1.4 BookSans;color:#625a50;margin-bottom:5px}.cycle-evidence aside b{color:var(--gold);margin-right:4px}.cycle-source{font:7px/1.45 BookSans;color:var(--muted);margin:8px 0 0}
.cycle-timeline h1{margin-bottom:3px}.cycle-timeline .trend-chart{margin:0 0 5px}.phase-grid{display:grid;grid-template-columns:repeat(3,1fr);border-block:1px solid var(--gold)}.phase-grid section{min-height:145px;padding:10px}.phase-grid section+section{border-left:1px solid var(--line)}.phase-grid small{display:block;font:7px BookSans;color:var(--gold)}.phase-grid b{display:block;font:24px BookSerif;color:var(--jade);margin:5px 0}.phase-grid p{font:7.8px/1.5 BookSans;color:#504b43;margin:0}.phase-grid em{display:block;font:normal 6.8px/1.4 BookSans;color:var(--muted);margin-top:5px}.cycle-turns{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.cycle-turns section{padding:9px 11px;border-top:2px solid var(--gold);background:#faf5e9}.cycle-turns h2{font-size:11px;color:var(--jade);margin:0 0 4px}.cycle-turns p{font:7.7px/1.45 BookSans;color:#504b43;margin:0}.cycle-action{font:7.5px/1.5 BookSans;color:#625b50;margin:9px 0 0;padding-left:9px;border-left:2px solid var(--gold)}
.cycle-wuxing{margin:5px 0 7px;padding:7px 9px;background:#faf5e9;border-block:1px solid var(--line)}.cycle-wuxing-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px}.cycle-wuxing-head b{font-size:10.5px;color:var(--jade)}.cycle-wuxing-head span{font:6.8px BookSans;color:var(--muted)}.cycle-wuxing-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:7px}.cycle-wuxing-grid section{display:grid;grid-template-columns:18px 1fr;grid-template-rows:7px 12px;align-items:center;column-gap:4px;min-width:0}.cycle-wuxing-grid b{grid-row:1/3;font:15px Calligraphy}.cycle-wuxing-grid i{position:relative;height:7px;background:#e7ddca;overflow:hidden}.cycle-wuxing-grid i:after{content:'';position:absolute;inset-block:0;left:0;width:calc(var(--power)*1%);background:var(--element-color,var(--jade))}.cycle-wuxing-grid em{font:normal 6.8px BookSans;color:var(--muted);white-space:nowrap}.cycle-wuxing-grid .rise em{color:var(--jade)}.cycle-wuxing-grid .fall em{color:var(--red)}.cycle-wuxing-grid .木{--element-color:#315e52}.cycle-wuxing-grid .火{--element-color:#974238}.cycle-wuxing-grid .土{--element-color:#a77934}.cycle-wuxing-grid .金{--element-color:#7b756a}.cycle-wuxing-grid .水{--element-color:#557487}
.cycle-year-bridge h1{margin-bottom:15px}.bridge-steps{border-top:1px solid var(--gold)}.bridge-steps section{display:grid;grid-template-columns:52px 1fr;gap:15px;padding:17px 4px;border-bottom:1px solid var(--line)}.bridge-steps i{font:34px Calligraphy;color:var(--gold);font-style:normal;text-align:center}.bridge-steps h2{font-size:15px;color:var(--jade);margin:0 0 5px}.bridge-steps p{font:9.5px/1.65 BookSans;color:#504b43;margin:0}.cycle-year-bridge blockquote{font:14px/1.75 BookSerif;color:var(--jade);margin:20px 0 0;padding:12px 15px;border-left:3px solid var(--gold);background:#faf5e9}
.annual-divider{padding:0;background:#203b34;color:#f1e6ce}.annual-divider footer{color:#bda978}.annual-divider .chapter-frame h1{right:22%;top:44%;font-size:49px}.annual-divider .chapter-frame p{right:49%;top:25%}.annual-divider .chapter-frame i{right:72%;left:auto;bottom:auto;top:13%}
'''


def _e(value: object) -> str:
    return escape(str(value or ""))


def _polyline_chart(points: list[dict], *, active_year: int | None = None, compact: bool = False) -> str:
    width, height = 500, (168 if compact else 235)
    left, right, top, bottom = 38, 18, 22, (34 if compact else 48)
    inner_w, inner_h = width - left - right, height - top - bottom
    if not points:
        return ""
    x_step = inner_w / max(1, len(points) - 1)
    ymin, ymax = 30, 80

    def xy(index: int, score: float) -> tuple[float, float]:
        x = left + index * x_step
        y = top + (ymax - score) / (ymax - ymin) * inner_h
        return x, y

    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(i, float(p["score"])) for i, p in enumerate(points)))
    grids = []
    for tick in (40, 50, 60, 70):
        _, y = xy(0, tick)
        grids.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/><text x="4" y="{y+4:.1f}">{tick}</text>')
    labels, nodes = [], []
    for index, point in enumerate(points):
        x, y = xy(index, float(point["score"]))
        active = active_year is not None and int(point.get("year") or 0) == active_year
        label = point.get("axis") or point.get("name") or point.get("year")
        labels.append(f'<text class="x-label" x="{x:.1f}" y="{height-10}" text-anchor="middle">{_e(label)}</text>')
        nodes.append(f'<circle class="point {"active" if active else ""}" cx="{x:.1f}" cy="{y:.1f}" r="{6 if active else 4}"/><text class="value" x="{x:.1f}" y="{y-9:.1f}" text-anchor="middle">{_e(point["score"])}</text>')
    return f'''<svg class="trend-chart {'compact' if compact else ''}" viewBox="0 0 {width} {height}" role="img" aria-label="结构顺势度折线图"><title>结构顺势度折线图</title><g class="chart-grid">{''.join(grids)}</g><polyline class="trend-line" points="{path}"/>{''.join(nodes)}{''.join(labels)}</svg>'''


def _bridge_page(data: dict) -> str:
    pattern = data["preference"]["pattern"]
    tiaohou = data["preference"]["tiaohou"]
    return f"""<article class="page verso bridge-page" data-page="50"><header>格局 · 本章小结</header><p class="eyebrow">主候选、二级结构与职业倾向已经落到同一条力量路径</p><h1>从结构出发，进入喜忌取舍</h1><div class="bridge-list"><section><b>{_e(pattern['pattern_center']['name'])}</b><p>{_e(pattern['pattern_center']['state'])}</p></section><section><b>{_e(pattern['supporting']['name'])}</b><p>{_e(pattern['supporting']['state'])}</p></section><section><b>调候仍有独立次序</b><p>{_e(tiaohou.get('season'))}、{_e(tiaohou.get('climate'))}，优先参考{_e('、'.join(tiaohou.get('primary_gods') or []))}。下一章会把两套用神合看，但不会混成一个概念。</p></section></div><blockquote>喜忌不是给五行贴永久标签，而是判断某种力量在这张命盘里何时能解决问题、何时会把问题放大。</blockquote><footer>50</footer></article>"""


def _preference_intro() -> str:
    return """<article class="page recto chapter-divider" data-page="51"><div class="chapter-frame"><small>第八章</small><h1>五行喜忌</h1><p>合格局之用<br>参四时之需</p><i>先找两条路径的交点<br>再分五行与十干</i></div><footer>51</footer></article>"""


def _synthesis_page(data: dict) -> str:
    pref = data["preference"]
    pattern = pref["pattern"]
    gods = list(pref["tiaohou"].get("primary_gods") or [])
    return f"""<article class="page verso synthesis" data-page="52"><header>喜忌 · 总体取舍</header><p class="eyebrow">格局负责结构，调候负责气候；先分别判断，再寻找共同方向</p><h1>土金承压，壬己调候</h1><div class="axis-merge"><section><small>格局用神</small><h2>{_e(pattern['supporting']['name'])} · {_e(pattern['further_flow']['name'])}</h2><p>{_e(pattern['supporting']['state'])}</p></section><i>合看</i><section><small>调候用神</small><h2>{_e(' · '.join(gods))}</h2><p>{_e(pref['tiaohou'].get('season'))}气候{_e(pref['tiaohou'].get('climate'))}，先处理温度、湿度与承载。</p></section><div class="merge-core"><b>{_e(gods[0] if gods else '用')}</b><span>调候优先<br>结构合参</span></div></div><p class="synthesis-copy">{_e(pref['summary'])}</p><footer>52</footer></article>"""


def _elements_page(data: dict) -> str:
    rows = "".join(f'<section class="element {item["name"]}"><b>{_e(item["name"])}</b><span>{_e(item["level"])}</span><p>{_e(item["reason"])}</p></section>' for item in data["preference"]["elements"])
    headline = "，".join(f"{item['name']}{item['level']}" for item in data["preference"]["elements"][:3])
    return f"""<article class="page recto elements" data-page="53"><header>喜忌 · 五行总表</header><p class="eyebrow">同一五行内部仍有阴阳差别，五行表只给第一层方向</p><h1>{_e(headline)}</h1><div class="element-list">{rows}</div><p class="boundary">任何五行都不是永久的好或坏。真正进入大运流年时，还要看具体天干地支、所在位置，以及与原盘形成什么关系。</p><footer>53</footer></article>"""


def _stems_page(data: dict) -> str:
    stems = data["preference"]["stems"]
    rows = "".join(f'<section class="stem {item["tone"]}"><b>{_e(item["name"])}</b><em>{_e(item["element"])}</em><span>{_e(item["tone"])}</span><p>{_e(item["role"])}</p></section>' for item in stems)
    top = sorted(stems, key=lambda item: item.get("total", 0), reverse=True)[:3]
    note = "；".join(f"{item['name']}：{item['role']}" for item in top)
    return f"""<article class="page verso stems" data-page="54"><header>喜忌 · 十天干细分</header><p class="eyebrow">甲乙、庚辛、壬癸不能只按同一五行处理</p><h1>十个天干，各有用法</h1><div class="stem-grid">{rows}</div><div class="stem-note"><b>本盘较优先的三项</b><p>{_e(note)}。进入具体岁运时仍要核对地支与冲合刑害。</p></div><footer>54</footer></article>"""


def _locations_page(data: dict) -> str:
    pref = data["preference"]
    pattern = pref["pattern"]
    gods = "、".join(pref["tiaohou"].get("primary_gods") or [])
    return f"""<article class="page recto locations" data-page="55"><header>喜忌 · 原盘状态</header><p class="eyebrow">先看所需力量是否已经存在，再看它是否受制或过量</p><h1>所需力量，有的已透，有的仍藏</h1><div class="location-flow"><section class="present"><b>{_e(gods)}</b><span>调候优先</span><p>{_e(pref['summary'])}</p></section><section class="hidden"><b>{_e(pattern['supporting']['name'])}</b><span>格局承接</span><p>{_e(pattern['supporting']['state'])}</p></section><section class="present"><b>{_e(pattern['further_flow']['name'])}</b><span>扶助日主</span><p>{_e(pattern['further_flow']['state'])}</p></section><section class="tension"><b>{_e(pattern['caution']['name'])}</b><span>需要节制</span><p>{_e(pattern['caution']['state'])}</p></section></div><footer>55</footer></article>"""


def _preference_close(data: dict) -> str:
    best = [item for item in data["preference"]["stems"] if item.get("tone") in {"优先", "有助"}]
    names = "、".join(item["name"] for item in best[:5])
    return f"""<article class="page verso preference-close" data-page="56"><header>喜忌 · 阅读结论</header><p class="eyebrow">把五行喜忌转成可以观察的现实条件</p><h1>所喜，是让结构运行得更顺</h1><div class="principles"><section><i>一</i><div><h2>先看是否解决原盘问题</h2><p>本盘较优先参考{names}，它们分别承担调候、承压、扶身或流通的作用；价值来自解决具体问题。</p></div></section><section><i>二</i><div><h2>再看是否形成新的拉扯</h2><p>即使是所喜力量，若参与冲刑、形成过强一气，也会带来调整成本，不能只看一个字下结论。</p></div></section><section><i>三</i><div><h2>最后看现实选择怎样承接</h2><p>岁运提供的是环境主调。工作方式、关系边界和长期投入，决定这股力量最终如何被使用。</p></div></section></div><p class="method-note">{_e(data['method']['description'])}</p><footer>56</footer></article>"""


def _luck_intro() -> str:
    return """<article class="page recto chapter-divider" data-page="57"><div class="chapter-frame"><small>第九章</small><h1>大运流年</h1><p>十年观其势<br>一年察其变</p><i>先比较九步大运<br>再走入每一个年份</i></div><footer>57</footer></article>"""


def _overall_chart_page(data: dict) -> str:
    points = [{"name": item["name"], "axis": item["name"], "score": item["score"]} for item in data["cycles"]]
    high = max(data["cycles"], key=lambda item: item["score"])
    low = min(data["cycles"], key=lambda item: item["score"])
    return f"""<article class="page verso overall-trend" data-page="58"><header>大运 · 总体走势</header><p class="eyebrow">九步大运使用同一套格局、调候与原盘关系标准比较</p><h1>走势有峰谷，但不是单线吉凶</h1>{_polyline_chart(points)}<div class="trend-reading"><section><b>相对高点 · {_e(high['name'])}</b><p>{_e(high['headline'])} 这一阶段与本盘所需力量的配合相对较多。</p></section><section><b>相对低点 · {_e(low['name'])}</b><p>{_e(low['headline'])} 需要更重视节奏、边界和现实承接。</p></section></div><footer>58</footer></article>"""


def _heatmap_page(data: dict) -> str:
    rows = []
    for cycle in data["cycles"]:
        cells = "".join(f'<i style="--v:{cycle["components"][key]}"><span>{cycle["components"][key]}</span></i>' for key in ("pattern", "climate", "relations"))
        rows.append(f'<section><b>{_e(cycle["name"])}</b>{cells}<strong>{cycle["score"]}</strong></section>')
    return f"""<article class="page recto cycle-compare" data-page="59"><header>大运 · 三层比较</header><p class="eyebrow">同一步大运，可能在格局、调候和作用关系上表现不同</p><h1>把综合分拆开来看</h1><div class="heat-head"><b>大运</b><span>格局</span><span>调候</span><span>关系</span><strong>综合</strong></div><div class="cycle-heat">{''.join(rows)}</div><p class="method-note">{_e(data['method']['cycle_formula'])} 分数越高，只表示与本书采用的喜忌结构更顺，不保证具体事件。</p><footer>59</footer></article>"""


def _cycle_god_cards(cycle: dict) -> str:
    return "".join(
        f'''<section><small>{_e(item['layer'])} · {_e(item['god'])}</small><h2>{_e(item['domain'])}</h2><p>{_e(item['use'])}</p><em>{_e(item['watch'])}</em></section>'''
        for item in cycle.get("ten_god_readings") or []
    )


def _cycle_relation_cards(cycle: dict) -> str:
    details = list(cycle.get("relation_details") or [])
    if not details:
        return '<section><h2>与原局关系较少</h2><p>这一运没有新增的显著冲合，十年主题主要由运干、运支十神与格局、调候的配合决定。</p></section>'
    return "".join(
        f'<section><h2>{_e(item["title"])}</h2><p>{_e(item["reading"])}</p></section>'
        for item in details[:3]
    )


def _cycle_shensha(cycle: dict) -> str:
    items = list(cycle.get("shensha") or [])
    if not items:
        return '<span>本运没有新增的主要神煞，以十神、用神和原局作用为主。</span>'
    return "".join(f'<span><b>{_e(item["name"])}</b>{_e(item["tagline"])}</span>' for item in items[:5])


def _cycle_wuxing_shift(cycle: dict) -> str:
    shift = cycle.get("wuxing_shift") or {}
    cells = []
    for item in shift.get("series") or []:
        delta = float(item.get("delta") or 0)
        direction = "rise" if delta > 0.05 else "fall" if delta < -0.05 else "level"
        delta_label = f"{delta:+.1f}" if direction != "level" else "±0.0"
        cells.append(
            f'''<section class="{_e(item.get('name'))} {direction}" title="原局 {_e(item.get('baseline'))}%"><b>{_e(item.get('name'))}</b><i style="--power:{_e(item.get('adjusted'))}"></i><em>{_e(item.get('adjusted'))}% · {delta_label}</em></section>'''
        )
    return (
        '<div class="cycle-wuxing">'
        '<div class="cycle-wuxing-head"><b>本运加入后的五行力量</b>'
        '<span>占比 · 较原局增减（百分点）</span></div>'
        f'<div class="cycle-wuxing-grid">{"".join(cells)}</div></div>'
    )


def _cycle_profile_page(cycle: dict, page_number: int) -> str:
    parity = "recto" if page_number % 2 else "verso"
    return f"""<article class="page {parity} cycle-profile" data-page="{page_number}"><header>大运分析 · {_e(cycle['name'])}</header><p class="eyebrow">{_e(cycle['start_year'])}—{_e(cycle['end_year'])} · 约{_e(cycle['age_start'])}岁起</p><div class="cycle-heading"><div><h1>{_e(cycle['name'])}大运</h1><p>{_e(cycle['gan_ten_god'])} · {_e(cycle['zhi_ten_god'])}</p></div><div class="cycle-mark"><b>{cycle['score']}</b><span>{_e(cycle['band'])}</span></div></div><p class="cycle-lead">{_e(cycle['headline'])} {_e(cycle['stem_note'])}</p><div class="cycle-gods">{_cycle_god_cards(cycle)}</div><div class="cycle-evidence"><div class="cycle-relations">{_cycle_relation_cards(cycle)}</div><aside><h2>本运神煞</h2>{_cycle_shensha(cycle)}</aside></div><p class="cycle-source">本页直接采用原排盘脚本给出的运干、运支十神、与原局成立的干支关系及神煞，再与前章格局用神和调候用神合参。</p><footer>{page_number}</footer></article>"""


def _cycle_timeline_page(cycle: dict, page_number: int) -> str:
    points = [{"year": item["year"], "axis": str(item["year"])[-2:], "score": item["score"]} for item in cycle["years"]]
    peaks = "、".join(f'{item["year"]}年' for item in cycle["peak_years"])
    turns = "、".join(f'{item["year"]}年' for item in cycle["turning_years"])
    parity = "recto" if page_number % 2 else "verso"
    phases = "".join(
        f'''<section><small>{_e(item['label'])} · {_e(item['years'])}</small><b>{item['average']}</b><p>{_e(item['high_year'])}年{_e(item['high_ganzhi'])}在本段相对较顺；{_e(item['focus'])}</p><em>{_e(item['dense_year'])}年关系最密集，共{_e(item['dense_relations'])}组。</em></section>'''
        for item in cycle.get("phases") or []
    )
    support = "；".join(cycle.get("support") or []) or "没有额外形成明显的补益组合"
    movement = "；".join(cycle.get("movement") or []) or "没有额外形成明显的冲刑穿破"
    return f"""<article class="page {parity} cycle-timeline" data-page="{page_number}"><header>大运分析 · {_e(cycle['name'])}十年节奏</header><p class="eyebrow">大运给出十年背景，流年决定每一年的具体起伏</p><h1>一运十年，岁岁不同</h1>{_polyline_chart(points, compact=True)}{_cycle_wuxing_shift(cycle)}<div class="phase-grid">{phases}</div><div class="cycle-turns"><section><h2>较易发挥</h2><p>{_e(peaks)}。{_e(support)}。</p></section><section><h2>需要调整</h2><p>{_e(turns)}。{_e(movement)}。</p></section></div><p class="cycle-action">{_e(cycle['action'])} 折线只比较本运内部十个流年的结构配合；五行一栏显示加入本运干支后，相对原局的力量变化。两者都不代替现实条件。</p><footer>{page_number}</footer></article>"""


def _cycle_to_year_bridge() -> str:
    return """<article class="page verso cycle-year-bridge" data-page="78"><header>大运分析 · 章节收束</header><p class="eyebrow">大运是十年背景，流年是当年触发，两者必须放在一起读</p><h1>先定底色，再看当年怎样落笔</h1><div class="bridge-steps"><section><i>一</i><div><h2>大运给出长期主题</h2><p>看运干、运支十神是否补足格局与调候所需，以及它们怎样改变原局连接方式。</p></div></section><section><i>二</i><div><h2>流年把某个议题推到前台</h2><p>同一大运中的十年不会完全相同，需要继续核对当年十神、冲合刑害、神煞与整柱重复。</p></div></section><section><i>三</i><div><h2>流月说明一年内部的节奏</h2><p>十二个月只作当年内部比较，帮助安排推进、复盘与留出余地的时间。</p></div></section></div><blockquote>以下进入流年分析：每个年份都带着所在大运的背景，不把流年从十年环境中单独抽离。</blockquote><footer>78</footer></article>"""


def _annual_intro() -> str:
    return """<article class="page recto chapter-divider annual-divider" data-page="79"><div class="chapter-frame"><small>大运流年 · 逐年细读</small><h1>流年分析</h1><p>岁岁有别<br>层层相参</p><i>大运底色 · 流年十神<br>原局关系 · 神煞 · 流月</i></div><footer>79</footer></article>"""


def _month_rhythm(year: dict) -> str:
    cells = []
    for month in year.get("months") or []:
        score = int(month.get("score") or 50)
        cells.append(
            f'''<section style="--month-score:{score}"><small>{_e(month.get('solar_month'))}月</small><b>{_e(month.get('ganzhi'))}</b><i>{score}</i><span>{_e(month.get('focus'))}</span></section>'''
        )
    return f'<div class="month-rhythm">{"".join(cells)}</div>'


def _month_names(items: list[dict]) -> str:
    return "、".join(f"{item.get('solar_month')}月{item.get('ganzhi')}" for item in items)


def _year_god_cards(year: dict) -> str:
    return "".join(
        f'''<section><small>{_e(item['layer'])} · {_e(item['god'])}</small><h2>{_e(item['domain'])}</h2><p>{_e(item['use'])}</p><em>{_e(item['watch'])}</em></section>'''
        for item in year.get("ten_god_readings") or []
    )


def _year_relation_cards(year: dict) -> str:
    details = list(year.get("relation_details") or [])
    if not details:
        return '<section><h2>关系密度较低</h2><p>这一年没有新增的显著冲合，重点放在流年十神与所在大运的组合。</p></section>'
    return "".join(f'<section><h2>{_e(item["title"])}</h2><p>{_e(item["reading"])}</p></section>' for item in details[:2])


def _year_shensha(year: dict) -> str:
    items = list(year.get("shensha") or [])
    if not items:
        return '<span>本年没有新增的主要神煞标签，仍以十神和冲合关系为主。</span>'
    return "".join(f'<span><b>{_e(item["name"])}</b>{_e(item["tagline"])}</span>' for item in items[:4])


def _year_page(year: dict, cycle: dict, page_number: int) -> str:
    parity = "recto" if page_number % 2 else "verso"
    overlap = " ".join(year.get("overlap_notes") or [])
    return f"""<article class="page {parity} year-page" data-page="{page_number}"><header>流年 · {_e(year['cycle_name'])}大运</header><p class="eyebrow">{_e(year['year'])} · {_e(year['ganzhi'])} · {_e(year['age'])}岁</p><div class="year-title"><div><h1>{_e(year['ganzhi'])}年</h1><p>{_e(year['gan_ten_god'])} · {_e(year['zhi_ten_god'])}</p></div><div class="year-score"><b>{year['score']}</b><span>{_e(year['band'])}</span></div></div><p class="year-overlap">{_e(overlap)}</p><div class="year-gods">{_year_god_cards(year)}</div><div class="month-head"><h2>十二月内部节奏</h2><span>分数只作同年月份之间的结构比较</span></div>{_month_rhythm(year)}<div class="month-notes"><span><b>关系较密集</b>{_e(_month_names(year.get('active_months') or []))}</span><span><b>相对可用</b>{_e(_month_names(year.get('supportive_months') or []))}</span><span><b>宜留余地</b>{_e(_month_names(year.get('adjustment_months') or []))}</span></div><div class="year-evidence"><div class="relation-reading">{_year_relation_cards(year)}</div><aside><h2>本年神煞</h2>{_year_shensha(year)}</aside></div><p class="annual-boundary">流月以节气交接为界，并非公历每月一日整齐切换。页面描述的是结构侧重，不保证具体事件。</p><footer>{page_number}</footer></article>"""


def render_luck_html(facts: dict) -> str:
    data = build_luck_analysis(facts)
    pages = [_bridge_page(data), _preference_intro(), _synthesis_page(data), _elements_page(data), _stems_page(data), _locations_page(data), _preference_close(data), _luck_intro(), _overall_chart_page(data), _heatmap_page(data)]
    cycle_by_id = {item["id"]: item for item in data["cycles"]}
    page_number = 60
    for cycle in data["cycles"]:
        pages.append(_cycle_profile_page(cycle, page_number))
        pages.append(_cycle_timeline_page(cycle, page_number + 1))
        page_number += 2
    pages.append(_cycle_to_year_bridge())
    pages.append(_annual_intro())
    page_number = 80
    for year in data["years"]:
        pages.append(_year_page(year, cycle_by_id[year["cycle_id"]], page_number))
        page_number += 1
    if len(pages) % 2:
        raise ValueError("luck chapter must contain an even number of A5 pages")
    spreads = "".join(f'<section class="spread">{pages[index]}{pages[index+1]}</section>' for index in range(0, len(pages), 2))
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 五行喜忌与大运流年</title><style>{_css()}{ANNUAL_CSS}{LUCK_V2_CSS}</style></head><body><main>{spreads}</main>{ELEMENT_COLOR_SCRIPT}{page_offset_script(10)}</body></html>'''


def _css() -> str:
    return r'''
@font-face{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}@font-face{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}@font-face{font-family:Calligraphy;src:url('../../../assets/fonts/MaShanZheng-Regular.ttf')}@page{size:A4 landscape;margin:0}:root{--paper:#f5eddd;--paper2:#fbf7ec;--ink:#292821;--muted:#746b5e;--line:#d5c19d;--gold:#a77934;--jade:#315e52;--red:#974238;--water:#557487}*{box-sizing:border-box}body{margin:0;background:#242422;color:var(--ink);font-family:BookSerif,serif}main{padding:28px 0 70px}.spread{display:flex;width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;filter:drop-shadow(0 14px 24px #111)}.page{position:relative;flex:0 0 50%;aspect-ratio:148/210;padding:7.5% 8%;overflow:hidden;background:linear-gradient(145deg,var(--paper2),var(--paper));contain:layout paint}.spread>.page:first-child:after{content:'';position:absolute;right:0;inset-block:0;width:1px;background:#cbbfae}header{font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px}.recto header{text-align:right}h1{font-size:29px;line-height:1.24;margin:7px 0 10px;font-weight:500}h2{font-weight:500}.eyebrow{font:9px BookSans;color:var(--gold);letter-spacing:.09em;margin:18px 0 0}footer{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#887d6b}.recto footer{text-align:right}.method-note,.boundary{font:9.5px/1.65 BookSans;color:var(--jade);padding:10px 13px;border-left:3px solid var(--gold);background:#faf5e9}.chapter-divider{padding:0;background:#203b34;color:#f1e6ce}.chapter-frame{position:absolute;inset:8%;border:1px solid #b89a60;outline:1px solid rgba(184,154,96,.45);outline-offset:-9px}.chapter-frame small,.chapter-frame h1,.chapter-frame p,.chapter-frame i{position:absolute;writing-mode:vertical-rl;white-space:nowrap;margin:0}.chapter-frame small{right:10%;bottom:10%;font:11px BookSans;letter-spacing:.25em;color:#c9ac73}.chapter-frame h1{right:22%;top:44%;transform:translateY(-50%);font:49px/1 Calligraphy;letter-spacing:.14em;font-weight:400}.chapter-frame p{right:48%;top:27%;font:20px/1.8 BookSerif;color:#e4d2ae;letter-spacing:.14em}.chapter-frame i{right:72%;top:13%;font:normal 10px/1.8 BookSans;color:#b9ad91;letter-spacing:.08em}.chapter-divider footer{color:#bda978}.bridge-list{margin-top:22px;border-top:1px solid var(--gold)}.bridge-list section{padding:18px 4px;border-bottom:1px solid var(--line)}.bridge-list b{font-size:16px;color:var(--jade)}.bridge-list p{font:10.3px/1.75 BookSans;color:#504b43;margin:5px 0 0}.bridge-page blockquote{font:14px/1.75 BookSerif;color:var(--jade);margin:22px 0 0;padding:12px 16px;border-left:3px solid var(--gold);background:#faf5e9}.axis-merge{display:grid;grid-template-columns:1fr 55px 1fr;position:relative;margin:22px 0 18px}.axis-merge section{min-height:210px;padding:18px;border:1px solid var(--line);background:#faf5e9}.axis-merge section small{font:9px BookSans;color:var(--gold);letter-spacing:.12em}.axis-merge h2{font-size:20px;margin:14px 0}.axis-merge section p{font:10px/1.7 BookSans;color:#504b43}.axis-merge>i{align-self:center;text-align:center;font:21px Calligraphy;color:var(--gold)}.merge-core{position:absolute;left:50%;top:165px;transform:translate(-50%,-50%);width:84px;height:84px;border-radius:50%;background:#203b34;color:#f1e6ce;border:5px solid var(--paper);text-align:center;padding-top:10px}.merge-core b{display:block;font:29px Calligraphy}.merge-core span{font:7px/1.3 BookSans}.synthesis-copy{font:10.3px/1.75 BookSans;color:#4e4941;margin:0;padding:14px;border-top:1px solid var(--gold);border-bottom:1px solid var(--gold)}.element-list{margin-top:20px;border-top:1px solid var(--gold)}.element-list section{display:grid;grid-template-columns:50px 80px 1fr;align-items:center;gap:14px;min-height:86px;border-bottom:1px solid var(--line)}.element-list b{font:30px Calligraphy}.element-list span{font:10px BookSans;color:var(--gold)}.element-list p{font:9.6px/1.6 BookSans;color:#504b43}.element-list .金 b{color:#7b756a}.element-list .土 b{color:#a77934}.element-list .木 b{color:#315e52}.element-list .水 b{color:#557487}.element-list .火 b{color:#974238}.stems h1{margin-bottom:15px}.stem-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 18px;border-top:1px solid var(--gold)}.stem-grid section{display:grid;grid-template-columns:35px 20px 52px 1fr;align-items:center;min-height:70px;border-bottom:1px solid var(--line)}.stem-grid b{font:25px Calligraphy}.stem-grid em{font:normal 8px BookSans;color:var(--muted)}.stem-grid span{font:8px BookSans;color:var(--gold)}.stem-grid p{font:8.5px/1.4 BookSans;color:#504b43}.stem-grid .优先 b,.stem-grid .有助 b{color:var(--jade)}.stem-grid .谨慎 b{color:var(--red)}.stem-note{margin-top:18px;padding:13px 15px;background:#faf5e9;border-left:3px solid var(--gold)}.stem-note b{font-size:13px}.stem-note p{font:9.5px/1.6 BookSans;margin:5px 0 0}.location-flow{margin-top:22px;display:grid;grid-template-columns:1fr 1fr;gap:15px}.location-flow section{min-height:180px;padding:17px;border:1px solid var(--line);background:#faf5e9}.location-flow b{display:block;font:26px Calligraphy;color:var(--jade)}.location-flow span{font:9px BookSans;color:var(--gold)}.location-flow p{font:9.6px/1.7 BookSans;color:#504b43;margin:8px 0 0}.location-flow .tension b{color:var(--red)}.principles{border-top:1px solid var(--gold);margin-top:22px}.principles section{display:grid;grid-template-columns:55px 1fr;gap:15px;padding:20px 0;border-bottom:1px solid var(--line)}.principles i{font:38px Calligraphy;color:var(--gold);font-style:normal;text-align:center}.principles h2{font-size:16px;margin:0 0 6px}.principles p{font:10px/1.7 BookSans;color:#504b43;margin:0}.preference-close .method-note{margin-top:20px}.trend-chart{width:100%;height:auto;display:block;margin:12px 0 8px}.chart-grid line{stroke:#d9ccb4;stroke-width:1}.chart-grid text,.trend-chart text{font:9px BookSans;fill:#756b5d}.trend-line{fill:none;stroke:var(--jade);stroke-width:3}.point{fill:var(--paper2);stroke:var(--gold);stroke-width:2}.point.active{fill:var(--red);stroke:var(--red)}.value{font-size:9px;fill:var(--gold)}.x-label{font-size:8px}.trend-reading{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:10px}.trend-reading section{padding:14px;border:1px solid var(--line);background:#faf5e9}.trend-reading b{font-size:13px;color:var(--jade)}.trend-reading p{font:9px/1.6 BookSans;color:#504b43}.heat-head,.cycle-heat section{display:grid;grid-template-columns:70px repeat(3,1fr) 54px;gap:8px;align-items:center}.heat-head{font:9px BookSans;color:var(--muted);text-align:center;padding:8px 0;border-bottom:1px solid var(--gold)}.cycle-heat section{min-height:49px;border-bottom:1px solid var(--line)}.cycle-heat b{font-size:14px}.cycle-heat i{display:block;height:20px;background:linear-gradient(90deg,#e8ddc8 calc(var(--v)*1%),transparent 0);border:1px solid #e0d3bd;text-align:center;font-style:normal}.cycle-heat i span{font:8px/18px BookSans}.cycle-heat strong{font:13px BookSans;color:var(--jade);text-align:right}.cycle-compare .method-note{margin-top:16px}.cycle-score{display:grid;grid-template-columns:70px 1fr;grid-template-rows:auto auto;margin:14px 0 0;padding:10px 14px;border-left:3px solid var(--gold);background:#faf5e9}.cycle-score b{grid-row:1/3;font:42px BookSerif;color:var(--jade)}.cycle-score span{font:9px BookSans;color:var(--gold)}.cycle-score p{font:10px/1.5 BookSans;margin:3px 0}.cycle-page .trend-chart{margin-top:3px}.cycle-copy{border-top:1px solid var(--gold)}.cycle-copy section{display:grid;grid-template-columns:95px 1fr;gap:12px;padding:11px 0;border-bottom:1px solid var(--line)}.cycle-copy h2{font-size:13px;color:var(--jade);margin:0}.cycle-copy p{font:9px/1.55 BookSans;color:#504b43;margin:0}.annual-divider{padding:0;background:#ede2ce}.annual-frame{position:absolute;inset:8%;border:1px solid var(--gold);padding:15% 12%}.annual-frame small{font:10px BookSans;color:var(--gold);letter-spacing:.18em}.annual-frame h1{font:62px Calligraphy;color:var(--jade);margin:18% 0 9%}.annual-frame p{font:19px/1.8 BookSerif}.annual-frame i{display:block;margin-top:18%;padding-top:16px;border-top:1px solid var(--line);font:normal 10px/1.7 BookSans;color:var(--muted)}.year-title{display:flex;align-items:flex-end;justify-content:space-between;margin-top:8px}.year-title h1{font:39px Calligraphy;margin:0;color:var(--ink)}.year-title p{font:10px BookSans;color:var(--gold);margin:0}.year-score{text-align:right}.year-score b{display:block;font:31px BookSerif;color:var(--jade)}.year-score span{font:8px BookSans;color:var(--gold)}.year-page .trend-chart{margin:2px 0 4px}.year-copy{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--gold)}.year-copy section{min-height:106px;padding:11px 12px;border-bottom:1px solid var(--line)}.year-copy section:nth-child(odd){border-right:1px solid var(--line)}.year-copy h2{font-size:12px;color:var(--jade);margin:0 0 5px}.year-copy p{font:8.6px/1.52 BookSans;color:#504b43;margin:0}.annual-boundary{font:7.7px/1.45 BookSans;color:var(--muted);margin:9px 0 0}.luck-close{background:linear-gradient(145deg,#efe4d0,#faf5e9)}.closing-copy{margin-top:26px;padding:22px;border-block:1px solid var(--gold)}.closing-copy p{font:13px/2 BookSerif;margin:0 0 18px}.luck-close blockquote{font:27px Calligraphy;color:var(--jade);margin:55px 0 0;text-align:center}@media print{body{background:#fff}main{padding:0}.spread{width:296mm;height:210mm;margin:0;filter:none;break-after:page}.page{width:148mm;height:210mm}}
'''


def write_luck_sample(facts: dict, html_path: str | Path, data_path: str | Path | None = None) -> Path:
    target = Path(html_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_luck_html(facts), encoding="utf-8")
    if data_path is not None:
        data_target = Path(data_path)
        data_target.parent.mkdir(parents=True, exist_ok=True)
        data_target.write_text(json.dumps(build_luck_analysis(facts), ensure_ascii=False, indent=2), encoding="utf-8")
    return target
