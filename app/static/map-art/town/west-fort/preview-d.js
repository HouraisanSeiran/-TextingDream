/*
 * 织梦 · west-fort 预览场景 d：城堡幕墙辐条围成的不规则城堡外环 + 外侧一圈斜向护城河（地面层先画）+ 整体小星堡地标。
 */
(function (root) {
  'use strict';
  root.WFScenesD = function (PV) {
    var WF = root.TownArtWF, CA = WF.castle, MO = WF.moat;
    if (!CA || !MO) return '';
    function ring(verts, prefix, nodeFor, base) {
      var cells = PV.trace(verts), out = [];
      Object.keys(cells).forEach(function (k) {
        var c = cells[k];
        Object.keys(c.dirs).forEach(function (d) { out.push(PV.item(prefix + d, c.x, c.y, base + root.TownArt_westFort.ORDER[d])); });
        out.push(PV.item(nodeFor(c.dirs), c.x, c.y, base + root.TownArt_westFort.ORDER.node));
      });
      return out;
    }
    // 护城河排序键整体减 1000：地面层先于一切墙体
    var moat = ring([[4, 1], [10, 1], [13, 4], [13, 9], [10, 12], [4, 12], [1, 9], [1, 4]], 'west-common-moatspoke-', MO.nodeFor, -1000);
    var wall = ring([[5, 3], [9, 3], [11, 5], [11, 8], [9, 10], [5, 10], [3, 8], [3, 5]], 'west-common-castlespoke-', CA.nodeFor, 0);
    var html = PV.scene(15, 14, moat.concat(wall), 0.9, [0, -110, 15 * 48, 14 * 48 + 110],
      '场景 d：城堡幕墙辐条（墙厚 30、高 60）围成的八边形外环，外绕斜向护城河辐条（地面层）');
    if (WF.starfort) html += PV.scene(8, 8, [PV.item('west-common-starfort-01', 1, 6, 0.5)], 1, [0, -60, 8 * 48, 8 * 48 + 60], '整体小星堡地标 starfort-01（6×6）');
    return html;
  };
})(this);
