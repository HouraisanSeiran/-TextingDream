/*
 * 织梦 · west-ground 预览：图册（全部 symbol，带 id 与中文名；摆件画锚点与占地框）（仅预览页使用）
 * 依赖 preview-scene.js 先跑（window.WGPrev）。
 */
(function (root) {
  'use strict';
  var V = root.WGPrev, NS = V.NS;
  var GROUPS = [
    ['water', null, '水面双网格（自然河岸 bank / 石砌码头岸 quay，各 16 张，0000 为透明占位）'],
    ['ground', null, '地面：草地底纹 grass-01..04 + 踩实土地/院坪双网格 dirt × 16'],
    ['prop', 'common', '通用地面摆件（锚点 = 红点，占地 = 虚线框，48 px 网格 1:1 与放大）'],
    ['prop', 'elf', '精灵摆件'], ['prop', 'dwarf', '矮人摆件'], ['prop', 'orc', '兽人摆件']];

  function card(s, sc) {
    var vb = s.viewBox, W = vb[2], H = vb[3], m = 4, isProp = s.meta.category === 'prop';
    var o = '<svg xmlns="' + NS + '" width="' + Math.round((W + 2 * m) * sc) + '" height="' + Math.round((H + 2 * m) * sc) +
      '" viewBox="' + (-m) + ' ' + (-m) + ' ' + (W + 2 * m) + ' ' + (H + 2 * m) + '">';
    if (isProp) {
      o += '<rect x="0" y="' + (H - 48) + '" width="48" height="48" fill="#c9c79a" stroke="#4a3826" stroke-opacity="0.35" stroke-dasharray="3 2"/>';
    } else {
      o += '<rect x="0" y="0" width="48" height="48" fill="#c9c79a" stroke="#4a3826" stroke-opacity="0.25" stroke-dasharray="2 2"/>';
    }
    o += '<use href="#' + s.id + '" x="0" y="0" width="' + W + '" height="' + H + '"/>';
    if (isProp) o += '<circle cx="' + s.meta.anchor[0] + '" cy="' + s.meta.anchor[1] + '" r="1.6" fill="#c0392b"/>';
    o += '</svg>';
    // 摆件另给一张 1:1 小图，检查 48 px 下是否认得出
    var small = isProp ? '<svg xmlns="' + NS + '" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" style="margin-top:3px">' +
      '<rect x="0" y="' + (H - 48) + '" width="48" height="48" fill="#c9c79a"/><use href="#' + s.id + '" width="' + W + '" height="' + H + '"/></svg>' : '';
    return '<div class="card">' + o + small + '<div class="lab"><b>' + s.meta.name + '</b></div><div class="lab"><i>' + s.id + '</i></div></div>';
  }

  var html = '<h2>图册（共 ' + V.all.length + ' 个 symbol）</h2>';
  GROUPS.forEach(function (g) {
    var list = V.all.filter(function (s) { return s.meta.category === g[0] && (!g[1] || s.meta.race === g[1]); });
    if (!list.length) return;
    html += '<h3>' + g[2] + '（' + list.length + '）</h3><div class="grid">' +
      list.map(function (s) { return card(s, g[0] === 'prop' ? 1.6 : 1.5); }).join('') + '</div>';
  });
  document.getElementById('atlas').innerHTML = html;
})(window);
