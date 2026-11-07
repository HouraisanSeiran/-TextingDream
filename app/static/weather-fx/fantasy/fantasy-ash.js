/*
 * 织梦 · 奇幻天气：ashfall 灰烬雨（注册到 WeatherFX_fantasy）
 * ground=积灰（低分辨率缓冲：可平铺 fbm × 场景权重，按 ground.ash_cover 阈值显出，cover 变化时才重算）
 * precip=灰黑飘落屑（三层景深，比雪落得快、翻转打旋；按深浅分三桶合批 fill）+ 火星本体（中度偶发，重度频繁，上升熄灭）
 * fog=重度时的灰霾（上方更浓）  light=昏红褐调色 + 火星辉光（lighter）
 */
(function (root) {
  'use strict';
  var F = root.WeatherFX_fantasy; if (!F) return;
  var U = F.util, TAU = Math.PI * 2;

  F.register('ashfall', function (env, seed) {
    var N = env.N, tex = env.tex, R = N.rng(seed), S = 6;
    var gb = null, gw = null, gKey = '', I = 0, nt = 0, wd = { x: 0, y: 0, gust: 0 }, cover = 0;
    var flakes = [], embers = [], haze = null, hazeKey = '';
    var SHADES = [[52, 48, 46], [86, 80, 76], [128, 122, 116]];

    function weights() {
      if (!gb) return;
      var M = U.sceneMask(env.scene, env.W, env.H, 24, 0); gw = new Float32Array(gb.w * gb.h);
      for (var j = 0; j < gb.h; j++) for (var i = 0; i < gb.w; i++) gw[j * gb.w + i] = U.maskAt(M, i * S + S / 2, j * S + S / 2);
      gKey = '';
    }
    function layAsh() {                                    // 积灰：开阔地 / 道路先积，水面不积
      var w = gb.w, h = gb.h, d = gb.d, c = cover;
      for (var j = 0; j < h; j++) for (var i = 0; i < w; i++) {
        var k = j * w + i, o = k * 4, wt = gw ? gw[k] : 0.5;
        var n = U.samp(tex.a, i * 2.6, j * 2.6) * 0.55 + U.samp(tex.f, i * 4.3, j * 4.3) * 0.45;
        var s = n * 0.5 + wt * 0.5, th = 1.0 - c * 0.95;
        var v = U.sstep(th - 0.05, th + 0.1, s) * (0.5 + 0.5 * c) * (0.08 + 0.92 * wt);   // 主要积在道路 / 空地，屋顶上只有极淡一层
        var g = 150 + 50 * U.samp(tex.f, i * 3.7 + 40, j * 3.7);  // 浅灰，带颗粒起伏
        d[o] = g; d[o + 1] = g * 0.97; d[o + 2] = g * 0.95; d[o + 3] = v * 215;
      }
    }
    function spawnFlake(p, top) {
      p.z = 0.4 + 0.6 * Math.pow(R(), 0.7); p.x = R() * (env.W + 200) - 100; p.y = top ? -10 - R() * 60 : R() * env.H;
      p.sz = (1.6 + R() * 2.6) * p.z; p.ph = R() * TAU; p.sp = 1.5 + R() * 3; p.sw = 6 + R() * 18; p.sh = (R() * 3) | 0;
      p.v = (38 + R() * 30) * (0.5 + 0.7 * p.z); return p;
    }
    function spawnEmber() {
      var W = env.W, H = env.H;
      embers.push({ x: R() * W, y: H * (0.35 + R() * 0.65), vx: (R() - 0.5) * 20, vy: -(25 + R() * 45), life: 0, max: 1.2 + R() * 2.2,
        ph: R() * TAU, sz: 1.2 + R() * 1.6 });
    }
    return {
      resize: function () { gb = U.buf(Math.ceil(env.W / S), Math.ceil(env.H / S)); weights(); haze = null; },
      setScene: function () { weights(); },
      update: function (st, dt) {
        I = U.clamp(+st.intensity || 0, 0, 1); nt = U.night(st); wd = U.wind(st, 120); cover = U.ground(st, 'ash_cover');
        var key = cover.toFixed(2); if (key !== gKey && gb) { gKey = key; layAsh(); }
        var want = Math.round(40 + 1100 * Math.pow(I, 1.4)), t = env.t;
        while (flakes.length < want) flakes.push(spawnFlake({}, false));
        if (flakes.length > want) flakes.length = want;
        var gust = 1 + wd.gust * 0.8 * Math.sin(t * 0.9) * Math.sin(t * 0.37);
        for (var i = 0; i < flakes.length; i++) {
          var p = flakes[i], sw = Math.sin(t * p.sp * 0.5 + p.ph) * p.sw;   // 左右打旋
          p.x += (wd.x * gust * p.z + sw * 0.9) * dt; p.y += (p.v + wd.y * p.z * 0.5) * dt;
          if (p.y > env.H + 10 || p.x < -120 || p.x > env.W + 120) spawnFlake(p, true);
        }
        var rate = I < 0.3 ? 0 : I < 0.7 ? 0.6 * (I - 0.3) / 0.4 : 3 + 22 * (I - 0.7);   // 火星每秒个数
        if (R() < rate * dt) spawnEmber(); if (rate > 30 && R() < (rate - 30) * dt) spawnEmber();
        for (i = embers.length - 1; i >= 0; i--) {
          var e = embers[i]; e.life += dt; e.vy *= 1 - 0.3 * dt;
          e.x += (e.vx + wd.x * 0.3 + Math.sin(e.life * 6 + e.ph) * 12) * dt; e.y += e.vy * dt;
          if (e.life > e.max) embers.splice(i, 1);
        }
      },
      ground: function (ctx) { if (cover > 0.01) U.blit(ctx, gb, env.W, env.H, 0.92); },
      precip: function (ctx) {
        var t = env.t;
        for (var s = 0; s < 3; s++) {                                  // 三种灰度各合批一次 fill
          ctx.beginPath();
          for (var i = 0; i < flakes.length; i++) {
            var p = flakes[i]; if (p.sh !== s) continue;
            var a = t * p.sp + p.ph, w = p.sz * (0.25 + 0.75 * Math.abs(Math.cos(a))), h = p.sz * 0.7, c = Math.cos(a * 0.6), sn = Math.sin(a * 0.6);
            var ux = c * w, uy = sn * w, vx = -sn * h, vy = c * h;
            ctx.moveTo(p.x - ux - vx, p.y - uy - vy); ctx.lineTo(p.x + ux - vx * 0.6, p.y + uy - vy * 0.6);
            ctx.lineTo(p.x + ux + vx, p.y + uy + vy); ctx.lineTo(p.x - ux + vx * 0.7, p.y - uy + vy * 0.7); ctx.closePath();
          }
          ctx.fillStyle = U.rgba(SHADES[s], 0.62 + 0.12 * s); ctx.fill();
        }
        for (i = 0; i < embers.length; i++) {
          var e = embers[i], k = e.life / e.max, f = (1 - k) * (0.6 + 0.4 * Math.sin(e.life * 25 + e.ph));
          ctx.fillStyle = U.rgba([255, Math.round(200 - 140 * k), Math.round(80 - 60 * k)], f);
          ctx.fillRect(e.x - e.sz / 2, e.y - e.sz / 2, e.sz, e.sz);
        }
      },
      fog: function (ctx) {
        var W = env.W, H = env.H, hv = U.sstep(0.45, 1, I), key = hv.toFixed(2) + '/' + nt.toFixed(1);
        if (hv < 0.01) return;
        if (hazeKey !== key) {
          hazeKey = key; haze = ctx.createLinearGradient(0, 0, 0, H);
          var c = [96 - 40 * nt | 0, 84 - 36 * nt | 0, 76 - 30 * nt | 0], ka = 1 - 0.35 * nt;   // 夜里减淡，别把城整片吞掉
          haze.addColorStop(0, U.rgba(c, 0.55 * hv * ka)); haze.addColorStop(0.5, U.rgba(c, 0.26 * hv * ka)); haze.addColorStop(1, U.rgba(c, 0.14 * hv * ka));
        }
        ctx.fillStyle = haze; ctx.fillRect(0, 0, W, H);
      },
      light: function (ctx) {
        var W = env.W, H = env.H, red = U.sstep(0.15, 0.7, I);
        // 昏红：白天红褐暗调，夜里天际像远处火光映红（屏幕上方更红）
        var g = ctx.createLinearGradient(0, 0, 0, H);
        g.addColorStop(0, U.rgba([150, 52, 22], (0.1 + 0.26 * red) * (1 - 0.25 * nt)));
        g.addColorStop(1, U.rgba([90, 38, 20], (0.04 + 0.14 * red) * (1 - 0.4 * nt)));
        ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
        if (nt > 0.05 && red > 0) {
          ctx.globalCompositeOperation = 'lighter'; var eg = ctx.createLinearGradient(0, 0, 0, H * 0.35);
          eg.addColorStop(0, U.rgba([150, 40, 10], 0.22 * red * nt)); eg.addColorStop(1, 'rgba(150,40,10,0)');
          ctx.fillStyle = eg; ctx.fillRect(0, 0, W, H * 0.35);
        }
        if (!embers.length) return;
        ctx.globalCompositeOperation = 'lighter'; var sp = U.glow([255, 120, 40], 12);
        for (var i = 0; i < embers.length; i++) {
          var e = embers[i], k = e.life / e.max, f = (1 - k) * (0.6 + 0.4 * Math.sin(e.life * 25 + e.ph)) * (0.6 + 0.5 * nt);
          var r = 9 + e.sz * 3; ctx.globalAlpha = Math.min(1, f); ctx.drawImage(sp, e.x - r, e.y - r, r * 2, r * 2);
        }
        ctx.globalAlpha = 1;
      },
      dispose: function () { flakes = []; embers = []; }
    };
  });
})(typeof window !== 'undefined' ? window : this);
