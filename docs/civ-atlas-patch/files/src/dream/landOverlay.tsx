/**
 * 城镇建筑范围 / 用地规划(作者侧) · 原生地图叠加层
 *
 * 它**不是**另一套地图引擎，也不自己算投影：
 *   - 屏幕 ↔ 世界像素用 `ui/mapWrap.ts` 的 `stageToWorld` / `worldToStage`；
 *   - 经纬度 ↔ 世界像素用 `render/globe.ts` 的 `lonLatToWorld` / `worldToLonLat`
 *     （两个都是原生导出；输入输出都是**弧度**，本文件只做度/弧度单位换算）。
 * 宿主把 `view` / `stage` / 世界尺寸传进来，本组件据此画；宿主不传就是「没有底图」，
 * 此时**禁止保存**（不能凭空绑一张随机地图）。
 *
 * **只支持等距圆柱（equirectangular）**：上面两条换算都是线性的。投影切到 robinson /
 * 摩尔威德这类弯边投影时叠加会错位，所以 `projection.linear !== true` 时直接拒画并提示，
 * 不用旧线性公式冒充——弯边投影要宿主给反投影函数，本组件不自造。
 *
 * 作者模式与玩家模式分开：
 *   - `mode='author'` 画建筑范围与用地，并调用织梦已上线的 spatial-drafts 接口；
 *   - `mode='player'` **只画宿主给的公开边界**，从不请求作者草稿，也不改任何状态——
 *     玩家侧的移动只是 `onMoveIntent` 事件，交给上层决定。
 *
 * 经济语义的边界：本组件只画、只编辑、只调接口。矿山是规划意图（非已勘探）、牧场不进
 * 粮食公式、没有供给也能存成空间草稿——这些规则都在服务端 `spatial_draft` 里，这里不复制。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { lonLatToWorld, worldToLonLat } from '../render/globe';
import { stageToWorld, worldToStage, type MapView, type StageBox } from '../ui/mapWrap';
import './landOverlay.css';

// ------------------------------------------------------------------ 类型契约
/** 一套用地/建筑范围的多边形（连续经纬度，度）。 */
export interface LonLat {
  lon: number;
  lat: number;
}

export type LandUseKind = 'farmland' | 'pasture' | 'mine' | 'forest' | 'wasteland' | 'other';

/** 用地/建筑范围的显示与编辑单位。 */
export interface DraftShape {
  kind: 'footprint' | LandUseKind;
  vertices: LonLat[];
  note?: string;
}

/** 宿主必须提供的最小上下文（scene identity 与 token，不从 URL 读）。 */
export interface LandOverlayScene {
  /** 当前世界的来源（导入 id + 内容哈希）；为空表示没有有效底图来源。 */
  worldSource: { importId: string; sourceSha256: string } | null;
  /** 取样点（作者在地图上选的点，度）。保存草稿时会一并记录。 */
  sampling?: { lon: number; lat: number; windowPx?: number } | null;
  /** 作者侧鉴权 token，由宿主注入，不进 URL、不落日志。 */
  authorToken: string;
  /**
   * 宿主选中的 civ 城市（可选）。**只认稳定实体 id**，不按名字猜：
   * `cityId` 必须是 `settlement:<数字>`（纯数字后缀，1–12 位），与后端
   * `spatial_draft._CITY_ID_RE` 逐字对齐；不合法时本次保存不带 city_ref。
   * 本组件只把它与 `worldSource` 组合成 `city_ref` 交出去，不新建城市、不复制同名数据。
   *
   * 构造方式：取原件 civ 里 `Settlement.id`（**数字**，`gen/civ/types.ts:130`），
   * 拼成 `settlement:${id}`。**不要**直接传推演内部键 `settlement:c4567#0`
   * （`gen/edits.ts:1882` 的 isCityKey），后端会拒——那是另一套键，不是这个契约。
   */
  cityRef?: { cityId: string; name: string } | null;
}

/** 世界投影与舞台：全部来自宿主（原生视图），本组件不自己维护第二套。 */
export interface LandOverlayProjection {
  view: MapView;
  stage: StageBox;
  /** 等距圆柱主图的像素尺寸（原生 `world.width` / `world.height`）。 */
  worldWidth: number;
  worldHeight: number;
  /** 宿主告知当前是不是等距圆柱：false 时本组件拒画（不拿线性公式冒充弯边投影）。 */
  linear: boolean;
}

/** 宿主与组件的完整契约。 */
export interface LandOverlayProps {
  mode: 'author' | 'player';
  scene: LandOverlayScene;
  projection: LandOverlayProjection;
  /** 作者侧：初始形状（从已存草稿载入时由宿主传入）。 */
  shapes?: DraftShape[];
  /** 作者侧：服务端返回的冲突/缺项摘要，只用于提示，不在前端重算几何。 */
  revision?: number | null;
  /** 作者工具栏可挂载到地图外部容器；画布仍保持在地图上。 */
  controlsHost?: HTMLElement | null;
  /** 作者侧改动回调（宿主决定是否持久化；组件自己也调接口，见 `apiBase`）。 */
  onShapesChange?: (shapes: DraftShape[]) => void;
  /** 玩家侧：只发移动意图，不改状态。 */
  onMoveIntent?: (target: LonLat) => void;
  /** 织梦后端地址（宿主注入；不从 location 猜）。 */
  apiBase?: string;
}

export type OverlayTool = 'select' | 'footprint' | 'land-use';

interface DraftSummary {
  id: string;
  revision: number;
  supply: { state: string } | null;
  site_name?: string;
  note?: string;
  /** 后端 summary 把 area_plan 展平成这两项（不是嵌套对象）。 */
  terrain_area_km2?: number | null;
  area_source?: string | null;
  overlaps?: unknown[];
  geometry_budget?: unknown;
  city_ref?: { import_id?: string; source_sha256?: string; city_id?: string; name?: string } | null;
  world_basis_ref?: { id?: string } | string | null;
  /** 列表项也带来源，用于按当前世界过滤。 */
  environment_ref?: { import_id?: string; source_sha256?: string } | null;
}

/**
 * 更新草稿时必须一起带上的「高级声明」。
 *
 * 后端 `update` 走 `parse_request` → `_document`，是**全量替换**而不是合并：少发一个键
 * 就等于把它清空。所以这些字段一律从已载入的文档按请求形状原样回传，前端不重算
 * 任何派生值（面积、供给、重叠扫描都由后端重新算）。
 */
export interface DraftAdvanced {
  /** `wb_…` 编号（不是 summary 里那个解析后的对象）。 */
  worldBasisRef: string | null;
  /** 只有三个请求键：原件 + 城市实体 id。 */
  cityRef: { import_id: string; source_sha256: string; city_id: string } | null;
  /** 作者声明的腹地；后端据此把 supply 记成 configured。 */
  hinterlandKm2: number | null;
  note: string;
  /**
   * 已存的取样选点（只保留请求允许的四个键）。
   * 宿主没给 `scene.sampling` 时用它；否则全量替换会把作者的选点冲成
   * 「按建筑范围顶点均值推算」，那是另一个地方。
   */
  sampling: { lon: number; lat: number; window_px: number; radius_km: number } | null;
}

/** 还没有载入过任何草稿时的「高级声明」：全空，不镯造。 */
const EMPTY_ADVANCED: DraftAdvanced = {
  worldBasisRef: null, cityRef: null, hinterlandKm2: null, note: '', sampling: null,
};

const LAND_USE_KINDS: { kind: LandUseKind; label: string }[] = [
  { kind: 'farmland', label: '农田' },
  { kind: 'pasture', label: '牧场' },
  { kind: 'mine', label: '矿山（仅规划）' },
  { kind: 'forest', label: '林地' },
  { kind: 'wasteland', label: '荒地' },
  { kind: 'other', label: '其它' },
];

/** 色板与宿主主题一致：建筑范围暖金，用地各自一色。 */
const STROKE: Record<string, string> = {
  footprint: '#e6c57a',
  farmland: '#72b69b',
  pasture: '#a8c98a',
  mine: '#c8a06e',
  forest: '#5f9c7d',
  wasteland: '#9a9a92',
  other: '#8aa0b4',
};

// ---------------------------------------------------------------- 纯换算函数

/** 弧度 → 度（原生 worldToLonLat 输出弧度，这里只做单位换算）。 */
const toDeg = (rad: number) => (rad * 180) / Math.PI;
/** 度 → 弧度（原生 lonLatToWorld 吃弧度）。 */
const toRad = (deg: number) => (deg * Math.PI) / 180;

/** 世界像素 → 经纬度（度）。几何公式全部来自原生 `worldToLonLat`，这里只把弧度换成度。 */
export function worldPxToLonLat(x: number, y: number, W: number, H: number): LonLat {
  const [lonRad, latRad] = worldToLonLat(x, y, W, H);
  return { lon: toDeg(lonRad), lat: toDeg(latRad) };
}


/** 形状内容的轻量签名：父级把数组拷一份回来时，别当成「新几何」清掉正在画的点。 */
function shapeSignature(list: DraftShape[] | undefined): string {
  return JSON.stringify((list ?? []).map((shape) => [shape.kind, shape.note || '',
    shape.vertices.map((v) => [v.lon, v.lat])]));
}

/**
 * 与后端 `spatial_draft._CITY_ID_RE`（`app/spatial_draft.py:104`）**逐字对齐**：
 * 上游 civ 的 settlement 实体 id 是数字，稳定引用就是 `settlement:<1..12 位数字>`。
 * 不自行放宽——前端一旦接受后端不认的 id，保存会在服务端被拒。
 */
const CITY_ID_RE = /^settlement:[0-9]{1,12}$/;

/**
 * `scene.cityRef` + `scene.worldSource` → 保存用的 `city_ref` 片段。
 *
 * 三个键必须同源：`import_id`/`source_sha256` 直接取自当前世界来源，`city_id` 取自宿主
 * 选中的 civ 实体。两者缺一、或 `cityId` 不是 `settlement:…` 形式时返回 `null`——
 * **不按名字猜 id，也不把城市默绑到另一座城**，宁可这次不绑。
 */
export function cityRefFromScene(scene: LandOverlayScene): DraftAdvanced['cityRef'] {
  const city = scene.cityRef;
  const src = scene.worldSource;
  if (!city || !src || !src.importId || !src.sourceSha256) return null;
  if (!CITY_ID_RE.test(city.cityId)) return null;
  return {
    import_id: src.importId,
    source_sha256: src.sourceSha256,
    city_id: city.cityId,
  };
}

/**
 * 保存时到底绑哪座城：
 *
 * 1. 宿主当前选了城 → 用它（作者现的选择优先）；
 * 2. 没选 → 保留已载入草稿里那份绑定（**不改绑、不按名字猜**）；
 * 3. 载入的那份与当前世界不同源 → 一律不带（跨源绑定是错的），宁可本次不绑。
 */
export function resolveCityRef(
  scene: LandOverlayScene,
  loaded: DraftAdvanced['cityRef'],
): DraftAdvanced['cityRef'] {
  const picked = cityRefFromScene(scene);
  if (picked) return picked;
  if (!loaded) return null;
  const src = scene.worldSource;
  if (!src || !src.importId || !src.sourceSha256) return null;
  if (loaded.import_id !== src.importId || loaded.source_sha256 !== src.sourceSha256) return null;
  return loaded;
}

/** 解析后的 basis / city 可能是对象，也可能是编号字符串：两种形状都认。 */
function basisId(raw: unknown): string | null {
  if (typeof raw === 'string') return raw || null;
  const id = (raw as { id?: unknown } | null | undefined)?.id;
  return typeof id === 'string' && id ? id : null;
}

function cityRequest(raw: unknown): DraftAdvanced['cityRef'] {
  const city = raw as Record<string, unknown> | null | undefined;
  if (!city || typeof city.import_id !== 'string' || typeof city.source_sha256 !== 'string'
      || typeof city.city_id !== 'string') {
    return null;
  }
  return { import_id: city.import_id, source_sha256: city.source_sha256, city_id: city.city_id };
}

/** 只保留请求允许的四个键；数字不合规就整份丢弃（不编一个）。 */
function samplingRequest(raw: unknown): DraftAdvanced['sampling'] {
  const item = raw as Record<string, unknown> | null | undefined;
  if (!item) return null;
  const num = (value: unknown) => (typeof value === 'number' && Number.isFinite(value)
    ? value : null);
  const lon = num(item.lon);
  const lat = num(item.lat);
  const windowPx = num(item.window_px);
  const radiusKm = num(item.radius_km);
  if (lon === null || lat === null || windowPx === null || radiusKm === null) return null;
  return { lon, lat, window_px: windowPx, radius_km: radiusKm };
}

/** 完整文档（POST/PUT 返回的 `draft`）：所有请求字段都在，直接映射回请求形状。 */
export function advancedFromDoc(doc: Record<string, unknown>): {
  siteName: string;
  advanced: DraftAdvanced;
} {
  return {
    siteName: typeof doc.site_name === 'string' ? doc.site_name : '',
    advanced: {
      worldBasisRef: basisId(doc.world_basis_ref),
      cityRef: cityRequest(doc.city_ref),
      hinterlandKm2: typeof doc.hinterland_km2 === 'number' ? doc.hinterland_km2 : null,
      note: typeof doc.note === 'string' ? doc.note : '',
      sampling: samplingRequest(doc.sampling),
    },
  };
}

/**
 * 详情（GET one）比完整文档少几个键，这里按能取回的原样映射，并明确告诉调用方哪些
 * 取不回来——**不静默丢**，由面板提示作者，不自己编造。
 *
 * 腹地没有单独暴露，但 `area_source === 'author_declared_hinterland'` 时
 * `terrain_area_km2` 就是它（后端 `_area_plan` 的唯一赋值路径），据此原样取回。
 */
export function advancedFromDetail(detail: Record<string, unknown>): {
  siteName: string;
  advanced: DraftAdvanced;
  lost: string[];
} {
  const hinterlandKm2 = detail.area_source === 'author_declared_hinterland'
    && typeof detail.terrain_area_km2 === 'number' ? detail.terrain_area_km2 : null;
  const lost: string[] = [];
  if (!('note' in detail)) lost.push('备注');
  if (!('city_ref' in detail)) lost.push('城市引用');
  return {
    siteName: typeof detail.site_name === 'string' ? detail.site_name : '',
    advanced: {
      worldBasisRef: basisId(detail.world_basis_ref),
      cityRef: cityRequest(detail.city_ref),
      hinterlandKm2,
      note: typeof detail.note === 'string' ? detail.note : '',
      sampling: samplingRequest(detail.sampling),
    },
    lost,
  };
}

/** 是否具备可保存的世界来源（导入 id + 内容哈希）。 */
export function hasSource(scene: LandOverlayScene): boolean {
  const src = scene.worldSource;
  return Boolean(src && src.importId && src.sourceSha256);
}

/**
 * 后端地址必须是受信任的：同源，或明确的本机回环。
 *
 * `''`（空串）**是合法值**，表示「与页面同源」——生产环境前后端同源部署，
 * 开发时由 Vite 代理到固定后端，所以空串绝不能当成「没有后端」而禁掉保存。
 * token 只放在定长请求头里，绝不发给一个来路不明的 origin，也不从 URL 读。
 */
export function trustedApiBase(base: string | undefined, pageOrigin: string): string | null {
  const raw = (base || '').trim();
  const origin = (() => {
    try {
      return new URL(pageOrigin).origin;
    } catch {
      return null;
    }
  })();
  if (!origin) return null;
  if (!raw) return origin;                       // 空串 = 同源
  let parsed: URL;
  try {
    parsed = new URL(raw, origin);
  } catch {
    return null;
  }
  const loopback = parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost'
    || parsed.hostname === '[::1]';
  if (!loopback && parsed.origin !== origin) return null;
  return parsed.origin + parsed.pathname.replace(/\/$/, '');
}

/** 屏幕坐标 → 经纬度。宿主给的 view/stage/world 尺寸，全程走原生换算。 */
export function screenToLonLat(
  clientX: number, clientY: number,
  p: LandOverlayProjection,
  rect: { left: number; top: number },
): LonLat {
  const [wx, wy] = stageToWorld(
    clientX - rect.left, clientY - rect.top,
    p.view, p.stage, p.worldWidth, p.worldHeight,
  );
  return worldPxToLonLat(wx, wy, p.worldWidth, p.worldHeight);
}

/** 经纬度 → 屏幕坐标（相对舞台左上角，CSS 像素）。 */
export function lonLatToScreen(pt: LonLat, p: LandOverlayProjection): [number, number] {
  // lonLatToWorld 吃弧度；这里把度换成弧度交给原生函数，不自己再写一份公式。
  const [wx, wy] = lonLatToWorld(toRad(pt.lon), toRad(pt.lat),
    p.worldWidth, p.worldHeight);
  return worldToStage(wx, wy, p.view, p.stage, p.worldWidth, p.worldHeight);
}

// ------------------------------------------------------------------- 组件本体
export function LandOverlay(props: LandOverlayProps) {
  const { mode, scene, projection, shapes: initialShapes, apiBase } = props;
  const author = mode === 'author';
  // 投影是否可用：弯边投影下线性换算是错的，直接拒画（不用旧公式冒充）。
  const supported = projection.linear !== false;

  // ---- 所有 hooks 无条件调用，顺序固定；「不支持投影」只在渲染里早退。
  const [tool, setTool] = useState<OverlayTool>('select');
  const [kind, setKind] = useState<LandUseKind>('farmland');
  const [shapes, setShapes] = useState<DraftShape[]>(initialShapes ?? []);
  const [pending, setPending] = useState<LonLat[]>([]);
  const [draft, setDraft] = useState<DraftSummary | null>(null);
  const [status, setStatus] = useState('');
  /** 已保存草稿列表（按当前世界来源过滤），供作者载入继续编辑。 */
  const [saved, setSaved] = useState<DraftSummary[]>([]);
  /** 选中的形状下标：选中了才能删（否则多块建筑范围会陷入无法保存的死角）。 */
  const [selected, setSelected] = useState<number | null>(null);
  /** 地点名：可看可改；不用 cityRef.name 盖掉草稿里已存的名字。 */
  const [siteName, setSiteName] = useState(scene.cityRef?.name || '');
  /** 载入草稿时一起拿回的高级声明（更新时必须原样回传，后端是全量替换）。 */
  const [advanced, setAdvanced] = useState<DraftAdvanced>(EMPTY_ADVANCED);
  /** 详情接口没暴露、拿不回来的字段：明确告知作者，不静默丢。 */
  const [lostAdvanced, setLostAdvanced] = useState<string[]>([]);

  /** 世界身份：换世界必须把草稿/待画点/提示一起清掉，绝不让旧草稿跟到新世界。 */
  const worldKey = `${scene.worldSource?.importId || ''}#${scene.worldSource?.sourceSha256 || ''}`;
  const lastWorld = useRef(worldKey);
  /**
   * 城市身份：换城（或取消选城）就是另一个目标草稿。
   * 不能接着改上一座城的草稿 —— 那会把 A 城的几何存到 B 城名下。
   */
  const cityKey = scene.cityRef?.cityId || '';
  const lastCity = useRef(cityKey);
  /** 丢弃晚到的保存响应（换世界后旧请求回来不能覆盖新状态）。 */
  const saveToken = useRef(0);
  /** 已告知宿主的几何签名：宿主把形状拷一份回来时不算「新几何」。 */
  const sigRef = useRef(shapeSignature(initialShapes));
  /** 换世界那一刻的旧几何签名：宿主没接 onShapesChange 时也不能把它带回新世界。 */
  const staleRef = useRef<string | null>(null);
  const onChangeRef = useRef(props.onShapesChange);
  onChangeRef.current = props.onShapesChange;

  /** 唯一的「改几何」出口：本地状态与宿主一起前进，签名同步更新。 */
  const emit = useCallback((next: DraftShape[]) => {
    sigRef.current = shapeSignature(next);
    staleRef.current = null;        // 我们自己给了新几何，不再有“不许回流”的旧签名
    setShapes(next);
    onChangeRef.current?.(next);
  }, []);

  // 换世界：旧世界的一切都不跟过去（几何、待画点、草稿、提示、选中、列表、地点名、
  // 高级声明），并让在途请求作废。这里**不读上一世界的 shapes prop**——宿主很可能
  // 还没把旧几何清掉，带过来就是「新世界顶着旧多边形」的假数据。
  useEffect(() => {
    if (lastWorld.current === worldKey) return;
    lastWorld.current = worldKey;
    saveToken.current += 1;          // 让在途保存作废
    staleRef.current = sigRef.current;  // 宿主没接回调时，这份旧几何不许回流
    emit([]);                        // 清本地 + 告诉宿主当前世界没有几何
    setPending([]);
    setDraft(null);
    setStatus('');
    setSelected(null);
    setSaved([]);
    setSiteName(scene.cityRef?.name || '');
    setAdvanced(EMPTY_ADVANCED);
    setLostAdvanced([]);
    lastCity.current = cityKey;
  }, [cityKey, emit, scene.cityRef, worldKey]);

  // 换城（世界没换）：几何与草稿绑定都属于上一座城，必须清掉重新开始；
  // 世界已经换过的情况由上面那个 effect 处理，这里不重复跑（否则多清一次）。
  useEffect(() => {
    if (lastCity.current === cityKey) return;
    lastCity.current = cityKey;
    saveToken.current += 1;
    staleRef.current = sigRef.current;
    emit([]);
    setPending([]);
    setDraft(null);
    setStatus('');
    setSelected(null);
    setSaved([]);
    setAdvanced(EMPTY_ADVANCED);
    setLostAdvanced([]);
    // 选城就带出它的名字；取消选城不留上一座城的名字。
    setSiteName(scene.cityRef?.name || '');
  }, [cityKey, emit, scene.cityRef]);

  /**
   * 跟随宿主的 shapes（玩家侧公开边界、会话投影变化、宿主自己载入）。
   * 内容签名相同就不动：否则宿主每次渲染新建的数组字面量会把作者正在做的编辑回滚。
   */
  const incomingSig = shapeSignature(initialShapes);
  useEffect(() => {
    if (incomingSig === sigRef.current) return;
    // 换世界时那份旧几何要被永久忽略：宿主可能根本不理 onShapesChange，
    // 它的 prop 会一直是旧数组，不能当成「宿主刚更新了几何」收回来。
    if (incomingSig === staleRef.current) return;
    staleRef.current = null;
    sigRef.current = incomingSig;
    setShapes(initialShapes ?? []);
    setPending([]);
    setSelected(null);
  }, [incomingSig, initialShapes]);

  /** 列出已存草稿，只保留与当前 worldSource（import id + 哈希）一致的那些。 */
  const loadList = useCallback(async () => {
    if (!hasSource(scene)) {
      setStatus('还没有有效的世界来源，无法列出草稿');
      return;
    }
    const base = trustedApiBase(apiBase, window.location.origin);
    if (!base) {
      setStatus('后端地址不受信任，已停止请求');
      return;
    }
    const token = ++saveToken.current;
    try {
      const response = await fetch(`${base}/api/inner/spatial-drafts`, {
        headers: { 'X-TextileDream-Token': scene.authorToken },
      });
      const rows = await response.json();
      if (token !== saveToken.current) return;
      if (!response.ok) {
        throw new Error(typeof rows.detail === 'string' ? rows.detail : '列表读取失败');
      }
      const mine = (Array.isArray(rows) ? rows : []).filter((row: DraftSummary) => {
        const ref = (row.environment_ref || {}) as { import_id?: string; source_sha256?: string };
        return ref.import_id === scene.worldSource!.importId
          && ref.source_sha256 === scene.worldSource!.sourceSha256;
      });
      setSaved(mine);
      setStatus(mine.length ? `找到 ${mine.length} 份本世界的草稿` : '这个世界还没有已存草稿');
    } catch (error) {
      if (token !== saveToken.current) return;
      setStatus('读取草稿列表失败：' + (error instanceof Error ? error.message : String(error)));
    }
  }, [apiBase, scene]);

  /** 载入一份草稿：详情里带几何，载入后 revision 用于后续 CAS 更新。 */
  const loadDraft = useCallback(async (id: string) => {
    const base = trustedApiBase(apiBase, window.location.origin);
    if (!base) {
      setStatus('后端地址不受信任，已停止请求');
      return;
    }
    const token = ++saveToken.current;
    try {
      const response = await fetch(`${base}/api/inner/spatial-drafts/${encodeURIComponent(id)}`, {
        headers: { 'X-TextileDream-Token': scene.authorToken },
      });
      const doc = await response.json();
      if (token !== saveToken.current) return;
      if (!response.ok) {
        throw new Error(typeof doc.detail === 'string' ? doc.detail : '载入失败');
      }
      const ref = (doc.environment_ref || {}) as { import_id?: string; source_sha256?: string };
      if (ref.import_id !== scene.worldSource!.importId
        || ref.source_sha256 !== scene.worldSource!.sourceSha256) {
        setStatus('这份草稿属于别的世界来源，已拒绝载入');
        return;
      }
      const next: DraftShape[] = [];
      if (doc.footprint && doc.footprint.vertices) {
        next.push({
          kind: 'footprint',
          vertices: doc.footprint.vertices.map(([lon, lat]: [number, number]) => ({ lon, lat })),
          note: doc.footprint.note || '',
        });
      }
      for (const entry of doc.land_use || []) {
        next.push({
          kind: entry.kind as LandUseKind,
          vertices: (entry.vertices || []).map(([lon, lat]: [number, number]) => ({ lon, lat })),
          note: entry.note || '',
        });
      }
      // 几何必须同时交给宿主：否则宿主手里还是旧几何，下一次保存会用旧数据覆盖。
      emit(next);
      setPending([]);
      setSelected(null);
      // 已存的地名与高级声明原样拿回：更新是全量替换，丢了就真丢了。
      const recalled = advancedFromDetail(doc);
      setSiteName(recalled.siteName);
      setAdvanced(recalled.advanced);
      setLostAdvanced(recalled.lost);
      setDraft({
        id: doc.id, revision: doc.revision, supply: doc.supply,
        terrain_area_km2: doc.terrain_area_km2, area_source: doc.area_source,
        overlaps: doc.overlaps, geometry_budget: doc.geometry_budget,
      });
      const bound = recalled.advanced.cityRef;
      setStatus(`已载入 ${doc.id}（rev ${doc.revision}），后续保存会走 CAS 更新`
        + (bound ? `，保留原城市绑定 ${bound.city_id}` : '，不自动绑城')
        + (recalled.lost.length
          ? `；详情接口未返回${recalled.lost.join('、')}，更新时会被清空，请先补齐再保存`
          : ''));
    } catch (error) {
      if (token !== saveToken.current) return;
      setStatus('载入失败：' + (error instanceof Error ? error.message : String(error)));
    }
  }, [apiBase, emit, scene]);

  const save = useCallback(async () => {
    if (!hasSource(scene)) {
      setStatus('还没有有效的世界来源（导入 id + 内容哈希），不能保存；请先在宿主里选定世界');
      return;
    }
    if (!scene.authorToken) {
      setStatus('缺少作者侧凭据，不能保存');
      return;
    }
    const base = trustedApiBase(apiBase, window.location.origin);
    if (!base) {
      setStatus('后端地址不受信任（只允许同源或本机回环），已停止保存以免泄露凭据');
      return;
    }
    // 后端每份草稿只接受**一个**建筑范围：多块时明确拒绝，不静默只存第一块。
    const footprints = shapes.filter((s) => s.kind === 'footprint');
    if (footprints.length > 1) {
      setStatus(`有 ${footprints.length} 块建筑范围，但一份草稿只能有一个建筑范围；`
        + '请删掉多余的再保存（不会替你挑一块）');
      return;
    }
    if (!shapes.length) {
      setStatus('还没有圈出任何范围');
      return;
    }
    const landUse = shapes.filter((s) => s.kind !== 'footprint');
    // 与后端 `spatial_draft.parse_request` 的 `_REQUEST_KEYS` 一一对应的请求体。
    // 关键：后端 update 是 parse_request → _document 的**全量替换**，不合并；
    // 所以已载入文档里的高级声明（world_basis_ref / city_ref / hinterland_km2 / note）
    // 必须原样回传，否则一次几何微调就把供给与来源抹掉。派生值（面积、overlaps、
    // supply…）一律不在这发，由后端重算。
    const body = {
      // 地点名：作者填的优先；没填就用宿主选中的城市名，都没有才是“未命名地点”。
      // 已存草稿的名字在载入时已回填到 siteName，不会被这一步抹掉。
      site_name: (siteName || scene.cityRef?.name || '').trim() || '未命名地点',
      footprint: footprints[0]
        ? {
          vertices: footprints[0].vertices.map((v) => [v.lon, v.lat]),
          note: footprints[0].note || '',
        }
        : null,
      land_use: landUse.map((s) => ({
        kind: s.kind, vertices: s.vertices.map((v) => [v.lon, v.lat]), note: s.note || '',
      })),
      environment_ref: {
        import_id: scene.worldSource!.importId,
        source_sha256: scene.worldSource!.sourceSha256,
      },
      world_basis_ref: advanced.worldBasisRef,
      // 城市绑定：稳定实体 id + 当前世界来源；没选城就不带，不改绑、不猜 id。
      city_ref: resolveCityRef(scene, advanced.cityRef),
      hinterland_km2: advanced.hinterlandKm2,
      note: advanced.note,
      // 与后端一致：window_px 默认 3（MIN_WINDOW_PX），radius 走后端默认 6371.0088。
      // 优先用作者的选点；宿主没给 `scene.sampling` 时回退到已载入草稿的选点，
      // 两个都没有才是 null（后端会按建筑范围顶点均值自己推并标注来源）。
      sampling: scene.sampling
        ? {
          lon: scene.sampling.lon, lat: scene.sampling.lat,
          window_px: scene.sampling.windowPx ?? 3, radius_km: 6371.0088,
        }
        : advanced.sampling,
    };
    const token = ++saveToken.current;
    // 已有草稿走 CAS（PUT + expected_revision），没有才新建（POST）。
    const target = draft
      ? `${base}/api/inner/spatial-drafts/${encodeURIComponent(draft.id)}`
      : `${base}/api/inner/spatial-drafts`;
    const payloadBody = draft ? { expected_revision: draft.revision, draft: body } : { draft: body };
    try {
      const response = await fetch(target, {
        method: draft ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json', 'X-TextileDream-Token': scene.authorToken },
        body: JSON.stringify(payloadBody),
      });
      const payload = await response.json();
      if (token !== saveToken.current) return;        // 换世界了：这次结果作废
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : '保存被拒绝');
      }
      const doc = payload.draft || payload;
      // 响应是完整文档：地名与高级声明从它回填，保证下一次 PUT 仍然带上同样的声明。
      const recalled = advancedFromDoc(doc);
      if (recalled.siteName) setSiteName(recalled.siteName);
      setAdvanced(recalled.advanced);
      setLostAdvanced([]);
      setDraft({
        id: doc.id, revision: doc.revision, supply: doc.supply,
        terrain_area_km2: doc.terrain_area_km2, area_source: doc.area_source,
        overlaps: doc.overlaps, geometry_budget: doc.geometry_budget,
      });
      setStatus(`已保存 ${doc.id}（rev ${doc.revision}）· `
        + (doc.supply?.state === 'configured' ? '供给已配置' : '供给未配置：能存，转换会缺项'));
    } catch (error) {
      if (token !== saveToken.current) return;
      setStatus('保存失败：' + (error instanceof Error ? error.message : String(error)));
    }
  }, [advanced, apiBase, draft, scene, shapes, siteName]);

  const click = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (!supported) return;
    const target = event.currentTarget.getBoundingClientRect();
    const pt = screenToLonLat(event.clientX, event.clientY, projection, target);
    if (!author) {
      props.onMoveIntent?.(pt);      // 玩家：只发意图，不改任何状态
      return;
    }
    if (tool === 'select') return;   // 选择态不吞事件（见下面的 pointer-events 规则）
    setPending((list) => [...list, pt]);
  }, [author, projection, props, supported, tool]);

  const finish = useCallback(() => {
    if (pending.length < 3) {
      setStatus('至少要 3 个点才能围成一块范围');
      return;
    }
    const next: DraftShape = {
      kind: tool === 'footprint' ? 'footprint' : kind,
      vertices: pending.slice(),
    };
    const updated = [...shapes, next];
    emit(updated);
    setPending([]);
    setStatus('已加入这一块（还没保存到服务器）');
  }, [emit, kind, pending, shapes, tool]);

  const summary = useMemo(() => {
    const count = (k: string) => shapes.filter((s) => s.kind === k).length;
    return { footprint: count('footprint'), landUse: shapes.length - count('footprint') };
  }, [shapes]);

  /** 所有顶点 → 屏幕点串（宿主 view 变了就重算，不缓存世界坐标）。 */
  const toPoints = useCallback((vertices: LonLat[]): string => vertices
    .map((v) => lonLatToScreen(v, projection))
    .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
    .join(' '), [projection]);

  if (!supported) {
    return (
      <div className="dream-land-overlay" data-mode={mode} data-unsupported="true">
        <p className="dream-land-warn">
          当前是弯边投影（如罗宾逊/摩尔威德），建筑范围与用地叠加只实现了等距圆柱；
          请切回等距圆柱再编辑。这里不做近似，以免把范围画到错误的位置。
        </p>
      </div>
    );
  }

  const drawing = author && tool !== 'select';
  return (
    <div className="dream-land-overlay" data-mode={mode}>
      <div
        className="dream-land-surface"
        data-tool={tool}
        data-drawing={drawing ? 'true' : 'false'}
        onClick={click}
        role="presentation"
        style={{ pointerEvents: drawing ? 'auto' : 'none' }}
      >
        <svg className="dream-land-shapes" viewBox={`0 0 ${projection.stage.sw} ${projection.stage.sh}`}
             preserveAspectRatio="none" aria-hidden="true"
             style={{ pointerEvents: 'none' }}>
          {shapes.map((shape, index) => (
            <polygon
              key={`${shape.kind}-${index}`}
              className={selected === index ? 'is-selected' : undefined}
              points={toPoints(shape.vertices)}
              fill={`${STROKE[shape.kind] || '#8aa0b4'}22`}
              stroke={STROKE[shape.kind] || '#8aa0b4'}
              strokeWidth={2}
            />
          ))}
          {pending.length > 1 && (
            <polyline
              points={toPoints(pending)}
              fill="none"
              stroke={STROKE[tool === 'footprint' ? 'footprint' : kind]}
              strokeWidth={2}
              strokeDasharray="5 4"
            />
          )}
        </svg>
      </div>

      {author && (props.controlsHost ? createPortal(
        <aside className="dream-land-panel" aria-label="圈地与用地规划工具"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => event.stopPropagation()}>
          <div className="dream-land-row">
            {(['select', 'footprint', 'land-use'] as OverlayTool[]).map((value) => (
              <button key={value} type="button" className={tool === value ? 'on' : ''}
                      onClick={() => { setTool(value); setPending([]); }}>
                {value === 'select' ? '选择' : value === 'footprint' ? '圈建筑范围' : '圈用地'}
              </button>
            ))}
          </div>
          {tool === 'land-use' && (
            <div className="dream-land-row">
              {LAND_USE_KINDS.map((item) => (
                <button key={item.kind} type="button" className={kind === item.kind ? 'on' : ''}
                        onClick={() => setKind(item.kind)}>{item.label}</button>
              ))}
            </div>
          )}
          {tool !== 'select' && (
            <div className="dream-land-row">
              <button type="button" onClick={() => setPending((l) => l.slice(0, -1))}
                      disabled={!pending.length}>撤销点</button>
              <button type="button" onClick={() => setPending([])} disabled={!pending.length}>清除</button>
              <button type="button" onClick={finish} disabled={pending.length < 3}>结束</button>
            </div>
          )}
          {shapes.length > 0 && (
            <div className="dream-land-row" aria-label="已画的形状">
              {shapes.map((shape, index) => (
                <button key={`pick-${index}`} type="button"
                        className={selected === index ? 'on' : ''}
                        onClick={() => setSelected(selected === index ? null : index)}>
                  {index + 1}.{shape.kind === 'footprint' ? '建筑' : shape.kind}
                </button>
              ))}
              <button type="button" disabled={selected === null}
                      onClick={() => {
                        if (selected === null) return;
                        const updated = shapes.filter((_s, i) => i !== selected);
                        emit(updated);
                        setSelected(null);
                        setStatus('已删除选中的那一块（还没保存）');
                      }}>
                删除选中
              </button>
            </div>
          )}
          <p className="dream-land-note">
            {summary.footprint ? `建筑范围 ${summary.footprint} 块` : '还没有建筑范围'}
            {' · '}
            {summary.landUse ? `用地 ${summary.landUse} 块` : '还没画用地'}
            {' · 没画到的区域算「未规划」，不是荒地'}
          </p>
          <div className="dream-land-row">
            <label className="dream-land-field">
              地点名
              <input type="text" value={siteName} maxLength={80}
                     placeholder={scene.cityRef?.name || '未命名地点'}
                     onChange={(event) => setSiteName(event.target.value)} />
            </label>
          </div>
          <div className="dream-land-row">
            <button type="button" onClick={() => void save()} disabled={!hasSource(scene)}>
              {draft ? '更新草稿' : '保存草稿'}
            </button>
            <button type="button" onClick={() => void loadList()} disabled={!hasSource(scene)}>
              列出本世界草稿
            </button>
          </div>
          {saved.length > 0 && (
            <div className="dream-land-row" aria-label="已存草稿">
              {saved.map((row) => (
                <button key={row.id} type="button" onClick={() => void loadDraft(row.id)}>
                  {row.id} · rev {row.revision}
                </button>
              ))}
            </div>
          )}
          {!hasSource(scene) && (
            <p className="dream-land-warn">没有有效的世界来源时不能保存（不绑定随机底图）。</p>
          )}
          {lostAdvanced.length > 0 && (
            <p className="dream-land-warn">
              这份草稿的详情接口没有返回{lostAdvanced.join('、')}；更新是整份替换，
              直接保存会把这些声明清掉，请先补齐再存。
            </p>
          )}
          {draft && (
            <p className="dream-land-note">
              {draft.id} · rev {draft.revision}
              {' · '}{draft.supply?.state === 'configured' ? '供给已配置' : '供给未配置'}
              {draft.terrain_area_km2 ? ` · ${draft.terrain_area_km2} km²` : ''}
            </p>
          )}
          {status && <p className="dream-land-note" role="status">{status}</p>}
        </aside>, props.controlsHost
      ) : null)}
    </div>
  );
}

export default LandOverlay;
