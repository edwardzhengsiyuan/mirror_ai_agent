"""Print-first special-topic chapter pages."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from .element_styles import ELEMENT_COLOR_SCRIPT
from .page_numbering import page_offset_script

from .topics_analysis import build_topics_analysis


TOPICS_V2_CSS = r'''
.chapter-frame h1{right:34%;top:12%;font-size:56px;letter-spacing:.08em}.chapter-frame p{right:59%;font-size:19px}.topic-blank{padding:0;background:var(--paper)}
'''


def _e(value: object) -> str:
    return escape(str(value or ""))


def _page(number: int, section: str, eyebrow: str, title: str, body: str, *, cls: str = "") -> str:
    side = "recto" if number % 2 else "verso"
    return f'''<article class="page {side} {cls}" data-page="{number}"><header>{_e(section)}</header><p class="eyebrow">{_e(eyebrow)}</p><h1>{_e(title)}</h1>{body}<footer>{number}</footer></article>'''


def _divider(number: int, chapter: str, title: str, lines: str, note: str) -> str:
    return f'''<article class="page recto chapter-divider" data-page="{number}"><div class="chapter-frame"><small>{_e(chapter)}</small><h1>{_e(title)}</h1><p>{lines}</p><i>{note}</i></div><footer>{number}</footer></article>'''


def _cards(items: list[dict], keys: tuple[str, str, str]) -> str:
    return '<div class="cards">' + ''.join(
        f'<section><small>{_e(item[keys[0]])}</small><h2>{_e(item[keys[1]])}</h2><p>{_e(item[keys[2]])}</p></section>'
        for item in items
    ) + '</div>'


def _list(items: list[str], cls: str = "clean-list") -> str:
    return f'<ul class="{cls}">' + ''.join(f'<li>{_e(item)}</li>' for item in items) + '</ul>'


def _intro_page() -> str:
    return _page(170, "大运流年 · 章节收束", "时间的变化已经逐年展开，接下来回到生活本身", "从岁运曲线，走向七项人生专题", '''
    <div class="closing-grid"><section><b>原盘回答</b><p>你更习惯怎样思考、行动、建立关系，并在什么地方容易出现拉扯。</p></section><section><b>岁运回答</b><p>不同阶段会把哪些主题推到前台，何时更适合扩展，何时更需要调整。</p></section><section><b>专题回答</b><p>把前面的结构放回事业、学习、感情、健康与家庭，不再重复术语。</p></section></div>
    <blockquote>命盘并不替你选择；它更像一张结构图，帮助你看见选择所需的条件。</blockquote>''', cls="topics-bridge")


def _personality_pages(d: dict) -> list[str]:
    p = d["personality"]
    pages = [_divider(161, "第十章", "专项报告", "七个主题<br>同一张原盘", "从生活问题出发<br>每一条都回到具体证据")]
    pages.append(_page(162, "专项 · 性格", "日主给出内核，五行与十神决定它怎样被使用", p["title"], f'<p class="lead">{_e(p["summary"])}</p>' + _cards(p["layers"], ("name", "evidence", "reading"))))
    pages.append(_page(163, "性格 · 力量的两面", "优势与负担往往来自同一股力量", "什么时候发挥得好，什么时候容易过量", f'<div class="duality"><section><h2>容易成为优势</h2>{_list(p["strengths"])}</section><section><h2>需要留意</h2>{_list(p["watch"])}</section></div><p class="note">这不是给性格贴标签，而是帮助你识别自己在不同压力水平下会怎样变化。</p>'))
    layers = p["layers"]
    pages.append(_page(164, "性格 · 决策方式", "现实结果与独立判断同时存在", "先把选择变成可以比较的条件", f'''<div class="decision-flow"><section><b>01</b><h2>{_e(layers[2]['name'])}</h2><p>{_e(layers[2]['reading'])}</p></section><i>→</i><section><b>02</b><h2>{_e(layers[1]['name'])}</h2><p>{_e(layers[1]['reading'])}</p></section><i>→</i><section><b>03</b><h2>落到行动</h2><p>把兴趣、回报、时间与退出条件写下来，再决定是否投入。</p></section></div><div class="quote-card">真正适合你的决定，通常既保留研究空间，也能说明最后要交付什么。</div>'''))
    pages.append(_page(165, "性格 · 与人相处", "热心、推进和边界感需要同时出现", "愿意承担，但不必把所有事都接过来", '''<div class="people-map"><section><b>刚认识时</b><p>反应快、愿意推进，容易给人可靠而有行动力的印象。</p></section><section><b>熟悉之后</b><p>会显露独立研究和坚持自己方法的一面，并不喜欢被过度干预。</p></section><section><b>压力增大时</b><p>可能加速、亲自上手，甚至替别人完成；这时最需要重新分工。</p></section><section><b>更舒服的关系</b><p>彼此说清目标、投入和边界，允许各自保留独立判断。</p></section></div>'''))
    return pages


def _career_pages(d: dict) -> list[str]:
    c = d["career"]
    pages = [_page(166, "专项 · 事业", "格局候选只作参考，更重要的是目标、方法与支持怎样形成工作链条", c["title"], f'<p class="lead">{_e(c["summary"])}</p>' + _cards(c["structure"], ("step", "gods", "reading")), cls="section-open")]
    pages.append(_page(167, "事业 · 工作结构", "职业名会变，能力链条更值得长期经营", "从专业方法，到成果，再到真实交换", '''<div class="career-chain"><section><b>研究</b><span>偏印</span><p>找到自己的问题意识和方法。</p></section><i>→</i><section><b>表达</b><span>食神·伤官</span><p>形成产品、流程、内容或方案。</p></section><i>→</i><section><b>兑现</b><span>正财·偏财</span><p>进入客户、市场和长期资源循环。</p></section></div><p class="note">原盘的食伤主要藏在地支：能力并非没有，而是更需要靠作品和持续交付被看见。</p>'''))
    pages.append(_page(168, "事业 · 适配场景", "判断一份工作是否合适，先看它有没有完整闭环", "四类岗位，只是同一条能力链的不同入口", _cards(c["roles"], ("name", "fit", "fit"))))
    pages.append(_page(169, "事业 · 用神落地", "格局需要承压与扶身，调候需要降温与湿土培金", "职业发展不是追某个行业，而是补齐四个条件", '''<div class="useful-grid"><section><b>己土 · 方法与承接</b><p>把压力转成流程、知识体系和稳定支持，不让每一次任务都从头硬扛。</p></section><section><b>壬水 · 降温与改进</b><p>保留观察、沟通和调整空间，用数据与复盘处理高压，而不是只靠加速。</p></section><section><b>金 · 自主与边界</b><p>明确权限、完成标准和不可长期透支的底线，补足日主的执行底气。</p></section><section><b>七杀 · 目标与责任</b><p>让要求与资源匹配：目标越重要，越要有清楚的责任人、时限和风险预案。</p></section></div>'''))
    pages.append(_page(170, "事业 · 大运节奏", "分数表示与本书采用结构的相对配合，不等于事业成败", "九步大运中的工作重心", _cycle_bars(c["cycles"])))
    best = c["best"]
    demanding = c["demanding"]
    pages.append(_page(171, "事业 · 行动建议", "顺势期扩大成果，调整期收紧边界", "不要只问何时走运，要问届时该准备什么", f'''<div class="timing"><section><h2>较适合扩展</h2>{_list([f"{x['name']}（{x['start_year']}—{x['end_year']}）：{x['headline']}" for x in best])}</section><section><h2>更需要调整</h2>{_list([f"{x['name']}（{x['start_year']}—{x['end_year']}）：{x['headline']}" for x in demanding])}</section></div>{_list(c['boundaries'], 'rules')}'''))
    return pages


def _cycle_bars(cycles: list[dict]) -> str:
    return '<div class="cycle-bars">' + ''.join(f'''<section><b>{_e(x['name'])}</b><span>{_e(x['years'])}</span><i style="--score:{x['score']}"></i><strong>{x['score']}</strong><p>{_e(x['focus'])}</p></section>''' for x in cycles) + '</div>'


def _study_pages(d: dict) -> list[str]:
    s = d["study"]
    return [
        _page(172, "专项 · 学业", "脚本没有独立学业节点，本节由偏印、食伤、作用关系与德秀等事实组合", s["title"], f'<p class="lead">{_e(s["summary"])}</p>' + _cards(s["method"], ("name", "why", "how")), cls="section-open"),
        _page(173, "学业 · 学习循环", "对你而言，输出不是学习结束后的附加项", "问题—输入—制作—反馈，构成完整掌握", '''<div class="learning-loop"><section><b>问</b><p>从真实问题开始</p></section><section><b>读</b><p>搭建知识地图</p></section><section><b>做</b><p>形成作品或案例</p></section><section><b>讲</b><p>用反馈校正理解</p></section></div><div class="quote-card">如果一个知识点无法被解释、演示或用于解决问题，它往往还没有真正成为你的能力。</div>'''),
        _page(174, "学业 · 优势与阻力", "学得快不等于学得稳，持续累积需要主线", "让好奇心服务于一个长期领域", f'<div class="duality"><section><h2>学习优势</h2>{_list(s["advantages"])}</section><section><h2>常见阻力</h2>{_list(s["friction"])}</section></div>'),
        _page(175, "学业 · 计划模板", "把偏印的探索与财星的结果要求放进同一张表", "十二周完成一次可验证的学习", '''<div class="study-plan"><section><b>第1—2周</b><p>确定问题、边界和最终成品。</p></section><section><b>第3—6周</b><p>集中输入，记录概念之间的关系。</p></section><section><b>第7—10周</b><p>制作案例、原型、文章或公开讲解。</p></section><section><b>第11—12周</b><p>收集反馈，删去无效分支，决定是否进入下一轮。</p></section></div><p class="note">德秀、天厨等神煞只作文化辅助；是否学成，仍取决于训练、反馈和持续时间。</p>'''),
    ]


def _relationship_pages(d: dict) -> list[str]:
    r = d["relationship"]
    pages = [_page(176, "专项 · 感情与婚姻", "从日支、财星和真实作用关系观察亲密需求", r["title"], f'<p class="lead">{_e(r["summary"])}</p>' + _cards(r["needs"], ("name", "evidence", "reading")), cls="section-open")]
    pages.append(_page(177, "感情 · 关系需求", "感情不是抽象契合，也是一套可以共同维持的生活", "四件事，比单纯的情绪浓度更重要", '''<div class="relationship-ring"><section><b>回应</b><p>说到的事能够做到</p></section><section><b>共建</b><p>共同处理现实安排</p></section><section><b>空间</b><p>保留独立思考时间</p></section><section><b>边界</b><p>金钱、人情与社交透明</p></section></div>'''))
    pages.append(_page(178, "感情 · 原盘作用", "关系里的摩擦要落到具体机制，不把术语当结论", "两组拉扯，分别发生在生活与选择", _cards(r["interactions"][:2], ("fact", "meaning", "action"))))
    pages.append(_page(179, "感情 · 神煞辅助", "神煞只补充支持、时机与沟通角度", "外界印象与长期适配，是两件不同的事", _cards(r["interactions"][2:], ("fact", "meaning", "action")) + '<p class="note">神煞不能单独判断婚姻结果；它只补充观察角度，仍需回到现实中的价值观、沟通和共同生活。</p>'))
    pages.append(_page(180, "感情 · 冲突修复", "午午自刑容易让同一问题在心里反复，修复要从小处开始", "把争执从“你总是”改写成一件可处理的事", '''<div class="repair"><section><b>发生了什么</b><p>只描述这一次具体行为，不追溯人格。</p></section><section><b>影响是什么</b><p>说明它怎样改变时间、信任或共同安排。</p></section><section><b>需要什么</b><p>提出可以执行、可以确认的请求。</p></section><section><b>如何复盘</b><p>约定下一次检查的时间，不把承诺留在情绪里。</p></section></div>'''))
    pages.append(_page(181, "感情 · 共同生活", "财星重视现实承接，偏印需要个人空间", "一份关系能否长久，要看两套系统能否同时存在", '''<div class="two-systems"><section><h2>共同系统</h2><p>预算、家务、时间、居住、照顾责任和对外人情。</p></section><section><h2>个人系统</h2><p>独处、研究、朋友、职业选择和不被打扰的恢复时间。</p></section></div><blockquote>好的边界不是疏远，而是让承诺有能力长期兑现。</blockquote>'''))
    return pages


def _health_pages(d: dict) -> list[str]:
    h = d["health"]
    return [
        _page(182, "专项 · 身心节律", "传统五行只用于生活方式观察，不用于诊断", h["title"], f'<p class="lead">{_e(h["summary"])}</p>' + _cards(h["signals"], ("name", "fact", "reading")), cls="section-open"),
        _page(183, "身心 · 能量曲线", "火旺的风险不是“火不好”，而是长时间只有加速没有回落", "工作强度需要有波峰，也要有谷底", '''<svg class="energy-chart" viewBox="0 0 500 250"><path class="grid" d="M25 55H475M25 125H475M25 195H475"/><path class="energy" d="M25 185 C80 170 95 75 150 70 S215 185 270 105 S345 45 395 80 S445 170 475 115"/><path class="recover" d="M25 205 C120 205 135 175 210 180 S310 210 370 165 S430 150 475 165"/><text x="28" y="35">投入</text><text x="28" y="232">恢复</text></svg><p class="note">真正可持续的节奏，不是把每天都安排成高点，而是让恢复能跟上投入。</p>'''),
        _page(184, "身心 · 日常配置", "把恢复写进行程，它才不会永远排在最后", "四项最基础、也最值得长期记录的习惯", _list(h["routine"], "habit-list")),
        _page(185, "身心 · 阅读边界", "旧脚本中的寿命和疾病断语已被移除", "该交给医生的问题，不交给命盘", '''<div class="medical-boundary"><section><b>命书可以做</b><p>提醒节奏、环境、习惯与压力管理，帮助你提出更好的观察问题。</p></section><section><b>命书不能做</b><p>诊断疾病、推断寿命、替代体检、解释异常指标，或建议停止治疗。</p></section><section><b>应该立即求助</b><p>持续或突然加重的不适、显著情绪困扰、异常检查结果及任何紧急症状。</p></section></div>'''),
    ]


def _family_pages(d: dict) -> list[str]:
    f = d["family"]
    pages = [_page(186, "专项 · 六亲", "宫位是观察关系角色的入口，不是给亲属定性", f["title"], f'<p class="lead">{_e(f["summary"])}</p><div class="pillar-strip">' + ''.join(f'<section><b>{_e(x["ganzhi"])}</b><span>{_e(x["label"])}</span><small>{_e(x["gan_god"])}</small></section>' for x in d["chart"]["pillars"]) + '</div>', cls="section-open")]
    pages.append(_page(187, "六亲 · 年月", "先看早年外缘，再看成长与工作环境", "家族如何塑造你对可靠与机会的理解", _cards(f["palaces"][:2], ("name", "role", "reading"))))
    pages.append(_page(188, "六亲 · 日时", "亲密生活与未来规划，都需要明确责任边界", "照顾别人，也要保留自己的长期主线", _cards(f["palaces"][2:], ("name", "role", "reading"))))
    pages.append(_page(189, "六亲 · 支持网络", "贵人不是凭空出现的人，而是关系里可持续的互相成就", "三种支持，各有不同的建立方式", _cards(f["support"], ("name", "facts", "reading"))))
    pages.append(_page(190, "六亲 · 同辈与合作", "同辈关系既能提供支持，也需要清楚分配规则", "把人情与规则放在同一张桌上", '''<div class="peer-grid"><section><b>可以借力</b><p>共创、信息交换、相互推动与快速试错。</p></section><section><b>容易卡住</b><p>谁说了算、谁投入更多、成果归属和收益分配。</p></section><section><b>保护关系</b><p>重要合作保留书面约定；变化发生时重新确认，不靠默契硬撑。</p></section><section><b>判断标准</b><p>好的合作让双方能力都被放大，而不是长期由一方补位。</p></section></div>'''))
    pages.append(_page(191, "六亲 · 现实核对", "命盘提供问题，真实经历负责回答", "用六个问题重新认识家庭关系", _list(["家里最重视的价值是什么：稳定、成就、照顾，还是自由？", "你通常承担哪一种角色：推进者、协调者、照顾者，还是解决问题的人？", "哪些责任是你主动选择的，哪些只是习惯性接过来的？", "家人表达支持的方式，是否正是你能接收到的方式？", "金钱、时间与照顾责任有没有被清楚讨论？", "哪些边界能让关系更长久，而不是让彼此疏远？"], "question-list")))
    return pages


def _risk_pages(d: dict) -> list[str]:
    r = d["risk"]
    pages = [_page(192, "专项 · 风险与应对", "把“劫难”改写为可观察、可管理的压力来源", r["title"], f'<p class="lead">{_e(r["summary"])}</p><div class="risk-overview"><b>不做灾祸预言</b><span>不判断事故、疾病、破产、生死</span><b>只做结构管理</b><span>识别信号、设置边界、准备预案</span></div>', cls="section-open")]
    pages.append(_page(193, "风险 · 结构矩阵", "风险来自失衡和叠加，不来自某一个字", "五类最值得提前管理的压力", '<div class="risk-matrix">' + ''.join(f'<section><em>{_e(x["level"])}</em><b>{_e(x["name"])}</b><span>{_e(x["source"])}</span><p>{_e(x["signal"])}</p></section>' for x in r["matrix"]) + '</div>'))
    pages.append(_page(194, "风险 · 应对清单", "每一个风险都对应一项现实动作", "把抽象担忧变成制度、记录和求助", '<div class="response-list">' + ''.join(f'<section><b>{_e(x["name"])}</b><p>{_e(x["response"])}</p></section>' for x in r["matrix"]) + '</div>'))
    pages.append(_page(195, "专项报告 · 七项总结", "七项专题最终指向同一个命题：如何使用自己的力量", "看见结构，也给自己留下改变结构的自由", f'''<div class="final-seven"><span>性格</span><span>事业</span><span>学业</span><span>感情</span><span>身心</span><span>六亲</span><span>风险</span></div><blockquote>真正有价值的命书，不是把未来写死，而是让你更早看见选择、代价与余地。</blockquote>{_list(d['boundaries'], 'final-boundaries')}'''))
    return pages


def render_topics_html(facts: dict) -> str:
    data = build_topics_analysis(facts)
    pages = [_intro_page()]
    groups = [
        ("一", "性格", "内在性情<br>外在表达", "先看力量怎样形成性格<br>再看压力之下如何变化", _personality_pages(data)[1:]),
        ("二", "事业", "能力成形<br>成果兑现", "从职业结构到大运节奏<br>说明天赋怎样进入现实", _career_pages(data)),
        ("三", "学业", "如何学习<br>如何学成", "从问题、输入到作品反馈<br>建立可持续的学习主线", _study_pages(data)),
        ("四", "感情婚姻", "彼此吸引<br>共同生活", "从亲密需求到冲突修复<br>把关系落回日常选择", _relationship_pages(data)),
        ("五", "身心节律", "张弛有度<br>长久可行", "只谈节奏、恢复与边界<br>不以命理替代医学判断", _health_pages(data)),
        ("六", "六亲", "关系角色<br>责任边界", "观察家人与支持网络<br>不替现实中的人下定论", _family_pages(data)),
        ("七", "风险与应对", "识别压力<br>准备预案", "不做灾祸预言<br>只把风险变成可管理动作", _risk_pages(data)),
    ]
    page_number = 171
    for index, (order, title, lines, note, content_pages) in enumerate(groups):
        if index and page_number % 2 == 0:
            pages.append(f'<article class="page verso topic-blank" data-page="{page_number}" aria-label="章节前留白页"></article>')
            page_number += 1
        pages.append(_divider(page_number, f"专项报告 · {order}", title, lines, note))
        page_number += 1
        for raw_page in content_pages:
            numbered = re.sub(r'data-page="\d+"', f'data-page="{page_number}"', raw_page, count=1)
            numbered = re.sub(r'<footer>\d+</footer>', f'<footer>{page_number}</footer>', numbered, count=1)
            pages.append(numbered)
            page_number += 1
    if len(pages) != 48 or len(pages) % 2 or page_number != 218:
        raise ValueError(f"topics chapter must contain 48 A5 pages through page 217, got {len(pages)} pages ending at {page_number - 1}")
    spreads = ''.join(f'<section class="spread">{pages[i]}{pages[i+1]}</section>' for i in range(0, len(pages), 2))
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 专项报告</title><style>{_css()}{TOPICS_V2_CSS}</style></head><body><main>{spreads}</main>{ELEMENT_COLOR_SCRIPT}{page_offset_script(10)}</body></html>'''


def _css() -> str:
    return r'''
@font-face{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}@font-face{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}@font-face{font-family:Brush;src:url('../../../assets/fonts/MaShanZheng-Regular.ttf')}@page{size:A4 landscape;margin:0}:root{--paper:#f6efdf;--paper2:#fbf7ed;--ink:#292821;--muted:#746b5e;--line:#d6c39f;--gold:#a77934;--jade:#315e52;--red:#974238;--blue:#607c85}*{box-sizing:border-box}body{margin:0;background:#242422;color:var(--ink);font-family:BookSerif,serif}main{padding:28px 0 70px}.spread{display:flex;width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;filter:drop-shadow(0 14px 24px #111)}.page{position:relative;flex:0 0 50%;aspect-ratio:148/210;padding:7.5% 8%;overflow:hidden;background:linear-gradient(145deg,var(--paper2),var(--paper));contain:layout paint}.spread>.page:first-child:after{content:'';position:absolute;right:0;inset-block:0;width:1px;background:#cbbfae}header{font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px}.recto header{text-align:right}h1{font-size:28px;line-height:1.26;margin:7px 0 12px;font-weight:500}h2{font-weight:500}.eyebrow{font:9px BookSans;color:var(--gold);letter-spacing:.07em;margin:18px 0 0}.lead{font:11.2px/1.85 BookSans;color:#4f4a42;padding:14px 16px;margin:0 0 15px;border-left:3px solid var(--gold);background:#faf5e9}footer{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#887d6b}.recto footer{text-align:right}.note{font:9px/1.6 BookSans;color:var(--muted);padding:10px 13px;border-left:3px solid var(--gold);background:#faf5e9}blockquote{font:25px/1.7 Brush;color:var(--jade);text-align:center;margin:38px 8% 0}.chapter-divider{padding:0;background:#203b34;color:#f1e6ce}.chapter-frame{position:absolute;inset:8%;border:1px solid #b89a60;outline:1px solid rgba(184,154,96,.45);outline-offset:-9px}.chapter-frame small,.chapter-frame h1,.chapter-frame p,.chapter-frame i{position:absolute;writing-mode:vertical-rl;white-space:nowrap;margin:0}.chapter-frame small{right:10%;bottom:10%;font:11px BookSans;letter-spacing:.25em;color:#c9ac73}.chapter-frame h1{right:37%;top:13%;font:70px Brush;font-weight:400}.chapter-frame p{right:58%;top:18%;font:20px/1.8 BookSerif}.chapter-frame i{left:12%;bottom:11%;font:normal 10px/1.7 BookSans;color:#ccb986}.cards{display:grid;grid-template-columns:1fr 1fr;gap:12px}.cards section{min-height:145px;padding:14px;border:1px solid var(--line);background:rgba(250,245,233,.72)}.cards small{font:8px BookSans;color:var(--gold)}.cards h2{font-size:15px;color:var(--jade);margin:5px 0 8px}.cards p{font:9.2px/1.65 BookSans;color:#504b43;margin:0}.clean-list,.rules,.habit-list,.question-list,.final-boundaries{margin:0;padding:0;list-style:none}.clean-list li,.rules li,.habit-list li,.question-list li,.final-boundaries li{font:10px/1.65 BookSans;padding:10px 8px 10px 27px;border-bottom:1px solid var(--line);position:relative}.clean-list li:before,.rules li:before,.habit-list li:before,.question-list li:before{content:'·';position:absolute;left:8px;color:var(--gold);font-size:20px}.closing-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin-top:32px}.closing-grid section{min-height:175px;border-top:3px solid var(--gold);padding:17px 13px;background:#faf5e9}.closing-grid b{font-size:17px;color:var(--jade)}.closing-grid p{font:10px/1.75 BookSans}.topics-bridge blockquote{margin-top:48px}.duality,.timing,.two-systems{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:25px}.duality section,.timing section,.two-systems section{padding:18px;border-top:3px solid var(--gold);background:#faf5e9}.duality h2,.timing h2,.two-systems h2{font-size:18px;color:var(--jade);margin:0 0 10px}.decision-flow,.career-chain{display:flex;align-items:center;gap:9px;margin-top:34px}.decision-flow section,.career-chain section{flex:1;min-height:220px;border:1px solid var(--line);padding:16px;background:#faf5e9}.decision-flow section>b,.career-chain section>b{font:26px Brush;color:var(--gold)}.decision-flow i,.career-chain i{font-style:normal;color:var(--gold)}.decision-flow h2,.career-chain h2{font-size:15px}.decision-flow p,.career-chain p{font:9.5px/1.65 BookSans}.quote-card{margin-top:30px;padding:18px;border-block:1px solid var(--gold);font:17px/1.8 BookSerif;text-align:center;color:var(--jade)}.people-map,.useful-grid,.peer-grid{display:grid;grid-template-columns:1fr 1fr;margin-top:22px;border-top:1px solid var(--gold)}.people-map section,.useful-grid section,.peer-grid section{min-height:180px;padding:17px;border-bottom:1px solid var(--line)}.people-map section:nth-child(odd),.useful-grid section:nth-child(odd),.peer-grid section:nth-child(odd){border-right:1px solid var(--line)}.people-map b,.useful-grid b,.peer-grid b{font-size:16px;color:var(--jade)}.people-map p,.useful-grid p,.peer-grid p{font:10px/1.7 BookSans}.career-chain section{text-align:center}.career-chain span{display:block;font:9px BookSans;color:var(--gold);margin:7px}.cycle-bars{margin-top:12px}.cycle-bars section{display:grid;grid-template-columns:40px 76px 1fr 30px;grid-template-rows:22px auto;align-items:center;gap:0 8px;border-bottom:1px solid var(--line)}.cycle-bars b{font-size:13px}.cycle-bars span{font:8px BookSans;color:var(--muted)}.cycle-bars i{height:12px;border:1px solid #d8ccb8;background:linear-gradient(90deg,var(--jade) calc(var(--score)*1%),transparent 0)}.cycle-bars strong{font:11px BookSans;color:var(--gold)}.cycle-bars p{grid-column:2/5;font:8px/1.35 BookSans;color:#5e574d;margin:0 0 7px}.rules{margin-top:16px;display:grid;grid-template-columns:1fr 1fr}.learning-loop,.relationship-ring{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-top:70px}.learning-loop section,.relationship-ring section{aspect-ratio:1;border:1px solid var(--gold);border-radius:50%;display:grid;place-content:center;text-align:center;margin-left:-7px;background:#faf5e9}.learning-loop b,.relationship-ring b{font:32px Brush;color:var(--jade)}.learning-loop p,.relationship-ring p{font:8px BookSans;margin:3px 8px}.study-plan,.repair,.medical-boundary,.response-list{margin-top:22px;border-top:1px solid var(--gold)}.study-plan section,.repair section,.medical-boundary section,.response-list section{display:grid;grid-template-columns:105px 1fr;gap:15px;padding:17px 8px;border-bottom:1px solid var(--line)}.study-plan b,.repair b,.medical-boundary b,.response-list b{font-size:14px;color:var(--jade)}.study-plan p,.repair p,.medical-boundary p,.response-list p{font:10px/1.6 BookSans;margin:0}.two-systems section{min-height:230px}.energy-chart{width:100%;margin:40px 0 20px}.energy-chart .grid{fill:none;stroke:#ddd0b9;stroke-width:1}.energy-chart .energy{fill:none;stroke:var(--red);stroke-width:4}.energy-chart .recover{fill:none;stroke:var(--blue);stroke-width:3;stroke-dasharray:8 6}.energy-chart text{font:10px BookSans;fill:var(--muted)}.habit-list{margin-top:28px;counter-reset:habit}.habit-list li{counter-increment:habit;min-height:92px;padding-left:72px;font-size:11px}.habit-list li:before{content:'0' counter(habit);font:28px BookSerif;color:var(--gold);left:12px}.pillar-strip{display:grid;grid-template-columns:repeat(4,1fr);margin-top:45px;border-block:1px solid var(--gold)}.pillar-strip section{text-align:center;padding:22px 5px;border-right:1px solid var(--line)}.pillar-strip section:last-child{border:0}.pillar-strip b{display:block;font:30px BookSerif}.pillar-strip span,.pillar-strip small{display:block;font:9px BookSans;color:var(--muted);margin-top:7px}.question-list{counter-reset:q;margin-top:18px}.question-list li{counter-increment:q;padding-left:48px;min-height:64px}.question-list li:before{content:counter(q);font:22px Brush;color:var(--gold);left:12px}.risk-overview{display:grid;grid-template-columns:110px 1fr;margin-top:30px;border:1px solid var(--line)}.risk-overview b,.risk-overview span{padding:16px;border-bottom:1px solid var(--line)}.risk-overview b{font-size:14px;color:var(--jade);background:#eee3cf}.risk-overview span{font:10px BookSans}.risk-matrix{margin-top:15px}.risk-matrix section{display:grid;grid-template-columns:35px 78px 130px 1fr;gap:8px;align-items:center;min-height:72px;border-bottom:1px solid var(--line)}.risk-matrix em{font:normal 8px BookSans;color:#fff;background:var(--gold);padding:4px;text-align:center}.risk-matrix b{font-size:13px}.risk-matrix span{font:8px BookSans;color:var(--muted)}.risk-matrix p{font:8.5px/1.45 BookSans}.final-seven{display:flex;justify-content:center;gap:8px;margin-top:55px}.final-seven span{writing-mode:vertical-rl;padding:14px 9px;border:1px solid var(--gold);font-size:17px;color:var(--jade)}.final-boundaries{margin-top:45px}.final-boundaries li{font-size:8.5px;color:var(--muted)}@media print{body{background:#fff}main{padding:0}.spread{width:296mm;height:210mm;margin:0;filter:none;break-after:page}.page{width:148mm;height:210mm}}
'''


def write_topics_sample(facts: dict, html_path: str | Path, data_path: str | Path | None = None) -> Path:
    target = Path(html_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_topics_html(facts), encoding="utf-8")
    if data_path is not None:
        data_target = Path(data_path)
        data_target.parent.mkdir(parents=True, exist_ok=True)
        data_target.write_text(json.dumps(build_topics_analysis(facts), ensure_ascii=False, indent=2), encoding="utf-8")
    return target
