// 织梦原生宿主的数据桥：**不自己实现快照格式，也不自己校验/上色**。
//
//   外层 CASNAP01  我们自己的导出容器。这里只切出 `SnapshotPart`（name/bytes/sum/zip/data），
//                  然后交给上游 `src/gen/snapshot.ts:321 readPart`——它自己做长度、
//                  SHA-256、压缩方式校验，并调 `unpackValue`。我们不重复实现任何一项。
//   来源身份     **由后端给**（`/api/inner/native-worlds/{id}` 的 `identity.sha256`）。
//                  浏览器不算 hash：`crypto.subtle` 在用户跨机器 HTTP（非 secure context）
//                  根本不存在，而且来源身份本来就该以服务端为准。
//
//   绘制不用本文件：`host.tsx` 调上游 `render/export.ts` 的 `drawMapTerrain` / `drawMapCiv`。
//
// 两个模式：
//   作者  走 `/api/inner/native-worlds*`（需 token），拿完整原件。
//   玩家  **不走这里**：玩家路的已知投影走会话接口（服务端已遮罩）。

import { readPart, unpackValue, type SnapshotPart } from '../gen/snapshot';
import { rasterize, type Raster } from '../gen/raster';
import type { World } from '../gen/world';
import type { Civ } from '../gen/civ/types';

export type BridgeMode = 'author' | 'player';

export interface SourceIdentity {
  /** 服务端算的整件 sha256（64 位 hex）。空 = 不可保存。 */
  contentSha256: string | null;
  worldId: string | null;
  generator: number | null;
  snapshotFormat: number | null;
  importId: string | null;
}

export interface NativeWorldRow {
  importId: string;
  worldId: string | null;
  snapshotFormat: number | null;
  generator: number | null;
  bytes: number | null;
}

/** 服务端记的一块（`app/native_worlds.py:58 _parts`）：不含字节本身。 */
export interface NativeWorldPart {
  name: string;
  /** 解压后的字节数（上游口径）。 */
  bytes: number | null;
  zip: string | null;
  /** 容器里的字节数（压缩后）。 */
  length: number | null;
  /** 服务端对**解压后**字节算的 SHA-256（与上游 `part.sum` 同口径）。 */
  sum: string | null;
  /** `'server'` = 这一块的 sum 是服务端解析时真算出来的。 */
  sumVerifiedBy: string | null;
}

export interface NativeWorldMeta {
  identity: SourceIdentity;
  storyRevision: string | null;
  storyId: string | null;
  parts: NativeWorldPart[];
  available: boolean;
}

export interface NativeWorld {
  world: World;
  civ: Civ | null;
  raster: Raster;
  /** 来源身份一律取服务端这份，浏览器不自己算 hash。 */
  identity: SourceIdentity;
  storyRevision: string | null;
}

const CASNAP_MAGIC = 'CASNAP01';
/** 单块解压后的硬上限（CIVSNAP1 结构 + 数组，远小于这个）。 */
const MAX_PART_BYTES = 128 * 1024 * 1024;
const HEX64 = /^[0-9a-f]{64}$/;

/** 作者令牌由宿主页注入（`window.__textileDreamToken`）。 */
function authorToken(): string {
  const injected = (window as any).__textileDreamToken;
  return typeof injected === 'string' ? injected : '';
}

/** `''` = 同源。宿主固定同源，不接受跳源 base。 */
export const API_BASE = '';

async function jsonGet(path: string): Promise<any> {
  const response = await fetch(API_BASE + path,
    { headers: { 'X-TextileDream-Token': authorToken() } });
  const text = await response.text();
  let body: any = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = null; }
  if (!response.ok) {
    const detail = (body && (body.detail || body.message)) || text || response.statusText;
    throw new Error(detail);
  }
  return body;
}

/**
 * 能不能把草稿绑到这份原件上保存：要作者模式，且服务端给了**完整**来源身份。
 *
 * 这是「来源是否可信」的判断，不是「现在能不能发请求」的判断——两者不混。
 */
export function canSave(identity: SourceIdentity | null, mode: BridgeMode): boolean {
  if (!identity || mode !== 'author') return false;
  if (!identity.importId || !identity.worldId) return false;
  return typeof identity.contentSha256 === 'string' && HEX64.test(identity.contentSha256);
}

/** 作者侧可回放的原件（服务端登记过的导入，只有 CASNAP01）。 */
export async function listNativeWorlds(): Promise<NativeWorldRow[]> {
  const body = await jsonGet('/api/inner/native-worlds');
  const rows = Array.isArray(body) ? body : (body && body.worlds) || [];
  return rows.map((row: any) => ({
    importId: row.import_id,
    worldId: row.world_id ?? null,
    snapshotFormat: row.snapshot_format ?? null,
    generator: row.generator_version ?? null,
    bytes: row.bytes ?? null,
  }));
}

/** 一份原件的完整身份 + 可用性（作者路由）。 */
export async function nativeWorldMeta(importId: string): Promise<NativeWorldMeta> {
  const body = await jsonGet('/api/inner/native-worlds/' + encodeURIComponent(importId));
  const identity = body?.identity || {};
  return {
    identity: {
      contentSha256: identity.sha256 ?? null,
      worldId: identity.world_id ?? null,
      generator: identity.generator_version ?? null,
      snapshotFormat: identity.snapshot_format ?? null,
      importId: identity.import_id ?? importId,
    },
    storyRevision: body?.story_revision ?? null,
    storyId: body?.story_id ?? null,
    parts: (body?.parts || []).map((part: any) => ({
      name: String(part?.name ?? ''),
      bytes: part?.bytes ?? null,
      zip: part?.zip ?? null,
      length: part?.length ?? null,
      sum: part?.sum ?? null,
      sumVerifiedBy: part?.sum_verified_by ?? null,
    })),
    available: body?.available !== false,
  };
}

/** 取原 CASNAP01 字节。作者路由，必须带 token。 */
export async function fetchSnapshotBytes(importId: string): Promise<Uint8Array> {
  const response = await fetch(
    API_BASE + '/api/inner/native-worlds/' + encodeURIComponent(importId) + '/snapshot',
    { headers: { 'X-TextileDream-Token': authorToken() } });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return new Uint8Array(await response.arrayBuffer());
}

/**
 * 切出 `SnapshotPart` 列表（不展开、不校验——那些是 `readPart` 的事）。
 *
 * 形状与 `app/civ_atlas_snapshot.py:131 parse_container` 一致：magic + uint32LE 清单长度
 * + UTF-8 JSON 清单 + 补到 8，然后各块字节（8 字节对齐）。
 */
export function splitParts(data: Uint8Array): {
  manifest: any; parts: SnapshotPart[];
} {
  const magic = new TextDecoder().decode(data.subarray(0, 8));
  if (magic !== CASNAP_MAGIC) throw new Error('不是 CASNAP01 容器');
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const headLen = view.getUint32(8, true);
  if (!headLen || 12 + headLen > data.length) throw new Error('清单被截断');
  const manifest = JSON.parse(new TextDecoder().decode(data.subarray(12, 12 + headLen)));
  const bodyStart = (12 + headLen + 7) & ~7;
  const parts: SnapshotPart[] = [];
  for (const entry of manifest.parts || []) {
    const offset = Number(entry.offset);
    const length = Number(entry.length);
    if (!Number.isFinite(offset) || !Number.isFinite(length) || offset < bodyStart
        || offset + length > data.length) {
      throw new Error('数据块 ' + entry.name + ' 越界');
    }
    const slice = data.slice(offset, offset + length);
    parts.push({
      name: String(entry.name),
      // 这两项是 readPart 校验用的（解压后长度与 SHA-256），由导出器写入。
      bytes: Number(entry.bytes ?? 0),
      sum: String(entry.sum ?? ''),
      zip: entry.zip === 'gzip' ? 'gzip' : 'none',
      data: slice.buffer,
    });
  }
  return { manifest, parts };
}

/**
 * 把一份原件装回 `CASNAP01` 容器（与 `tools/civ_atlas_export.js` 逐字节同口径）。
 *
 * 为什么作者生成完不能直接交给后端：后端只有一个入口——它认的是我们自己定义的容器
 * （`app/civ_atlas_snapshot.py:131 parse_container` 在导入时做全套校验并记下逐块 sum）。
 * 所以生成完就地打包、直接 POST，作者不用再“导出文件再手动导入”一趟。
 *
 * `offset` 写成定宽十进制串：清单会把 offset 一起序列化，长度就与数值位数无关，
 * 一遍就能算准（这正是导出器当初踩过的坑）。
 */
export function packContainer(snapshot: { format: number; generator: number; recipe: string;
                                           formation: boolean; parts: SnapshotPart[] },
                              worldId: string, app = '织梦原生宿主'): Uint8Array {
  const pad8 = (n: number) => (n + 7) & ~7;
  const padOffset = (value: number) => String(value).padStart(12, '0');
  const manifest: any = {
    container: CASNAP_MAGIC,
    schema: 1,
    exported_by: '织梦 src/dream/bridge.ts',
    exported_at: new Date().toISOString(),
    site: typeof location !== 'undefined' ? location.origin : '',
    world: { id: worldId, generator: snapshot.generator, app, at: '' },
    snapshot: { format: snapshot.format, generator: snapshot.generator,
                recipe: snapshot.recipe, formation: Boolean(snapshot.formation) },
    parts: snapshot.parts.map((part) => ({
      name: part.name,
      bytes: part.bytes,
      sum: part.sum,
      zip: part.zip,
      length: part.data.byteLength,
      offset: padOffset(0),
    })),
  };
  const encoder = new TextEncoder();
  // 先写占位 offset 算 body 起点；定宽串不随数值变，清单长度不变
  let head = encoder.encode(JSON.stringify(manifest));
  const bodyStart = pad8(CASNAP_MAGIC.length + 4 + head.length);
  let cursor = bodyStart;
  manifest.parts.forEach((part: any, index: number) => {
    part.offset = padOffset(cursor);
    cursor = pad8(cursor + snapshot.parts[index].data.byteLength);
  });
  head = encoder.encode(JSON.stringify(manifest));
  if (pad8(CASNAP_MAGIC.length + 4 + head.length) !== bodyStart) {
    throw new Error('清单长度不稳定，拒绝打包');
  }
  const offsets: number[] = [];
  let at = bodyStart;
  snapshot.parts.forEach((part) => {
    offsets.push(at);
    at = pad8(at + part.data.byteLength);
  });
  const end = snapshot.parts.reduce(
    (max, part, index) => Math.max(max, offsets[index] + part.data.byteLength), bodyStart);
  const out = new Uint8Array(end);
  for (let i = 0; i < CASNAP_MAGIC.length; i += 1) out[i] = CASNAP_MAGIC.charCodeAt(i);
  new DataView(out.buffer).setUint32(CASNAP_MAGIC.length, head.length, true);
  out.set(head, CASNAP_MAGIC.length + 4);
  snapshot.parts.forEach((part, index) => {
    out.set(new Uint8Array(part.data), offsets[index]);
  });
  return out;
}

/**
 * 把打包好的原件交给后端登记（`POST /api/inner/map-imports`），返回导入编号。
 *
 * 服务端会重新走一遍自己的解析器、逐块重算 sum 并记住 `sum_verified_by: 'server'`；
 * 同一个内容哈希重复上传是幂等的（返回已有记录）。
 *
 * **不传 `generator_version`**：那个 query 参数在后端是 `strict=True` 的 int，
 * 而 query 字符串永远是字符串，传它必然 422。版本号本来就在容器清单的
 * `snapshot.generator` 里（服务端从清单读，不靠这个 query），所以不传不丢信息。
 */
export async function uploadSnapshot(
  bytes: Uint8Array,
  meta: { note?: string } = {},
): Promise<{ importId: string; worldId: string | null }> {
  const query = new URLSearchParams();
  if (meta.note) query.set('note', meta.note);
  const suffix = query.toString() ? '?' + query.toString() : '';
  const response = await fetch(API_BASE + '/api/inner/map-imports' + suffix, {
    method: 'POST',
    headers: { 'X-TextileDream-Token': authorToken(),
               'Content-Type': 'application/octet-stream' },
    body: bytes,
  });
  const text = await response.text();
  let body: any = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = null; }
  if (!response.ok) {
    const detail = body && body.detail;
    const reason = typeof detail === 'string' ? detail
      : Array.isArray(detail) ? detail.map((item: any) => item?.msg || JSON.stringify(item)).join('；')
      : (text || response.statusText);
    throw new Error('上传失败（' + response.status + '）：' + reason);
  }
  const importId = body?.id ?? null;
  if (!importId) throw new Error('上传已受理但没有拿到导入编号');
  return { importId, worldId: body?.source?.world_id ?? null };
}

/** 浏览器有没有 WebCrypto？用户跳机走 HTTP（非 secure context）时它会不存在。 */
function hasSubtle(): boolean {
  return typeof crypto !== 'undefined' && !!(crypto as any).subtle;
}

/** 有界解压：超过 limit 就拒，不把整块吐进内存再量。 */
async function inflateBounded(blob: ArrayBuffer, limit: number): Promise<Uint8Array> {
  const stream = new Blob([blob]).stream().pipeThrough(new DecompressionStream('gzip'));
  const reader = stream.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > limit) {
      await reader.cancel();
      throw new Error('数据块解压后超过上限 ' + limit + ' 字节');
    }
    chunks.push(value);
  }
  const out = new Uint8Array(total);
  let at = 0;
  for (const chunk of chunks) { out.set(chunk, at); at += chunk.byteLength; }
  return out;
}

/**
 * 解一块：优先上游 `readPart`（它自带长度 + SHA-256 + 压缩方式校验）。
 *
 * `readPart` 内部也直接调 `crypto.subtle`（`gen/snapshot.ts:136`），而用户跳机走
 * HTTP 时那是 **非 secure context**，`crypto.subtle` 不存在。此时：
 *
 *   * 只有当服务端 metadata 明确给出这一块的 `sum_verified_by === 'server'` 见证，
 *     且声明的 `bytes`（解压后长度）与 `length`（压缩后长度）都与实际一致时，
 *     才改用**有界** inflate + 上游 `unpackValue`；
 *   * 缺见证就明确拒绝，不静默降级。
 *
 * 两条路都不自己算 hash：来源身份以服务端 `identity.sha256` 为准，逐块校验要么由
 * `readPart` 在浏览器里做，要么由服务端在导入时做过（`sum_verified_by: 'server'`）。
 */
async function readVerifiedPart(part: SnapshotPart,
                                witness: NativeWorldPart | undefined): Promise<unknown> {
  // 服务端真算过 sum 的话，manifest 里写的 sum 必须与它一致（改过的原件在这里露馅）。
  const serverSum = witness?.sum ?? null;
  if (serverSum && HEX64.test(serverSum) && part.sum && part.sum !== serverSum) {
    throw new Error('数据块 ' + part.name + ' 的校验和与服务端记录不一致');
  }
  if (hasSubtle()) return readPart(part);
  const verified = witness?.sumVerifiedBy === 'server' && !!serverSum;
  if (!verified) {
    throw new Error('这份原件没有服务端逐块校验见证，且当前页面无法本地校验；'
                    + '请在 HTTPS 或 localhost 下打开');
  }
  const declared = witness?.bytes == null ? part.bytes : Number(witness.bytes);
  if (!declared || declared > MAX_PART_BYTES) {
    throw new Error('服务端声明的解压长度不可信：' + String(declared));
  }
  const compressed = part.data.byteLength;
  const recorded = witness?.length == null ? null : Number(witness.length);
  if (recorded != null && recorded !== compressed) {
    throw new Error('数据块 ' + part.name + ' 长度与服务端记录不一致');
  }
  if (part.zip === 'none') {
    const raw = new Uint8Array(part.data);
    if (raw.length !== declared) throw new Error('数据块 ' + part.name + ' 长度与服务端记录不一致');
    return unpackValue(raw);
  }
  if (part.zip !== 'gzip') throw new Error('原件的压缩方式认不出');
  const raw = await inflateBounded(part.data, MAX_PART_BYTES);
  if (raw.length !== declared) throw new Error('数据块 ' + part.name + ' 解压长度与服务端记录不一致');
  return unpackValue(raw);
}

/** 清单声明的世界身份必须与服务端登记的一致，否则不画。 */
function checkIdentity(manifest: any, identity: SourceIdentity): void {
  const worldId = manifest?.world?.id;
  if (worldId && identity.worldId && String(worldId) !== String(identity.worldId)) {
    throw new Error('原件里的世界编号与服务端记录不一致');
  }
  const generator = manifest?.snapshot?.generator;
  if (generator != null && identity.generator != null
      && Number(generator) !== Number(identity.generator)) {
    throw new Error('原件里的生成器版本与服务端记录不一致');
  }
}

/**
 * 读一份原件：切成块 → 逐块校验/解 → 上游 `rasterize` 现算栅格。
 *
 * 返回的 `identity` 就是服务端那份（`canSave` 用它判断能否绑草稿）。
 * `map` 块里**没有** raster 字段（实测），所以栅格必须现算。
 */
export async function readNativeWorld(importId: string): Promise<NativeWorld> {
  const [meta, bytes] = await Promise.all([nativeWorldMeta(importId),
                                           fetchSnapshotBytes(importId)]);
  if (!meta.available) throw new Error('这份原件服务端标为不可用');
  const { manifest, parts } = splitParts(bytes);
  checkIdentity(manifest, meta.identity);
  const witnesses = new Map(meta.parts.map((part) => [part.name, part]));
  const byName = new Map(parts.map((part) => [part.name, part]));
  const mapPart = byName.get('map');
  if (!mapPart) throw new Error('原件里没有 map 那块');
  const mapValue = await readVerifiedPart(mapPart, witnesses.get('map'));
  if (!mapValue || typeof mapValue !== 'object') throw new Error('map 那块解不出对象');
  const world = mapValue as World;
  const civPart = byName.get('civ');
  const civ = civPart
    ? ((await readVerifiedPart(civPart, witnesses.get('civ'))) as Civ)
    : null;
  if (civ && civ.regions?.count != null && world.mesh?.n != null
      && civ.regions.of?.length !== world.mesh.n) {
    throw new Error('历史与原件的网格对不上');
  }
  const raster = rasterize(world, 1, true);
  return { world, civ, raster, identity: meta.identity, storyRevision: meta.storyRevision };
}
