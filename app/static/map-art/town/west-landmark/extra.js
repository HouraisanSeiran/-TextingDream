/*
 * 织梦 · 西式文化地标：余项（独立的意大利式钟楼 campanile）
 * draw(c) 的 c = { rnd, W, H, up, id }：占地区 y = up..H；锚点 (W/2, H)。
 * 浏览器挂 window.TownArtWL_extra；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var P = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWL_core;
  var C = P.C, f = P.f, seg = P.seg, ln = P.ln, rect = P.rect, poly = P.poly, path = P.path;
  var defs = [];
  function def(o) { defs.push(o); }

  /** 一层带伦巴第小拱带的檐口：x0..x1，y 檐线 */
  function cornice(x0, x1, y) {
    var d = '', st = 5;
    for (var x = x0 + 1; x < x1 - st + 0.5; x += st) d += 'M' + f(x) + ' ' + f(y + 6) + 'A' + f(st / 2) + ' ' + f(st / 2) + ' 0 0 1 ' + f(x + st) + ' ' + f(y + 6);
    return rect(x0 - 1.5, y - 1.5, x1 - x0 + 3, 3, C.stone3, 1.1) + ln(d, 0.8, 0.7);
  }
  /** n 联拱窗：x0..x1 内，y 拱顶，h 高；小柱分隔 */
  function multiArch(x0, x1, y, h, n) {
    var gap = 2.4, w = (x1 - x0 - gap * (n - 1)) / n, o = path(P.archPath(x0 - 2, y - 2, x1 - x0 + 4, h + 2), C.stone3, 1.1);
    for (var i = 0; i < n; i++) {
      var x = x0 + i * (w + gap);
      o += path(P.archPath(x, y, w, h), C.dark, 1);
      if (i) o += rect(x - gap + 0.3, y + w * 0.5, gap - 0.6, h - w * 0.5, C.stone, 0.6);
    }
    return o;
  }

  // ——————————————————— 独立钟楼（意大利式 campanile） ———————————————————
  def({
    kind: 'campanile', variant: 1, name: '意大利式独立钟楼', fp: [1, 1], up: 200, seed: 5101,
    facility: 'temple', culture: 'romanesque', roof: 'steep_slate',
    tags: ['campanile', 'bell_tower', 'freestanding', 'lombard_band', 'romanesque', 'important'],
    note: '与教堂分开独立的方形砖石钟楼：通高壁柱分格，每层檐下伦巴第小拱带，窗洞自下而上由单拱→双联→三联逐层放大；' +
      '顶层钟室挂钟，红瓦四角攒尖顶与十字。占地 1×1，可放在教堂或广场旁。facility 归 temple（教堂附属）',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', x0 = 9, x1 = 39, cx = 24, h = 196, yt = yf - h + 20;
      o += P.boxShadow(x0, x1, yf - 26, yf, 6, W, H);
      // 攒尖顶 + 十字
      o += P.pyramid(x0, x1, yt, 20, 34, 'tile', { finial: false, ov: 2 }) + P.cross(cx, yt - 10 - 34 - 11, 11);
      // 塔身
      o += P.wall(x0, x1, yt, yf, 'brick', r, { plinth: 8, ch: 5, fill: '#cfae86' });
      o += rect(x0, yt, 3.5, yf - yt, C.stone2, 1) + rect(x1 - 3.5, yt, 3.5, yf - yt, C.stone2, 1);
      // 层位：从下到上
      var lv = [yf - 46, yf - 82, yf - 116, yf - 148];
      lv.forEach(function (y) { o += cornice(x0, x1, y); });
      // 窗：单拱 → 单拱 → 双联 → 三联（钟室）
      o += P.win(cx - 2, yf - 72, 4, 14, { shape: 'arch', panes: false });
      o += P.win(cx - 2.5, yf - 108, 5, 16, { shape: 'arch', panes: false });
      o += multiArch(cx - 7, cx + 7, yf - 140, 18, 2);
      o += multiArch(x0 + 6, x1 - 6, yt + 9, yf - 150 - yt - 11, 3);
      // 钟
      o += path('M' + f(cx - 3.5) + ' ' + f(yt + 24) + 'Q' + f(cx - 3.5) + ' ' + f(yt + 17) + ' ' + f(cx) + ' ' + f(yt + 17) +
        'Q' + f(cx + 3.5) + ' ' + f(yt + 17) + ' ' + f(cx + 3.5) + ' ' + f(yt + 24) + 'L' + f(cx + 4.5) + ' ' + f(yt + 25.5) + 'L' + f(cx - 4.5) + ' ' + f(yt + 25.5) + 'Z', C.wash, 0.9);
      o += cornice(x0, x1, yt + 1);
      // 门 + 门上小圆窗
      o += P.door(cx, yf, 10, 18, { shape: 'arch', frame: C.stone3 }) + P.circle(cx, yf - 30, 3, C.dark, 1);
      o += ln(seg(x0 + 4, yf - 46, x0 + 4, yt) + seg(x1 - 4, yf - 46, x1 - 4, yt), 0.8, 0.45);
      void poly;
      return o;
    }
  });

  if (typeof module !== 'undefined' && module.exports) module.exports = defs;
  else root.TownArtWL_extra = defs;
})(typeof window !== 'undefined' ? window : this);
