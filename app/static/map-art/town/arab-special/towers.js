/*
 * 阿拉伯风格塔类画笔：宣礼塔 minaret、风塔 windtower、星形瓷砖塔身 starShaft。
 * 浏览器挂 window.TownArtAS_towers；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var P = N ? require('./parts.js') : root.TownArtAS_parts;
  var Ms = N ? require('./mass.js') : root.TownArtAS_mass;
  var C = K.C, f = K.f;

  /** 宣礼塔：底中心 cx,by；塔身半宽 r；塔身高 h；o.kind 'round'|'square'；o.tiers 阳台层数；o.cap 'dome'|'cone' */
  function minaret(cx, by, r, h, o) {
    o = o || {};
    var s = '', kind = o.kind || 'round', tiers = o.tiers || 1, wall = o.wall || C.lime;
    // 塔基
    s += K.rect(cx - r * 1.35, by - r * 1.6, r * 2.7, r * 1.6, o.base || C.lime2, 1.3);
    var top = by - h;
    s += K.rect(cx - r, top, 2 * r, h - r * 1.6, wall, 1.4);
    s += K.flat([[cx + r * 0.35, top + 1], [cx + r - 0.7, top + 1], [cx + r - 0.7, by - r * 1.6 - 0.7], [cx + r * 0.35, by - r * 1.6 - 0.7]], C.adobe3, 0.22);
    if (kind === 'round') { // 圆塔：竖向细线暗示弧面
      s += K.ln(K.seg(cx - r * 0.55, top + 2, cx - r * 0.55, by - r * 1.6 - 1), 0.6, 0.35);
    } else { // 方塔：拱龛
      for (var q = 0; q < 2; q++) {
        var ay = top + (h - r * 1.6) * (0.35 + q * 0.35);
        s += P.arch(cx - r * 0.45, ay, r * 0.9, r * 2.1, C.hole, 0.7);
      }
    }
    // 阳台层（自上而下均布）
    var seg = (h - r * 1.6) / (tiers + 0.6);
    for (var i = 0; i < tiers; i++) {
      var gy = top + seg * (i + 0.6);
      s += P.tileBand(cx - r, cx + r, gy - 4.2, 3.6, i % 2 === 1);
      s += K.rect(cx - r * 1.45, gy, r * 2.9, 2.6, o.gal || C.lime2, 0.9);
      s += K.poly([[cx - r * 1.45, gy + 2.6], [cx + r * 1.45, gy + 2.6], [cx + r, gy + 5], [cx - r, gy + 5]], C.adobe2, 0.8);
      var dd = ''; for (var b = -1; b <= 1; b += 0.5) dd += K.seg(cx + r * 1.3 * b, gy, cx + r * 1.3 * b, gy - 2.5);
      s += K.ln(dd + K.seg(cx - r * 1.45, gy - 2.5, cx + r * 1.45, gy - 2.5), 0.6, 0.8);
    }
    // 灯笼亭 + 顶
    var lw = r * 0.8, lh = r * 2;
    s += K.rect(cx - lw, top - lh, lw * 2, lh, wall, 1.1);
    s += P.arch(cx - lw * 0.45, top - 1, lw * 0.9, lh * 0.75, C.hole, 0.6);
    s += K.rect(cx - lw * 1.25, top - lh - 1.6, lw * 2.5, 1.6, C.lime2, 0.8);
    if ((o.cap || 'dome') === 'cone') {
      s += K.poly([[cx - lw * 1.1, top - lh - 1.6], [cx, top - lh - r * 3.2], [cx + lw * 1.1, top - lh - 1.6]], o.capFill || C.turq, 1.1);
      s += K.ln(K.seg(cx, top - lh - r * 3.2, cx, top - lh - r * 3.2 - 4), 1, 1, C.gold);
    } else {
      s += Ms.dome(cx, top - lh - 1.6, lw * 1.05, r * 1.9, o.capFill || C.turq, 'pointed');
    }
    return s;
  }

  /** 风塔 barjeel：底中心 cx,by；宽 w；高 h（伸出屋顶部分） */
  function windtower(cx, by, w, h, fill) {
    var s = K.rect(cx - w / 2, by - h, w, h, fill || C.adobe, 1.3);
    s += K.flat([[cx + w * 0.22, by - h + 1], [cx + w / 2 - 0.7, by - h + 1], [cx + w / 2 - 0.7, by - 0.7], [cx + w * 0.22, by - 0.7]], C.adobe3, 0.3);
    // 上部通风槽：竖条
    var n = Math.max(2, Math.round(w / 4)), st = w / n, d = '';
    for (var i = 0; i < n; i++) s += K.rect(cx - w / 2 + st * i + st * 0.25, by - h + 4, st * 0.5, h * 0.4, C.hole, 0.6);
    s += K.rect(cx - w / 2 - 1.2, by - h - 2.2, w + 2.4, 2.2, C.lime2, 0.9);
    s += K.ln(K.seg(cx - w / 2, by - h * 0.45, cx + w / 2, by - h * 0.45), 0.7, 0.6);
    // 四角小柱头
    s += K.rect(cx - w / 2 - 1.2, by - h - 4.5, 2.4, 2.3, C.lime, 0.7) + K.rect(cx + w / 2 - 1.2, by - h - 4.5, 2.4, 2.3, C.lime, 0.7);
    return s + d;
  }

  /** 星形瓷砖塔身：在矩形 x,y,w,h 内铺八角星 + 十字（钴蓝/绿松石） */
  function starTiles(x, y, w, h, r) {
    r = r || 4;
    var s = K.rect(x, y, w, h, C.cobalt, 1.2), st = r * 2.6;
    var nx = Math.max(1, Math.floor(w / st)), ny = Math.max(1, Math.floor(h / st));
    var sx = w / nx, sy = h / ny;
    for (var j = 0; j < ny; j++) for (var i = 0; i < nx; i++) {
      var cx = x + sx * (i + 0.5), cy = y + sy * (j + 0.5);
      s += P.star8(cx, cy, Math.min(r, sx * 0.42, sy * 0.42), (i + j) % 2 ? C.turq2 : C.lime, 0.5);
      s += K.circle(cx, cy, Math.min(r, sx * 0.42) * 0.28, C.gold, 0.4);
    }
    return s;
  }

  var T = { minaret: minaret, windtower: windtower, starTiles: starTiles };
  if (N) module.exports = T; else root.TownArtAS_towers = T;
})(this);
