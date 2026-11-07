/*
 * 织梦 · 奇幻天气：miasma 瘴气（注册到 WeatherFX_fantasy）
 * fog=黄绿浊雾：低分辨率缓冲，密度 = 场景权重（道路 / 空地 / 水面=低洼更浓）× 两层反向滚动的域扭曲噪波（翻滚感）；
 *     强度越高越漫出道路，重度铺满全屏，再用 scene.buildings 的屋顶带（roofY 起往下约 45%）destination-out 挖掉 → 只露屋顶。
 * precip=浊雾里缓慢上浮的孢子点  light=整体黄绿浊色 + 夜间微弱磷光（lighter）
 */
(function (root) {
  'use strict';
  var F = root.WeatherFX_fantasy; if (!F) return;
  var U = F.util;

  F.register('miasma', function (env, seed) {
    var N = env.N, tex = env.tex, R = N.rng(seed), S = 8;
    var mb = null, mw = null, mid = null, roofs = null, I = 0, nt = 0, wd = { x: 0, y: 0 }, frame = 0, sx = 0, sy = 0;
    var spores = [], DARK = [96, 112, 40], PALE = [196, 206, 112];

    function weights() {                                   // 缓冲像素对应的场景权重（低洼 / 道路 = 1）
      if (!mb) return;
      var M = U.sceneMask(env.scene, env.W, env.H, 24, 1); mw = new Float32Array(mb.w * mb.h);
      for (var j = 0; j < mb.h; j++) for (var i = 0; i < mb.w; i++) mw[j * mb.w + i] = U.maskAt(M, i * S + S / 2, j * S + S / 2);
    }
    function roofMask() {                                  // 屋顶带遮罩（1/2 分辨率，模糊软边），重度时从雾里挖掉
      var W = env.W, H = env.H, raw = U.canvas(W / 2, H / 2), x = raw.getContext('2d');
      roofs = U.canvas(W / 2, H / 2);
      x.scale(0.5, 0.5);
      ((env.scene && env.scene.buildings) || []).forEach(function (b) {
        var y0 = b.roofY, y1 = b.y + b.h * 0.5, g = x.createLinearGradient(0, y0, 0, y1);
        g.addColorStop(0, 'rgba(0,0,0,1)'); g.addColorStop(0.7, 'rgba(0,0,0,0.85)'); g.addColorStop(1, 'rgba(0,0,0,0)');
        x.fillStyle = g; x.fillRect(b.x + b.w * 0.1, y0, b.w * 0.8, y1 - y0);
      });
      var rx = roofs.getContext('2d'); rx.filter = 'blur(5px)'; rx.drawImage(raw, 0, 0); rx.filter = 'none';
    }
    function field() {
      var w = mb.w, h = mb.h, d = mb.d, spread = U.sstep(0.15, 0.95, I), base = 0.6 + 0.4 * U.sstep(0, 0.6, I);
      var th = 0.44 - 0.2 * I, aMax = 175 + 80 * I, sc = 64 / 40;          // 轻度也沿道路连成薄带
      for (var j = 0; j < h; j++) for (var i = 0; i < w; i++) {
        var k = j * w + i, o = k * 4, wt = mw ? mw[k] : 0.35;
        var n1 = U.warp(tex, (i + sx) * sc, (j + sy) * sc, 150), n2 = U.samp(tex.a, (i - sx * 0.7) * sc * 1.7 + 90, (j + sx * 0.3) * sc * 1.7);
        var n = n1 * 0.62 + n2 * 0.38;
        var occ = wt + (1 - wt) * spread * 0.85;                  // 强度高时漫出道路
        var v = U.sstep(th - 0.2, th + 0.25, n * (0.55 + 0.6 * occ)) * occ * base;
        var thick = U.sstep(0.65, 0.95, I);                        // 浓瘴：整片铺底，只靠屋顶遮罩露出屋顶
        if (thick > 0) v = Math.max(v, thick * (0.8 + 0.2 * n));
        v = v > 1 ? 1 : v;
        var m = U.sstep(0.45, 0.85, n2);
        d[o] = DARK[0] + (PALE[0] - DARK[0]) * m; d[o + 1] = DARK[1] + (PALE[1] - DARK[1]) * m; d[o + 2] = DARK[2] + (PALE[2] - DARK[2]) * m;
        d[o + 3] = v * aMax;
      }
    }
    function spawn(p, init) {
      var tries = 0; do { p.x = R() * env.W; p.y = R() * env.H; tries++; }
      while (tries < 6 && mw && R() > mw[U.clamp((p.y / S) | 0, 0, mb.h - 1) * mb.w + U.clamp((p.x / S) | 0, 0, mb.w - 1)] + 0.15 * I);
      p.life = init ? R() * 4 : 0; p.max = 3 + R() * 4; p.sz = 1 + R() * 1.6; p.ph = R() * 6.28;
      return p;
    }
    return {
      resize: function () { mb = U.buf(Math.ceil(env.W / S), Math.ceil(env.H / S)); mid = U.canvas(env.W / 2, env.H / 2); weights(); roofMask(); },
      setScene: function () { weights(); roofMask(); },
      update: function (st, dt) {
        I = U.clamp(+st.intensity || 0, 0, 1); nt = U.night(st); wd = U.wind(st, 18);
        sx += (wd.x + 4) * dt / S; sy += (wd.y + 1.5) * dt / S;
        if ((frame++ & 1) === 0) field();
        var want = Math.round(12 + 140 * I);
        while (spores.length < want) spores.push(spawn({}, true));
        if (spores.length > want) spores.length = want;
        for (var i = 0; i < spores.length; i++) {
          var p = spores[i]; p.life += dt; p.x += (wd.x + Math.sin(env.t * 0.8 + p.ph) * 5) * dt; p.y += (wd.y - 7) * dt;
          if (p.life > p.max) spawn(p, false);
        }
      },
      precip: function (ctx) {
        for (var i = 0; i < spores.length; i++) {
          var p = spores[i], a = Math.sin(Math.PI * U.clamp(p.life / p.max, 0, 1)) * 0.6;
          ctx.fillStyle = U.rgba([214, 226, 120], a); ctx.fillRect(p.x, p.y, p.sz, p.sz);
        }
      },
      fog: function (ctx) {
        var W = env.W, H = env.H, cut = U.sstep(0.55, 0.85, I), mx = mid.getContext('2d');
        mb.flush(); mx.globalCompositeOperation = 'copy'; mx.imageSmoothingEnabled = true; mx.drawImage(mb.cv, 0, 0, mid.width, mid.height);
        if (cut > 0.01 && roofs) { mx.globalCompositeOperation = 'destination-out'; mx.globalAlpha = cut; mx.drawImage(roofs, 0, 0); mx.globalAlpha = 1; }
        mx.globalCompositeOperation = 'source-over';
        ctx.imageSmoothingEnabled = true; ctx.globalAlpha = 0.9 - 0.25 * nt; ctx.drawImage(mid, 0, 0, W, H); ctx.globalAlpha = 1;
      },
      light: function (ctx) {
        var W = env.W, H = env.H;
        ctx.fillStyle = U.rgba([110, 120, 40], 0.05 + 0.14 * I); ctx.fillRect(0, 0, W, H);   // 整体浊黄绿
        if (nt > 0.05) {                                                                      // 夜间磷光
          ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = 0.16 * nt * (0.4 + 0.6 * I); ctx.drawImage(mid, 0, 0, W, H);
          var sp = U.glow([170, 220, 90], 8);
          for (var i = 0; i < spores.length; i++) {
            var p = spores[i], a = Math.sin(Math.PI * U.clamp(p.life / p.max, 0, 1)) * 0.7 * nt; if (a < 0.03) continue;
            ctx.globalAlpha = a; ctx.drawImage(sp, p.x - 6, p.y - 6, 12, 12);
          }
          ctx.globalAlpha = 1;
        }
      },
      dispose: function () { spores = []; }
    };
  });
})(typeof window !== 'undefined' ? window : this);
