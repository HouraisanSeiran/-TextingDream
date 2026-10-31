// 原生宿主数据桥的**真实 JS 行为**探针（给 tests/test_civ_native_contract.py 调）。
//
// 不是字符串断言：真的把上游 `src/dream/bridge.ts` 跑起来——切容器、逐块校验、
// 上游 `unpackValue` 解码、上游 `rasterize` 现算栅格；并用本地 fetch 桩把
// `/api/inner/native-worlds*` 的真实形状（`app/native_worlds.py` 的 detail/pairs）
// 喂进去，验证安全上下文与非安全（无 crypto.subtle）两条路。
//
// 用法： tsx tools/dream_bridge_behavior.mjs <real.civsnap>  → stdout 一行 JSON
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';

import { canSave, readNativeWorld, splitParts } from '../external/civ-atlas/src/dream/bridge.ts';
import { readPart } from '../external/civ-atlas/src/gen/snapshot.ts';

const IMPORT_ID = 'sn_2f3648720158';
const SAMPLE = process.argv[2];
if (!SAMPLE) {
  console.error('需要真实 .civsnap 路径');
  process.exit(2);
}

const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
const container = new Uint8Array(readFileSync(SAMPLE));
const wholeSum = sha256(container);

/** 服务端（`app/civ_atlas_snapshot.py:749`）的逐块口径：对解压后的字节算 SHA-256。 */
function serverPart(part) {
  const raw = part.zip === 'gzip'
    ? new Uint8Array(gunzipSync(new Uint8Array(part.data)))
    : new Uint8Array(part.data);
  return { name: part.name, bytes: raw.length, zip: part.zip,
           length: part.data.byteLength, sum: sha256(raw), sum_verified_by: 'server' };
}

function metaOf(parts) {
  return {
    identity: { import_id: IMPORT_ID, sha256: wholeSum, world_id: 'wmvrpuwi29m3yi',
                generator_version: 45, snapshot_format: 1 },
    story_revision: null,
    story_id: null,
    parts,
    available: true,
  };
}

/** 本地 fetch 桩：只应答两个作者路由，别的路径直接报错（证明没打别的接口）。 */
function serve(meta) {
  const asked = [];
  globalThis.fetch = async (url, init) => {
    asked.push(String(url));
    if (init?.headers?.['X-TextileDream-Token'] !== 'test-token') {
      return new Response('禁止访问', { status: 403 });
    }
    if (String(url) === '/api/inner/native-worlds/' + IMPORT_ID) {
      return new Response(JSON.stringify(meta), { status: 200 });
    }
    if (String(url) === '/api/inner/native-worlds/' + IMPORT_ID + '/snapshot') {
      return new Response(container, { status: 200 });
    }
    return new Response('没有这个接口：' + url, { status: 404 });
  };
  return asked;
}

const report = { sample: SAMPLE, containerBytes: container.length, wholeSum };

// ---- 1. 切容器：形状必须与 Python 的 parse_container 一致 ------------------
const { manifest, parts } = splitParts(container);
report.split = {
  manifestWorldId: manifest?.world?.id ?? null,
  manifestGenerator: manifest?.snapshot?.generator ?? null,
  manifestFormat: manifest?.snapshot?.format ?? null,
  names: parts.map((p) => p.name),
  parts: parts.map((p) => ({ name: p.name, bytes: p.bytes, sum: p.sum, zip: p.zip,
                             length: p.data.byteLength })),
};
if (JSON.stringify(report.split.names) !== JSON.stringify(['map', 'eras', 'civ'])) {
  throw new Error('块清单不对：' + JSON.stringify(report.split.names));
}

// ---- 2. 安全上下文：readNativeWorld 全链路 ---------------------------------
const witnesses = parts.map(serverPart);
report.serverParts = witnesses;
globalThis.window = { __textileDreamToken: 'test-token' };
const asked = serve(metaOf(witnesses));
const started = Date.now();
const secure = await readNativeWorld(IMPORT_ID);
report.secureLoadMs = Date.now() - started;
report.secure = {
  cells: secure.world?.mesh?.n ?? null,
  raster: [secure.raster.w, secure.raster.h],
  rasterPixels: secure.raster.elev.length,
  waterLand: secure.raster.water.reduce((n, v) => n + (v === 0 ? 1 : 0), 0),
  elevationFinite: secure.raster.elev.every(Number.isFinite),
  hasCiv: !!secure.civ,
  civRegions: secure.civ?.regions?.count ?? null,
  civEndYear: secure.civ?.endYear ?? null,
  identitySha: secure.identity.contentSha256,
  importId: secure.identity.importId,
  storyRevision: secure.storyRevision,
  canSaveAuthor: canSave(secure.identity, 'author'),
  canSavePlayer: canSave(secure.identity, 'player'),
  canSaveWithoutSha: canSave({ ...secure.identity, contentSha256: null }, 'author'),
  askedRoutes: asked.slice(),
};
if (secure.raster.w <= 0 || secure.raster.h <= 0) throw new Error('栅格没有算出来');
if (secure.raster.elev.length !== secure.raster.w * secure.raster.h) {
  throw new Error('raster.elev 长度与 w×h 不一致');
}
// map 块里没有 raster 字段：所以栅格一定是现算的（长度对得上就算证明）
const mapPart = parts.find((p) => p.name === 'map');
const decodedMap = await readPart(mapPart);
report.mapHasRasterField = Object.prototype.hasOwnProperty.call(decodedMap, 'raster');
if (report.mapHasRasterField) throw new Error('map 块里竟然有 raster');

// ---- 3. 非安全上下文（跨机 HTTP：没有 crypto.subtle） ----------------------
const nativeCrypto = globalThis.crypto;
function withoutSubtle() {
  Object.defineProperty(globalThis, 'crypto', {
    value: { getRandomValues: (a) => a }, configurable: true, writable: true,
  });
}
function restoreCrypto() {
  Object.defineProperty(globalThis, 'crypto', {
    value: nativeCrypto, configurable: true, writable: true,
  });
}

const insecure = {};
// 3a. 有服务端逐块见证：照样读得出来，且结果与安全上下文一致
withoutSubtle();
try {
  serve(metaOf(witnesses));
  const viaWitness = await readNativeWorld(IMPORT_ID);
  insecure.withWitness = {
    raster: [viaWitness.raster.w, viaWitness.raster.h],
    cells: viaWitness.world.mesh.n,
    sameIdentity: viaWitness.identity.contentSha256 === secure.identity.contentSha256,
  };
  if (viaWitness.raster.w !== secure.raster.w || viaWitness.raster.h !== secure.raster.h) {
    throw new Error('有见证时算出的栅格与安全上下文不一致');
  }
  // 3b. 缺见证：必须明确拒绝，不能静默降级
  const unsigned = witnesses.map((w) => ({ ...w, sum: null, sum_verified_by: null }));
  serve(metaOf(unsigned));
  try {
    await readNativeWorld(IMPORT_ID);
    throw new Error('缺服务端见证时竟然没拒');
  } catch (error) {
    insecure.withoutWitness = String(error.message || error);
  }
  // 3c. 服务端记录与原件不符：must reject
  const wrongSum = witnesses.map((w) => ({ ...w, sum: 'f'.repeat(64) }));
  serve(metaOf(wrongSum));
  try {
    await readNativeWorld(IMPORT_ID);
    throw new Error('服务端记录的块校验和与原件不符时竟然没拒');
  } catch (error) {
    insecure.wrongSum = String(error.message || error);
  }
  // 3d. 块长度与服务端记录不符：must reject
  const wrongLength = witnesses.map((w) => ({ ...w, length: (w.length || 0) + 8 }));
  serve(metaOf(wrongLength));
  try {
    await readNativeWorld(IMPORT_ID);
    throw new Error('块长度与服务端记录不符时竟然没拒');
  } catch (error) {
    insecure.wrongLength = String(error.message || error);
  }
  // 3e. 身份不符：manifest 里的世界编号 vs 服务端记录
  serve({ ...metaOf(witnesses),
          identity: { ...metaOf(witnesses).identity, world_id: 'otherworld' } });
  try {
    await readNativeWorld(IMPORT_ID);
    throw new Error('世界编号与服务端不符时竟然没拒');
  } catch (error) {
    insecure.wrongWorld = String(error.message || error);
  }
} finally {
  restoreCrypto();
}
report.insecure = insecure;

// 非安全上下文里没有任何一条路依赖 crypto.subtle：上面 3a 能解开就是证明。
console.log(JSON.stringify({ ok: true, ...report }));
