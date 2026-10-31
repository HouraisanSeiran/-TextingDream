/**
 * 把网格上的世界"铺"成像素:等距圆柱主图(东西无缝、上下边是南北极)。
 * 每个像素中心的方向落在哪个球面三角形里,就在那个三角形里做重心插值,再叠一层细节噪声。
 * 结果只和世界有关、和画风无关;画风切换不用重算。
 *
 * 细节噪声不是处处一样强:
 *   - 按当地起伏走:起伏 = 地块和邻居的平均高差。平原 / 沙漠只剩几米,山地几百米
 *   - 海岸另加一层:岸线沿法向挪动几个像素。平原海岸圆润但仍有细碎的分形细节,
 *     山地海岸挪得更多、再叠一层低频扭曲,显得破碎(海湾、岬角、小岛);
 *     网格粗(地块大)时平原海岸另加一层低频弯曲,免得岸线只是柔化后的地块轮廓、一圈圆包
 *   - 沿河道刻出河谷:河越大谷越宽越深,山里的谷更深;谷底把噪声压平
 * 噪声不逐像素现算,而是预先算两张可平铺的噪声贴图(细节 / 气候抖动),按像素在球面上的三维位置
 * 从三个方向投影取样、按法向加权("三向贴图")—— 东西没有接缝,两极不"拉丝"。
 *
 * 流程:地块上算插值源 → 球面三角形覆盖(sphereCover:跨 180° 经线的三角形像素列取模,包着极点的三角形
 * 扫到极点、整圈经度)→ 铺海拔 → 柔化(按纬度修正:高纬度一个像素的东西向地面宽度只有 cos(纬度),列下标取模)
 * → 刻河谷(沿展开后的河道,跨接缝的河在两边各刻一份)→ 逐像素(其余字段 + 噪声 + 群落)→ 去近岸碎点 → 海冰。
 * 几个重循环各放在独立的小函数里,引擎更快把它们优化成机器码(第一次调用也快)。
 * 结果带 wrap = true:画风据此把邻域操作的列下标取模。
 */
import type { World } from './world';
import type { Mesh } from './mesh';
import { blurField } from './mesh';
import { classifyBiome } from './biomes';
import { SEA_ICE_MIN, seaIceNodes, seaIcePixels } from './seaice';
import { Gullies, gullyHeights, type GullyInput } from './gully';
export { gullyHeights } from './gully';
import { smoothstep, subSeed, tileableFbm } from './util';
// 河谷要正好落在画出来的河下面,所以直接用画河的同一套几何(纯计算,不碰页面,worker / Node 都能跑)
import { bankBytes, carveValleys, valleyLines } from './valleys';
export { bankBytes, carveValleys, valleyLines, type ValleyLines } from './valleys';
import { veinsOf, type DrainLines, type Streams, type VeinJob } from './pixelDrain';
import { creeksOf } from './creeks';
import { boxSpans, inBox, type PixelBox } from './pixelBox';
export { stampVeins, veinLinesOf, veinsOf, type VeinJob } from './pixelDrain';

export interface Raster {
  w: number;
  h: number;
  /** 像素 / 世界单位 */
  scale: number;
  /** 海拔(米)。水面像素为水面/海底高度 */
  elev: Float32Array;
  /** 年均温 °C(已按像素海拔修正) */
  temp: Float32Array;
  /** 年降水 mm */
  precip: Float32Array;
  /** 0 陆地 / 1 海洋 / 2 湖泊 */
  water: Uint8Array;
  biome: Uint8Array;
  /** 最近的地块编号(查询用) */
  cell: Int32Array;
  /**
   * 海冰覆盖 0–1(已含浮冰破碎,见 seaice.ts),只有海洋像素可能非 0。
   * 群落 = 海冰 ⇔ ice ≥ 0.5;画风直接读它,不再重新取样
   */
  ice: Float32Array;
  /** 冰缘起伏后的平滑海冰程度 × 255(浮冰打碎之前;0 = 附近没冰)。写实风用来给冰间水面上色 */
  iceConc: Uint8Array;
  /** 这个像素所在那块浮冰的随机色调 × 255(ice > 0 时才有意义)。写实风用来让每块冰明暗略有不同 */
  iceTone: Uint8Array;
  /**
   * 山坡上的沟和山脊(米,见 gen/gully.ts):写实风打光时叠在海拔上。只管明暗 —— 海拔、水陆、群落都不变,
   * 手绘风、数据图层、查询看到的还是 elev。没有 = 不叠
   */
  gully?: Float32Array;
  /**
   * 离河多近 × 255(刻河谷时的噪声抑制系数 calm:河面上 1,往外到谷壁外一点收到 0;见 carveValleys)。
   * 写实风据此把谷底压暗、干旱地方的河两岸画绿。没有 = 当作附近没河
   */
  bank?: Uint8Array;
  /**
   * 细沟 × 255(见 gen/pixelDrain.ts、stampVeins):逐像素汇流,集水面积越大越重,离沟中线越远越淡。
   * 写实风据此把地面上的一条条旱沟、小谷压暗,干旱地方再带一点绿(叶脉一样的水系)。没有 = 不画
   */
  vein?: Uint8Array;
  /**
   * 细沟的线(世界单位,在 1 倍的整张主图上算的;见 veinLinesOf):放大现算的块、导出的大图都按这一份画,
   * 和屏幕上的整张图一样,也不用各算一遍。没有 = 用到时现算
   */
  veinLines?: DrainLines;
  /**
   * 放大后现算的一块(gen/rasterWindow.ts):这一块左上角在 W × H 的主图(scale 倍)里的像素位置。
   * 没有 = 整张主图。画风据此按真实的纬度、整张图上的位置算晕渲和纹理(和整张图接得上)
   */
  win?: { x0: number; y0: number; W: number; H: number };
  /**
   * 等距圆柱主图东西相连 —— 第 0 列和最后一列相邻,邻域操作的列下标取模;
   * 第 py 行像素中心的纬度 = 90° − (py + 0.5) / h × 180°(上边是北极、下边是南极)
   */
  wrap: true;
}

const LAPSE = 0.0065;
/** 贴图归一化后乘的标准差:和旧版逐像素 fbm 一致,湖岸抖动 / 气候抖动的系数保持原意 */
const DETAIL_STD = 0.25;
const JITTER_STD = 0.29;
/** 细节贴图:512² 像素,最底层 36 格 → 波长约 14 像素,4 层 */
const DETAIL_SIZE = 512;
/** 气候抖动贴图:256²,最底层 18 格,3 层;采样时放大到波长约 40 像素 */
const JITTER_SIZE = 256;
/**
 * 网格粗时平原海岸另加的弯曲:海拔是在地块三角形上插值再柔化的,地块越大,平原岸线越"圆鼓"(一串圆包、成段的缓弧),
 * 固定几个像素的碎边盖不住。按地块间距(世界单位)加:20 万地块(间距约 2.1)以下不加,
 * 3.6 万(约 4.95)加满一份,再粗最多两份。山地海岸本来就破碎,不加
 */
const COAST_FINE = 2.1;
const COAST_STEP = 2.85;
/** 加满一份时这层弯曲的幅度(世界单位,和下面 D 同一个量纲) */
const COAST_BEND = 5;
/** 小于这么多像素(1 倍主图)、四面都是海的陆地碎点去掉:多是近岸噪声撒出来的,不是板块算出来的岛 */
const SPECK_MAX = 4;

/**
 * 每个三角形存 8 个字段(依次为湖泊比例、细节幅度、海岸标记、海平面等效温度、降水、海岸陡峭度、平滑海冰程度、陆地比例),
 * 每个字段 3 个数:重心权重的线性函数 v = P₀·w_A + P₁·w_B + P₂
 */
export const PLANE = 24;

/** 当地起伏(米)→ 陆地细节噪声幅度(米):平原几米,山地几百米 */
function landAmp(rel: number): number {
  return Math.min(520, 7 + rel * (0.1 + 0.9 * smoothstep(40, 350, rel)));
}

/** 海岸有多"陡峭破碎"(0..1):按当地起伏,平原海岸 0,山地海岸 1 */
function rugged(rel: number): number {
  return smoothstep(60, 450, rel);
}

/** 每个地块上的插值源 */
export interface CellFields {
  /** 海岸用的有符号海拔:陆地至少 +8m,湖按湖面 */
  sElev: Float32Array;
  lake: Float32Array;
  /** 海平面等效温度 */
  t0: Float32Array;
  precip: Float32Array;
  /** 细节噪声幅度(米) */
  amp: Float32Array;
  /** 海岸标记:海岸地块 1,其余海洋 1e-3,内陆 0(> 0 即"这里允许出现海") */
  coast: Float32Array;
  /** 海岸陡峭度 0..1 */
  rug: Float32Array;
  /** 平滑海冰程度(见 seaIceNodes) */
  ice: Float32Array;
  /** 原始陆地比例：海岸美化不能淹没地块中心（城址、道路端点使用这些坐标）。 */
  land: Float32Array;
}

export function cellFields(world: World): CellFields {
  const { mesh, elevation, water, waterLevel, temperature, precipitation } = world;
  const { n, adjStart, adj } = mesh;
  const sElev = new Float32Array(n);
  const lake = new Float32Array(n);
  const land = new Float32Array(n);
  const t0 = new Float32Array(n);
  const ground = new Float32Array(n); // 算起伏用:海面按 0,湖按湖面
  for (let i = 0; i < n; i++) {
    const e = elevation[i];
    land[i] = water[i] === 0 ? 1 : 0;
    if (water[i] === 1) sElev[i] = e;
    else sElev[i] = Math.max(e, 8);
    if (water[i] === 2) {
      lake[i] = 1;
      sElev[i] = Math.max(waterLevel[i], 8);
    }
    t0[i] = temperature[i] + LAPSE * Math.max(0, water[i] === 1 ? 0 : sElev[i]);
    ground[i] = water[i] === 1 ? 0 : Math.max(0, water[i] === 2 ? waterLevel[i] : e);
  }

  // 当地起伏 = 和邻居的平均高差,再在网格上柔化两遍(让噪声强弱渐变,不出现分界线)
  const mad = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const s = adjStart[i];
    const t = adjStart[i + 1];
    let acc = 0;
    for (let k = s; k < t; k++) acc += Math.abs(ground[i] - ground[adj[k]]);
    mad[i] = t > s ? acc / (t - s) : 0;
  }
  const rel = blurField(mesh, mad, 2);

  const amp = new Float32Array(n);
  const coast = new Float32Array(n);
  const rug = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const sea = water[i] === 1;
    let coastal = false;
    for (let k = adjStart[i]; k < adjStart[i + 1]; k++) {
      if ((water[adj[k]] === 1) !== sea) {
        coastal = true;
        break;
      }
    }
    const la = landAmp(rel[i]);
    const seaAmp = 30 + 0.02 * -elevation[i];
    // 近岸海底不用海洋的大幅度,免得平原海岸边的陆地也被带得坑坑洼洼
    amp[i] = !sea ? la : coastal ? Math.min(seaAmp, Math.max(la, 12)) : seaAmp;
    coast[i] = coastal ? 1 : sea ? 1e-3 : 0;
    rug[i] = rugged(rel[i]);
  }
  return { sElev, lake, t0, precip: precipitation, amp, coast, rug, ice: seaIceNodes(world), land };
}

/** 噪声贴图只和种子有关:记住上一次的,只调参数不换种子时直接复用 */
let tileCache: { seed: number; dTile: Float32Array; jTile: Float32Array } | null = null;
export function noiseTiles(seed: number) {
  if (tileCache && tileCache.seed === seed) return tileCache;
  const dTile = tileableFbm(subSeed(seed, 'detail'), DETAIL_SIZE, 36, 4, 0.55);
  const jTile = tileableFbm(subSeed(seed, 'jitter'), JITTER_SIZE, 18, 3, 0.5);
  for (let i = 0; i < dTile.length; i++) dTile[i] *= DETAIL_STD;
  for (let i = 0; i < jTile.length; i++) jTile[i] *= JITTER_STD;
  tileCache = { seed, dTile, jTile };
  return tileCache;
}

// ---------------------------------------------------------------------------
// 等距圆柱主图:球面三角形覆盖、三向贴图

/** 主栅格每列 / 每行像素中心的经度、纬度三角函数(存 Float32:各引擎最后一位的差别被舍掉) */
export interface SphereGrid {
  w: number;
  h: number;
  cosLon: Float32Array;
  sinLon: Float32Array;
  cosLat: Float32Array;
  sinLat: Float32Array;
}

/** w × h 的等距圆柱主图:第 px 列经度 = (px + 0.5) / w × 360° − 180°,第 py 行纬度 = 90° − (py + 0.5) / h × 180° */
export function sphereGrid(w: number, h: number): SphereGrid {
  const cosLon = new Float32Array(w);
  const sinLon = new Float32Array(w);
  const cosLat = new Float32Array(h);
  const sinLat = new Float32Array(h);
  for (let px = 0; px < w; px++) {
    const l = ((px + 0.5) / w) * 2 * Math.PI - Math.PI;
    cosLon[px] = Math.cos(l);
    sinLon[px] = Math.sin(l);
  }
  for (let py = 0; py < h; py++) {
    const l = Math.PI / 2 - ((py + 0.5) / h) * Math.PI;
    cosLat[py] = Math.cos(l);
    sinLat[py] = Math.sin(l);
  }
  return { w, h, cosLon, sinLon, cosLat, sinLat };
}

/** 球面三角形铺出来的主栅格:每个像素属于哪个三角形(编号 + 1,0 = 没盖到)、顶点 A / B 的重心权重(C = 1 − A − B) */
export interface SphereCover {
  tri: Int32Array;
  wa: Float32Array;
  wb: Float32Array;
  /** 没被任何三角形盖到的像素数(应为 0;单测核对) */
  holes: number;
}

/**
 * 按球面三角形铺等距圆柱主栅格。像素中心的方向 q 在三角形 ABC 里 ⇔ q 在三条边所在大圆的同一侧:
 * d_A = q·(B×C)、d_B = q·(C×A)、d_C = q·(A×B) 都 ≥ 0;这三个数归一化就是重心权重(按"有向体积"分,
 * 三角形很小时和平面重心坐标几乎一样,边上连续)。相邻两个三角形共用的边,两边算出的 d 正好互为相反数
 * (叉积、点积都对称),所以边上的像素两边都认、不会漏。
 *
 * 每个三角形只扫它的经纬度范围:
 *   - 纬度:三个顶点 + 三条边(大圆弧会往极点方向鼓出去,算出弧上的最高 / 最低点)各多放一行
 *   - 经度:三个顶点经度在圆周上最短的覆盖弧(去掉最大的空隙);跨 180° 经线时列下标取模
 *   - 包着极点的(三条边都从同一侧绕过极点),扫到极点、整圈经度;贴着极点、经度范围说不清的也扫整圈
 */
export function sphereCover(mesh: Mesh, g: SphereGrid): SphereCover {
  const { w, h, cosLon, sinLon, cosLat, sinLat } = g;
  const xyz = mesh.xyz!;
  const { triangles } = mesh;
  const N = w * h;
  const tri = new Int32Array(N);
  const wa = new Float32Array(N);
  const wb = new Float32Array(N);
  const nt = triangles.length / 3;
  const TAU = 2 * Math.PI;
  const toY = (z: number) => ((Math.PI / 2 - Math.asin(z < -1 ? -1 : z > 1 ? 1 : z)) / Math.PI) * h - 0.5;
  const toX = (l: number) => ((l + Math.PI) / TAU) * w - 0.5;
  const ext = [0, 0];
  for (let t = 0; t < nt; t++) {
    const a = triangles[3 * t];
    const b = triangles[3 * t + 1];
    const c = triangles[3 * t + 2];
    const ax = xyz[3 * a];
    const ay = xyz[3 * a + 1];
    const az = xyz[3 * a + 2];
    const bx = xyz[3 * b];
    const by = xyz[3 * b + 1];
    const bz = xyz[3 * b + 2];
    const cx = xyz[3 * c];
    const cy = xyz[3 * c + 1];
    const cz = xyz[3 * c + 2];
    // 三条边的大圆法向:n1 = A×B(对着 C)、n2 = B×C(对着 A)、n3 = C×A(对着 B)
    let n1x = ay * bz - az * by;
    let n1y = az * bx - ax * bz;
    let n1z = ax * by - ay * bx;
    let n2x = by * cz - bz * cy;
    let n2y = bz * cx - bx * cz;
    let n2z = bx * cy - by * cx;
    let n3x = cy * az - cz * ay;
    let n3y = cz * ax - cx * az;
    let n3z = cx * ay - cy * ax;
    const vol = ax * n2x + ay * n2y + az * n2z;
    if (vol === 0) continue;
    // 纬度范围(按 z):顶点 + 各条边上的最高 / 最低点
    ext[0] = Math.max(az, bz, cz);
    ext[1] = Math.min(az, bz, cz);
    arcZ(ax, ay, az, bx, by, bz, n1x, n1y, n1z, ext);
    arcZ(bx, by, bz, cx, cy, cz, n2x, n2y, n2z, ext);
    arcZ(cx, cy, cz, ax, ay, az, n3x, n3y, n3z, ext);
    if (vol < 0) {
      n1x = -n1x;
      n1y = -n1y;
      n1z = -n1z;
      n2x = -n2x;
      n2y = -n2y;
      n2z = -n2z;
      n3x = -n3x;
      n3y = -n3y;
      n3z = -n3z;
    }
    // 包着北极 / 南极:极点方向 (0, 0, ±1) 在三条边的内侧
    const north = n1z >= 0 && n2z >= 0 && n3z >= 0;
    const south = n1z <= 0 && n2z <= 0 && n3z <= 0;
    const y0 = north ? 0 : Math.max(0, Math.ceil(toY(ext[0])) - 1);
    const y1 = south ? h - 1 : Math.min(h - 1, Math.floor(toY(ext[1])) + 1);
    let x0 = 0;
    let x1 = w - 1;
    if (!north && !south && Math.max(Math.abs(az), Math.abs(bz), Math.abs(cz)) < 0.999) {
      // 三个顶点的经度从小到大(冒泡,相等的不换位置:和稳定排序一样)
      let l0 = Math.atan2(ay, ax);
      let l1 = Math.atan2(by, bx);
      let l2 = Math.atan2(cy, cx);
      if (l0 > l1) {
        const t = l0;
        l0 = l1;
        l1 = t;
      }
      if (l1 > l2) {
        const t = l1;
        l1 = l2;
        l2 = t;
      }
      if (l0 > l1) {
        const t = l0;
        l0 = l1;
        l1 = t;
      }
      const g1 = l1 - l0;
      const g2 = l2 - l1;
      const g3 = l0 + TAU - l2;
      const gmax = Math.max(g1, g2, g3);
      // 最大的空隙要明显超过半圈才靠得住(否则三角形紧贴极点,经度范围说不清,整圈都扫)
      if (gmax > Math.PI * 1.1) {
        const lo = g3 === gmax ? l0 : g1 === gmax ? l1 : l2;
        const hi = g3 === gmax ? l2 : g1 === gmax ? l0 + TAU : l1 + TAU;
        const xa = Math.ceil(toX(lo)) - 1;
        const xb = Math.floor(toX(hi)) + 1;
        if (xb - xa < w) {
          x0 = xa;
          x1 = xb;
        }
      }
    }
    const tv = t + 1;
    for (let py = y0; py <= y1; py++) {
      const cl = cosLat[py];
      const sl = sinLat[py];
      const e1 = n1z * sl;
      const e2 = n2z * sl;
      const e3 = n3z * sl;
      const row = py * w;
      for (let xx = x0; xx <= x1; xx++) {
        const px = xx < 0 ? xx + w : xx >= w ? xx - w : xx;
        const qx = cl * cosLon[px];
        const qy = cl * sinLon[px];
        const dC = n1x * qx + n1y * qy + e1;
        if (dC < 0) continue;
        const dA = n2x * qx + n2y * qy + e2;
        if (dA < 0) continue;
        const dB = n3x * qx + n3y * qy + e3;
        if (dB < 0) continue;
        const s = dA + dB + dC;
        if (!(s > 0)) continue;
        const k = row + px;
        tri[k] = tv;
        wa[k] = dA / s;
        wb[k] = dB / s;
      }
    }
  }
  // 没盖到的像素(应为 0):沿用左边像素的三角形和权重
  let holes = 0;
  for (let py = 0; py < h; py++) {
    const row = py * w;
    for (let px = 0; px < w; px++) {
      const k = row + px;
      if (tri[k]) continue;
      holes++;
      const j = row + (px > 0 ? px - 1 : w - 1);
      tri[k] = tri[j];
      wa[k] = wa[j];
      wb[k] = wb[j];
    }
  }
  return { tri, wa, wb, holes };
}

/**
 * 大圆弧 p → q(法向 n = p × q)上 z 的最高 / 最低点,把 ext = [最大 z, 最小 z] 往外推。
 * 大圆上 z 最大的点的方向 m = ẑ − (ẑ·n̂) n̂;它在这段弧上 ⇔ (p × m)·n ≥ 0 且 (m × q)·n ≥ 0;最低点是 −m(两个判别式都变号)
 */
function arcZ(px: number, py: number, pz: number, qx: number, qy: number, qz: number, nx: number, ny: number, nz: number, ext: number[]) {
  const nn = nx * nx + ny * ny + nz * nz;
  if (!(nn > 0)) return;
  const t2 = (nz * nz) / nn;
  if (t2 >= 1) return;
  const mx = -nz * nx;
  const my = -nz * ny;
  const mz = nn - nz * nz;
  const s1 = (py * mz - pz * my) * nx + (pz * mx - px * mz) * ny + (px * my - py * mx) * nz;
  const s2 = (my * qz - mz * qy) * nx + (mz * qx - mx * qz) * ny + (mx * qy - my * qx) * nz;
  const top = Math.sqrt(1 - t2);
  if (s1 >= 0 && s2 >= 0 && top > ext[0]) ext[0] = top;
  if (s1 <= 0 && s2 <= 0 && -top < ext[1]) ext[1] = -top;
}

/** 三向贴图的投影面在自己平面里转一个角度,贴图的格子不和经纬线对齐 */
const TRI_C = Math.cos(0.61);
const TRI_S = Math.sin(0.61);
/** 三向贴图的混合:法向分量超过这个值的投影面才参与(极点、赤道附近只取一两个面,省一半取样) */
const TRI_T = 0.45;

/**
 * 当前像素的三向贴图参数 [X, Y, Z, w0, w1, w2],逐像素循环先写进来再调 tri3。
 * 放在类型化数组里传,而不是作为参数:一个像素要调好几次 tri3,小数作参数每次都要另外装箱,拖慢逐像素循环。
 */
const TRI_AT = new Float64Array(6);

/**
 * 三向贴图取样:球面上一点 (X, Y, Z)(世界单位,取自 TRI_AT)处,可平铺贴图 tile 在频率 f(每世界单位几个贴图像素)下的值。
 * 三个投影面(YZ、ZX、XY)各取一次,按权重 w0..w2 混合(调用方已按 √Σw² 归一:混合后标准差不变)。
 * o 是这一层的偏移,同一张贴图不同的 o 互不相关。size 必须是 2 的幂。
 */
function tri3(tile: Float32Array, size: number, f: number, o: number): number {
  const X = TRI_AT[0];
  const Y = TRI_AT[1];
  const Z = TRI_AT[2];
  const w0 = TRI_AT[3];
  const w1 = TRI_AT[4];
  const w2 = TRI_AT[5];
  const m = size - 1;
  let s = 0;
  for (let p = 0; p < 3; p++) {
    const wp = p === 0 ? w0 : p === 1 ? w1 : w2;
    if (!(wp > 0)) continue;
    let su: number;
    let sv: number;
    if (p === 0) {
      const u = Y * f;
      const v = Z * f;
      su = TRI_C * u - TRI_S * v + o;
      sv = TRI_S * u + TRI_C * v + 0.37 * o + 17.9;
    } else if (p === 1) {
      const u = Z * f;
      const v = X * f;
      su = TRI_C * u - TRI_S * v + 1.31 * o + 131.3;
      sv = TRI_S * u + TRI_C * v + 0.73 * o + 7.7;
    } else {
      const u = X * f;
      const v = Y * f;
      su = TRI_C * u - TRI_S * v + 0.59 * o + 61.1;
      sv = TRI_S * u + TRI_C * v + 1.13 * o + 233.9;
    }
    // 在贴图上双线性取值(坐标以贴图像素为单位,自动环绕);直接写在这里,省掉逐次调用
    const ui = Math.floor(su);
    const vi = Math.floor(sv);
    const tx = su - ui;
    const ty = sv - vi;
    const x0 = ui & m;
    const x1 = (ui + 1) & m;
    const r0 = (vi & m) * size;
    const r1 = ((vi + 1) & m) * size;
    const a = tile[r0 + x0];
    const b = tile[r0 + x1];
    const c = tile[r1 + x0];
    const d = tile[r1 + x1];
    const top = a + (b - a) * tx;
    s += wp * (top + (c + (d - c) * tx - top) * ty);
  }
  return s;
}

/**
 * 铺像素(流程见文件头)。沟和山脊、细沟(只管写实风的明暗、颜色)当场算好,存进 gully、vein;
 * gully = false:不算(高度图、手绘风、数据图层用不着,省下和整张图一样大的几个数组和逐像素的噪声)。
 * lines:细沟的线已经有了(放大导出时用屏幕上那张 1 倍主图的)就照它画,不重算
 */
export function rasterize(world: World, scale = 1, gully = true, lines?: DrainLines): Raster {
  const { raster, job, veins } = rasterizeRaw(world, scale, gully, lines);
  if (job) finishGully(raster, job, gullyHeights(job, 0, job.n));
  if (veins) finishVeins(raster, veinsOf(veins));
  return raster;
}

/**
 * 铺像素,但沟和山脊、细沟先不算:返回要算的像素(job)和细沟要的几样(veins)。这两样是铺像素里最慢的
 * (沟壑全是陆地上的逐像素噪声,细沟要逐像素汇流),后台线程可以分给几个线程,和推文明同时算
 * (gullyHeights 分段算、finishGully 叠回去;veinsOf 算、finishVeins 存进去);结果和 rasterize 一样
 */
export function rasterizeDeferred(world: World, scale = 1, lines?: DrainLines, cover?: Cover, pre?: Precomputed): { raster: Raster; job: GullyJob; veins: VeinJob; inputs: RasterInputs } {
  return drain(rasterizeDeferredSteps(world, scale, lines, cover, pre));
}

/**
 * 同 rasterizeDeferred,一段一段做(段与段之间 yield;逐像素那一步按整行分段):后台线程每隔一会儿让一下,
 * 新的一笔来了就不用等这张铺完(放下时什么都不用改回去:铺的是新开的数组)。做完的结果和 rasterizeDeferred 逐位相同
 */
export function* rasterizeDeferredSteps(world: World, scale = 1, lines?: DrainLines, cover?: Cover, pre?: Precomputed): Generator<void, { raster: Raster; job: GullyJob; veins: VeinJob; inputs: RasterInputs }> {
  const { raster, job, veins, inputs } = yield* rasterizeRawSteps(world, scale, true, lines, cover, pre);
  return { raster, job: trimJob(job!), veins: veins!, inputs };
}

/** 一口气做完一段一段做的 */
export function drain<T>(it: Generator<void, T>): T {
  for (;;) {
    const r = it.next();
    if (r.done) return r.value;
  }
}

/** 一段一段铺的时候,逐像素那一步每一段大约铺多少个像素(几毫秒) */
export const SHADE_STEP = 1 << 16;

/**
 * 已经算好的这个世界 1 倍主图的输入(rasterInputs;编辑地形按块重铺不划算、改成整张铺时接着用)和最近地块
 * (同一张网格、同一个球面三角形覆盖的主图,最近地块一样)
 */
export interface Precomputed {
  inputs: RasterInputs;
  cell: Int32Array;
}

/**
 * 球面三角形覆盖连同主栅格每列 / 每行的经纬度:只和网格、主图大小有关。
 * 编辑地形不换网格(gen/world.ts 的前一半接着用),铺下一张时接着用(sphereCover 一次几十毫秒)
 */
export interface Cover {
  mesh: Mesh;
  g: SphereGrid;
  tri: Int32Array;
  wa: Float32Array;
  wb: Float32Array;
}

/**
 * 铺像素的输入(只和世界有关):柔化后的海拔(base)、河谷下切(carve)、离河多近(calm)、三角形上的插值源(planes),
 * 外加球面三角形覆盖。编辑地形以后拿新旧两份比,就知道哪一块要重铺(gen/rasterEdit.ts)
 */
export interface RasterInputs {
  base: Float32Array;
  carve: Float32Array;
  calm: Float32Array;
  planes: Float32Array;
  cover: Cover;
  /** 算 base 用的地块海拔(CellFields.sElev)、刻河谷用的河和成河门槛:下一张这几样没变就接着用 base、carve、calm */
  sElev: Float32Array;
  rivers: readonly { pts: Float32Array }[];
  riverThreshold: number;
}

/** cover 是不是这个网格、这么大的主图的(网格对象换了也逐个比:重新生成出来的同一张网格照样认) */
export function coverFits(cover: Cover, mesh: Mesh, w: number, h: number): boolean {
  if (cover.g.w !== w || cover.g.h !== h) return false;
  const m = cover.mesh;
  if (m === mesh) return true;
  if (m.n !== mesh.n || m.triangles.length !== mesh.triangles.length || !m.xyz || !mesh.xyz || m.xyz.length !== mesh.xyz.length) return false;
  for (let i = 0; i < m.triangles.length; i++) if (m.triangles[i] !== mesh.triangles[i]) return false;
  for (let i = 0; i < m.xyz.length; i++) if (m.xyz[i] !== mesh.xyz[i]) return false;
  return true;
}

/** 细沟要流进的河和小溪(放大后画的、刻谷的同一组;每个世界记一份) */
export function streamsOf(world: World): Streams {
  let s = streamCache.get(world);
  if (!s) streamCache.set(world, (s = { rivers: [...world.rivers, ...creeksOf(world)], threshold: world.riverThreshold, width: world.width }));
  return s;
}
const streamCache = new WeakMap<World, Streams>();

/** 细沟存进主图 */
export function finishVeins(r: Raster, v: { lines: DrainLines; vein: Uint8Array }): void {
  r.veinLines = v.lines;
  r.vein = v.vein;
}

/** 铺像素;gully = true 时把要算沟壑的像素记进 job(没截短)、细沟要的几样记进 veins */
function rasterizeRaw(world: World, scale: number, gully: boolean, lines?: DrainLines, cover?: Cover, pre?: Precomputed): { raster: Raster; job: GullyJob | null; veins: VeinJob | null; inputs: RasterInputs } {
  return drain(rasterizeRawSteps(world, scale, gully, lines, cover, pre));
}

/** 同 rasterizeRaw,一段一段做(见 rasterizeDeferredSteps) */
function* rasterizeRawSteps(world: World, scale: number, gully: boolean, lines?: DrainLines, cover?: Cover, pre?: Precomputed): Generator<void, { raster: Raster; job: GullyJob | null; veins: VeinJob | null; inputs: RasterInputs }> {
  const pi = pre && scale === 1 && coverFits(pre.inputs.cover, world.mesh, Math.round(world.width), Math.round(world.height)) ? pre.inputs : null;
  const b = pi
    ? { w: pi.cover.g.w, h: pi.cover.g.h, N: pi.cover.g.w * pi.cover.g.h, g: pi.cover.g, tri: pi.cover.tri, wa: pi.cover.wa, wb: pi.cover.wb, planes: pi.planes, elev: pi.base, cell: pre!.cell, sElev: pi.sElev }
    : rasterBase(world, scale, cover);
  const { w, h, N } = b;
  let carve: Float32Array;
  let calm: Float32Array;
  if (pi) {
    carve = pi.carve;
    calm = pi.calm;
  } else {
    carve = (b as ReturnType<typeof rasterBase>).scratch.fill(0);
    calm = new Float32Array(N);
    carveValleys(valleyLines(world.rivers, world.riverThreshold, world.width), world.riverThreshold, scale, w, h, carve, calm);
  }
  yield;

  const { dTile, jTile } = noiseTiles(world.params.seed);
  const out: Raster = {
    w,
    h,
    scale,
    elev: new Float32Array(N),
    temp: new Float32Array(N),
    precip: new Float32Array(N),
    water: new Uint8Array(N),
    biome: new Uint8Array(N),
    cell: b.cell,
    ice: new Float32Array(N),
    iceConc: new Uint8Array(N),
    iceTone: new Uint8Array(N),
    wrap: true,
  };
  const R = world.width / (2 * Math.PI);
  const job = gully ? newGullyJob(subSeed(world.params.seed, 'gully'), w, h, R, scale) : null;
  // 逐像素按整行分段铺(一个像素只看输入,和一口气整张铺逐位相同;沟壑要算的像素照样按行记进 job)
  const rows = Math.max(1, Math.floor(SHADE_STEP / w));
  for (let y = 0; y < h; y += rows) {
    shadeSphere(out, b.tri, b.wa, b.wb, b.planes, b.elev, carve, calm, dTile, jTile, b.g, R, world.mesh.spacing, job, null, { x0: 0, y0: y, w, h: Math.min(rows, h - y) });
    yield;
  }
  dropSpecks(out, Math.round(SPECK_MAX * scale * scale));
  yield;
  out.bank = bankBytes(calm);
  seaIcePixels(world, out);
  // 细沟只有写实风用(和沟壑一样,gully = false 时不算)
  const veins: VeinJob | null = gully ? { w, h, scale, elev: out.elev, water: out.water, bank: out.bank, streams: lines ? undefined : streamsOf(world), lines } : null;
  const inputs: RasterInputs = {
    base: b.elev,
    carve,
    calm,
    planes: b.planes,
    cover: { mesh: world.mesh, g: b.g, tri: b.tri, wa: b.wa, wb: b.wb },
    sElev: b.sElev,
    rivers: world.rivers,
    riverThreshold: world.riverThreshold,
  };
  return { raster: out, job, veins, inputs };
}

/**
 * 去掉近岸噪声撒出来的陆地碎点:不超过 max 个像素(四连通)、四周全是没冰的海,改成浅海。
 * 只管整张主图;温度按海面改回(陆地像素按海拔降过温),群落重分
 */
function dropSpecks(r: Raster, max: number) {
  const { w, h, water, elev, temp, precip, biome, ice } = r;
  const seen = new Uint8Array(w * h);
  const comp: number[] = [];
  const stack: number[] = [];
  for (let k0 = 0; k0 < w * h; k0++) {
    if (water[k0] !== 0 || seen[k0]) continue;
    comp.length = 0;
    stack.push(k0);
    seen[k0] = 1;
    let shut = false;
    while (stack.length) {
      const k = stack.pop()!;
      comp.push(k);
      const x = k % w;
      const y = (k - x) / w;
      for (let d = 0; d < 4; d++) {
        if ((d === 2 && y === 0) || (d === 3 && y === h - 1)) {
          shut = true;
          continue;
        }
        const q = d === 0 ? k - x + ((x + w - 1) % w) : d === 1 ? k - x + ((x + 1) % w) : d === 2 ? k - w : k + w;
        if (water[q] === 0) {
          if (!seen[q]) {
            seen[q] = 1;
            stack.push(q);
          }
        } else if (water[q] !== 1 || ice[q] > 0) shut = true;
      }
    }
    if (shut || comp.length > max) continue;
    for (const k of comp) {
      temp[k] += LAPSE * Math.max(0, elev[k]);
      elev[k] = -2;
      water[k] = 1;
      biome[k] = classifyBiome(temp[k], precip[k], 1, 0);
    }
  }
}

/**
 * 同 dropSpecks,只看框里(编辑地形后按块重铺):连通块一碰到框边就当作不是碎点(框外的像素这时不一定是铺好的样子)。
 * 调用方保证框比要的那块四周各多出几个像素(碎点最多 max 个像素,离框边远的那块里结果和整张图一起做一样),多出的那圈另外换回原样
 */
export function dropSpecksIn(r: Raster, max: number, box: PixelBox) {
  const { w, h, water, elev, temp, precip, biome, ice } = r;
  const { x0: bx, y0: by, w: bw, h: bh } = box;
  // 框里的像素按框里的下标记"看过了":(y − by) × bw + 列在框里的第几列
  const seen = new Uint8Array(bw * bh);
  const comp: number[] = [];
  const stack: number[] = [];
  for (let y0 = by; y0 < by + bh; y0++) {
    for (const [xa, xb] of boxSpans(box, w)) {
      for (let x0 = xa; x0 < xb; x0++) {
        const k0 = y0 * w + x0;
        const d0 = x0 - bx;
        const l0 = (y0 - by) * bw + (d0 < 0 ? d0 + w : d0);
        if (water[k0] !== 0 || seen[l0]) continue;
        comp.length = 0;
        stack.push(k0);
        seen[l0] = 1;
        let shut = false;
        while (stack.length) {
          const k = stack.pop()!;
          comp.push(k);
          const x = k % w;
          const y = (k - x) / w;
          for (let d = 0; d < 4; d++) {
            if ((d === 2 && y === 0) || (d === 3 && y === h - 1)) {
              shut = true;
              continue;
            }
            const qx = d === 0 ? (x > 0 ? x - 1 : w - 1) : d === 1 ? (x < w - 1 ? x + 1 : 0) : x;
            const qy = d === 2 ? y - 1 : d === 3 ? y + 1 : y;
            let dq = qx - bx;
            if (dq < 0) dq += w;
            if (qy < by || qy >= by + bh || dq >= bw) {
              shut = true;
              continue;
            }
            const q = qy * w + qx;
            if (water[q] === 0) {
              const lq = (qy - by) * bw + dq;
              if (!seen[lq]) {
                seen[lq] = 1;
                stack.push(q);
              }
            } else if (water[q] !== 1 || ice[q] > 0) shut = true;
          }
        }
        if (shut || comp.length > max) continue;
        for (const k of comp) {
          temp[k] += LAPSE * Math.max(0, elev[k]);
          elev[k] = -2;
          water[k] = 1;
          biome[k] = classifyBiome(temp[k], precip[k], 1, 0);
        }
      }
    }
  }
}

/** 主图上碎点最多几个像素(scale 倍) */
export const speckMax = (scale: number) => Math.round(SPECK_MAX * scale * scale);

/**
 * 铺像素的前半段(整张主图和放大现算都要用):插值源、球面三角形覆盖、柔化后的海拔、最近地块。
 * cover:上一次铺这张网格时的球面三角形覆盖(对得上就接着用)
 */
export function rasterBase(world: World, scale: number, cover?: Cover) {
  const w = Math.round(world.width * scale);
  const h = Math.round(world.height * scale);
  const N = w * h;
  const mesh = world.mesh;
  const f = cellFields(world);
  const reuse = cover && coverFits(cover, mesh, w, h) ? cover : null;
  const g = reuse ? reuse.g : sphereGrid(w, h);
  const { tri, wa, wb } = reuse ?? sphereCover(mesh, g);
  const planes = cellPlanes(mesh, f);
  const elev = new Float32Array(N);
  const cell = new Int32Array(N);
  sphereFill(mesh.triangles, f.sElev, tri, wa, wb, elev, cell);

  // 柔化(约半个地块宽;东西向按纬度放宽,列下标取模)
  const br = Math.max(1, Math.round(mesh.spacing * scale * 0.35));
  const scratch = new Float32Array(N);
  blurSphere(elev, w, h, br, scratch, g.cosLat);
  blurSphere(elev, w, h, br, scratch, g.cosLat);
  return { w, h, N, g, tri, wa, wb, planes, elev, cell, scratch, sElev: f.sElev };
}

/**
 * 这个世界铺 1 倍主图的输入(见 RasterInputs),球面三角形覆盖用现成的 cover(调用方核对过对得上这张网格)。
 * prev = 上一张的输入:地块海拔一样就接着用它的 base,河一样就接着用它的 carve、calm(共用数组,都只读)。
 * 和 rasterBase、rasterizeRaw 里算的逐位相同
 */
export function rasterInputs(world: World, cover: Cover, prev?: RasterInputs): RasterInputs {
  const { w, h } = cover.g;
  const N = w * h;
  const mesh = world.mesh;
  const f = cellFields(world);
  const planes = cellPlanes(mesh, f);
  let base: Float32Array;
  if (prev && sameBits(prev.sElev, f.sElev)) base = prev.base;
  else {
    base = new Float32Array(N);
    sphereFill(mesh.triangles, f.sElev, cover.tri, cover.wa, cover.wb, base, null);
    const br = Math.max(1, Math.round(mesh.spacing * 0.35));
    const scratch = new Float32Array(N);
    blurSphere(base, w, h, br, scratch, cover.g.cosLat);
    blurSphere(base, w, h, br, scratch, cover.g.cosLat);
  }
  let carve: Float32Array;
  let calm: Float32Array;
  if (prev && prev.riverThreshold === world.riverThreshold && sameRivers(prev.rivers, world.rivers)) {
    carve = prev.carve;
    calm = prev.calm;
  } else {
    carve = new Float32Array(N);
    calm = new Float32Array(N);
    carveValleys(valleyLines(world.rivers, world.riverThreshold, world.width), world.riverThreshold, 1, w, h, carve, calm);
  }
  return { base, carve, calm, planes, cover: { ...cover, mesh }, sElev: f.sElev, rivers: world.rivers, riverThreshold: world.riverThreshold };
}

/** 两个数组逐位相同 */
function sameBits(a: Float32Array, b: Float32Array): boolean {
  if (a.length !== b.length) return false;
  const p = new Int32Array(a.buffer, a.byteOffset, a.length);
  const q = new Int32Array(b.buffer, b.byteOffset, b.length);
  for (let i = 0; i < p.length; i++) if (p[i] !== q[i]) return false;
  return true;
}

/** 两组河的折线逐位相同(刻河谷只看折线) */
function sameRivers(a: readonly { pts: Float32Array }[], b: readonly { pts: Float32Array }[]): boolean {
  if (a === b) return true;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (!sameBits(a[i].pts, b[i].pts)) return false;
  return true;
}

/** 海拔之外的字段存成"权重的线性函数":v = P₀·w_A + P₁·w_B + P₂(P₀ = v_A − v_C,P₁ = v_B − v_C,P₂ = v_C),每个三角形 PLANE 个数 */
export function cellPlanes(mesh: Mesh, f: CellFields): Float32Array {
  const { triangles } = mesh;
  const nt = triangles.length / 3;
  const planes = new Float32Array(nt * PLANE);
  const fields = [f.lake, f.amp, f.coast, f.t0, f.precip, f.rug, f.ice, f.land];
  for (let t = 0; t < nt; t++) {
    const a = triangles[3 * t];
    const b = triangles[3 * t + 1];
    const c = triangles[3 * t + 2];
    for (let q = 0; q < fields.length; q++) {
      const fv = fields[q];
      const o = t * PLANE + q * 3;
      planes[o] = fv[a] - fv[c];
      planes[o + 1] = fv[b] - fv[c];
      planes[o + 2] = fv[c];
    }
  }
  return planes;
}

// ---------------------------------------------------------------------------
// 整张主图的沟和山脊:先记下要算的像素,算好再叠回去

/**
 * 整张主图上要算沟和山脊的像素(按行排好)。gullyHeights 只要 GullyInput 那几样(可以分段交给后台线程);
 * base / cut / floor 留在原地,finishGully 用
 */
export interface GullyJob extends GullyInput {
  n: number;
  /** 叠沟壑之前的海拔(坡上的细节噪声已经压过) */
  base: Float32Array;
  /** 河谷往下切多少(米;0 = 不在河谷里) */
  cut: Float32Array;
  /** 1 = 内陆(最低垫到 2 米,不出现海) */
  floor: Uint8Array;
  /**
   * 叠到这一份上(编辑地形后按块重铺:原来那张图的沟壑,要重铺的那块先清零;gen/rasterEdit.ts)。
   * 没有 = 新开一份全 0 的
   */
  into?: Float32Array;
}

/** 记像素用的大数组(1 倍主图的)留着下次用:每次重新分配几十 MB 也要时间。导出用的大图不留(用完就放掉) */
let jobBuf: GullyJob | null = null;

/**
 * 记像素的数组先按整张图像素数的 JOB_START 分配,记满了再加大 JOB_GROW 倍(最多整张图那么大):
 * 要算沟壑的像素一般只占整张图的两三成,一开始就按整张分配,1 倍主图多占三十来 MB、两倍的导出图多占一百多 MB
 */
const JOB_START = 0.25;
const JOB_GROW = 1.5;

export function newGullyJob(seed: number, w: number, h: number, R: number, scale: number): GullyJob {
  const N = w * h;
  if (jobBuf && jobBuf.w === w && jobBuf.h === h) return { ...jobBuf, seed, w, h, R, scale, n: 0 };
  const cap = Math.min(N, Math.max(4096, Math.ceil(N * JOB_START)));
  const job: GullyJob = {
    seed,
    w,
    h,
    R,
    scale,
    n: 0,
    idx: new Int32Array(cap),
    ge: new Float32Array(cap),
    gn: new Float32Array(cap),
    amp: new Float32Array(cap),
    base: new Float32Array(cap),
    cut: new Float32Array(cap),
    floor: new Uint8Array(cap),
  };
  if (scale === 1) jobBuf = job;
  return { ...job };
}

/** 记满了:几个数组加大(记过的照搬),留着下次用的那一份跟着换 */
function growGullyJob(job: GullyJob): void {
  const cap = Math.min(job.w * job.h, Math.ceil(job.idx.length * JOB_GROW));
  const more = <T extends Int32Array | Float32Array | Uint8Array>(a: T): T => {
    const b = new (a.constructor as new (n: number) => T)(cap);
    b.set(a);
    return b;
  };
  const kept = jobBuf && jobBuf.idx === job.idx ? jobBuf : null;
  job.idx = more(job.idx);
  job.ge = more(job.ge);
  job.gn = more(job.gn);
  job.amp = more(job.amp);
  job.base = more(job.base);
  job.cut = more(job.cut);
  job.floor = more(job.floor);
  if (kept) Object.assign(kept, { idx: job.idx, ge: job.ge, gn: job.gn, amp: job.amp, base: job.base, cut: job.cut, floor: job.floor });
}

/**
 * 放掉留着下次用的大数组(1 倍主图上约 50 MB):不编辑地形的时候一个世界只铺一次像素,留着白占内存
 * (手机上内存紧);下次铺像素时再分配
 */
export function dropGullyBuffers(): void {
  jobBuf = null;
}

/** 按实际个数截短(交给后台线程时只拷用到的那一段) */
function trimJob(j: GullyJob): GullyJob {
  const n = j.n;
  return {
    ...j,
    idx: j.idx.slice(0, n),
    ge: j.ge.slice(0, n),
    gn: j.gn.slice(0, n),
    amp: j.amp.slice(0, n),
    base: j.base.slice(0, n),
    cut: j.cut.slice(0, n),
    floor: j.floor.slice(0, n),
  };
}

/** 只留框里的像素(按原来的先后),再按个数截短;沟壑叠到 into 上(编辑地形后按块重铺,见 GullyJob.into) */
export function trimJobIn(j: GullyJob, box: PixelBox, into: Float32Array): GullyJob {
  const { idx, ge, gn, amp, base, cut, floor, w } = j;
  let n = 0;
  for (let i = 0; i < j.n; i++) {
    const k = idx[i];
    const y = (k / w) | 0;
    if (!inBox(box, k - y * w, y, w)) continue;
    idx[n] = k;
    ge[n] = ge[i];
    gn[n] = gn[i];
    amp[n] = amp[i];
    base[n] = base[i];
    cut[n] = cut[i];
    floor[n] = floor[i];
    n++;
  }
  return { ...trimJob({ ...j, n }), into };
}

/** 算好的沟壑叠回去:raster.gully = 叠了沟壑(再按河谷、内陆规则修过)的海拔 − 原来的海拔 */
export function finishGully(r: Raster, j: GullyJob, heights: Float32Array): void {
  const gully = j.into ?? new Float32Array(r.w * r.h);
  const { idx, base, cut, floor } = j;
  const elev = r.elev;
  for (let i = 0; i < j.n; i++) {
    const k = idx[i];
    // 记下以后又被去掉的陆地碎点(dropSpecks)已经是海,不叠
    if (r.water[k] !== 0) continue;
    let eg = base[i] + heights[i];
    if (floor[i] && eg < 2) eg = 2;
    const c = cut[i];
    if (c > 0 && eg > 0) eg = Math.max(eg - c, Math.min(eg, 1));
    gully[k] = eg - elev[k];
  }
  r.gully = gully;
}

/** 按重心权重插值一个地块字段(海拔),同时定最近地块(权重最大的顶点) */
function sphereFill(
  triangles: Uint32Array,
  field: Float32Array,
  tri: Int32Array,
  wa: Float32Array,
  wb: Float32Array,
  out: Float32Array,
  cell: Int32Array | null,
) {
  for (let k = 0; k < out.length; k++) {
    const t = tri[k] - 1;
    if (t < 0) continue;
    const a = triangles[3 * t];
    const b = triangles[3 * t + 1];
    const c = triangles[3 * t + 2];
    const ua = wa[k];
    const ub = wb[k];
    const uc = 1 - ua - ub;
    out[k] = ua * field[a] + ub * field[b] + uc * field[c];
    if (cell) cell[k] = ua >= ub ? (ua >= uc ? a : c) : ub >= uc ? b : c;
  }
}

/** 球面网格上的一个标量场按球面三角形插值到 w × h 的等距圆柱主图(回放帧用;三角形覆盖按尺寸缓存) */
export function sphereField(mesh: Mesh, field: Float32Array, w: number, h: number): Float32Array {
  let c = coverCache.get(mesh);
  if (!c || c.w !== w || c.h !== h) coverCache.set(mesh, (c = { w, h, cover: sphereCover(mesh, sphereGrid(w, h)) }));
  const out = new Float32Array(w * h);
  sphereFill(mesh.triangles, field, c.cover.tri, c.cover.wa, c.cover.wb, out, null);
  return out;
}
const coverCache = new WeakMap<Mesh, { w: number; h: number; cover: SphereCover }>();

/**
 * 球面主图的盒式模糊(原地):东西向列下标取模,半径按纬度放宽(round(r / cos 纬度),极点附近整行平均 ——
 * 那几行本来就挤在极点周围一小块地方);南北向同平面(上下边按最近一行延伸)。
 */
function blurSphere(src: Float32Array, w: number, h: number, r: number, tmp: Float32Array, cosLat: Float32Array) {
  const maxR = (w - 1) >> 1;
  for (let y = 0; y < h; y++) {
    const row = y * w;
    const rx = Math.min(maxR, Math.round(r / Math.max(cosLat[y], 1e-3)));
    const inv = 1 / (2 * rx + 1);
    let acc = 0;
    for (let x = -rx; x <= rx; x++) acc += src[row + (x < 0 ? x + w : x >= w ? x - w : x)];
    for (let x = 0; x < w; x++) {
      tmp[row + x] = acc * inv;
      const add = x + rx + 1;
      const sub = x - rx;
      acc += src[row + (add >= w ? add - w : add)] - src[row + (sub < 0 ? sub + w : sub)];
    }
  }
  const acc = new Float64Array(w);
  for (let y = -r; y <= r; y++) {
    const row = (y < 0 ? 0 : y > h - 1 ? h - 1 : y) * w;
    for (let x = 0; x < w; x++) acc[x] += tmp[row + x];
  }
  const inv = 1 / (2 * r + 1);
  for (let y = 0; y < h; y++) {
    const row = y * w;
    const add = (y + r + 1 > h - 1 ? h - 1 : y + r + 1) * w;
    const sub = (y - r < 0 ? 0 : y - r) * w;
    for (let x = 0; x < w; x++) {
      src[row + x] = acc[x] * inv;
      acc[x] += tmp[add + x] - tmp[sub + x];
    }
  }
}

/** 山里的河谷切得更深:下切深度 × (1 + 当地起伏(米)/ 这个数) */
const VALLEY_RELIEF = 120;
/** 谷壁上的沟朝河拐多少:坡向 = 原来的坡 + 这个数 × 谷壁的坡 */
const VALLEY_PULL = 2;
/** 离河多近(Raster.bank 的 0..1)往里,地面的起伏、沟壑才压平 */
const VALLEY_FLOOR = 0.65;

/** 沟和山脊(gen/gully.ts)的强弱:幅度 = 系数 × (当地起伏 × 平地留多少 ~ 1(坡越陡越强)+ 破碎海岸另加) */
const GULLY_K = 1.1;
/** 平地上沟壑留多少(相对陡坡) */
const GULLY_FLAT = 0.3;
/** 破碎海岸(峡湾那样的)另加的幅度(米) */
const GULLY_FJORD = 160;
/** 坡度(米 / 世界单位)从多少到多少,沟壑从"平地"过渡到"陡坡" */
const GULLY_S0 = 2;
const GULLY_S1 = 30;
/** 幅度不到这么多米的地方不算(整张图上看不出来:写实风会把平原上很小的明暗起伏压掉) */
const GULLY_MIN = 5;

/**
 * 放大现算的一块(gen/rasterWindow.ts):海拔底图是整张主图柔化后的海拔(scale 1 倍)按三次 B 样条取样来的,
 * 海岸挪动也到这里取(会取到这一块外面)。(x0, y0) = 这一块左上角在 S 倍主图里的像素
 */
export interface ZoomBase {
  /** 沟和山脊(直接算进海拔) */
  gullies: Gullies;
  base: Float32Array;
  w: number;
  h: number;
  x0: number;
  y0: number;
  S: number;
}

/**
 * 主图的逐像素:字段按重心权重插值;噪声是三向贴图(按像素在球面上的三维位置取样,
 * 波长按地面上的世界单位算);海岸挪动的东西向位移按纬度放大(同样的地面距离,高纬度占更多像素)、列下标取模。
 * R = 球半径(世界单位)。
 * 沟和山脊:整张主图记进 job(之后 finishGully 单独存进 out.gully,海拔、水陆不变);放大现算的一块(zoom)直接算进海拔,
 * 另外多叠两层更细的细节噪声、海岸多挪一层细的(放大以后海岸、山都要更碎)。
 * rect:整张主图只铺这一块(编辑地形后按块重铺,gen/rasterEdit.ts);每个像素和整张一起铺逐位相同
 */
export function shadeSphere(
  out: Raster,
  tri: Int32Array,
  wA: Float32Array,
  wB: Float32Array,
  P: Float32Array,
  base: Float32Array,
  carve: Float32Array,
  calm: Float32Array,
  dTile: Float32Array,
  jTile: Float32Array,
  g: SphereGrid,
  R: number,
  spacing: number,
  job: GullyJob | null,
  zoom: ZoomBase | null = null,
  rect: PixelBox | null = null,
) {
  const { w, h, scale } = out;
  const ry0 = rect ? rect.y0 : 0;
  const ry1 = rect ? rect.y0 + rect.h : h;
  const rx0 = rect ? rect.x0 : 0;
  const rw = rect ? rect.w : w;
  const { elev: oElev, temp: oTemp, precip: oPrecip, water: oWater, biome: oBiome, ice: oIce } = out;
  const gl = zoom?.gullies ?? null;
  const { cosLon, sinLon, cosLat, sinLat } = g;
  // 贴图频率(每世界单位几个贴图像素):细节 1(波长约 14)、海岸低频 1/3、山地细纹理 2.37、气候抖动(波长约 40)
  const FJ = JITTER_SIZE / 18 / 40;
  const fine2 = !!zoom && scale >= 2;
  const fine4 = !!zoom && scale >= 4;
  const coarse = Math.min(2, Math.max(0, (spacing - COAST_FINE) / COAST_STEP));
  let ti = 0;
  for (let py = ry0; py < ry1; py++) {
    const row = py * w;
    const cl = cosLat[py];
    const sl = sinLat[py];
    const Z = sl * R;
    const a2 = (sl < 0 ? -sl : sl) - TRI_T;
    const w2r = a2 > 0 ? a2 * a2 : 0;
    // 海岸挪动的东西向位移:同样的地面距离在高纬度占 1 / cos(纬度) 个像素(极点附近封顶)
    const stretch = 1 / Math.max(cl, 0.05);
    const up = py > 0 ? -w : 0;
    const dn = py < h - 1 ? w : 0;
    for (let i = 0; i < rw; i++) {
      const px = rx0 + i < w ? rx0 + i : rx0 + i - w;
      const k = row + px;
      const tv = tri[k];
      if (tv > 0) ti = tv - 1;
      const o = ti * PLANE;
      const fx = wA[k];
      const fy = wB[k];
      const lake = P[o] * fx + P[o + 1] * fy + P[o + 2];
      const amp = P[o + 3] * fx + P[o + 4] * fy + P[o + 5];
      const cw = P[o + 6] * fx + P[o + 7] * fy + P[o + 8];

      // 三向贴图的权重(按像素在球面上的法向),归一到"混合后标准差不变"
      const cL = cosLon[px];
      const sL = sinLon[px];
      const qx = cl * cL;
      const qy = cl * sL;
      const X = qx * R;
      const Y = qy * R;
      const a0 = (qx < 0 ? -qx : qx) - TRI_T;
      const a1 = (qy < 0 ? -qy : qy) - TRI_T;
      let w0 = a0 > 0 ? a0 * a0 : 0;
      let w1 = a1 > 0 ? a1 * a1 : 0;
      let w2 = w2r;
      const nrm = 1 / Math.sqrt(w0 * w0 + w1 * w1 + w2 * w2);
      w0 *= nrm;
      w1 *= nrm;
      w2 *= nrm;

      TRI_AT[0] = X;
      TRI_AT[1] = Y;
      TRI_AT[2] = Z;
      TRI_AT[3] = w0;
      TRI_AT[4] = w1;
      TRI_AT[5] = w2;
      const e = base[k];
      let d = tri3(dTile, DETAIL_SIZE, 1, 0);
      if (fine2) d += 0.45 * tri3(dTile, DETAIL_SIZE, 2, 19.7);
      if (fine4) d += 0.2 * tri3(dTile, DETAIL_SIZE, 4, 27.1);
      const isLake = lake + 0.12 * d > 0.5;
      let ee = e;
      let eg = e;
      if (!isLake) {
        // 谷底(和谷壁最下面一点)平,谷壁上照样有沟(顺着谷壁流进河里)
        const q = 1 - 0.85 * smoothstep(VALLEY_FLOOR, 1, calm[k]);
        let eb = e;
        let rug = 0;
        if (cw > 0.01) {
          rug = P[o + 15] * fx + P[o + 16] * fy + P[o + 17];
          const flat = coarse * (1 - rug);
          const sD = (scale * smoothstep(0.01, 0.5, cw)) / DETAIL_STD;
          const D = (1.2 + 3.5 * rug) * sD;
          let wx = tri3(dTile, DETAIL_SIZE, 1, 211.3);
          let wy = tri3(dTile, DETAIL_SIZE, 1, 53.9);
          if (flat > 0.02) {
            // 粗网格的平原海岸:两层低频(波长约 56、28)把圆鼓的岸线掰出海湾和岬角
            const m = (COAST_BEND * flat) / (1.2 + 3.5 * rug);
            wx += m * (tri3(dTile, DETAIL_SIZE, 1 / 4, 401.9) + 0.5 * tri3(dTile, DETAIL_SIZE, 1 / 2, 433.7));
            wy += m * (tri3(dTile, DETAIL_SIZE, 1 / 4, 277.3) + 0.5 * tri3(dTile, DETAIL_SIZE, 1 / 2, 129.1));
          }
          if (fine2) {
            wx += 0.25 * tri3(dTile, DETAIL_SIZE, 2, 311.3);
            wy += 0.25 * tri3(dTile, DETAIL_SIZE, 2, 83.9);
          }
          if (rug > 0.02) {
            wx += 1.3 * rug * tri3(dTile, DETAIL_SIZE, 1 / 3, 101.7);
            wy += 1.3 * rug * tri3(dTile, DETAIL_SIZE, 1 / 3, 157.1);
          }
          eb = zoom
            ? sampleSpline(zoom.base, zoom.w, zoom.h, (zoom.x0 + px + 0.5 + D * wx * stretch) / zoom.S - 0.5, (zoom.y0 + py + 0.5 + D * wy) / zoom.S - 0.5)
            : sampleWrapped(base, w, h, px + D * wx * stretch, py + D * wy);
        }
        let dd = d;
        if (amp > 60 && e > 0) dd += 0.5 * smoothstep(60, 250, amp) * tri3(dTile, DETAIL_SIZE, 2.37, 33.1);
        ee = eb + amp * q * dd;
        const cv = carve[k];
        if (cw === 0 && ee < 2) ee = 2;
        if (cv > 0 && ee > 0) ee = Math.max(ee - cv * (1 + amp / VALLEY_RELIEF), Math.min(ee, 1));
        eg = ee;
        // 沟和山脊:坡向取柔化海拔的坡(东西向按纬度修正,列下标取模)。
        // 整张图只算陆地(只管打光,海上看不出来);放大现算的一块连近岸的浅海也算(沟壑会把海岸切碎)
        if ((job || gl) && (amp > 15 || cw > 0.01) && (zoom ? eb > -120 : ee >= 0)) {
          const ke = px < w - 1 ? k + 1 : k - w + 1;
          const kw = px > 0 ? k - 1 : k + w - 1;
          let ge = (base[ke] - base[kw]) * 0.5 * scale * stretch;
          let gn = (base[k + up] - base[k + dn]) * (up && dn ? 0.5 : 1) * scale;
          // 河谷的谷壁:坡向朝河(两边的沟顺着谷壁流进河里)
          if (cv > 0 || carve[ke] > 0 || carve[kw] > 0) {
            const kc = VALLEY_PULL * (1 + amp / VALLEY_RELIEF);
            ge -= (carve[ke] - carve[kw]) * 0.5 * scale * stretch * kc;
            gn -= (carve[k + up] - carve[k + dn]) * (up && dn ? 0.5 : 1) * scale * kc;
          }
          const st = smoothstep(GULLY_S0, GULLY_S1, Math.sqrt(ge * ge + gn * gn));
          const a = GULLY_K * q * (amp * (GULLY_FLAT + (1 - GULLY_FLAT) * st) + (rug > 0 ? GULLY_FJORD * rug * smoothstep(0.01, 0.5, cw) : 0));
          if (a > GULLY_MIN) {
            // 坡上本来的细节噪声压一些,让沟壑当主角
            const gb = eb + amp * q * dd * (1 - 0.6 * st);
            if (job) {
              if (job.n === job.idx.length) growGullyJob(job);
              const n = job.n++;
              job.idx[n] = k;
              job.ge[n] = ge;
              job.gn[n] = gn;
              job.amp[n] = a;
              job.base[n] = gb;
              job.cut[n] = cv > 0 ? cv * (1 + amp / VALLEY_RELIEF) : 0;
              job.floor[n] = cw === 0 ? 1 : 0;
            } else if (gl) {
              eg = gb + gl.height(X, Y, Z, -sL, cL, -sl * cL, -sl * sL, cl, ge, gn, a, scale);
              if (cw === 0 && eg < 2) eg = 2;
              if (cv > 0 && eg > 0) eg = Math.max(eg - cv * (1 + amp / VALLEY_RELIEF), Math.min(eg, 1));
            }
          }
        }
        if (zoom) ee = eg;
      }
      // 保留混合岸带的噪声；朝陆地内部平滑收敛，80% 陆地覆盖处不允许变海。
      // 放在 zoom 沟壑之后、温度/群落之前，整图、导出、局部细化共用同一约束。
      const land = P[o + 21] * fx + P[o + 22] * fy + P[o + 23];
      if (!isLake && ee < 2) ee += (2 - ee) * smoothstep(0.5, 0.8, land);
      oElev[k] = ee;
      const wtr = isLake ? 2 : ee < 0 ? 1 : 0;
      oWater[k] = wtr;
      const j = tri3(jTile, JITTER_SIZE, FJ, 3.7);
      const t = P[o + 9] * fx + P[o + 10] * fy + P[o + 11] - LAPSE * Math.max(0, wtr === 1 ? 0 : ee) + 1.2 * j;
      oTemp[k] = t;
      const pr = (P[o + 12] * fx + P[o + 13] * fy + P[o + 14]) * (1 + 0.22 * j);
      oPrecip[k] = pr;
      oBiome[k] = classifyBiome(t, pr, wtr, 0);
      if (wtr === 1 && tv > 0) {
        const c0 = P[o + 18] * fx + P[o + 19] * fy + P[o + 20];
        if (c0 > SEA_ICE_MIN) oIce[k] = c0;
      }
    }
  }
}

/**
 * 整张主图铺像素时海岸挪动(shadeSphere 里取 eb 的那一步)最多挪多少个像素(东西向再乘 shadeSphere 里的 stretch):
 * 挪动 = D × (几层三向贴图取样的加权和),D = (1.2 + 3.5 rug) × sD,sD ≤ scale / DETAIL_STD;
 * 每次三向贴图取样不超过 √3 × 贴图的最大绝对值(三个投影面的权重平方和是 1)。
 * wx = n₁ + m·(n₂ + 0.5·n₃) + 1.3·rug·n₄,m = COAST_BEND·flat / (1.2 + 3.5 rug),flat = coarse·(1 − rug):
 * D·wx 的系数 (1.2 + 3.5 rug)(1 + 1.3 rug) + 1.5·COAST_BEND·coarse·(1 − rug) 对 rug 是下凸的,最大在 rug = 0 或 1;wy 同理。
 * 按最坏的组合算,只多不少(编辑地形后按块重铺,要往外扩多少看它,gen/rasterEdit.ts;改上面那几个系数时这里跟着改)
 */
export function coastShiftMax(seed: number, spacing: number, scale: number): number {
  const { dTile } = noiseTiles(seed);
  let tm = tileMax.get(dTile);
  if (tm === undefined) {
    tm = 0;
    for (let i = 0; i < dTile.length; i++) tm = Math.max(tm, Math.abs(dTile[i]));
    tileMax.set(dTile, tm);
  }
  const coarse = Math.min(2, Math.max(0, (spacing - COAST_FINE) / COAST_STEP));
  const k = Math.max((1.2 + 3.5) * (1 + 1.3), 1.2 + 1.5 * COAST_BEND * coarse);
  return (scale / DETAIL_STD) * Math.sqrt(3) * tm * k * 1.001 + 1;
}
const tileMax = new WeakMap<Float32Array, number>();

/**
 * 东西相连的主图上三次 B 样条取值(列下标取模,行夹在上下边之内):比双线性平滑(二阶导数连续),
 * 放大很多倍再打光也看不出一格一格
 */
export function sampleSpline(base: Float32Array, w: number, h: number, sx: number, sy: number): number {
  const xf = Math.floor(sx);
  const yf = Math.floor(sy);
  const tx = sx - xf;
  const ty = sy - yf;
  const ux = 1 - tx;
  const uy = 1 - ty;
  const bx0 = (ux * ux * ux) / 6;
  const bx1 = (3 * tx * tx * tx - 6 * tx * tx + 4) / 6;
  const bx2 = (-3 * tx * tx * tx + 3 * tx * tx + 3 * tx + 1) / 6;
  const bx3 = (tx * tx * tx) / 6;
  let x0 = (xf - 1) % w;
  if (x0 < 0) x0 += w;
  const x1 = x0 + 1 === w ? 0 : x0 + 1;
  const x2 = x1 + 1 === w ? 0 : x1 + 1;
  const x3 = x2 + 1 === w ? 0 : x2 + 1;
  let v = 0;
  for (let j = 0; j < 4; j++) {
    const yy = yf - 1 + j;
    const r = (yy < 0 ? 0 : yy > h - 1 ? h - 1 : yy) * w;
    const by = j === 0 ? (uy * uy * uy) / 6 : j === 1 ? (3 * ty * ty * ty - 6 * ty * ty + 4) / 6 : j === 2 ? (-3 * ty * ty * ty + 3 * ty * ty + 3 * ty + 1) / 6 : (ty * ty * ty) / 6;
    v += by * (bx0 * base[r + x0] + bx1 * base[r + x1] + bx2 * base[r + x2] + bx3 * base[r + x3]);
  }
  return v;
}

/** 东西相连的主图上双线性取值:列下标取模,行夹在上下边(极点)之内 */
function sampleWrapped(base: Float32Array, w: number, h: number, sx: number, sy: number): number {
  sy = sy < 0 ? 0 : sy > h - 1 ? h - 1 : sy;
  const xf = Math.floor(sx);
  const tx = sx - xf;
  let x0 = xf % w;
  if (x0 < 0) x0 += w;
  const x1 = x0 + 1 === w ? 0 : x0 + 1;
  const y0 = Math.floor(sy);
  const y1 = y0 < h - 1 ? y0 + 1 : y0;
  const ty = sy - y0;
  const r0 = y0 * w;
  const r1 = y1 * w;
  const top = base[r0 + x0] + (base[r0 + x1] - base[r0 + x0]) * tx;
  const bot = base[r1 + x0] + (base[r1 + x1] - base[r1 + x0]) * tx;
  return top + (bot - top) * ty;
}
