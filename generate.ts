// 作者侧世界生成：在浏览器里用**上游自己的 worker** 生成世界，然后就地打包上传。
//
// 不做的事（都很明确）：
//   * 不重写地形生成 —— `new Worker(new URL('../worker.ts', import.meta.url))` 就是上游那个
//     `src/worker.ts`，参数、阶段、推演全部原样；
//   * 不开独立上游页面 / 不嵌 iframe —— 生成就在这里完成；
//   * 不自己写容器 —— 打包用 `bridge.ts: packContainer`（与导出器逐字节同口径），
//     上传直接用后端既有的 `POST /api/inner/map-imports`。
//
// 作者看到的就是：填参数 → 生成（带阶段进度）→ 地图自己出现在右边 → 刷新后仍在
// （因为它已经作为导入记录存在服务端）。

import type { WorldParams } from '../gen/world';
import { DEFAULT_PARAMS } from '../gen/world';
import type { Snapshot } from '../gen/snapshot';
import { packContainer, uploadSnapshot } from './bridge';
import type { WorkerRequest, WorkerResponse } from '../worker';

export { DEFAULT_PARAMS, type WorldParams };

/** 作者能改的那几项，名字与上游参数一致（不另起一套）。 */
export const PARAM_FIELDS: { key: keyof WorldParams; label: string; min: number; max: number;
                              step: number; hint: string }[] = [
  { key: 'seed', label: '种子', min: 1, max: 2147483646, step: 1,
    hint: '同一个种子 + 同一套参数 = 同一个世界' },
  { key: 'cells', label: '地块数', min: 6000, max: 90000, step: 1000,
    hint: '越多越细、越慢' },
  { key: 'landFraction', label: '陆地比例', min: 0.05, max: 0.95, step: 0.01,
    hint: '整颗星球上陆地的占比' },
  { key: 'plates', label: '板块数', min: 4, max: 80, step: 1,
    hint: '越多陆地越碎、岛越多' },
  { key: 'mountains', label: '山脉强度', min: 0, max: 2, step: 0.05, hint: '' },
  { key: 'temperature', label: '气温偏移', min: -2, max: 2, step: 0.05, hint: '' },
  { key: 'rainfall', label: '降水偏移', min: 0, max: 2, step: 0.05, hint: '' },
  { key: 'continents', label: '主要大陆', min: 0, max: 5, step: 1,
    hint: '0 = 按种子定，2—5 块另有群岛' },
  { key: 'gather', label: '大陆聚拢', min: 0, max: 1, step: 0.05,
    hint: '0 = 彼此尽量远，1 = 挤在一起留大片大洋' },
  { key: 'rugged', label: '破碎度', min: 0, max: 2, step: 0.05,
    hint: '小 = 大陆完整、海岸平直；大 = 支离破碎' },
  { key: 'hardness', label: '板块硬度', min: 0, max: 2, step: 0.05,
    hint: '硬 = 内陆平坦、山脉窄' },
  { key: 'north', label: '陆地偏向半球', min: -1, max: 1, step: 0.05,
    hint: '-1 南，0 均匀，1 北' },
];

export interface GenerateProgress { stage: string; pct: number; }

export interface GeneratedWorld {
  /** 服务端登记后的导入编号（`sn_…`），可直接当作者的“当前世界”。 */
  importId: string;
  worldId: string;
  /** 服务端记下的整件 sha256（保存草稿要用）。 */
  contentSha256: string;
  bytes: number;
  parts: string[];
}

/** 默认给作者一组能很快看完的参数（地块数比上游默认 36000 小，生成更快）。 */
export function defaultAuthorParams(seed = Math.floor(Math.random() * 2000000000) + 1): WorldParams {
  return { ...DEFAULT_PARAMS, seed, cells: 16000 };
}

/** 世界编号：从配方指纹里取，稳定且可读；同一套输入 → 同一个编号。 */
function worldIdOf(snapshot: Snapshot): string {
  const tail = (snapshot.recipe || '').slice(0, 11) || String(snapshot.generator);
  return 'wm' + tail;
}

/**
 * 生成一个世界并登记到服务端。
 *
 * 返回后调用方应当把 `importId` 当作当前世界，用 `readNativeWorld(importId)` 把它读回来画
 * ——不要拿生成时的内存对象当第二套数据源（那份是上游内部的，重读才是真的）。
 */
export async function generateAndRegister(
  params: WorldParams,
  onProgress?: (progress: GenerateProgress) => void,
): Promise<GeneratedWorld> {
  if (typeof Worker === 'undefined') throw new Error('这个浏览器没有 Web Worker，无法在后台生成世界');
  const worker = new Worker(new URL('../worker.ts', import.meta.url), { type: 'module' });
  const id = 1;
  try {
    const snapshot = await new Promise<Snapshot>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('生成超时：5 分钟没有完成')), 5 * 60 * 1000);
      const done = (work: () => void) => { clearTimeout(timer); work(); };
      worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
        const message = event.data;
        if (!message || message.id !== id) return;
        if (message.type === 'progress') {
          onProgress?.({ stage: message.stage, pct: message.pct });
          return;
        }
        if (message.type === 'snapshot') {
          done(() => resolve(message.snapshot));
          return;
        }
        // 任何终态错误都结束等待，不挂死
        if (message.type === 'loadFailed' || message.type === 'aborted') {
          done(() => reject(new Error('生成没有完成（' + message.type + '）')));
        }
      };
      worker.onerror = (event) => {
        // `event.message` 在跨模块 worker 里往往是空的：把能拿到的都写出来，
        // 否则只剩一句“未知”，根本没法定位（实测就是这样卡住过一次）。
        const detail = [
          event.message || '',
          event.filename ? event.filename + ':' + event.lineno + ':' + event.colno : '',
          event.error && (event.error.stack || event.error.message) || '',
        ].filter(Boolean).join(' / ');
        done(() => reject(new Error('生成线程报错：' + (detail || '工作线程启动失败（无错误详情）'
          + '；常见原因是 assets/worker-*.js 没有被一起托管'))));
      };
      // worker 内部抛的错误会先到 messageerror（结构克隆失败）或直接终止；也一并兜住
      worker.onmessageerror = () => {
        done(() => reject(new Error('生成线程消息无法反序列化（messageerror）')));
      };
      // 上游的请求形状：只给参数，不带地形修改/草图/干预 → 等同于“新建随机世界”
      const request: WorkerRequest = { type: 'generate', id, scale: 1, params };
      worker.postMessage(request);
    });

    const worldId = worldIdOf(snapshot);
    const container = packContainer(snapshot, worldId);
    // 不传 generator_version：那个 query 在服务端是 strict int，字符串形式必然 422；
    // 版本号本来就在容器清单的 snapshot.generator 里。
    const registered = await uploadSnapshot(container, { note: '织梦原生宿主 · 作者生成' });
    // 上传后用服务端记录的身份回读（不信本地自己算的）
    const looked = await fetch('/api/inner/native-worlds/' + encodeURIComponent(registered.importId),
      { headers: { 'X-TextileDream-Token': (window as any).__textileDreamToken || '' } });
    if (!looked.ok) throw new Error('已上传但取不回原生记录：' + looked.status);
    const detail = await looked.json();
    const sha = detail?.identity?.sha256 ?? null;
    if (!sha) throw new Error('服务端没有给整件哈希，无法作为可保存来源');
    return {
      importId: registered.importId,
      worldId: detail?.identity?.world_id || registered.worldId || worldId,
      contentSha256: sha,
      bytes: container.byteLength,
      parts: (detail?.parts || []).map((part: any) => String(part?.name ?? '')),
    };
  } finally {
    worker.terminate();
  }
}
