/*
 * 织梦 · 奇幻天气：mana_storm 魔力风暴（注册到 WeatherFX_fantasy）
 * 层次：fog=暗化天幕 + 域扭曲 fbm 发光云团（低分辨率缓冲，随时间缓慢旋转；重度叠加旋转漩涡）
 *       precip=符文碎光本体（按云团密度场出生、闪烁）  ground=地面晶屑（按 ground.mana_residue，噪波 × 道路权重分布）
 *       light=云团 / 符文 / 晶屑的 lighter 辉光（夜间更亮）  flash=电弧状魔力闪（中度天上，重度连地）
 */
(function (root) {
  'use strict';
  var F = root.WeatherFX_fantasy; if (!F) return;
  var U = F.util, TAU = Math.PI * 2;

  F.register('mana_storm', function (env, seed) {
    var N = env.N, tex = env.tex, R = N.rng(seed), S = 8;      // 云团缓冲：1/8 屏
    var cb = null, dens = null, mask = null, I = 0, mg = U.magic(null, 0), nt = 0, wd = { x: 0, y: 0 }, ang = 0, frame = 0;
    var c1 = [180, 90, 255], c2 = [80, 220, 255];
    var runes = [], arcs = [], shards = [], haze = null, hazeKey = '', resid = 0, flashA = 0, vortex = { x: 0, y: 0, k: 0 };

    // ---------------------------------------------------------------- 云团场（每 2 帧重算一次低分辨率缓冲）
    function cloud() {
      var w = cb.w, h = cb.h, d = cb.d, t = env.t, W = env.W, H = env.H;
      var reach = 0.26 + 1.2 * I, th = 0.56 - 0.3 * I, amt = 1.6 + 2.2 * I;
      var ca = Math.cos(ang), sa = Math.sin(ang), cx = w * 0.5, cy = h * 0.5;
      var vx = vortex.x / S, vy = vortex.y / S, vk = vortex.k, vr = Math.min(w, h) * 0.42, ox = t * 2.2, oy = t * 0.9;
      var sc = 64 / 70;                                           // 70 缓冲像素 ≈ 1 个噪波格（约 560 屏幕像素）
      for (var j = 0; j < h; j++) {
        var sky = 1 - U.sstep(reach * 0.55, reach, j / h);       // 低强度只在屏幕上方（天边）
        for (var i = 0; i < w; i++) {
          var k = j * w + i, o = k * 4;
          if (sky <= 0) { dens[k] = 0; d[o + 3] = 0; continue; }
          var px = i - cx, py = j - cy, qx = px * ca - py * sa + cx, qy = px * sa + py * ca + cy, swirl = 0;
          if (vk > 0) {                                           // 漩涡：离中心越近旋得越多，并朝中心收拢
            var ex = qx - vx, ey = qy - vy, rr = Math.sqrt(ex * ex + ey * ey) / vr, fall = Math.exp(-rr * rr * 1.6);
            var a2 = vk * (2.8 * fall - t * 0.5), c = Math.cos(a2), s = Math.sin(a2);
            if (fall > 0.02) { qx = vx + (ex * c - ey * s) * (1 - 0.25 * fall * vk); qy = vy + (ex * s + ey * c) * (1 - 0.25 * fall * vk); }
            swirl = vk * fall * (0.6 + 0.4 * Math.sin(rr * 18 - t * 3)) * 0.35;
          }
          var n = U.warp(tex, qx * sc + ox, qy * sc + oy, amt * 64);
          var v = U.sstep(th - 0.06, th + 0.5, n) * sky + swirl;
          v = v > 1 ? 1 : v; dens[k] = v;
          var m = U.samp(tex.f, i * 0.9 + ox * 0.6, j * 0.9 - oy); m = m * m * (0.5 + 0.5 * v); // 紫为主，青只在浓处高光
          var e = 0.5 + 0.75 * v + 0.6 * v * (1 - v);
          d[o] = Math.min(255, (c1[0] + (c2[0] - c1[0]) * m) * e);
          d[o + 1] = Math.min(255, (c1[1] + (c2[1] - c1[1]) * m) * e);
          d[o + 2] = Math.min(255, (c1[2] + (c2[2] - c1[2]) * m) * e);
          d[o + 3] = v * 190;
        }
      }
    }
    function densAt(x, y) {
      if (!cb) return 0; var i = U.clamp((x / S) | 0, 0, cb.w - 1), j = U.clamp((y / S) | 0, 0, cb.h - 1); return dens[j * cb.w + i];
    }

    // ---------------------------------------------------------------- 符文碎光
    var SHAPES = [
      [[0, -1, 0.87, 0.5, -0.87, 0.5, 0, -1]],                                    // 三角
      [[0, -1, 0.7, 0, 0, 1, -0.7, 0, 0, -1]],                                    // 菱形
      [[0, -1, 0, 1], [0, -0.5, 0.6, -0.9], [0, 0, 0.6, -0.4]],                    // 似 ᚠ 的竖符
      [[-1, 0, 1, 0], [0, -1, 0, 1], [-0.6, -0.6, 0.6, 0.6]],                      // 星芒
      [[1, 0, 0.5, 0.87, -0.5, 0.87, -1, 0, -0.5, -0.87, 0.5, -0.87, 1, 0]]        // 六边形
    ];
    function spawnRune(p, anywhere) {
      var W = env.W, H = env.H, x = 0, y = 0;
      for (var tries = 0; tries < 8; tries++) {                  // 拒绝采样：落在云团密度高处
        x = R() * W; y = R() * H;
        if (anywhere || R() < densAt(x, y) * 1.1 + 0.03) break;
      }
      p.x = x; p.y = y; p.life = 0; p.max = 2.5 + R() * 4; p.ph = R() * TAU; p.sz = 2.5 + R() * 4.5 * (0.6 + I * 0.6);
      p.sh = (R() * SHAPES.length) | 0; p.rot = R() * TAU; p.vr = (R() - 0.5) * 1.2; p.m = R(); p.tw = 2 + R() * 4;
      return p;
    }
    function runeCount() { return Math.round(8 + 120 * Math.pow(I, 1.25)); }

    // ---------------------------------------------------------------- 地面晶屑（setScene 时按权重图 × 噪波撒点，残留量决定显出多少）
    function layShards() {
      var W = env.W, H = env.H, r = N.rng(seed ^ 0x51ab), M = mask; shards = [];
      for (var tries = 0; tries < 9000 && shards.length < 420; tries++) {
        var x = r() * W, y = r() * H * 0.97 + H * 0.03, n = U.samp(tex.a, x * 0.11, y * 0.11);
        var w = (M ? 0.25 + 0.75 * U.maskAt(M, x, y) : 0.6) * U.sstep(0.35, 0.8, n);
        if (r() > w) continue;
        shards.push({ x: x, y: y, th: r() * 0.92 + 0.04 * (1 - n), sz: 1.6 + r() * 2.8, a: r() * TAU, ph: r() * TAU, m: r() });
      }
      shards.sort(function (a, b) { return a.th - b.th; });
    }

    // ---------------------------------------------------------------- 电弧
    function arcColor(m) { return m < 0.5 ? c1 : c2; }
    function spawnArc(toGround) {
      var W = env.W, H = env.H, x0, y0, x1, y1, p;
      for (var k = 0; k < 6; k++) { x0 = R() * W; y0 = R() * H * (0.12 + 0.5 * I); if (densAt(x0, y0) > 0.35) break; }
      if (toGround) {
        var b = env.scene && env.scene.buildings && env.scene.buildings.length && R() < 0.6 ? env.scene.buildings[(R() * env.scene.buildings.length) | 0] : null;
        if (b) { x1 = b.x + b.w * (0.3 + R() * 0.4); y1 = b.roofY; } else { x1 = x0 + (R() - 0.5) * 260; y1 = H * (0.55 + R() * 0.42); }
        p = U.bolt(R, x0, y0, x1, y1, 0.55, 6);
      } else {
        var a = R() * TAU, L = 120 + R() * 260 * (0.6 + I);
        x1 = x0 + Math.cos(a) * L; y1 = y0 + Math.sin(a) * L * 0.45;
        p = U.bolt(R, x0, y0, x1, y1, 0.7, 5);
      }
      var branches = [];
      for (var q = 0; q < (toGround ? 3 : 1); q++) {                // 分叉
        var s = (2 + ((R() * (p.length / 2 - 4)) | 0)) * 2, ba = R() * TAU, bl = 40 + R() * 90;
        branches.push(U.bolt(R, p[s], p[s + 1], p[s] + Math.cos(ba) * bl, p[s + 1] + Math.abs(Math.sin(ba)) * bl, 0.8, 4));
      }
      arcs.push({ p: p, br: branches, life: 0, max: toGround ? 0.45 : 0.32 + R() * 0.2, g: toGround, m: R(), x: x1, y: y1 });
      flashA = Math.max(flashA, toGround ? 0.16 + 0.12 * I : 0.05 + 0.06 * I);
    }

    // ---------------------------------------------------------------- 接口
    var api = {
      resize: function () {
        cb = U.buf(Math.ceil(env.W / S), Math.ceil(env.H / S)); dens = new Float32Array(cb.w * cb.h); haze = null; layShards();
      },
      setScene: function () { mask = U.sceneMask(env.scene, env.W, env.H, 24, 0.2); layShards(); },
      update: function (st, dt) {
        I = U.clamp(+st.intensity || 0, 0, 1); mg = U.magic(st, I); nt = U.night(st); wd = U.wind(st, 40);
        resid = U.ground(st, 'mana_residue');
        c1 = U.hsl(mg.h, 0.9, 0.62); c2 = U.hsl(mg.h - 0.26, 0.85, 0.6);
        ang += dt * (0.004 + 0.02 * I);                            // 云团整体缓慢旋转
        vortex.k = U.sstep(0.66, 0.9, I);
        vortex.x = env.W * (0.55 + 0.08 * Math.sin(env.t * 0.05)); vortex.y = env.H * (0.3 + 0.05 * Math.cos(env.t * 0.07));
        if ((frame++ & 1) === 0 || !dens) cloud();
        // 符文：数量随强度，按云密度场重生，随风与云漂移
        var want = runeCount();
        while (runes.length < want) runes.push(spawnRune({}, false));
        if (runes.length > want) runes.length = want;
        for (var i = 0; i < runes.length; i++) {
          var p = runes[i]; p.life += dt; p.rot += p.vr * dt;
          p.x += (wd.x + Math.sin(p.ph + env.t * 0.7) * 8) * dt; p.y += (wd.y - 6 + Math.cos(p.ph + env.t * 0.5) * 6) * dt;
          if (vortex.k > 0) { var ex = p.x - vortex.x, ey = p.y - vortex.y, rr = Math.hypot(ex, ey) + 1, f = vortex.k * 90 / (1 + rr / 160);
            p.x += (-ey / rr * f - ex / rr * f * 0.15) * dt; p.y += (ex / rr * f - ey / rr * f * 0.15) * dt; }
          if (p.life > p.max || p.x < -20 || p.x > env.W + 20 || p.y < -20 || p.y > env.H + 20) spawnRune(p, false);
        }
        // 魔力闪：中度间歇天上电弧，重度频繁且连地
        var b = U.band(I), rate = b === 0 ? 0 : b === 1 ? 0.25 + 0.6 * (I - 0.3) : 1.2 + 4 * (I - 0.7);
        rate *= 0.6 + 0.8 * mg.strength;
        if (R() < rate * dt) spawnArc(b === 2 && R() < 0.55);
        for (i = arcs.length - 1; i >= 0; i--) { arcs[i].life += dt; if (arcs[i].life > arcs[i].max) arcs.splice(i, 1); }
        flashA = Math.max(0, flashA - dt * 1.6);
      },
      // -------------------------------------------------------------- ground：晶屑本体（暗色晶核 + 亮边）
      ground: function (ctx) {
        if (resid <= 0.01) return;
        var n = shards.length, t = env.t, f = 0.6 + 3.4 * mg.pulse;
        ctx.globalCompositeOperation = 'source-over';
        for (var i = 0; i < n; i++) {
          var s = shards[i]; if (s.th > resid) break;
          var fade = U.clamp((resid - s.th) / 0.08, 0, 1), c = s.m < 0.5 ? c1 : c2, z = s.sz;
          ctx.save(); ctx.translate(s.x, s.y); ctx.rotate(s.a);
          ctx.fillStyle = U.rgba([c[0] * 0.35 | 0, c[1] * 0.3 | 0, c[2] * 0.45 | 0], 0.75 * fade);
          ctx.beginPath(); ctx.moveTo(0, -z * 1.4); ctx.lineTo(z * 0.6, 0); ctx.lineTo(0, z * 0.9); ctx.lineTo(-z * 0.6, 0); ctx.closePath(); ctx.fill();
          ctx.fillStyle = U.rgba(c, (0.55 + 0.35 * Math.sin(t * f + s.ph)) * fade);
          ctx.fillRect(-z * 0.18, -z * 1.1, z * 0.36, z * 1.4);
          ctx.restore();
        }
      },
      // -------------------------------------------------------------- precip：符文碎光本体
      precip: function (ctx) {
        var t = env.t; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        for (var i = 0; i < runes.length; i++) {
          var p = runes[i], life = U.sstep(0, 0.5, p.life) * (1 - U.sstep(p.max - 0.8, p.max, p.life));
          var tw = 0.45 + 0.55 * Math.abs(Math.sin(t * p.tw + p.ph)), a = life * tw * (0.55 + 0.45 * mg.strength);
          if (a < 0.02) continue;
          var c = p.m < 0.5 ? c1 : c2, sh = SHAPES[p.sh], z = p.sz;
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.scale(z, z);
          ctx.lineWidth = 1.3 / z; ctx.strokeStyle = U.rgba([Math.min(255, c[0] + 70), Math.min(255, c[1] + 70), Math.min(255, c[2] + 70)], a);
          for (var q = 0; q < sh.length; q++) { U.path(ctx, sh[q]); ctx.stroke(); }
          ctx.restore();
        }
      },
      // -------------------------------------------------------------- fog：天边紫光 + 发光云团（正常混合，白天可见为紫色浊云）
      fog: function (ctx) {
        var W = env.W, H = env.H, key = mg.h.toFixed(3) + '/' + I.toFixed(2) + '/' + W + 'x' + H;
        if (hazeKey !== key) {
          hazeKey = key; haze = ctx.createLinearGradient(0, 0, 0, H);
          var dk = U.hsl(mg.h, 0.55, 0.16), reach = Math.min(1, 0.25 + 0.9 * I);
          haze.addColorStop(0, U.rgba(dk, 0.32 + 0.4 * I)); haze.addColorStop(reach * 0.5, U.rgba(dk, 0.12 + 0.3 * I));
          haze.addColorStop(reach, U.rgba(dk, 0.08 * I + (I > 0.7 ? 0.12 : 0))); if (reach < 1) haze.addColorStop(1, U.rgba(dk, 0.08 * I));
        }
        ctx.fillStyle = haze; ctx.fillRect(0, 0, W, H);
        U.blit(ctx, cb, W, H, 0.36 + 0.3 * I);
      },
      // -------------------------------------------------------------- light：辉光（lighter；夜间加强）
      light: function (ctx) {
        var W = env.W, H = env.H, t = env.t, g = 0.35 + 0.65 * nt, st = mg.strength;
        U.blit(ctx, cb, W, H, (0.1 + 0.22 * I) * g * (0.6 + 0.6 * st) * (0.85 + 0.15 * Math.sin(t * (0.6 + 3 * mg.pulse))), 'lighter');
        ctx.globalCompositeOperation = 'lighter';
        // 天边紫光：屏幕上沿一道发光带，轻度时是主要可见元素
        var eg = ctx.createLinearGradient(0, 0, 0, H * (0.18 + 0.25 * I)), ea = (0.22 + 0.2 * I) * (0.6 + 0.4 * st) * (0.7 + 0.5 * nt);
        eg.addColorStop(0, U.rgba(c1, ea)); eg.addColorStop(0.45, U.rgba(c1, ea * 0.35)); eg.addColorStop(1, U.rgba(c1, 0));
        ctx.fillStyle = eg; ctx.fillRect(0, 0, W, H * (0.18 + 0.25 * I));
        var s1 = U.glow(c1, 16), s2 = U.glow(c2, 16);
        for (var i = 0; i < runes.length; i++) {
          var p = runes[i], life = U.sstep(0, 0.5, p.life) * (1 - U.sstep(p.max - 0.8, p.max, p.life));
          var a = life * (0.45 + 0.55 * Math.abs(Math.sin(t * p.tw + p.ph))) * g * (0.5 + 0.5 * st);
          if (a < 0.03) continue;
          var r = p.sz * 2.2, c = p.m < 0.5 ? c1 : c2; ctx.globalAlpha = Math.min(1, a * 0.55); ctx.drawImage(p.m < 0.5 ? s1 : s2, p.x - r, p.y - r, r * 2, r * 2);
          // 夜间重描符文线条，让几何形状在暗处也读得出
          ctx.globalAlpha = 1; ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.scale(p.sz, p.sz);
          ctx.lineWidth = 1.2 / p.sz; ctx.strokeStyle = U.rgba([Math.min(255, c[0] + 90), Math.min(255, c[1] + 90), Math.min(255, c[2] + 90)], Math.min(1, a * nt));
          var sh = SHAPES[p.sh]; for (var q = 0; q < sh.length; q++) { U.path(ctx, sh[q]); ctx.stroke(); } ctx.restore();
        }
        if (resid > 0.01) {                                       // 晶屑脉动辉光，频率随 magic.pulse
          var f = 0.6 + 3.4 * mg.pulse, gl = (0.3 + 0.7 * nt) * (0.4 + 0.6 * U.sstep(0.3, 0.9, I + resid * 0.3));
          for (i = 0; i < shards.length; i++) {
            var s = shards[i]; if (s.th > resid) break;
            var pa = gl * (0.35 + 0.65 * Math.pow(0.5 + 0.5 * Math.sin(t * f + s.ph), 2)) * U.clamp((resid - s.th) / 0.08, 0, 1);
            if (pa < 0.03) continue;
            var rr = s.sz * 4; ctx.globalAlpha = Math.min(1, pa); ctx.drawImage(s.m < 0.5 ? s1 : s2, s.x - rr, s.y - rr, rr * 2, rr * 2);
          }
        }
        ctx.globalAlpha = 1;
      },
      // -------------------------------------------------------------- flash：魔力闪电弧 + 全屏染色闪
      flash: function (ctx) {
        var W = env.W, H = env.H;
        if (flashA > 0.005) { ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = U.rgba(c1, flashA * (0.5 + 0.5 * nt)); ctx.fillRect(0, 0, W, H); }
        if (!arcs.length) return;
        ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        for (var i = 0; i < arcs.length; i++) {
          var a = arcs[i], k = a.life / a.max, fl = (1 - k) * (0.6 + 0.4 * Math.sin(a.life * 70)), c = arcColor(a.m);
          var lw = [16, 5, 2], al = [0.22, 0.6, 1];
          for (var L = 0; L < 3; L++) {
            ctx.strokeStyle = L === 2 ? U.rgba([255, 245, 255], al[L] * fl) : U.rgba(c, al[L] * fl);
            ctx.lineWidth = lw[L] * (a.g ? 1.3 : 1); U.path(ctx, a.p); ctx.stroke();
            if (L > 0) for (var q = 0; q < a.br.length; q++) { ctx.lineWidth = lw[L] * 0.6; U.path(ctx, a.br[q]); ctx.stroke(); }
          }
          if (a.g) { var gr = 50 * fl, sp = U.glow(c, 32); ctx.globalAlpha = fl; ctx.drawImage(sp, a.x - gr, a.y - gr * 0.6, gr * 2, gr * 1.2); ctx.globalAlpha = 1; }
        }
      },
      dispose: function () { runes = []; arcs = []; shards = []; }
    };
    return api;
  });
})(typeof window !== 'undefined' ? window : this);
