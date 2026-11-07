/*
 * 织梦 · 天气美术共用噪波库（浏览器挂 window.WeatherNoise，Node 用 module.exports）
 * 全部由种子派生，同种子同坐标结果一致。值域：noise* 返回 [0,1]，snoise* 返回 [-1,1]。
 */
(function (root) {
  'use strict';
  function hash32(x) { x |= 0; x = Math.imul(x ^ (x >>> 16), 0x45d9f3b); x = Math.imul(x ^ (x >>> 16), 0x45d9f3b); return (x ^ (x >>> 16)) >>> 0; }
  function rng(seed) { // mulberry32
    return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  function fade(t) { return t * t * t * (t * (t * 6 - 15) + 10); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function h2(seed, x, y) { return hash32(seed ^ Math.imul(x, 374761393) ^ Math.imul(y, 668265263)) / 4294967296; }
  function h3(seed, x, y, z) { return hash32(seed ^ Math.imul(x, 374761393) ^ Math.imul(y, 668265263) ^ Math.imul(z, 2147483647)) / 4294967296; }

  /** 2D 值噪波 [0,1] */
  function noise2(seed, x, y) {
    var xi = Math.floor(x), yi = Math.floor(y), u = fade(x - xi), v = fade(y - yi);
    return lerp(lerp(h2(seed, xi, yi), h2(seed, xi + 1, yi), u), lerp(h2(seed, xi, yi + 1), h2(seed, xi + 1, yi + 1), u), v);
  }
  /** 3D 值噪波 [0,1]：第三维常用作时间，做缓慢流动 */
  function noise3(seed, x, y, z) {
    var xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z), u = fade(x - xi), v = fade(y - yi), w = fade(z - zi);
    function c(dx, dy, dz) { return h3(seed, xi + dx, yi + dy, zi + dz); }
    return lerp(lerp(lerp(c(0, 0, 0), c(1, 0, 0), u), lerp(c(0, 1, 0), c(1, 1, 0), u), v),
                lerp(lerp(c(0, 0, 1), c(1, 0, 1), u), lerp(c(0, 1, 1), c(1, 1, 1), u), v), w);
  }
  /** 分形布朗运动 [0,1]；octaves 层，每层频率 ×lac、幅度 ×gain */
  function fbm2(seed, x, y, octaves, lac, gain) {
    octaves = octaves || 4; lac = lac || 2; gain = gain || 0.5;
    var s = 0, a = 1, n = 0;
    for (var i = 0; i < octaves; i++) { s += a * noise2(seed + i * 131, x, y); n += a; a *= gain; x *= lac; y *= lac; }
    return s / n;
  }
  function fbm3(seed, x, y, z, octaves, lac, gain) {
    octaves = octaves || 4; lac = lac || 2; gain = gain || 0.5;
    var s = 0, a = 1, n = 0;
    for (var i = 0; i < octaves; i++) { s += a * noise3(seed + i * 131, x, y, z); n += a; a *= gain; x *= lac; y *= lac; z *= lac; }
    return s / n;
  }
  /** 域扭曲：先用两张噪波偏移采样坐标，再取 fbm，适合雾团、云影、积雪边缘 */
  function warp2(seed, x, y, amount, octaves) {
    var qx = fbm2(seed + 7, x, y, 3) - 0.5, qy = fbm2(seed + 19, x + 5.2, y + 1.3, 3) - 0.5;
    return fbm2(seed, x + amount * qx, y + amount * qy, octaves || 4);
  }
  /**
   * 预烘一张可平铺噪波纹理（ImageData 或 Uint8Array），避免每帧逐像素算噪波。
   * period = 周期格数（纹理在 size 像素内正好重复 period 个噪波格，四边无缝）。
   */
  function tile(seed, size, period, octaves) {
    var out = new Uint8ClampedArray(size * size);
    for (var y = 0; y < size; y++) for (var x = 0; x < size; x++) {
      var s = 0, a = 1, n = 0, p = period;
      for (var o = 0; o < (octaves || 4); o++) {
        var fx = x / size * p, fy = y / size * p, xi = Math.floor(fx), yi = Math.floor(fy), u = fade(fx - xi), v = fade(fy - yi);
        var w = function (ix, iy) { return h2(seed + o * 131, ((ix % p) + p) % p, ((iy % p) + p) % p); };
        s += a * lerp(lerp(w(xi, yi), w(xi + 1, yi), u), lerp(w(xi, yi + 1), w(xi + 1, yi + 1), u), v);
        n += a; a *= 0.5; p *= 2;
      }
      out[y * size + x] = Math.round(s / n * 255);
    }
    return out;
  }
  function smoothstep(a, b, x) { var t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); }

  var API = { rng: rng, hash32: hash32, noise2: noise2, noise3: noise3, fbm2: fbm2, fbm3: fbm3, warp2: warp2, tile: tile,
    snoise2: function (s, x, y) { return noise2(s, x, y) * 2 - 1; }, smoothstep: smoothstep, lerp: lerp };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.WeatherNoise = API;
})(this);
