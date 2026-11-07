/*
 * 织梦 · west-fort 预览场景 b：五座棱堡用斜向 / 正交幕墙连成的星形要塞，南门（gate-h）外一座三角堡。
 * 棱堡以拐点墙格为中心占 3×3：gx = 中心列 - 1，gy（占地最前一行）= 中心行 + 1；排序键 = 前沿 y + 0.45。
 */
(function (root) {
  'use strict';
  root.WFScenesB = function (PV) {
    var B = root.TownArtWF.bastion;
    if (!B) return '';
    var V = [[10, 1], [17, 8], [14, 11], [14, 14], [6, 14], [6, 11], [3, 8]];
    var cells = PV.trace(V);
    var over = { '10,14': 'west-common-wall-gate-h', '14,11': 'west-common-nodetower-round', '6,11': 'west-common-nodetower-round' };
    var list = PV.wallItems(cells, over);
    var BS = { n: [10, 1], e: [17, 8], se: [14, 14], sw: [6, 14], w: [3, 8] };
    Object.keys(BS).forEach(function (d) {
      var c = BS[d];
      list.push(PV.item('west-common-bastion-' + d, c[0] - 1, c[1] + 1, 0.45));
    });
    list.push(PV.item('west-common-ravelin-s', 9.5, 17, 0.45));
    return PV.scene(20, 19, list, 0.9, [0, -96, 20 * 48, 19 * 48 + 96],
      '场景 b：星形要塞——五座棱堡（n / e / se / sw / w）由斜向与正交幕墙相连，南门 gate-h 外一座三角堡 ravelin-s，两处 135° 拐点放圆角楼');
  };
})(this);
