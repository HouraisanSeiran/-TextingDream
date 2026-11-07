/*
 * 织梦 · west-fort 预览页：图册 + 场景 a（不规则八边形城墙）/ b（星形要塞）/ c（格角特写 ×3）。
 */
(function (root) {
  'use strict';
  var PV = root.WFPreview, S = 48, doc = root.document;
  doc.getElementById('sprite').innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;width:0;height:0">' + PV.SYM.join('') + '</svg>';
  // —— 图册 ——
  var atlas = '';
  Object.keys(PV.META).forEach(function (id) {
    var m = PV.META[id];
    if (!/^west-common-(wall(spoke|node)|nodetower|bastion|ravelin|castle|starfort|moat)/.test(id)) return;
    var vb = m.viewBox, z = m.footprint[0] > 3 ? 0.8 : 1.5;
    atlas += '<div class="card"><svg width="' + vb[2] * z + '" height="' + vb[3] * z + '" viewBox="' + vb.join(' ') + '">' +
      '<rect x="0" y="' + (vb[3] - m.footprint[1] * S) + '" width="' + m.footprint[0] * S + '" height="' + m.footprint[1] * S + '" fill="none" stroke="#4a3826" stroke-opacity="0.25" stroke-dasharray="3 3"/>' +
      '<use href="#' + id + '" x="' + vb[0] + '" y="0" width="' + vb[2] + '" height="' + vb[3] + '"/></svg>' +
      id.replace('west-common-', '') + '<br>' + m.footprint.join('×') + '</div>';
  });
  doc.getElementById('atlas').innerHTML = atlas;
  // —— 场景 a：不规则八边形 + 南侧凹口 ——
  var A = [[3, 1], [9, 1], [12, 4], [12, 8], [10, 10], [8, 10], [8, 8], [6, 8], [6, 10], [4, 10], [1, 7], [1, 3]];
  var cellsA = PV.trace(A);
  var tw = root.TownArtWF.towers ? ['west-common-nodetower-round', 'west-common-nodetower-octagon'] : ['west-common-wall-tower-round', 'west-common-wall-tower-square'];
  var overA = { '6,1': 'west-common-wall-gate-h', '9,10': 'west-common-wall-gate-h', '12,6': 'west-common-wall-gate-v', '1,5': 'west-common-wall-gate-v',
    '9,1': tw[0], '12,8': tw[1], '1,3': tw[1], '4,10': tw[0], '3,1': 'west-common-wallnode-02', '12,4': 'west-common-wallnode-02' };
  var html = PV.scene(14, 12, PV.wallItems(cellsA, overA), 1, null, '场景 a：不规则八边形城墙（正交 + 45° 斜段，南侧一个凹口），gate-h / gate-v 来自 west-base，节点放角楼与望台');
  // —— 场景 c：斜段与正交段对接处 ×3 特写（取场景 a 东北角） ——
  html += PV.scene(14, 12, PV.wallItems(cellsA, {}), 3, [7.5 * S, -0.5 * S, 4 * S, 4 * S], '场景 c：东北角 (9,1) 处 W 直段接 SE 斜段，放大 3 倍（墙节点未替换）');
  html += PV.scene(14, 12, PV.wallItems(cellsA, {}), 3, [0, 5 * S, 4 * S, 4 * S], '场景 c2：西南角 (4,10)–(1,7) 斜段接 W 直段，放大 3 倍');
  if (root.WFScenesB) html += root.WFScenesB(PV);
  if (root.WFScenesD) html += root.WFScenesD(PV);
  doc.getElementById('scenes').innerHTML = html;
})(this);
