"""Render the first seven reader pages and their print-accurate spreads."""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

from .opening_content import DAY_MASTER_PROFILES, MONTH_PROFILES, ZODIAC_PROFILES, daymaster_asset


ROOT = Path(__file__).resolve().parents[1]
ILLUSTRATIONS = ROOT / "assets" / "mingshu" / "illustrations"


def _e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _facts_view(facts: dict) -> dict:
    chart = facts.get("chart") or {}
    pillars = list(chart.get("pillars") or [])[:4]
    day_code = (chart.get("day_master") or {}).get("code") or "GAN:BING"
    month_code = ((pillars[1].get("zhi") or {}).get("name") if len(pillars) > 1 else None) or "ZHI:ZI"
    year_code = ((pillars[0].get("zhi") or {}).get("name") if pillars else None) or "ZHI:SI"
    return {
        "subject": (facts.get("subject") or {}).get("display_name") or "",
        "gender": (facts.get("subject") or {}).get("gender") or "male",
        "pillars": pillars,
        "day_code": day_code,
        "month_code": month_code,
        "year_code": year_code,
        "day": DAY_MASTER_PROFILES[day_code],
        "month": MONTH_PROFILES[month_code],
        "zodiac": ZODIAC_PROFILES[year_code],
        "wuxing": list((facts.get("analysis_facts") or {}).get("wuxing") or []),
        "luck": list(facts.get("luck_cycles") or []),
    }


def _radar_svg(items: list[dict]) -> str:
    order = ["WUXING:MU", "WUXING:HUO", "WUXING:TU", "WUXING:JIN", "WUXING:SHUI"]
    labels = {"WUXING:MU":"木", "WUXING:HUO":"火", "WUXING:TU":"土", "WUXING:JIN":"金", "WUXING:SHUI":"水"}
    values = {x.get("code"): float(x.get("percent") or 0) for x in items}
    cx, cy, radius = 190, 188, 126
    def point(i: int, ratio: float) -> tuple[float, float]:
        angle = math.radians(-90 + i * 72)
        return cx + math.cos(angle) * radius * ratio, cy + math.sin(angle) * radius * ratio
    rings = []
    for scale in (.25, .5, .75, 1):
        rings.append(" ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, scale) for i in range(5))))
    maximum = max([values.get(code, 0) for code in order] + [1])
    data = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, .18 + .78 * values.get(code, 0) / maximum) for i, code in enumerate(order)))
    axes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{point(i,1)[0]:.1f}" y2="{point(i,1)[1]:.1f}"/>' for i in range(5))
    text = []
    for i, code in enumerate(order):
        x, y = point(i, 1.25)
        text.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle"><tspan>{labels[code]}</tspan><tspan x="{x:.1f}" dy="17">{values.get(code,0):.1f}%</tspan></text>')
    return f'''<svg class="radar" viewBox="0 0 380 380" role="img" aria-label="五行力量雷达图">
      <defs><linearGradient id="mineral" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#b33b2f"/><stop offset=".48" stop-color="#b68a42"/><stop offset="1" stop-color="#315c55"/></linearGradient></defs>
      <g class="radar-rings">{''.join(f'<polygon points="{r}"/>' for r in rings)}{axes}</g>
      <polygon class="radar-data" points="{data}"/><circle cx="{cx}" cy="{cy}" r="5"/>
      <g class="radar-labels">{''.join(text)}</g></svg>'''


def _pillar_html(pillar: dict, index: int) -> str:
    gan, zhi = pillar.get("gan") or {}, pillar.get("zhi") or {}
    hidden = " · ".join(f"{x.get('name_label')}{x.get('shishen_label')}" for x in zhi.get("hidden_gans") or [])
    return f'''<div class="pillar{' day' if index == 2 else ''}">
      <small>{_e(pillar.get('label'))}</small><b class="gan">{_e(gan.get('name_label'))}</b>
      <span>{_e(gan.get('shishen_label'))}</span><b class="zhi">{_e(zhi.get('name_label'))}</b>
      <em>{_e(hidden)}</em><i>{_e((pillar.get('nayin') or {}).get('label'))}</i></div>'''


def _luck_html(cycles: list[dict]) -> str:
    kept = [x for x in cycles if not x.get("is_pre_luck")][:8]
    current = next((x for x in kept if int(x.get("start_year") or 0) <= 2026 <= int(x.get("end_year") or 0)), None)
    rows = []
    for item in kept:
        active = item is current
        rows.append(f'''<div class="luck-item{' active' if active else ''}"><span class="luck-dot"></span>
          <b>{_e(item.get('name'))}</b><small>{_e(item.get('start_year'))}—{_e(item.get('end_year'))}</small>
          <em>{_e((item.get('gan_shishen') or {}).get('label'))} · {_e((item.get('zhi_shishen') or {}).get('label'))}</em>
          {'<i>当下</i>' if active else ''}</div>''')
    return "".join(rows)


def build_opening_html(facts: dict, *, asset_prefix: str = "../../../assets/mingshu/illustrations") -> str:
    v = _facts_view(facts)
    cover = f"{asset_prefix}/covers/cover-celestial-v1.png"
    day_image = f"{asset_prefix}/{daymaster_asset(v['day_code'], v['gender'])}"
    month_image = f"{asset_prefix}/seasons/{v['month']['asset']}"
    zodiac_image = f"{asset_prefix}/zodiac/{v['zodiac']['slug']}-v1.png"
    strongest = sorted(v["wuxing"], key=lambda x: float(x.get("percent") or 0), reverse=True)
    wuxing_note = "五行气势尚未显出清晰重心。" if not strongest else (
        f"{strongest[0].get('label')}最显，约占 {float(strongest[0].get('percent') or 0):.1f}%；"
        f"{strongest[-1].get('label')}相对收敛，约占 {float(strongest[-1].get('percent') or 0):.1f}%。"
        "高低只是结构对比，不等于好坏，也不建议按“缺什么补什么”直接行动。"
    )
    pillars = "".join(_pillar_html(x, i) for i, x in enumerate(v["pillars"]))
    pages = f'''
    <section class="spread cover-spread" data-spread="1"><article class="page blank" aria-label="封面左侧留空"></article>
      <article class="page cover" data-page="cover"><img src="{cover}" alt="星图山水封面底图"><div class="cover-veil"></div>
        <div class="cover-kicker">四柱 · 五行 · 岁运 · 人生专题</div><h1>命书</h1><p>以古老的时间语言，照见当下的选择</p>
        <div class="cover-name"><span data-cover-name>{_e(v['subject'])}</span><small>珍藏本</small></div><div class="seal">镜<br>观</div></article></section>
    <section class="spread" data-spread="2"><article class="page usage" data-page="inside-cover"><header>阅读之前</header><h2>把它当作一面镜子，<br>而不是一份判决。</h2>
      <div class="usage-list"><div><b>01</b><p><strong>资料是起点</strong><span>出生日期、时间与性别无误，四柱才有可靠的根基。</span></p></div><div><b>02</b><p><strong>五行看气势</strong><span>占比多不一定为喜，占比少也不等于命里缺失。</span></p></div><div><b>03</b><p><strong>十神看关系</strong><span>同一十神落在不同柱位，会连接不同的人生场景。</span></p></div><div><b>04</b><p><strong>岁运看节奏</strong><span>大运铺陈十年背景，流年让具体主题渐次显露。</span></p></div></div>
      <footer>使用说明</footer></article><article class="page greeting" data-page="1"><div class="sun"></div><header>首页寄语</header><h2>愿你认识来处，<br>也保有改写去处的自由。</h2>
      <p class="lead">命盘记录的是出生一刻的时空结构。它像一张气候地图：让人看见惯性、资源与容易反复遇到的课题，却不替你决定要走哪一条路。</p>
      <blockquote>“知命”不是等待安排，<br>而是在看清条件之后，仍然认真选择。</blockquote><p>读这本书时，请保留好奇，也保留判断。合于经验的部分，可以成为整理生活的语言；暂时无感的部分，不妨放在一旁，让时间验证。</p><footer>01</footer></article></section>
    <section class="spread" data-spread="3"><article class="page chart" data-page="2"><header>原盘 · 出生时刻的结构</header><h2>四柱排盘</h2><p class="deck">天干看外显，地支看根基，藏干看潜在通道。先核对排盘，再进入解读。</p><div class="pillars">{pillars}</div><div class="relation-band"><b>结构提示</b><span>日主为{_e(v['day']['char'])}{_e(v['day']['element'])}，生于{_e(v['month']['char'])}月。四柱之间的生克合冲会在后文逐层展开。</span></div><footer>02</footer></article>
      <article class="page luck" data-page="3"><header>大运 · 时间的长镜头</header><h2>十年一程</h2><p class="deck">大运不是吉凶排名，而是每十年更容易被反复提出的环境主题。</p><div class="luck-axis">{_luck_html(v['luck'])}</div><div class="luck-note"><b>岁运相叠</b><span>大运铺陈十年背景，流年让具体主题在不同年份显露轻重。</span></div><footer>03</footer></article></section>
    <section class="spread" data-spread="4"><article class="page wuxing" data-page="4"><header>五行 · 力量分布</header><h2>哪一股气，最先被看见</h2><div class="radar-wrap">{_radar_svg(v['wuxing'])}<span class="radar-sun"></span></div><div class="chart-copy"><b>读图结论</b><p>{_e(wuxing_note)}</p></div><footer>04</footer></article>
      <article class="page daymaster" data-page="5"><div class="day-bg-char">{_e(v['day']['char'])}</div><header>日主 · 自我视角</header><div class="day-copy"><span>{_e(v['day']['element'])}之象</span><h2>{_e(v['day']['metaphor'])}</h2><h3>{_e(v['day']['tagline'])}</h3><p>{_e(v['day']['intro'])}</p><p><b>顺势：</b>{_e(v['day']['strength'])}</p><p><b>平衡：</b>{_e(v['day']['balance'])}</p></div><img class="day-person" src="{day_image}" alt="{_e(v['day']['char'])}{_e(v['day']['element'])}日主国风人物"><footer>05</footer></article></section>
    <section class="spread" data-spread="5"><article class="page month" data-page="6"><header>月令 · 出生时的季节底色</header><div class="month-copy"><span>{_e(v['month']['season'])}</span><h2>{_e(v['month']['char'])}月</h2><h3>{_e(v['month']['tagline'])}</h3><p>{_e(v['month']['intro'])}</p><p>{_e(v['month']['reading'])}</p></div><img src="{month_image}" alt="{_e(v['month']['image'])}"><footer>06</footer></article>
      <article class="page zodiac" data-page="7"><header>生肖 · 一眼可亲的年份记忆</header><div class="zodiac-ring"><span>巳</span></div><h2>生肖{_e(v['zodiac']['animal'])}</h2><h3>{_e(v['zodiac']['tagline'])}</h3><img src="{zodiac_image}" alt="年画风生肖{_e(v['zodiac']['animal'])}"><p>{_e(v['zodiac']['intro'])}</p><div class="zodiac-note">生肖是年支的文化入口，只占四柱中的一字。它适合帮助阅读，不适合单独判断性格与关系。</div><footer>07</footer></article></section>'''
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 开篇七页</title>
    <style>{_css()}</style></head><body><aside class="proof-tools"><label>封面姓名（可选）<input data-testid="cover-name-input" value="{_e(v['subject'])}" placeholder="留空则不显示姓名"></label><span>真实 A5 跨页预览 · 左装</span></aside><main>{pages}</main>
    <script>const i=document.querySelector('[data-testid="cover-name-input"]'),n=document.querySelector('[data-cover-name]');i.addEventListener('input',()=>{{n.textContent=i.value;n.parentElement.classList.toggle('empty',!i.value.trim())}});n.parentElement.classList.toggle('empty',!i.value.trim());</script></body></html>'''


def _css() -> str:
    return r'''
@font-face{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}@font-face{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}
:root{--paper:#f5f0e6;--ink:#292a26;--muted:#786f62;--gold:#a98243;--red:#a2382c;--jade:#315e55;--line:#d9c8aa}*{box-sizing:border-box}body{margin:0;background:#282725;color:var(--ink);font-family:BookSerif,"Songti SC",serif}.proof-tools{position:sticky;top:0;z-index:20;height:54px;background:#1d1d1c;color:#ddd;display:flex;align-items:center;justify-content:center;gap:36px;font:13px BookSans;padding:0 20px}.proof-tools label{display:flex;align-items:center;gap:12px}.proof-tools input{width:210px;border:0;border-bottom:1px solid #8c7b5e;background:transparent;color:#fff;padding:7px 4px;outline:none}main{padding:26px 0 60px}.spread{width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto 34px;display:flex;filter:drop-shadow(0 12px 24px #0007)}.page{position:relative;flex:0 0 50%;overflow:clip;contain:layout paint;background:var(--paper);padding:7.5% 8%;aspect-ratio:148/210}.spread>.page:first-child:after{content:"";position:absolute;right:0;top:0;bottom:0;width:1px;background:#1e1b1728}.blank{background:#292825}.cover{padding:0;color:#efe8d8;text-align:center}.cover>img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.cover-veil{position:absolute;inset:0;background:linear-gradient(#1f252477,#1522202c 45%,#15201fb8)}.cover-kicker,.cover h1,.cover p,.cover-name,.seal{position:absolute;z-index:2}.cover-kicker,.cover h1,.cover p{left:0}.cover-kicker{top:10%;width:100%;font:12px BookSans;letter-spacing:.28em;color:#d5bd86}.cover h1{top:24%;margin:0;width:100%;font-size:91px;letter-spacing:.18em;text-indent:.18em;font-weight:700;text-shadow:0 4px 18px #0d141488}.cover h1:after{content:"";display:block;width:108px;height:5px;margin:8px auto 0;background:linear-gradient(90deg,transparent,#b23a2c,transparent);transform:rotate(-2deg)}.cover p{top:49%;width:100%;font-size:17px;letter-spacing:.12em}.cover-name{bottom:11%;left:50%;transform:translateX(-50%);min-width:150px;padding:10px 24px;border-top:1px solid #c9ae75}.cover-name span{display:block;font-size:20px;letter-spacing:.18em}.cover-name small{font:10px BookSans;letter-spacing:.35em;color:#c8b177}.cover-name.empty span{display:none}.seal{right:9%;bottom:8%;width:38px;height:38px;border:1px solid #ce8175;color:#e19a8e;font:bold 13px BookSerif;padding-top:4px;transform:rotate(-4deg)}header{font:11px BookSans;color:var(--gold);letter-spacing:.18em;text-transform:uppercase;border-bottom:1px solid var(--line);padding-bottom:9px}.page h2{font-size:33px;line-height:1.35;margin:25px 0 20px;font-weight:600}.page h3{font-weight:500;color:var(--red);letter-spacing:.06em}.page p{font-size:14px;line-height:1.9;color:#48463f}.page footer{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#8f877a;letter-spacing:.14em}.usage:before{content:"";position:absolute;width:220px;height:220px;border:1px solid #bd9e6533;border-radius:50%;right:-90px;top:-70px}.usage-list{margin-top:32px}.usage-list>div{display:flex;gap:16px;border-top:1px solid #dfd2bd;padding:17px 0}.usage-list b{font:24px BookSerif;color:#b49a6c}.usage-list p{margin:0}.usage-list strong,.usage-list span{display:block}.usage-list strong{font-size:15px;margin-bottom:4px}.usage-list span{font-size:12px;line-height:1.7;color:#777064}.greeting{background:linear-gradient(150deg,#f7f1e7,#eee5d6)}.greeting .sun{position:absolute;width:188px;height:188px;border-radius:50%;background:#ae392c12;right:-45px;top:70px}.greeting .lead{font-size:16px;line-height:2}.greeting blockquote{margin:30px 0;padding:21px 0;border-top:1px solid var(--gold);border-bottom:1px solid var(--gold);font-size:22px;line-height:1.65;color:var(--red)}.deck{margin-top:-12px!important;color:#716b61!important}.pillars{display:grid;grid-template-columns:repeat(4,1fr);margin:30px 0 26px;border-top:1px solid var(--gold);border-bottom:1px solid var(--gold)}.pillar{text-align:center;padding:19px 8px 16px;min-width:0;position:relative}.pillar+.pillar{border-left:1px solid #d9c8aa}.pillar.day{background:#a33a2e0b}.pillar.day:before{content:"日主";position:absolute;top:-11px;left:50%;transform:translateX(-50%);background:var(--red);color:#fff;font:9px BookSans;padding:3px 8px}.pillar small,.pillar span,.pillar em,.pillar i{display:block}.pillar small{font:11px BookSans;color:#817b71}.pillar .gan,.pillar .zhi{font-size:44px;line-height:1.25}.pillar .gan{color:var(--red);margin-top:8px}.pillar .zhi{color:var(--jade);margin-top:12px}.pillar span{font-size:11px;color:var(--gold)}.pillar em{height:38px;margin-top:12px;font:normal 9px/1.6 BookSans;color:#6c675f}.pillar i{font:normal 11px BookSerif;border-top:1px solid #ddd0ba;padding-top:9px}.relation-band,.chart-copy,.luck-note,.zodiac-note{border-left:3px solid var(--red);background:#ffffff70;padding:14px 16px}.relation-band b,.relation-band span{display:block}.relation-band span{font-size:12px;line-height:1.7;margin-top:5px}.luck-axis{position:relative;margin:22px 0}.luck-axis:before{content:"";position:absolute;left:12px;top:8px;bottom:8px;width:1px;background:#bda26d}.luck-item{height:50px;padding-left:34px;display:grid;grid-template-columns:62px 1fr;grid-template-rows:22px 18px;position:relative}.luck-dot{position:absolute;left:7px;top:7px;width:11px;height:11px;border-radius:50%;border:2px solid var(--gold);background:var(--paper)}.luck-item b{font-size:17px}.luck-item small{font:11px BookSans;color:#777}.luck-item em{font:normal 11px BookSans;color:#968460;grid-column:2}.luck-item i{position:absolute;right:0;top:2px;font:9px BookSans;color:#fff;background:var(--red);padding:3px 7px}.luck-item.active{color:var(--red)}.luck-item.active .luck-dot{background:var(--red);border-color:var(--red);box-shadow:0 0 0 5px #a2382c1c}.luck-note{display:flex;gap:13px}.luck-note b{font-size:25px;color:var(--red)}.luck-note span{font-size:11px;line-height:1.7}.wuxing{background:radial-gradient(circle at 64% 32%,#b88b4515,transparent 34%),var(--paper)}.wuxing h2{font-size:28px;margin-bottom:6px}.radar-wrap{position:relative;width:90%;margin:-2px auto 0}.radar{width:100%}.radar-rings polygon,.radar-rings line{fill:none;stroke:#a9874f;stroke-width:1;opacity:.55}.radar-data{fill:url(#mineral);fill-opacity:.36;stroke:#8d362d;stroke-width:2}.radar>circle{fill:#9d342b}.radar-labels{font:14px BookSans;fill:#3f403a}.radar-labels tspan+ tspan{font-size:10px;fill:#8e7653}.radar-sun{position:absolute;width:92px;height:92px;border-radius:50%;background:#ae392c12;top:34%;left:38%;z-index:-1}.chart-copy{margin-top:-10px}.chart-copy b{color:var(--red)}.chart-copy p{font-size:12px;line-height:1.65;margin:5px 0}.daymaster{background:linear-gradient(160deg,#f7f0e4,#efe4d2)}.day-bg-char{position:absolute;font-size:310px;color:#a43a2d0b;right:-28px;top:0}.day-copy{position:relative;width:63%;z-index:2}.day-copy>span{display:inline-block;margin-top:30px;color:var(--gold);font:11px BookSans;letter-spacing:.2em}.day-copy h2{font-size:32px;margin:8px 0}.day-copy h3{font-size:17px;margin:0 0 18px}.day-copy p{font-size:12px;line-height:1.75;margin:10px 0}.day-person{position:absolute;right:-3%;bottom:0;width:58%;max-height:71%;object-fit:contain;object-position:right bottom}.month{padding-bottom:0;background:#edf0ef}.month-copy{position:relative;z-index:2;background:linear-gradient(#f5f0e6 78%,transparent);margin:-1px -1px 0;padding-bottom:14px}.month-copy>span{display:block;margin-top:25px;color:var(--gold);font:11px BookSans;letter-spacing:.2em}.month-copy h2{font-size:44px;margin:4px 0}.month-copy h3{margin:0 0 11px}.month-copy p{font-size:11.5px;line-height:1.68;margin:5px 0}.month>img{position:absolute;left:0;right:0;bottom:0;width:100%;height:43%;object-fit:cover;mask-image:linear-gradient(transparent,#000 22%)}.month footer{color:#f3eee2;text-shadow:0 1px 3px #000}.zodiac{background:radial-gradient(circle at 50% 44%,#bd3b2f14,transparent 34%),#f6eee0;text-align:center}.zodiac-ring{position:absolute;width:250px;height:250px;border:1px solid #b7975a55;border-radius:50%;left:50%;top:19%;transform:translateX(-50%)}.zodiac-ring:after{content:"";position:absolute;inset:20px;border:1px dashed #a83b3022;border-radius:50%}.zodiac-ring span{position:absolute;right:16px;top:14px;color:#b23b2e26;font-size:40px}.zodiac h2{font-size:37px;margin:20px 0 0}.zodiac h3{margin:4px}.zodiac img{height:42%;width:65%;object-fit:contain;position:relative;z-index:2}.zodiac>p{font-size:12px;text-align:left;margin:3px 7%}.zodiac-note{text-align:left;margin:12px 7%;font-size:10.5px;line-height:1.65;color:#6c6358}
.usage:before{right:0}.greeting .sun{right:0}.day-bg-char{right:0}.day-person{right:0}
@media(max-width:800px){.spread{display:block;width:min(560px,calc(100vw - 24px));aspect-ratio:auto}.page{width:100%}.blank{display:none}.proof-tools{justify-content:flex-start;overflow:auto}.proof-tools span{display:none}}
@media print{body{background:white}.proof-tools{display:none}main{padding:0}.spread{display:flex!important;width:296mm;height:210mm;margin:0;filter:none;break-after:page;break-inside:avoid;page-break-inside:avoid}.spread:last-child{break-after:auto}.page{flex:0 0 147.9mm;width:147.9mm;height:210mm;aspect-ratio:auto}.blank{display:block}}
@page{size:296mm 210mm;margin:0}
'''


def write_opening_html(facts: dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_opening_html(facts), encoding="utf-8")
    return output


def write_opening_manifest(facts: dict, output: Path) -> Path:
    v = _facts_view(facts)
    payload = {
        "format": "A5 portrait, left-bound",
        "spread_order": [
            ["blank", "cover"], ["inside_cover", "page_1"], ["page_2", "page_3"],
            ["page_4", "page_5"], ["page_6", "page_7"],
        ],
        "loaded_profiles": {"day_master": v["day_code"], "month": v["month_code"], "zodiac": v["year_code"]},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
