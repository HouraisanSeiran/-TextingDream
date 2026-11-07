/*
 * 织梦 · west-ground 预览：拼接验证（L 形河道 / 方形港池 / 不规则院坪）+ 示意街区（仅预览页使用）
 * 双网格：逻辑格 (x,y)；渲染瓦片 (i,j) 左上角 = (i*48-24, j*48-24)，四角 = 逻辑格 (i-1,j-1)(i,j-1)(i-1,j)(i,j) 的中心。
 * 绘制顺序：草地底纹 → 土地/水面瓦片 → 其余物件按锚点 y（底边）从小到大、同 y 按 x。
 */
(function (root) {
  'use strict';
  var WG = root.TownArt_westGround, S = 48, NS = 'http://www.w3.org/2000/svg';
  var all = WG.symbols(), M = {};
  all.forEach(function (s) { M[s.id] = s; });
  document.getElementById('sprite-host').innerHTML = WG.spriteSVG(all);

  // 只读引用的外部 symbol（west-base 民居、special-infra 码头）；拿不到就跳过
  var extra = [];
  var WB = root.TownArt_westBase;
  if (WB && WB.house) [[1, 1], [2, 2], [3, 1], [5, 3], [11, 1]].forEach(function (h) {
    try { var r = WB.house(h[0], h[1]); M[r.id] = r; extra.push(WB.symbolSVG(r)); } catch (e) { /* 跳过 */ }
  });
  var SI = root.TownArt_specialInfra;
  if (SI && SI.list) SI.list().forEach(function (d) {
    if (d.id !== 'west-common-dock-01') return;
    var m = SI.meta(d); M[d.id] = { id: d.id, viewBox: m.viewBox, meta: m }; extra.push(SI.symbol(d));
  });
  document.getElementById('extra-host').innerHTML = '<svg xmlns="' + NS + '" width="0" height="0" style="position:absolute;overflow:hidden">' + extra.join('') + '</svg>';

  function bin(m) { return ('000' + m.toString(2)).slice(-4); }
  function useAt(id, x, bottom) {
    var s = M[id]; if (!s) return '';
    var W = s.viewBox[2], H = s.viewBox[3];
    return '<use href="#' + id + '" x="' + x + '" y="' + (bottom - H) + '" width="' + W + '" height="' + H + '"/>';
  }
  /** 双网格：rows 字符串数组，pred(ch) 是否「在」，prefix 瓦片前缀 */
  function dual(rows, pred, prefix) {
    var H = rows.length, W = rows[0].length, s = '';
    function at(x, y) { return x >= 0 && y >= 0 && x < W && y < H && pred(rows[y].charAt(x)) ? 1 : 0; }
    for (var j = 0; j <= H; j++) for (var i = 0; i <= W; i++) {
      var m = at(i - 1, j - 1) * 8 + at(i, j - 1) * 4 + at(i - 1, j) * 2 + at(i, j);
      if (m) s += useAt(prefix + bin(m), i * S - S / 2, j * S + S / 2);
    }
    return s;
  }
  /** 草地底纹：按格坐标哈希挑变体（01 素面占一半） */
  function grass(W, H) {
    var s = '', pick = ['01', '01', '02', '01', '03', '04', '02', '01'];
    for (var y = -1; y <= H; y++) for (var x = -1; x <= W; x++) {
      var h = Math.imul(x * 73856093 ^ y * 19349663, 2654435761) >>> 0;
      s += useAt('west-common-ground-grass-' + pick[(h >>> 7) % pick.length], x * S, y * S + S);
    }
    return s;
  }
  function gridLines(W, H) {
    var d = '';
    for (var x = 0; x <= W; x++) d += 'M' + x * S + ' 0V' + H * S;
    for (var y = 0; y <= H; y++) d += 'M0 ' + y * S + 'H' + W * S;
    return '<path d="' + d + '" fill="none" stroke="#4a3826" stroke-opacity="0.13" stroke-dasharray="2 3"/>';
  }
  /** items: [{ id, cx, cy, w }]：逻辑格 (cx,cy) 起、占地宽 w 格、进深 d 格 → 底边 = (cy+d)*48 */
  function placed(items) {
    var list = items.map(function (it) {
      var s = M[it.id], fp = s && s.meta ? s.meta.footprint : [1, 1];
      return { id: it.id, x: it.cx * S + (it.dx || 0), bottom: (it.cy + fp[1]) * S + (it.dy || 0) };
    });
    list.sort(function (a, b) { return a.bottom - b.bottom || a.x - b.x; });
    return list.map(function (it) { return useAt(it.id, it.x, it.bottom); }).join('');
  }
  function scene(W, H, up, sc, inner, title, grid) {
    var vb = [-24, -up, W * S + 48, H * S + up + 30];
    return '<div class="card" style="text-align:left"><div class="lab"><b>' + title + '</b></div>' +
      '<svg xmlns="' + NS + '" width="' + Math.round(vb[2] * sc) + '" height="' + Math.round(vb[3] * sc) + '" viewBox="' + vb.join(' ') + '">' +
      '<rect x="' + vb[0] + '" y="' + vb[1] + '" width="' + vb[2] + '" height="' + vb[3] + '" fill="#c9c79a"/>' +
      grass(W, H) + inner + (grid ? gridLines(W, H) : '') + '</svg></div>';
  }

  // ---------- 拼接验证 ----------
  var RIVER = [ // ~ = 水；含 L 形转弯、对角相邻（1001/0110 应不连通）、一个小池
    '..~~......',
    '..~~......',
    '..~~......',
    '..~~~~~~~~',
    '..~~~~~~~~',
    '..........',
    '......~...',
    '.......~..'];
  var HARBOR = [ // ~ = 港池
    '.........',
    '.~~~~~~~.',
    '.~~~~~~~.',
    '.~~~~~~~.',
    '.~~~~~~~.',
    '.........'];
  var YARD = [ // # = 院坪
    '..........',
    '.###......',
    '.#####....',
    '.######...',
    '..#####...',
    '...##..##.',
    '.......#..',
    '..........'];
  var isW = function (c) { return c === '~'; }, isY = function (c) { return c === '#'; };
  var joins = '';
  joins += scene(10, 8, 0, 0.9, dual(RIVER, isW, 'west-common-water-bank-'), 'L 形河道 · 自然河岸（右下为对角相邻测试）', true);
  joins += scene(9, 6, 74, 0.9, dual(HARBOR, isW, 'west-common-water-quay-') +
    placed([{ id: 'west-common-dock-01', cx: 3, cy: 0, dy: 18 }, { id: 'west-common-prop-crate-01', cx: 1, cy: 0 },
      { id: 'west-common-prop-barrel-stack-02', cx: 7, cy: 0 }]), '方形港池 · 码头岸（上沿嵌 special-infra 码头比水色）', true);
  joins += scene(10, 8, 0, 0.9, dual(YARD, isY, 'west-common-ground-dirt-'), '不规则院坪 · 踩实土地', true);
  document.getElementById('joins').innerHTML = joins;

  // ---------- 示意街区 ----------
  var BLOCK_YARD = [
    '............',
    '.#####......',
    '.######..##.',
    '.#######.##.',
    '..######....',
    '....##......',
    '............',
    '............'];
  var B = [
    { id: 'west-common-house-02-2', cx: 1, cy: 1 }, { id: 'west-common-house-03-1', cx: 3, cy: 1 },
    { id: 'west-common-house-01-1', cx: 6, cy: 1 }, { id: 'west-common-house-05-3', cx: 9, cy: 1 },
    { id: 'west-common-house-11-1', cx: 8, cy: 4 },
    { id: 'west-common-prop-well-bits-01', cx: 4, cy: 3 }, { id: 'west-common-prop-barrel-stack-01', cx: 2, cy: 2 },
    { id: 'west-common-prop-crate-02', cx: 5, cy: 2 }, { id: 'west-common-prop-handcart-01', cx: 6, cy: 3 },
    { id: 'west-common-prop-bench-01', cx: 3, cy: 4 }, { id: 'west-common-prop-flower-bed-01', cx: 5, cy: 4 },
    { id: 'west-common-prop-chickens-01', cx: 2, cy: 4 }, { id: 'west-common-prop-hay-bale-01', cx: 9, cy: 3 },
    { id: 'west-common-prop-woodpile-01', cx: 10, cy: 3 }, { id: 'west-common-prop-clothesline-01', cx: 7, cy: 2, dy: 6 },
    { id: 'west-common-prop-vegetable-bed-01', cx: 1, cy: 5 }, { id: 'west-common-prop-vegetable-bed-01', cx: 2, cy: 5 },
    { id: 'west-common-prop-tree-oak-01', cx: 0, cy: 1 }, { id: 'west-common-prop-tree-pine-02', cx: 11, cy: 0 },
    { id: 'west-common-prop-tree-fruit-01', cx: 6, cy: 6 }, { id: 'west-common-prop-bush-01', cx: 0, cy: 4 },
    { id: 'west-common-prop-bush-02', cx: 7, cy: 5 }, { id: 'west-common-prop-bush-03', cx: 11, cy: 5 },
    { id: 'west-common-prop-rock-02', cx: 10, cy: 6 }, { id: 'west-common-prop-grass-tuft-02', cx: 4, cy: 6 },
    { id: 'west-common-prop-flower-clump-01', cx: 8, cy: 6 }, { id: 'west-common-prop-signpost-01', cx: 5, cy: 7 },
    { id: 'west-common-prop-puddle-01', cx: 3, cy: 6 }, { id: 'west-common-prop-wagon-01', cx: 9, cy: 5 }];
  for (var fx = 1; fx <= 4; fx++) B.push({ id: 'west-common-prop-fence-h-01', cx: fx, cy: 6 });
  B.push({ id: 'west-common-prop-fence-corner-01', cx: 0, cy: 6 });
  var blk = dual(BLOCK_YARD, isY, 'west-common-ground-dirt-') + placed(B);
  document.getElementById('block').innerHTML = scene(12, 8, 110, 1.15, blk, '示意街区', false);

  root.WGPrev = { M: M, all: all, NS: NS, useAt: useAt };
})(window);
