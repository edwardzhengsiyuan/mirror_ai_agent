"""Transition spread between the relation and ten-god chapters."""

from __future__ import annotations

from html import escape
from pathlib import Path

def _e(value: object) -> str:
    return escape(str(value or ""))


def _page20() -> str:
    return """<article class="page verso conclusion-page" data-page="30">
      <header>干支关系 · 小结</header><p class="eyebrow">线条说明怎样作用，下一章继续追问：究竟牵动了什么</p><h1>关系落定，主题才会出现</h1>
      <div class="logic-chain">
        <div class="logic-row"><span>辛</span><i>冲</i><span>乙</span><strong>资源取舍 ↔ 学习方法</strong></div>
        <div class="logic-row"><span>巳</span><i>拱</i><span>丑</span><strong>行动动能 → 日常输出</strong></div>
        <div class="logic-row"><span>午</span><i>穿</i><span>丑</span><strong>外层环境 ↔ 生活节奏</strong></div>
      </div>
      <div class="reading-grid"><section><b>干支</b><p>告诉我们关系发生在哪里，以及它属于冲、合、穿等哪一种作用。</p></section><section><b>十神</b><p>把同一条作用翻译成资源、表达、责任、协作等更容易理解的生活主题。</p></section></div>
      <blockquote>下一页开始，不另起一本书；只是换一种语言，继续读同一张原盘。</blockquote><footer>30</footer>
    </article>"""


def _page21() -> str:
    return """<article class="page recto chapter-divider" data-page="31">
      <div class="chapter-frame"><small>第五章</small><h1>十神分析</h1><p>看它是谁<br>看它在哪</p><i>十神不是性格标签<br>是日主与外界的十种关系</i></div><footer>31</footer>
    </article>"""


def render_integrated_bridge_html() -> str:
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命书 · 关系与十神过桥页</title><style>
@font-face{{font-family:BookSerif;src:url('../../../assets/fonts/NotoSerifSC-Regular.ttf')}}@font-face{{font-family:BookSans;src:url('../../../assets/fonts/NotoSansSC-Regular.ttf')}}@font-face{{font-family:BookBrush;src:url('../../../assets/fonts/MaShanZheng-Regular.ttf')}}
@page{{size:A4 landscape;margin:0}}:root{{--paper:#f4ead8;--paper2:#fbf6ea;--ink:#292823;--muted:#6e675c;--line:#d5c3a3;--gold:#a77c38;--jade:#315d51;--red:#984238}}*{{box-sizing:border-box}}body{{margin:0;background:#242422;color:var(--ink);font-family:BookSerif,serif}}main{{padding:28px 0 70px}}.spread{{display:flex;width:min(1184px,calc(100vw - 44px));aspect-ratio:296/210;margin:0 auto;filter:drop-shadow(0 14px 24px #111)}}.page{{position:relative;flex:0 0 50%;aspect-ratio:148/210;padding:7.5% 8%;overflow:hidden;background:linear-gradient(145deg,var(--paper2),var(--paper));contain:layout paint}}.spread>.page:first-child:after{{content:'';position:absolute;right:0;inset-block:0;width:1px;background:#cbbfae}}header{{font:11px BookSans;color:var(--gold);letter-spacing:.16em;border-bottom:1px solid var(--line);padding-bottom:9px}}.recto header{{text-align:right}}.eyebrow{{font:9px BookSans;color:var(--gold);letter-spacing:.1em;margin:18px 0 0}}h1{{font-size:29px;line-height:1.25;margin:7px 0 10px;font-weight:500}}footer{{position:absolute;bottom:5%;left:8%;right:8%;font:11px BookSans;color:#887d6b}}.recto footer{{text-align:right}}
.conclusion-page:before{{content:'';position:absolute;inset:4.7%;border:1px solid rgba(163,126,67,.25);pointer-events:none}}.logic-chain{{margin-top:26px;border-block:1px solid var(--gold)}}.logic-row{{display:grid;grid-template-columns:48px 42px 48px 1fr;align-items:center;gap:9px;padding:18px 8px;border-bottom:1px solid var(--line)}}.logic-row:last-child{{border:0}}.logic-row span{{display:grid;place-items:center;width:44px;height:44px;border:1px solid var(--gold);border-radius:50%;font-size:25px;background:#fffaf0}}.logic-row i{{font:18px BookBrush;color:var(--red);font-style:normal;text-align:center}}.logic-row strong{{font:13px BookSerif;color:var(--jade);font-weight:500;border-left:1px solid var(--line);padding-left:14px}}.reading-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:20px}}.reading-grid section{{padding:14px;border-top:2px solid var(--gold);background:rgba(255,253,247,.58)}}.reading-grid b{{font-size:15px;color:var(--jade)}}.reading-grid p{{font:10px/1.72 BookSans;color:#555048;margin:6px 0 0}}.conclusion-page blockquote{{font:15px/1.7 BookSerif;color:var(--jade);margin:22px 0 0;padding-left:14px;border-left:3px solid var(--gold)}}
.chapter-divider{{padding:0;background:#203b34;color:#f1e6ce}}.chapter-frame{{position:absolute;inset:8%;border:1px solid #b89a60;outline:1px solid rgba(184,154,96,.45);outline-offset:-9px}}.chapter-frame small,.chapter-frame h1,.chapter-frame p,.chapter-frame i{{position:absolute;writing-mode:vertical-rl;white-space:nowrap;margin:0}}.chapter-frame small{{right:10%;bottom:10%;font:11px BookSans;letter-spacing:.3em;color:#c9ac73}}.chapter-frame h1{{right:22%;top:44%;transform:translateY(-50%);font:49px/1 BookBrush;letter-spacing:.14em;font-weight:400}}.chapter-frame p{{right:48%;top:27%;font:20px/1.8 BookSerif;color:#e4d2ae;letter-spacing:.14em}}.chapter-frame i{{right:72%;top:13%;font:normal 10px/1.8 BookSans;color:#b9ad91;letter-spacing:.08em}}.chapter-divider footer{{color:#bda978}}
@media print{{body{{background:#fff}}main{{padding:0}}.spread{{width:296mm;height:210mm;margin:0;filter:none;break-after:page}}.page{{width:148mm;height:210mm}}}}</style></head><body><main><section class="spread">{_page20()}{_page21()}</section></main></body></html>"""


def write_integrated_bridge(destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_integrated_bridge_html(), encoding="utf-8")
    return path
