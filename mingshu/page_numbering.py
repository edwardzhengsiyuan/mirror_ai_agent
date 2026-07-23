"""Runtime page-number adjustments used when an earlier chapter gains pages."""

from __future__ import annotations


def page_offset_script(offset: int) -> str:
    return f"""<script>(()=>{{
      const offset={int(offset)};
      document.querySelectorAll('[data-page]').forEach(node=>{{
        const value=node.getAttribute('data-page');
        if (/^\\d+$/.test(value||'')) node.setAttribute('data-page', String(Number(value)+offset));
      }});
      document.querySelectorAll('footer').forEach(node=>{{
        const value=(node.textContent||'').trim();
        if (/^\\d+$/.test(value)) node.textContent=String(Number(value)+offset);
      }});
    }})()</script>"""
