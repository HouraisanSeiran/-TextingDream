/*
 * 织梦 · 西式防御工事 —— 棱堡 bastion-<dir>（3×3）与三角堡 ravelin-<n|s|e|w>（2×2），category = fort
 * 棱堡放在城墙 90° 拐点（墙节点）上，以该墙格为中心占 3×3；两条幕墙（arms，= 尖角方向 ±135°）穿过棱堡的
 * 喉部（gorge）从占地格边中点（正交臂）或格角（斜臂）接出。占地内墙格的辐条照常画，棱堡排序键
 * = 占地前沿 y + 0.45 画在其后：棱堡台面（高 44，墙高 40）盖住幕墙外侧一半，墙内一半与内侧立面照常露出。
 * 两种模板：尖角正交（n，两臂斜向 sw/se）、尖角斜向（ne，两臂正交 w/s）；其余方向按 90° 旋转得到。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWF.core;
  var G = isNode ? require('./geom.js') : root.TownArtWF.geom;
  var PAL = C.PAL, f = C.f, H = 44, WH = 40;
  var DIRS = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'];
  var DNAME = { n: '北', ne: '东北', e: '东', se: '东南', s: '南', sw: '西南', w: '西', nw: '西北' };
  /** 顺时针转 90°×k（y 向下的坐标里 (x, y) → (-y, x)） */
  function rot(p, k) { var x = p[0], y = p[1]; for (var i = 0; i < k; i++) { var t = x; x = -y; y = t; } return [x, y]; }
  function rotDir(d, k) { return DIRS[(DIRS.indexOf(d) + 2 * k) % 8]; }
  // 相对占地中心的轮廓；第 0、5 条边是喉部（open），第 1、4 条是侧翼（flank），第 2、3 条是棱面，顶点 3 是尖角
  var TPL = {
    n: { poly: [[0, 0], [-72, 72], [-72, -12], [0, -70], [72, -12], [72, 72]], arms: ['sw', 'se'] },
    ne: { poly: [[0, 0], [-72, 0], [-72, -24], [66, -66], [24, 72], [0, 72]], arms: ['w', 's'] }
  };
  var KINDS = ['open', 'wall', 'wall', 'wall', 'wall', 'open'];
  function shape(dir) {
    var k = DIRS.indexOf(dir), t = TPL[k % 2 ? 'ne' : 'n'], q = (k - k % 2) / 2;
    return { poly: t.poly.map(function (p) { return rot(p, q); }), arms: t.arms.map(function (a) { return rotDir(a, q); }) };
  }
  function norm(v) { var L = Math.hypot(v[0], v[1]) || 1; return [v[0] / L, v[1] / L]; }
  /** 棱角哨亭（guérite）：小圆筒 + 青石板穹顶 */
  function guerite(ctx, x, y, z) {
    var r = 4.6, z1 = z + 13, s = '';
    var body = 'M' + f(x - r) + ' ' + f(y - z1) + 'V' + f(y - z) + 'A' + f(r) + ' ' + f(r) + ' 0 0 0 ' + f(x + r) + ' ' + f(y - z) + 'V' + f(y - z1) + 'Z';
    s += C.path(body, PAL.stone, 1.2) + C.poly([[x + 1.6, y - z1], [x + r, y - z1], [x + r, y - z], [x + 1.6, y - z + r * 0.95]], PAL.stone2, 0);
    s += C.path(body, 'none', 1.2) + C.poly([[x - 0.9, y - z - 4], [x - 0.9, y - z - 9], [x + 0.9, y - z - 9], [x + 0.9, y - z - 4]], PAL.hole, 0);
    s += C.path('M' + f(x - r - 1) + ' ' + f(y - z1) + 'A' + f(r + 1) + ' ' + f(r + 1) + ' 0 0 1 ' + f(x + r + 1) + ' ' + f(y - z1) + 'Z', PAL.slate, 1.2);
    s += C.path(C.seg([x, y - z1 - r - 1], [x, y - z1 - r - 4]), 'none', 1.1);
    ctx.top(y - z1 - r - 5);
    return s;
  }
  /** 一门炮：木炮架 + 铁炮管指向 n（外法线） */
  function cannon(q, n, z) {
    var b = [q[0], q[1] - z], e = [q[0] + n[0] * 8, q[1] + n[1] * 8 - z - 1.5];
    var s = C.poly([[b[0] - 3, b[1] + 1.5], [b[0] - 3, b[1] - 2], [b[0] + 3, b[1] - 2], [b[0] + 3, b[1] + 1.5]], PAL.wood, 0.8);
    return s + '<path d="' + C.seg(b, e) + '" stroke="' + PAL.ink + '" stroke-width="3.6" stroke-linecap="round"/>' +
      '<path d="' + C.seg(b, e) + '" stroke="' + PAL.slate2 + '" stroke-width="1.8" stroke-linecap="round"/>';
  }
  // —— bastion() / ravelin() / items() 追加在下面 ——
  /**
   * 通用堡体：rel 为相对中心 (cx, cy) 的地面轮廓；o.tip 尖角顶点序号；o.faces 两条棱面边序号（上炮位）；
   * o.step：喉部切口处补一条 step..h 的台阶立面（棱堡台面比幕墙高 4 px）；o.door：在朝南的 plain 边上开门洞。
   */
  function fortBody(ctx, rel, cx, cy, h, kinds, o) {
    var poly = rel.map(function (p) { return [p[0] + cx, p[1] + cy]; });
    var s = G.prism(ctx, poly, h, kinds, { mode: 'ortho' }), E = G.edges(poly), guns = '';
    E.forEach(function (e, i) {
      if (kinds[i] === 'open' && o.step && e.n[1] > 0.05)
        s += C.poly([[e.a[0], e.a[1] - o.step], [e.b[0], e.b[1] - o.step], [e.b[0], e.b[1] - h], [e.a[0], e.a[1] - h]], PAL.stone2, 1.1);
      if (kinds[i] === 'plain' && o.door && e.n[1] > 0.5) {
        var mx = (e.a[0] + e.b[0]) / 2, my = (e.a[1] + e.b[1]) / 2;
        s += C.path('M' + f(mx - 6) + ' ' + f(my) + 'V' + f(my - 12) + 'A6 6 0 0 1 ' + f(mx + 6) + ' ' + f(my - 12) + 'V' + f(my) + 'Z', PAL.hole, 1.3);
      }
      if (o.faces.indexOf(i) >= 0) [0.32, 0.66].forEach(function (t) {
        guns += cannon([e.a[0] + (e.b[0] - e.a[0]) * t - e.n[0] * 9, e.a[1] + (e.b[1] - e.a[1]) * t - e.n[1] * 9], e.n, h);
      });
    });
    var tp = poly[o.tip], v = norm([cx - tp[0], cy - tp[1]]);
    return s + guns + guerite(ctx, tp[0] + v[0] * 10, tp[1] + v[1] * 10, h);
  }
  function bastion(ctx, dir) {
    var sh = shape(dir);
    return fortBody(ctx, sh.poly, 72, -72, H, KINDS, { tip: 3, faces: [2, 3], step: WH });
  }
  // 三角堡：底边（喉部）朝城门，尖角朝外；高 30，低于城墙
  var RAV = [[-40, 44], [-40, 18], [0, -44], [40, 18], [40, 44]], RK = ['wall', 'wall', 'wall', 'wall', 'plain'];
  var RQ = { n: 0, e: 1, s: 2, w: 3 };
  function ravelin(ctx, dir) {
    var rel = RAV.map(function (p) { return rot(p, RQ[dir]); });
    return fortBody(ctx, rel, 48, -48, 30, RK, { tip: 2, faces: [1, 2], door: true });
  }
  function items() {
    var out = DIRS.map(function (dir, k) {
      var sh = shape(dir);
      return {
        id: 'west-common-bastion-' + dir, fp: [3, 3], draw: function (ctx) { return bastion(ctx, dir); },
        meta: { category: 'fort', kind: 'bastion', facility: 'watchtower', variant: k + 1, dir: dir, arms: sh.arms, sort_offset: 0.45, name: '棱堡（尖角朝' + DNAME[dir] + '）',
          tags: ['bastion', 'dir_' + dir, 'crenellated', 'cannon', 'guerite', 'star_fort'],
          note: '棱堡：五边形尖角堡（两棱面 + 两侧翼 + 喉部），占地 3×3，以城墙拐点墙格为中心；幕墙辐条沿 ' + sh.arms.join(' / ') +
            ' 两个方向从喉部接出（占地内的辐条与墙节点照常画）。台面高 44 px（比幕墙高 4 px，喉部补台阶立面），棱面各两门炮，尖角有哨亭。排序键 = 占地前沿 y + 0.45' }
      };
    });
    ['n', 'e', 's', 'w'].forEach(function (dir, k) {
      out.push({
        id: 'west-common-ravelin-' + dir, fp: [2, 2], draw: function (ctx) { return ravelin(ctx, dir); },
        meta: { category: 'fort', kind: 'ravelin', facility: 'watchtower', variant: k + 1, dir: dir, name: '三角堡（尖角朝' + DNAME[dir] + '）',
          tags: ['ravelin', 'dir_' + dir, 'crenellated', 'cannon', 'outwork'],
          note: '三角堡（ravelin）：放在城门外护城河里的独立三角小堡，尖角朝外、喉部朝城门；高 30 px，低于城墙，棱面各两门炮' }
      });
    });
    return out;
  }
  var API = { H: H, DIRS: DIRS, TPL: TPL, shape: shape, bastion: bastion, ravelin: ravelin, guerite: guerite, cannon: cannon, rot: rot, items: items };
  if (isNode) module.exports = API;
  else root.TownArtWF.bastion = API;
})(this);
