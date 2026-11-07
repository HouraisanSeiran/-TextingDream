/*
 * 织梦 · 奇幻天气：spirit_mist 灵雾（东方，注册到 WeatherFX_fantasy）
 * fog=流动雾带（低分辨率缓冲：横向正弦带 × 域扭曲 fbm，扭曲量随强度增大形成祥云卷涡，浓淡交界描淡金边）
 *     + 重度白茫遮挡远景（屏幕上方更浓）
 * precip=光点本体（淡金 / 青白，沿噪波流场漂；重度成群）  light=光点辉光与雾的夜间微光（lighter）
 */
(function (root) {
  'use strict';
  var F = root.WeatherFX_fantasy; if (!F) return;
  var U = F.util, TAU = Math.PI * 2;

  F.register('spirit_mist', function (env, seed) {
    var N = env.N, tex = env.tex, R = N.rng(seed), S = 8;
    var mb = null, I = 0, mg = U.magic(null, 0), nt = 0, wd = { x: 0, y: 0 }, frame = 0, sx = 0, sy = 0;
    var motes = [], clusters = [], veil = null, veilKey = '';
    var GOLD = [255, 212, 130], JADE = [168, 238, 228], WHITE = [238, 245, 247];

    function mist() {
      var w = mb.w, h = mb.h, d = mb.d, t = env.t;
      var amt = (0.9 + 3.2 * I) * 64, th = 0.52 - 0.36 * I, fill = U.sstep(0.6, 1, I), pw = 3 - 2.2 * U.sstep(0, 0.6, I);
      var period = h / (2.2 + 0.8 * I), sc = 64 / 55, aMax = 120 + 135 * U.sstep(0, 0.6, I);
      for (var j = 0; j < h; j++) {
        for (var i = 0; i < w; i++) {
          var k = j * w + i, o = k * 4;
          var yy = j + (U.samp(tex.b, i * 0.7 + sx * 0.4, j * 0.7) - 0.5) * period * 0.9;
          var band = Math.pow(0.5 + 0.5 * Math.sin(yy * TAU / period + t * 0.04), pw);
          var n = U.warp(tex, (i + sx) * sc, (j + sy) * sc * 1.6, amt);
          var cl = U.sstep(th, th + 0.38, n), v = (band * (0.35 + 0.65 * cl)) * (1 - fill) + (0.45 + 0.55 * cl) * fill;
          v = v > 1 ? 1 : v;
          var rim = U.sstep(0.15, 0.5, v) * (1 - U.sstep(0.5, 0.85, v)) * (0.4 + 0.6 * cl);   // 云边淡金
          var m = Math.min(1, U.samp(tex.f, i * 0.8 - sx * 0.3, j * 0.8) * (1 + 0.6 * I));   // 中重度青色更显，和浅色地面拉开
          d[o] = WHITE[0] + (JADE[0] - WHITE[0]) * m + (GOLD[0] - WHITE[0]) * rim;
          d[o + 1] = WHITE[1] + (JADE[1] - WHITE[1]) * m + (GOLD[1] - WHITE[1]) * rim;
          d[o + 2] = WHITE[2] + (JADE[2] - WHITE[2]) * m + (GOLD[2] - WHITE[2]) * rim * 1.2;
          d[o + 3] = v * aMax;
        }
      }
    }
    // 流场方向：3D 噪波（第三维 = 时间）给角度，光点顺着雾流打旋
    function flow(x, y) { return N.noise3(seed, x / 260, y / 260, env.t * 0.06) * TAU * 2; }
    function spawn(p) {
      var W = env.W, H = env.H, grp = clusters.length && R() < U.sstep(0.55, 0.95, I);
      if (grp) { var c = clusters[(R() * clusters.length) | 0], a = R() * TAU, r = Math.pow(R(), 0.6) * c.r; p.x = c.x + Math.cos(a) * r; p.y = c.y + Math.sin(a) * r * 0.7; }
      else { p.x = R() * W; p.y = R() * H; }
      p.life = 0; p.max = 3 + R() * 5; p.ph = R() * TAU; p.sz = 1 + R() * 1.8; p.gold = R() < 0.55; p.tw = 1 + R() * 2.5;
      return p;
    }
    function count() { return Math.round(10 + 230 * Math.pow(I, 1.3)); }

    return {
      resize: function () {
        mb = U.buf(Math.ceil(env.W / S), Math.ceil(env.H / S)); veil = null; veilKey = '';
        var r = N.rng(seed ^ 0x77); clusters = [];
        for (var q = 0; q < 5; q++) clusters.push({ x: r() * env.W, y: r() * env.H, r: 60 + r() * 90, a: r() * TAU });
      },
      update: function (st, dt) {
        I = U.clamp(+st.intensity || 0, 0, 1); mg = U.magic(st, I); nt = U.night(st); wd = U.wind(st, 36);
        sx += (wd.x + 10) * dt / S; sy += wd.y * dt / S * 0.5;
        if ((frame++ & 1) === 0) mist();
        clusters.forEach(function (c) {                                   // 光群缓慢绕圈漂移，出界从另一边回来
          c.a += dt * 0.1; c.x += (wd.x * 0.6 + Math.cos(c.a) * 14) * dt; c.y += (wd.y * 0.6 + Math.sin(c.a) * 9) * dt;
          if (c.x < -150) c.x += env.W + 300; if (c.x > env.W + 150) c.x -= env.W + 300;
          if (c.y < -150) c.y += env.H + 300; if (c.y > env.H + 150) c.y -= env.H + 300;
        });
        var want = count();
        while (motes.length < want) motes.push(spawn({}));
        if (motes.length > want) motes.length = want;
        for (var i = 0; i < motes.length; i++) {
          var p = motes[i], a = flow(p.x, p.y), sp = 10 + 8 * I; p.life += dt;
          p.x += (wd.x * 0.7 + Math.cos(a) * sp) * dt; p.y += (wd.y * 0.7 + Math.sin(a) * sp - 3) * dt;
          if (p.life > p.max || p.x < -20 || p.x > env.W + 20 || p.y < -20 || p.y > env.H + 20) spawn(p);
        }
      },
      precip: function (ctx) {
        var t = env.t;
        for (var i = 0; i < motes.length; i++) {
          var p = motes[i], a = U.sstep(0, 0.8, p.life) * (1 - U.sstep(p.max - 1, p.max, p.life)) * (0.55 + 0.45 * Math.sin(t * p.tw + p.ph));
          if (a < 0.03) continue;
          ctx.fillStyle = U.rgba(p.gold ? [255, 236, 180] : [225, 252, 255], Math.min(1, a));
          ctx.fillRect(p.x - p.sz * 0.5, p.y - p.sz * 0.5, p.sz, p.sz);
        }
      },
      fog: function (ctx) {
        var W = env.W, H = env.H, hv = U.sstep(0.3, 1, I), key = hv.toFixed(2) + '/' + nt.toFixed(2);
        U.blit(ctx, mb, W, H, 0.6 + 0.35 * U.sstep(0, 0.6, I) - 0.15 * nt);
        if (hv > 0.01) {                                                   // 重度白茫：远景（屏幕上方）先被吞没
          if (veilKey !== key) {
            veilKey = key; veil = ctx.createLinearGradient(0, 0, 0, H);
            var c = nt > 0.5 ? [150, 172, 190] : [228, 238, 240];
            veil.addColorStop(0, U.rgba(c, 0.75 * hv)); veil.addColorStop(0.55, U.rgba(c, 0.42 * hv)); veil.addColorStop(1, U.rgba(c, 0.22 * hv));
          }
          ctx.fillStyle = veil; ctx.fillRect(0, 0, W, H);
        }
      },
      light: function (ctx) {
        var W = env.W, H = env.H, t = env.t, g = 0.4 + 0.6 * nt;
        if (nt > 0.05) U.blit(ctx, mb, W, H, 0.12 * nt * (0.5 + 0.5 * mg.strength), 'lighter');   // 夜里雾带泛微光
        ctx.globalCompositeOperation = 'lighter';
        var sg = U.glow(GOLD, 16), sj = U.glow(JADE, 16);
        for (var i = 0; i < motes.length; i++) {
          var p = motes[i], a = U.sstep(0, 0.8, p.life) * (1 - U.sstep(p.max - 1, p.max, p.life)) * (0.55 + 0.45 * Math.sin(t * p.tw + p.ph));
          a *= g * (0.5 + 0.6 * mg.strength); if (a < 0.03) continue;
          var r = p.sz * 5; ctx.globalAlpha = Math.min(1, a); ctx.drawImage(p.gold ? sg : sj, p.x - r, p.y - r, r * 2, r * 2);
        }
        ctx.globalAlpha = 1;
      },
      dispose: function () { motes = []; }
    };
  });
})(typeof window !== 'undefined' ? window : this);
