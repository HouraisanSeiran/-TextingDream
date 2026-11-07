/*
 * 织梦 · arab-base 预览：图册（每个 symbol 一格，标 id 与占地）。依赖 arab-base.js。
 */
(function (root) {
  'use strict';
  var AB = root.TownArt_arabBase;
  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }
  /** 图册：按 category 分组 */
  function atlas(list, host, scale) {
    scale = scale || 1.5;
    var groups = {};
    list.forEach(function (s) { (groups[s.meta.category] = groups[s.meta.category] || []).push(s); });
    Object.keys(groups).forEach(function (cat) {
      host.appendChild(el('h2', {}, cat + '（' + groups[cat].length + '）'));
      var wrap = el('div', { 'class': 'grid' });
      groups[cat].forEach(function (s) {
        var vb = s.viewBox, W = vb[2] * scale, H = vb[3] * scale;
        var card = el('div', { 'class': 'card' });
        var inner = '<svg width="' + W + '" height="' + H + '" viewBox="' + vb.join(' ') + '" overflow="visible">' +
          '<rect x="0" y="' + (vb[3] - s.meta.footprint[1] * 48) + '" width="' + vb[2] + '" height="' + s.meta.footprint[1] * 48 + '" fill="#e3cf9f" stroke="#a97f4c" stroke-dasharray="2 3" stroke-width="0.6"/>' +
          '<use href="#' + s.id + '" x="0" y="0" width="' + vb[2] + '" height="' + vb[3] + '"/>' +
          '<circle cx="' + s.meta.anchor[0] + '" cy="' + s.meta.anchor[1] + '" r="1.6" fill="#c0392b"/></svg>';
        card.innerHTML = inner + '<div class="lab">' + s.id.replace('arab-common-', '') + '<br>' + s.meta.footprint.join('×') + (s.meta.facility ? ' · ' + s.meta.facility : '') + '</div>';
        wrap.appendChild(card);
      });
      host.appendChild(wrap);
    });
  }
  root.ABPreview = { el: el, atlas: atlas };
})(window);
