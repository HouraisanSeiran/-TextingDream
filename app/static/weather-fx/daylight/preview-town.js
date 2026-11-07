/*
 * 日光预览用城镇：用 TOWN_CATALOG 拼一块带河的西式小镇，栅格化成两张画布
 *   ground：草地 + 道路 + 河岸水面；objects：建筑 / 树 / 码头 / 路灯 / 火盆（透明底）
 * 并从摆放算出 scene（water / buildings / lights / ground）。
 * 绘制顺序（预览页）：ground 图 → reflect pass → objects 图 → light pass。倒影画在实物之下，水上屋檐不会被盖住。
 */
(function (root) {
  'use strict';
  var C = 48, W = 1400, H = 900, GW = 30, GH = 19, NS = 'http://www.w3.org/2000/svg';
  var cat = root.TOWN_CATALOG, meta = {};
  cat.meta.forEach(function (m) { meta[m.id] = m; });

  // ---------------------------------------------------------------- 逻辑格
  var water = {}, road = {};
  for (var x = 0; x < GW; x++) for (var y = 11; y <= 15; y++) {
    if (y === 11 && (x < 4 || x >= 25)) continue;
    if (y === 15 && (x < 9 || x >= 25)) continue;
    if (y === 14 && x < 3) continue;
    water[x + ',' + y] = 1;
  }
  for (x = 0; x < GW; x++) { road[x + ',7'] = 1; road[x + ',17'] = 1; }
  for (y = 0; y <= 10; y++) road['13,' + y] = 1;
  var isW = function (i, j) { return !!water[i + ',' + j]; }, isR = function (i, j) { return !!road[i + ',' + j]; };

  // ---------------------------------------------------------------- 摆放 [id, cx, cy]（底边 = (cy+进深)*48）
  var H1 = 'west-common-house-', T = 'west-common-prop-';
  var items = [
    [H1 + '01-1', 4, 10], [H1 + '03-1', 6, 10], [H1 + '08-1', 8, 10], ['west-common-dock-01', 10, 10], [H1 + '12-1', 14, 10],
    [H1 + '05-1', 16, 10], [H1 + '06-1', 17, 10], [H1 + '02-1', 19, 10], [H1 + '14-1', 20, 10], [H1 + '15-1', 22, 10], [H1 + '04-1', 23, 10],
    [H1 + '09-1', 1, 5], [H1 + '13-1', 4, 5], [H1 + '10-1', 6, 5], [H1 + '16-1', 9, 5], [H1 + '11-1', 11, 6], [H1 + '07-1', 15, 5],
    [H1 + '04-1', 16, 6], [H1 + '03-1', 19, 6], [H1 + '12-1', 22, 6], [H1 + '06-1', 25, 6], [H1 + '05-1', 27, 6],
    [H1 + '01-1', 1, 18], [H1 + '12-1', 3, 18], [H1 + '08-1', 6, 18], [H1 + '03-1', 8, 18], [H1 + '02-1', 15, 18], [H1 + '06-1', 18, 18],
    [H1 + '05-1', 21, 18], [H1 + '14-1', 23, 18], [H1 + '11-1', 27, 18],
    [T + 'tree-oak-01', 0, 10], [T + 'tree-oak-02', 2, 9], [T + 'tree-pine-01', 25, 9], [T + 'tree-pine-02', 27, 10], [T + 'tree-oak-01', 28, 9],
    [T + 'tree-pine-01', 0, 2], [T + 'tree-oak-02', 3, 1], [T + 'tree-pine-02', 8, 1], [T + 'tree-oak-01', 17, 2], [T + 'tree-pine-01', 21, 1], [T + 'tree-oak-02', 26, 2],
    [T + 'tree-oak-01', 1, 15], [T + 'tree-fruit-01', 4, 15], [T + 'bush-01', 6, 16], [T + 'tree-oak-02', 26, 15], [T + 'tree-pine-02', 28, 16],
    [T + 'bush-02', 12, 16], [T + 'reedclump-01', 9, 16], [T + 'reedclump-01', 24, 15], [T + 'campfire-01', 14, 16], [T + 'bench-01', 15, 16],
    [T + 'barrel-stack-01', 12, 9], [T + 'crate-02', 14, 9], [T + 'woodpile-01', 3, 16], [T + 'campfire-01', 20, 16], [T + 'hay-bale-01', 22, 16]
  ];
  var placed = [];
  items.forEach(function (it) {
    var m = meta[it[0]]; if (!m) return;
    var bottom = (it[2] + m.footprint[1]) * C;
    placed.push({ id: it[0], m: m, x: it[1] * C, y: bottom - m.viewBox[3], w: m.viewBox[2], h: m.viewBox[3], bottom: bottom });
  });
  placed.sort(function (a, b) { return a.bottom - b.bottom || a.x - b.x; });

  // ---------------------------------------------------------------- scene
  var scene = { width: W, height: H, cell: C, water: [], buildings: [], lights: [], ground: [] };
  Object.keys(water).forEach(function (k) { var p = k.split(','); scene.water.push([p[0] * C, p[1] * C, C, C]); });
  Object.keys(road).forEach(function (k) { var p = k.split(','); scene.ground.push([p[0] * C, p[1] * C, C, C]); });
  for (x = 0; x < GW; x++) { if (!water[x + ',16']) scene.ground.push([x * C, 16 * C, C, C]); if (!water[x + ',10']) scene.ground.push([x * C, 10 * C, C, C]); }
  var hr = root.WeatherNoise.rng(4242);
  placed.forEach(function (p) {
    var cat2 = p.m.category, tree = /tree/.test(p.id);
    if (cat2 === 'house' || tree) {
      var dep = tree ? 18 : p.h - (p.m.height_px || 40);
      scene.buildings.push({ x: p.x, y: p.y, w: p.w, h: p.h, roofY: p.y, depth: dep, tree: tree });
    }
    if (cat2 === 'house') { // 前墙上 1–3 扇窗
      var hp = p.m.height_px || 40, n = p.w > 60 ? 2 + (hr() < 0.4 ? 1 : 0) : 1;
      for (var i = 0; i < n; i++) scene.lights.push({ x: p.x + p.w * (i + 0.5 + (hr() - 0.5) * 0.25) / n, y: p.bottom - Math.min(26, hp * 0.42) - 4, kind: 'window' });
      if (hp > 50 && hr() < 0.6) scene.lights.push({ x: p.x + p.w * (0.3 + hr() * 0.4), y: p.bottom - hp * 0.78, kind: 'window' });
    }
    if (/campfire/.test(p.id)) scene.lights.push({ x: p.x + 24, y: p.bottom - 9, kind: 'fire' });
  });
  // 自绘路灯（铁杆挂灯）与火盆：[x, 地面 y]
  var lamps = [[3.5, 8.05], [9.6, 8.05], [16.4, 8.05], [24.4, 8.05], [10.3, 11.6], [12.7, 11.6], [5.5, 16.9], [17.5, 16.9], [25.5, 16.9]];
  var braziers = [[8.5, 6.6], [26.6, 10.75], [13.4, 10.2]];
  lamps.forEach(function (l) { scene.lights.push({ x: l[0] * C, y: l[1] * C - 30, kind: 'lamp' }); });
  braziers.forEach(function (b) { scene.lights.push({ x: b[0] * C, y: b[1] * C - 14, kind: 'fire' }); });
  scene.lamps = lamps; scene.braziers = braziers;

  root.DaylightTown = { scene: scene, build: function (dpr, done) { build(dpr, done); },
    raster: function (t, d, cb) { raster(t, d, cb); }, drawProps: function (c, d, l, b) { drawProps(c, d, l, b); }, symbolText: function (id) { return symbolText(id); } };

  // ---------------------------------------------------------------- 栅格化
  function symbolText(id) {
    var s = cat.sprite, i = s.indexOf('<symbol id="' + id + '"'); if (i < 0) return '';
    return s.slice(i, s.indexOf('</symbol>', i) + 9);
  }
  function useAt(id, x, y) {
    var m = meta[id]; if (!m) return '';
    return '<use href="#' + id + '" x="' + x + '" y="' + y + '" width="' + m.viewBox[2] + '" height="' + m.viewBox[3] + '"/>';
  }
  function dual(prefix, test) {
    var s = '';
    for (var j = 0; j <= GH; j++) for (var i = 0; i <= GW; i++) {
      var m = (test(i - 1, j - 1) ? 8 : 0) + (test(i, j - 1) ? 4 : 0) + (test(i - 1, j) ? 2 : 0) + (test(i, j) ? 1 : 0);
      if (m) s += useAt(prefix + ('000' + m.toString(2)).slice(-4), i * C - C / 2, j * C - C / 2);
    }
    return s;
  }
  function groundSVG() {
    var s = '<rect width="' + W + '" height="' + H + '" fill="#9fae8c"/>', R = root.WeatherNoise.rng(7), pick = ['01', '01', '02', '01', '03', '04'];
    for (var j = 0; j < GH; j++) for (var i = 0; i < GW; i++) s += useAt('west-common-ground-grass-' + pick[(R() * pick.length) | 0], i * C, j * C);
    return s + dual('west-common-road-dirt-', isR) + dual('west-common-water-bank-', isW);
  }
  function objectsSVG() {
    return placed.map(function (p) { return useAt(p.id, p.x, p.y); }).join('');
  }
  var used = {};
  function collect(str) { str.replace(/href="#([^"]+)"/g, function (_, id) { used[id] = 1; }); }
  function svgDoc(body) {
    var defs = Object.keys(used).map(symbolText).join('');
    return '<svg xmlns="' + NS + '" xmlns:xlink="http://www.w3.org/1999/xlink" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '"><defs>' + defs + '</defs>' + body + '</svg>';
  }
  function raster(svgText, dpr, cb) {
    var img = new Image(), url = URL.createObjectURL(new Blob([svgText], { type: 'image/svg+xml' }));
    img.onload = function () {
      var c = document.createElement('canvas'); c.width = W * dpr; c.height = H * dpr;
      c.getContext('2d').drawImage(img, 0, 0, W * dpr, H * dpr); URL.revokeObjectURL(url); cb(c);
    };
    img.onerror = function () { URL.revokeObjectURL(url); cb(null); };
    img.src = url;
  }
  /** 路灯：铁杆 + 横臂 + 灯笼；火盆：三脚架 + 铁盆 + 炭火（白天看得到实物，夜里由光照层点亮） */
  /** lamps / braziers：[x, 地面 y] 像素坐标 */
  function drawProps(c, dpr, lamps, braziers) {
    var g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
    lamps.forEach(function (l) {
      var x = l[0], y = l[1];
      g.fillStyle = 'rgba(58,44,30,0.22)'; g.beginPath(); g.ellipse(x + 3, y, 6, 2, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = '#3a3330'; g.fillRect(x - 1.3, y - 38, 2.6, 38); g.fillRect(x - 3, y - 3, 6, 3);
      g.fillStyle = '#4a3f36'; g.fillRect(x - 1, y - 38, 8, 1.6);
      g.fillStyle = '#2e2724'; g.fillRect(x + 3.5, y - 36.5, 6, 1.6);
      g.fillStyle = '#d9c48a'; g.fillRect(x + 4.2, y - 35, 4.6, 6.5);
      g.strokeStyle = '#2e2724'; g.lineWidth = 1; g.strokeRect(x + 4.2, y - 35, 4.6, 6.5);
    });
    braziers.forEach(function (b) {
      var x = b[0], y = b[1];
      g.fillStyle = 'rgba(58,44,30,0.22)'; g.beginPath(); g.ellipse(x + 2, y, 9, 2.6, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = '#3a3330'; g.lineWidth = 1.6; g.beginPath();
      g.moveTo(x - 6, y); g.lineTo(x - 2, y - 11); g.moveTo(x + 6, y); g.lineTo(x + 2, y - 11); g.moveTo(x, y + 1); g.lineTo(x, y - 11); g.stroke();
      g.fillStyle = '#4a3f36'; g.beginPath(); g.ellipse(x, y - 12, 8, 3.2, 0, 0, Math.PI); g.fill();
      g.fillStyle = '#7a3a1a'; g.beginPath(); g.ellipse(x, y - 13, 7, 2.4, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = '#e07a2a'; g.beginPath(); g.moveTo(x - 4, y - 13); g.quadraticCurveTo(x - 1, y - 21, x, y - 25); g.quadraticCurveTo(x + 2, y - 19, x + 4, y - 13); g.fill();
      g.fillStyle = '#ffd27a'; g.beginPath(); g.moveTo(x - 2, y - 13); g.quadraticCurveTo(x, y - 18, x + 0.5, y - 20); g.quadraticCurveTo(x + 1.5, y - 16, x + 2, y - 13); g.fill();
    });
  }
  function build(dpr, done) {
    var gs = groundSVG(), os = objectsSVG(); collect(gs); collect(os);
    // sprite 容器：0×0 绝对定位，只承载本页用到的 <symbol>（供调试 / 其他 <use> 引用）
    var holder = document.createElementNS(NS, 'svg');
    holder.setAttribute('width', 0); holder.setAttribute('height', 0); holder.setAttribute('aria-hidden', 'true');
    holder.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;overflow:hidden';
    holder.innerHTML = Object.keys(used).map(symbolText).join(''); document.body.prepend(holder);
    raster(svgDoc(gs), dpr, function (gc) {
      raster(svgDoc(os), dpr, function (oc) {
        var px = function (a) { return a.map(function (p) { return [p[0] * C, p[1] * C]; }); };
        if (oc) drawProps(oc, dpr, px(scene.lamps), px(scene.braziers));
        scene.objectsImage = oc; scene.objectsScale = dpr;
        done({ ground: gc, objects: oc, scene: scene });
      });
    });
  }
})(this);
