"""Shared five-element colors for prominent stem, branch, and element glyphs."""

ELEMENT_COLORS = {
    "木": "#315f47",
    "火": "#a9362b",
    "土": "#a5742f",
    "金": "#77756e",
    "水": "#244e68",
}

SYMBOL_ELEMENTS = {
    **{symbol: "木" for symbol in "甲乙寅卯"},
    **{symbol: "火" for symbol in "丙丁巳午"},
    **{symbol: "土" for symbol in "戊己辰戌丑未"},
    **{symbol: "金" for symbol in "庚辛申酉"},
    **{symbol: "水" for symbol in "壬癸亥子"},
    **{symbol: symbol for symbol in "木火土金水"},
}


# Applied only to display-sized glyphs and headings. Body copy stays in the book's
# normal ink color, so the page does not become visually noisy.
ELEMENT_COLOR_SCRIPT = r"""<script>
(() => {
  const elementBySymbol = {
    甲:'木',乙:'木',寅:'木',卯:'木',木:'木',
    丙:'火',丁:'火',巳:'火',午:'火',火:'火',
    戊:'土',己:'土',辰:'土',戌:'土',丑:'土',未:'土',土:'土',
    庚:'金',辛:'金',申:'金',酉:'金',金:'金',
    壬:'水',癸:'水',亥:'水',子:'水',水:'水'
  };
  const colors = {木:'#315f47',火:'#a9362b',土:'#a5742f',金:'#77756e',水:'#244e68'};
  const selectors = [
    '.big-glyph','.cycle-name b','.day-copy h2','.month-copy h2',
    '.qiongtong h2','.tiaohou-gods h2','.god-card>b','.glyph','.pair-glyph',
    '.ghost-glyph','.tri-node text','.empty-node+text','.layer-glyph>b',
    '.branch-glyph>strong','.ss-node .gan','.ss-node .zhi','.flow-node>b',
    '.stem-grid b','.location-flow b','.element-list b','.axis-merge h2',
    '.merge-core b','.pillar-strip b','.synthesis>h1','.elements>h1',
    '.locations>h1','.cycle-heading h1','.year-title h1'
  ].join(',');
  document.querySelectorAll(selectors).forEach((node) => {
    if (node.dataset.wuxingColored === '1') return;
    node.dataset.wuxingColored = '1';
    if (node.namespaceURI === 'http://www.w3.org/2000/svg') {
      const symbol = node.textContent.trim();
      const element = elementBySymbol[symbol];
      if (element) node.style.fill = colors[element];
      return;
    }
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach((textNode) => {
      const fragment = document.createDocumentFragment();
      for (const char of textNode.nodeValue || '') {
        const element = elementBySymbol[char];
        if (!element) {
          fragment.append(char);
          continue;
        }
        const span = document.createElement('span');
        span.className = `wuxing-glyph wuxing-${element}`;
        span.style.color = colors[element];
        span.textContent = char;
        fragment.append(span);
      }
      textNode.replaceWith(fragment);
    });
  });
})();
</script>"""
