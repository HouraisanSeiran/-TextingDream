/**
 * civ-atlas 原件（Snapshot）只读导出工具 —— 在 civ-atlas 页面里手动运行，不联网、不写库。
 *
 * 为什么需要它：civ-atlas 的存档文件只记「种子 + 参数 + 修改」，不含地形；逐地块的
 * 高程/海陆/气温/降水/群系与网格几何都在浏览器的 IndexedDB 里的「原件」（Snapshot）中，
 * 而页面本身没有把原件下载成文件的入口（详见 docs/civ-atlas-integration.md §4/§8）。
 *
 * 这个脚本做什么：只读打开 IndexedDB 库 `civ-atlas:results` 的 `results` / `heads` 两张表，
 * 列出这台浏览器里存着的原件，由**你显式选中**其中一个，把它的三块 part 与元数据原样打包
 * 成一个文件下载下来。文件格式是我们自己定义的 CASNAP01 容器（见下），只装上游的字节，
 * 不改内容、不解析内容。
 *
 * 明确不做的事（读代码可核）：
 *   - 不读 localStorage、不读 API Key、不读账号或云同步凭据、不读别的站点/别的库的数据；
 *   - 不发任何网络请求（没有 fetch / XHR / WebSocket）；
 *   - 不写 IndexedDB（事务一律 `readonly`），不改页面状态，不覆盖任何东西；
 *   - 不自动挑「最新的那个」：必须由你给序号选中，避免拿错世界。
 *
 * 用法：在**生成过该世界的** civ-atlas 页面（同一浏览器、同一站点）打开开发者工具
 * Console，整段粘贴本文件，回车。它会先打印候选清单，然后按提示调用：
 *
 *   __civAtlasExport.export(0)     // 导出清单里的第 0 个
 *   __civAtlasExport.list()        // 重新列一遍
 *
 * 得到 `civ-atlas-<世界编号>-g<生成器版本>.civsnap`，交给织梦的「地图导入」页。
 *
 * 许可：本脚本是本工程原创代码，只调用浏览器的 IndexedDB API，不 import、不复制上游源码。
 * 上游 civ-atlas 的**代码**是 AGPL-3.0-only；它生成的世界数据归你（上游 README「许可」节
 * 明确说明代码许可不约束生成的地图与文字）。这里不构成任何法律结论，只记录事实。
 */

/* eslint-disable no-console */
(async () => {
  'use strict';

  const DB_NAME = 'civ-atlas:results';   // src/ui/resultStore.ts:66
  const STORES = ['results', 'heads'];   // 两张表，keyPath ['id','generator']（resultStore.ts:74-81）
  const MAGIC = 'CASNAP01';              // 我们自己定义的容器头
  const SCHEMA = 1;
  const MAX_PARTS = 8;
  const MAX_PART_BYTES = 64 * 1024 * 1024;
  const MAX_TOTAL_BYTES = 96 * 1024 * 1024;

  /** 只读打开库：不给 version，就不会触发 upgradeneeded（resultStore.ts:76-77 的语义） */
  function openReadonly() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME);
      request.onupgradeneeded = () => {
        // 库不存在时浏览器会建一个空库并触发这里：立刻中止，免得留下空库。
        request.transaction.abort();
        reject(new Error('这台浏览器里没有 civ-atlas 的原件库（civ-atlas:results）。' +
          '请在生成过世界的那个 civ-atlas 页面、同一浏览器里运行本脚本。'));
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error('IndexedDB 打不开'));
      request.onblocked = () => reject(new Error('IndexedDB 被别的标签页占用，关掉其他 civ-atlas 页再试'));
    });
  }

  function readAll(db, storeName) {
    return new Promise((resolve, reject) => {
      const tx = db.transaction([storeName], 'readonly');
      const request = tx.objectStore(storeName).getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error || new Error('读取 ' + storeName + ' 失败'));
    });
  }

  function readOne(db, storeName, key) {
    return new Promise((resolve, reject) => {
      const tx = db.transaction([storeName], 'readonly');
      const request = tx.objectStore(storeName).get(key);   // key = [id, generator]
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error('读取 ' + storeName + ' 失败'));
    });
  }

  /** 只收录认得的字段，别的一概不带出去 */
  function headOf(head) {
    return {
      id: String(head.id),
      generator: Number(head.generator),
      recipe: String(head.recipe || ''),
      sums: String(head.sums || ''),
      size: Number(head.size || 0),
      at: String(head.at || ''),
    };
  }

  function bytes(n) {
    if (!Number.isFinite(n) || n <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let v = n;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1; }
    return v.toFixed(i ? 1 : 0) + ' ' + units[i];
  }

  function pad8(n) { return (n + 7) & ~7; }

  async function candidates() {
    const db = await openReadonly();
    try {
      const heads = (await readAll(db, 'heads')).map(headOf);
      heads.sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : (a.id < b.id ? -1 : 1)));
      return { db, heads };
    } catch (error) {
      db.close();
      throw error;
    }
  }

  async function list() {
    const { db, heads } = await candidates();
    db.close();
    if (!heads.length) {
      console.log('这台浏览器里没有可导出的原件。原件只在你于本浏览器生成过、并且推演完成的世界才有。');
      return [];
    }
    console.table(heads.map((h, index) => ({
      序号: index,
      世界编号: h.id,
      生成器版本: h.generator,
      时间: h.at,
      大小: bytes(h.size),
      配方指纹: (h.recipe || '').slice(0, 12),
    })));
    console.log('选中哪一个就运行：__civAtlasExport.export(序号)');
    return heads;
  }

  function download(blob, name) {
    const url = URL.createObjectURL(blob);
    const link = Object.assign(document.createElement('a'), { href: url, download: name });
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }

  async function exportAt(index) {
    if (!Number.isInteger(index) || index < 0) throw new Error('序号必须是清单里的整数');
    const { db, heads } = await candidates();
    try {
      if (index >= heads.length) throw new Error('序号超出清单（共 ' + heads.length + ' 个）');
      const head = heads[index];
      const record = await readOne(db, 'results', [head.id, head.generator]);
      if (!record || !record.snapshot) throw new Error('这条记录里没有原件，换一个试试');
      const snapshot = record.snapshot;
      const parts = Array.isArray(snapshot.parts) ? snapshot.parts : [];
      if (!parts.length) throw new Error('原件里没有 part');
      if (parts.length > MAX_PARTS) throw new Error('part 数量异常：' + parts.length);

      const manifest = {
        container: MAGIC,
        schema: SCHEMA,
        exported_by: '织梦 tools/civ_atlas_export.js',
        exported_at: new Date().toISOString(),
        site: location.origin,
        world: {
          id: String(record.id),
          generator: Number(record.generator),
          app: String(record.app || ''),
          at: String(record.at || ''),
        },
        snapshot: {
          format: snapshot.format,
          generator: snapshot.generator,
          recipe: String(snapshot.recipe || ''),
          formation: Boolean(snapshot.formation),
        },
        head: head,
        parts: [],
      };

      let total = 0;
      const chunks = [];
      for (const part of parts) {
        const data = part && part.data;
        if (!(data instanceof ArrayBuffer)) throw new Error('某块 part 的 data 不是 ArrayBuffer');
        if (data.byteLength > MAX_PART_BYTES) throw new Error('单块 part 超过上限：' + bytes(data.byteLength));
        total += data.byteLength;
        if (total > MAX_TOTAL_BYTES) throw new Error('原件总大小超过上限：' + bytes(total));
        chunks.push(new Uint8Array(data));
        manifest.parts.push({
          name: String(part.name || ''),
          bytes: Number(part.bytes || data.byteLength),
          sum: String(part.sum || ''),
          zip: part.zip === 'gzip' ? 'gzip' : 'none',
          length: data.byteLength,
        });
      }

      // 清单里写着每块的 offset，而清单会把 offset 一起序列化——于是「长度 ↔ 数值」互相
      // 依赖，直接预算一遍必然对不上（上一次就报过“清单长度不一致”和“越界”）。
      // 可靠做法：offset 一律写成定宽十进制串，长度就不随数值位数变；读侧 parseInt 兼容。
      const OFFSET_WIDTH = 12;                 // 10^12 字节，远大于任何原件总大小
      const padOffset = (value) => String(value).padStart(OFFSET_WIDTH, '0');
      manifest.parts.forEach((part) => { part.offset = padOffset(0); });
      let head_bytes = new TextEncoder().encode(JSON.stringify(manifest));
      const body_start = pad8(MAGIC.length + 4 + head_bytes.length);
      let cursor = body_start;
      manifest.parts.forEach((part, i) => {
        part.offset = padOffset(cursor);
        cursor = pad8(cursor + chunks[i].byteLength);
      });
      head_bytes = new TextEncoder().encode(JSON.stringify(manifest));
      if (pad8(MAGIC.length + 4 + head_bytes.length) !== body_start) {
        throw new Error('清单长度不稳定，导出中止');
      }
      // 字节写入位置要用数字：单独算一遍，不回头改 manifest（或改就改变长度）。
      // 注意：每块之间按 8 字节对齐会有填充，body 必须为填充也留出空间，
      // 否则最后一块写入时就会越界（这正是之前“offset is out of bounds”的原因）。
      const offsets = [];
      let at = body_start;
      manifest.parts.forEach((part, i) => {
        offsets.push(at);
        at = pad8(at + chunks[i].byteLength);
      });
      const payload_end = manifest.parts.reduce((end, part, i) => (
        Math.max(end, offsets[i] + chunks[i].byteLength)), body_start);
      const body = new Uint8Array(payload_end);
      for (let i = 0; i < MAGIC.length; i += 1) body[i] = MAGIC.charCodeAt(i);
      new DataView(body.buffer).setUint32(MAGIC.length, head_bytes.length, true);
      body.set(head_bytes, MAGIC.length + 4);
      manifest.parts.forEach((part, i) => body.set(chunks[i], offsets[i]));

      const name = 'civ-atlas-' + record.id + '-g' + record.generator + '.civsnap';
      download(new Blob([body], { type: 'application/octet-stream' }), name);
      console.log('已导出 ' + name + '（' + bytes(body.length) + '，' + parts.length + ' 块）。' +
        '把它交给织梦的「地图导入」页；本脚本没有联网、没有写库。');
      return { name, size: body.length, parts: manifest.parts.map((p) => p.name) };
    } finally {
      db.close();
    }
  }

  const api = { list, export: exportAt };
  globalThis.__civAtlasExport = api;
  console.log('%c civ-atlas 原件只读导出 ', 'background:#2b4b6f;color:#fff;padding:2px 6px');
  console.log('只读打开 IndexedDB `civ-atlas:results` 的 results/heads，不联网、不写库、不碰 localStorage。');
  console.log('下一步：__civAtlasExport.list() 看候选，然后 __civAtlasExport.export(序号) 导出。');
  return api.list();
})();
