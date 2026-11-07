/*
 * 织梦 · east-ground · 预览拼接场景（只给 preview.html 用）
 *
 * 逻辑格 (x, y) 占 [x*48, x*48+48] × [y*48, y*48+48]；双网格渲染瓦片 (i, j) 的四角是逻辑格 (i-1..i, j-1..j) 的中心，
 * 所以它画在 (i*48-24, j*48-24)。i 取 0..W、j 取 0..H，越界的逻辑格当 false。
 * 绘制顺序：地面底纹 → 院坪 → 水面 → 叠加件 / 建筑 / 摆件（按锚点 y、再按 x 排序）。
 */
(function (root) {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';

  function hash(x, y, s) { var h = (x * 374761393 + y * 668265263 + (s || 0) * 2246822519) | 0; h = (h ^ (h >>> 13)) * 1274126177 | 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; }
  function use(id, x, y, vb) { return '<use href="#' + id + '" x="' + x + '" y="' + y + '" width="' + vb[2] + '" height="' + vb[3] + '"/>'; }
  function parse(rows) { return rows.map(function (r) { return r.split(''); }); }

  function Scene(res, base, W, H) {
    this.W = W; this.H = H; this.layers = ''; this.objs = []; this.meta = {};
    var self = this;
    res.items.forEach(function (it) { self.meta[it.id] = it.meta; });
    if (base) base.items.forEach(function (it) { self.meta[it.id] = it.meta; });
    if (root.TownArt_specialInfra) root.TownArt_specialInfra.metaAll().forEach(function (m) { self.meta[m.id] = m; });
  }
  Scene.prototype.has = function (id) { return !!this.meta[id]; };
  Scene.prototype.earth = function (seed) {
    for (var y = 0; y < this.H; y++) for (var x = 0; x < this.W; x++) {
      var v = 1 + Math.floor(hash(x, y, seed) * 4), id = 'east-common-ground-earth-0' + v;
      this.layers += use(id, x * 48, y * 48, this.meta[id].viewBox);
    }
  };
  /** 双网格铺一层：grid[y][x] 为真表示该逻辑格属于这种材质。 */
  Scene.prototype.dual = function (EG, prefix, grid) {
    for (var j = 0; j <= this.H; j++) for (var i = 0; i <= this.W; i++) {
      var m = EG.maskAt(grid, i, j);
      if (!m) continue;
      var id = prefix + EG.bits(m);
      this.layers += use(id, i * 48 - 24, j * 48 - 24, this.meta[id].viewBox);
    }
  };
  /** 放一个物件：锚点对齐到占地前沿中点。cx, cy = 占地左上逻辑格。 */
  Scene.prototype.put = function (id, cx, cy) {
    var m = this.meta[id];
    if (!m) return;
    var ax = cx * 48 + m.footprint[0] * 24, ay = (cy + m.footprint[1]) * 48;
    this.objs.push({ ay: ay, ax: ax, s: use(id, ax - m.anchor[0], ay - m.anchor[1], m.viewBox) });
  };
  /** 双网格叠加件：画在渲染瓦片 (i, j) 上，与地面层同层但在水面之后。 */
  Scene.prototype.overlay = function (id, i, j) { this.layers += use(id, i * 48 - 24, j * 48 - 24, this.meta[id].viewBox); };
  Scene.prototype.svg = function (sc, bg) {
    this.objs.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
    var w = this.W * 48, h = this.H * 48;
    return '<svg xmlns="' + NS + '" width="' + w * sc + '" height="' + h * sc + '" viewBox="0 0 ' + w + ' ' + h + '" style="background:' + (bg || '#d9c58f') + '">' +
      this.layers + this.objs.map(function (o) { return o.s; }).join('') + '</svg>';
  };
  function box(el, cap, svg) {
    var d = document.createElement('div'); d.className = 'scene';
    d.innerHTML = svg + '<div class="cap">' + cap + '</div>';
    el.appendChild(d);
  }
  function grid(rows, ch) { return parse(rows).map(function (r) { return r.map(function (c) { return ch.indexOf(c) >= 0; }); }); }

  function render(EG, res, base, scenesEl, blockEl) {
    // 1. L 形河道（自然岸）：先南北向、再折向东，宽 2 格，带一处对角接触与一个小水湾
    var riv = ['....~~......', '....~~......', '....~~......', '....~~~.....', '....~~~~~~~~', '.....~~~~~~~', '..~.........', '.~..........'];
    var s1 = new Scene(res, base, 12, 8);
    s1.earth(11); s1.dual(EG, 'east-common-water-bank-', grid(riv, '~'));
    s1.put('east-common-prop-willow-01', 3, 2); s1.put('east-common-prop-willow-02', 7, 3); s1.put('east-common-prop-taihurock-02', 6, 1);
    s1.put('east-common-prop-bamboo-01', 9, 6); s1.put('east-common-prop-haystack-01', 1, 3);
    box(scenesEl, 'L 形河道 · 自然河岸 bank（左下角是 1001 / 0110 对角两块不连通的小水塘）', s1.svg(1.5));

    // 2. 方形港池（驳岸）+ 东方码头 east-common-dock-01 对色
    var har = ['..........', '..........', '..........', '..~~~~~~..', '..~~~~~~..', '..~~~~~~..', '..~~~~~~..', '....~~....', '....~~....'];
    var s2 = new Scene(res, base, 10, 9);
    s2.earth(23); s2.dual(EG, 'east-common-water-quay-', grid(har, '~'));
    s2.overlay('east-common-water-quay-steps-n', 7, 7 - 0);
    s2.overlay('east-common-water-quay-steps-s', 7, 3);
    if (s2.has('east-common-dock-01')) s2.put('east-common-dock-01', 2, 2);
    s2.put('east-common-prop-hitchingpost-01', 1, 3); s2.put('east-common-prop-woodpile-01', 8, 2); s2.put('east-common-prop-bamboobasket-01', 7, 1);
    s2.put('east-common-prop-bamboobasket-02', 8, 4); s2.put('east-common-prop-wheelbarrow-01', 8, 6);
    box(scenesEl, '方形港池 · 条石驳岸 quay + 驳岸石阶叠加件 + special-infra 码头（对比水色）', s2.svg(1.5));

    // 3. 不规则青砖院坪
    var pav = ['..........', '...###....', '..#####...', '..######..', '...#####..', '..###.##..', '..##...#..', '..........'];
    var s3 = new Scene(res, base, 10, 8);
    s3.earth(37); s3.dual(EG, 'east-common-ground-paving-', grid(pav, '#'));
    s3.put('east-common-prop-taipingvat-01', 4, 2); s3.put('east-common-prop-stonelantern-01', 6, 3);
    box(scenesEl, '不规则青砖院坪 paving（含内凹缺口与对角）', s3.svg(1.5));

    // 4. 底纹大片：检查重复格
    var s4 = new Scene(res, base, 14, 6);
    s4.earth(51);
    box(scenesEl, '地面底纹 earth-01..04 随机铺 14×6（查重复格与接缝）', s4.svg(1));

    // 5. 示意街区（1 倍 = 实际 48 px 网格，再给一份 2 倍）
    var blk = new Scene(res, base, 14, 10), pv = ['..............', '..............', '..............', '.....####.....', '....######....', '....######....', '....######....', '..............', '..............', '..............'];
    blk.earth(67); blk.dual(EG, 'east-common-ground-paving-', grid(pv, '#'));
    var rv = ['', '', '', '', '', '', '', '', '~~~~~~~~~~~~~~', '~~~~~~~~~~~~~~'].map(function (r) { return r || '..............'; });
    blk.dual(EG, 'east-common-water-bank-', grid(rv, '~'));
    var houses = [['east-common-house-siheyuan-01', 0, 0], ['east-common-house-sanheyuan-01', 9, 0], ['east-common-house-huipai-01', 5, 0], ['east-common-house-yupeng-01', 1, 7]];
    houses.forEach(function (h) { blk.put(h[0], h[1], h[2]); });
    var P = 'east-common-prop-';
    [['bamboo-02', 4, 2], ['bamboo-03', 3, 4], ['plum-01', 11, 3], ['pine-01', 12, 5], ['plantain-01', 10, 4], ['stonelion-01', 5, 6], ['stonelion-02', 8, 6],
      ['taipingvat-01', 6, 4], ['stonetable-01', 7, 5], ['lanternpost-01', 4, 6], ['lanternpost-01', 9, 6], ['tudishrine-01', 1, 5], ['waterjar-01', 2, 4],
      ['chickens-01', 12, 7], ['haystack-02', 13, 6], ['dryingmat-01', 11, 6], ['bamboofence-01', 0, 6], ['bamboofence-01', 1, 6], ['bamboofence-03', 2, 6],
      ['bamboofence-02', 2, 7], ['vegbed-01', 0, 7], ['oxcart-01', 3, 3], ['carrypole-01', 9, 4], ['luobasket-01', 10, 5], ['dryingpole-01', 13, 3],
      ['willow-01', 6, 7], ['taihurock-01', 11, 7], ['woodpile-02', 13, 2], ['hitchingpost-01', 10, 3]].forEach(function (p) { blk.put(P + p[0], p[1], p[2]); });
    var html = blk.svg(1);
    box(blockEl, '示意街区 · 1 倍（实际 48 px 网格）' + (base ? '' : '（未找到 east-base，民居已跳过）'), html);
    box(blockEl, '示意街区 · 2 倍', blk.svg(2));
  }

  root.TownArtEG_scenes = { render: render, Scene: Scene, hash: hash };
})(typeof window !== 'undefined' ? window : this);
