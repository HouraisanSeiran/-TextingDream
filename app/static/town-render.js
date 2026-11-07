/* Local-only SVG renderer. No world-map state or application service required. */
(function (root) {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const holders = new WeakMap();
  function element(name, attrs) {
    const node = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(key => node.setAttribute(key, attrs[key]));
    return node;
  }
  function render(container, layout, catalog) {
    if (typeof container === 'string') container = document.querySelector(container);
    if (!container) throw new Error('TownRender container not found');
    let holder = holders.get(catalog);
    if (!holder || !holder.isConnected) {
      holder = element('svg', { width: 0, height: 0, 'aria-hidden': 'true' });
      holder.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
      holder.innerHTML = catalog.sprite;
      document.body.prepend(holder);
      holders.set(catalog, holder);
    }
    const metadata = new Map(catalog.meta.map(m => [m.id, m]));
    const grid = layout.grid, cell = grid.cell;
    // v2 layouts: underlay (base texture, yards, water tiles, moat passes) is drawn first in
    // array order; item.x already includes viewBox[0] (pad_x), keys include same-cell offsets.
    const underlay = layout.underlay || [];
    const ordered = underlay.concat(layout.ground || [],
      (layout.items || []).slice().sort((a, b) => a.key - b.key || a.x - b.x));
    let left = -cell, top = -cell, right = (grid.w + 1) * cell, bottom = (grid.h + 1) * cell;
    ordered.forEach(it => {
      const m = metadata.get(it.id);
      if (!m) return;
      left = Math.min(left, it.x); top = Math.min(top, it.bottom - m.anchor[1]);
      right = Math.max(right, it.x + m.viewBox[2]);
      bottom = Math.max(bottom, it.bottom - m.anchor[1] + m.viewBox[3]);
    });
    const svg = element('svg', { viewBox: [left, top - 12, right - left, bottom - top + 24].join(' '),
      role: 'img', 'aria-label': 'Town layout', preserveAspectRatio: 'xMidYMid meet' });
    svg.style.cssText = 'display:block;width:100%;height:auto';
    svg.append(element('rect', { x: left, y: top - 12, width: right - left,
      height: bottom - top + 24,
      fill: { east: '#ced6aa', arab: '#e3cf9f' }[layout.style] || '#bfcba9' }));
    // Legacy layouts have no water tiles: keep the flat placeholder squares for them.
    if (!underlay.some(it => it.layer === 'water')) {
      (grid.water || []).forEach(p => svg.append(element('rect', {
        x: p[0] * cell, y: p[1] * cell, width: cell, height: cell, fill: '#7eafb8'
      })));
    }
    ordered.forEach(it => {
      const m = metadata.get(it.id);
      if (!m) return;
      const use = element('use', { href: '#' + it.id, x: it.x,
        y: it.bottom - m.anchor[1] + (m.viewBox[1] || 0), width: m.viewBox[2], height: m.viewBox[3] });
      if (it.source) use.setAttribute('data-town-source', it.source);
      const title = element('title');
      title.textContent = it.name || m.name_zh || m.name || m.facility || m.id;
      use.append(title); svg.append(use);
    });
    container.replaceChildren(svg);
    return svg;
  }
  root.TownRender = { render };
})(window);
