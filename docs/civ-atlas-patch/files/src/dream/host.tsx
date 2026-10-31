// 织梦原生宿主：真地图主画面 + 作者生成 + 可挂载的原生叠加层。
//
// 地图怎么画：**不自己上色**。走上游现有的原生管线（`src/finderThumbDraw.ts:41-49`
// 就是同一路径的小图版）：
//
//   rasterize(world, SCALE, false)  ->  Raster
//   drawMapTerrain(ctx, {world, raster, civ, style:'fantasy', layer:'elevation', year, show}, make)
//   drawMapCiv(ctx, {…}, make)       <- civ 存在时叠文明层
//
// 两者都在 `src/render/export.ts`，内部走原生 `renderFantasy` / `renderRealistic` / `renderLayer`。
//
// 画布与投影必须一致：canvas 的位图尺寸就是 raster.w × raster.h，CSS 按 2:1 等比缩；
// 叠加层的 StageBox 用**同一个** 2:1 尺寸。地图框在舞台里**居中**
// （`ui/mapWrap.ts:55 boxLeft/boxTop`）：X = v.x + (boxLeft + wx/W·bw)·k。
//
// 作者能在同一画面里完成两件事：**新建世界**（上游 worker 生成 → 打包 → 登记到服务端）
// 和 **打开已有世界**（服务端已登记的导入）；两者结果都是同一个 `importId`，
// 之后一律用 `readNativeWorld` 重新读回来画——不拿生成时的内存对象当第二套数据源。
//
// player 模式不走作者路由：这里只做 `not_ready` 提示，玩家路是服务端已遮罩的投影。

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { canSave, listNativeWorlds, type BridgeMode, type NativeWorldRow } from './bridge';
import { defaultAuthorParams, generateAndRegister,
         type GenerateProgress, type WorldParams } from './generate';
import { CIV_SHOW_OFF, type CivShow } from '../render/civ/show';
import { LandOverlay, type DraftShape, type LandOverlayScene } from './landOverlay';
import { settlementsAt } from '../render/civ/settlements';
import { WorldMapCanvas, type Viewport } from './WorldMapCanvas';
import { useNativeWorlds } from './useNativeWorlds';
import { authorToken, errorMessage, postHost, record } from './hostApi';
import { WorldGenerationForm } from './WorldGenerationForm';
import styles from './host.module.css';
import { BIOMES } from '../gen/biomes';
import { pickMapPoint, selectCity, type MapSelection } from './mapPicking';


const MIN_K = 1;
/**
 * 浏览时的缩放上限用**上游自己的**那个数：`ui/App.tsx:4799` 的
 * `Math.min(12, Math.max(1, v.k * f))`。不自己定更大的值——那会假装比原生看得更细。
 */
const MAX_K = 12;
/**
 * 作者圈地时的局部放大上限（只影响视口，**不增地形细节**）。
 *
 * 为什么需要：世界宽 2048 像素 = 360° ≈ 40075 km，在右栏 ~800px、k=12 时一个屏幕像素
 * 约 1.6 km；而建筑/城镇范围上限是 50 km²（`app/land_footprint.py`），在 k=12 下只有
 * 几像素宽，圈不准。这里把视口再放大，**只是把同一批 raster 像素放得更大**（双线性拉伸），
 * 不发明细节、不改后端面积上限。超过 MAX_K 时界面会明说这一点。
 */
const PLAN_MAX_K = 64;
/** 一键圈地的倍数：直接从当前视口跳到能看清一块地的尺度。 */
const PLAN_JUMP_K = 48;
/** 国土、国界、道路；城镇和文字由视口层分级绘制，不打开调试城址圆点。 */
const SHOW_CIV: CivShow = { ...CIV_SHOW_OFF, polities: false, routes: true, labels: true };
/** 生成时实时刷新进度，不必等整份完成才知道在干什么。 */
const STAGE_LABEL: Record<string, string> = {
  mesh: '网格', plates: '板块', tectonics: '地壳', erosion: '侵蚀', rivers: '水系',
  climate: '气候', biome: '群落', raster: '铺像素', civ: '文明推演', civBase: '宜居度',
  regions: '划州', polities: '立国', snapshot: '打包原件', done: '完成',
};

export function DreamMapHost({ mode = 'author' as BridgeMode } = {}): JSX.Element {
  const author = mode === 'author';
  const { worlds, setWorlds, importId, setImportId, loaded, busy, error: loadError, retry } = useNativeWorlds(author);
  const [startCity, setStartCity] = useState('');
  const [starting, setStarting] = useState(false);
  const [show, setShow] = useState<CivShow>(SHOW_CIV);
  const [selection, setSelection] = useState<MapSelection | null>(null);
  const visibleCityIds = useRef<ReadonlySet<number>>(new Set());
  const cityEntries = useMemo(() => loaded?.civ ? settlementsAt(loaded.civ, loaded.civ.endYear) : [], [loaded]);
  const cities = useMemo(() => {
    return cityEntries.map(entry => entry.s);
  }, [cityEntries]);
  const chosenCity = cities.find(s => String(s.id) === startCity) ?? cities[0];
  const selectedCity = cityEntries.find(entry => entry.s.id === selection?.cityId);
  const beginExploration = async () => {
    if (!loaded || !chosenCity || starting) return;
    setStarting(true); setError('');
    try {
      if (!window.loadSession) throw new Error('请从织梦主页面开始探索');
      const title = chosenCity.name + '周边探索';
      const saved = await postHost('/inner/native-starts', {draft: {
        import_id: loaded.identity.importId, source_sha256: loaded.identity.contentSha256,
        world_id: loaded.identity.worldId, base_year: loaded.civ!.endYear, branch: 'main',
        city_id: 'settlement:' + chosenCity.id, start_cell: chosenCity.cell,
        title, premise: '从城镇出发，沿道路探索周边聚落与街区。', exploration: true,
      }});
      const draft = record(saved.draft);
      if (typeof draft.id !== 'string' || typeof draft.revision !== 'number') throw new Error('开局草稿响应不完整');
      await postHost('/inner/native-starts/' + encodeURIComponent(draft.id) + '/confirm', {expected_revision: draft.revision});
      const journey = await postHost('/sessions', {title, mode: 'protagonist'});
      if (typeof journey.id !== 'string') throw new Error('旅程响应缺少编号');
      await window.loadSession!(journey.id);
    } catch (error: unknown) { setError(errorMessage(error)); }
    finally { setStarting(false); }
  };
  const [view, setView] = useState<Viewport>({ k: 1, x: 0, y: 0 });
  const [stage, setStage] = useState({ sw: 800, sh: 420 });
  const [shapes, setShapes] = useState<DraftShape[]>([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  // 作者生成：参数面板默认收起，空世界时自动展开
  const [params, setParams] = useState<WorldParams>(() => defaultAuthorParams());
  const [showCreate, setShowCreate] = useState(false);
  const [progress, setProgress] = useState<GenerateProgress | null>(null);
  const [creating, setCreating] = useState(false);
  /** 作者圈地模式：允许超过原生 12 倍的局部放大（只放大像素，不增细节）。 */
  const [planning, setPlanning] = useState(false);
  /** 工具的 Portal 目标在外层工作区；独立宿主预览时仍可在舞台旁使用。 */
  const [toolbox, setToolbox] = useState<HTMLElement | null>(null);
  const [controlsTarget, setControlsTarget] = useState<HTMLElement | null>(null);
  useEffect(() => { setToolbox(document.getElementById('native-map-toolbox')); }, []);
  /** 当前实际可用的缩放上限。 */
  const maxK = planning ? PLAN_MAX_K : MAX_K;

  const stageRef = useRef<HTMLDivElement | null>(null);
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  useEffect(() => {
    const node = stageRef.current;
    if (!node) return;
    const measure = () => {
      const bounds = node.getBoundingClientRect();
      if (bounds.width > 0 && bounds.height > 0) {
        setStage({ sw: Math.round(bounds.width), sh: Math.round(bounds.height) });
      }
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setSelection(null); visibleCityIds.current = new Set(); setShapes([]); setStartCity('');
    setView({ k: 1, x: 0, y: 0 }); setPlanning(false); setError('');
  }, [author, importId]);
  useEffect(() => {
    if (author && !busy && !loadError && !worlds.length) setShowCreate(true);
  }, [author, busy, loadError, worlds.length]);

  /** 2:1 地图框：canvas 与叠加层共用同一尺寸（不拉满舞台）。 */
  const box = useMemo(() => {
    if (!loaded) return { bw: 1, bh: 1 };
    const aspect = loaded.raster.w / loaded.raster.h;
    let bw = stage.sw;
    let bh = Math.round(bw / aspect);
    if (bh > stage.sh) { bh = stage.sh; bw = Math.round(bh * aspect); }
    return { bw: Math.max(1, bw), bh: Math.max(1, bh) };
  }, [loaded, stage.sw, stage.sh]);

  /** 地图框在舞台里的左上角（和 `ui/mapWrap.ts` 的 boxLeft/boxTop 同一个定义）。 */
  const home = useMemo(() => ({
    left: Math.round((stage.sw - box.bw) / 2),
    top: Math.round((stage.sh - box.bh) / 2),
  }), [stage.sw, stage.sh, box.bw, box.bh]);

  /**
   * 缩放：把锚点下的那个世界点留在原地（和 `ui/App.tsx:4799` 的 zoomAt 同一个行为）。
   * 锚点默认舞台中心；给鼠标位置就是“就地放大”——圈建筑范围时得能直接放到那块地上。
   */
  const zoomBy = useCallback((factor: number, anchor?: { x: number; y: number }) => {
    setView((old) => {
      const k = Math.min(maxK, Math.max(MIN_K, old.k * factor));
      const ratio = k / old.k;
      const cx = anchor ? anchor.x : stage.sw / 2;
      const cy = anchor ? anchor.y : stage.sh / 2;
      return { k, x: cx - (cx - old.x) * ratio, y: cy - (cy - old.y) * ratio };
    });
  }, [stage.sw, stage.sh, maxK]);

  /** 一键跳到圈地尺度（以舞台中心为锚点，不改变当前看的是哪一块）。 */
  const zoomToPlan = useCallback(() => {
    setPlanning(true);
    setView((old) => {
      const k = PLAN_JUMP_K;
      const ratio = k / old.k;
      const cx = stage.sw / 2;
      const cy = stage.sh / 2;
      return { k, x: cx - (cx - old.x) * ratio, y: cy - (cy - old.y) * ratio };
    });
  }, [stage.sw, stage.sh]);

  const onWheel = useCallback((event: React.WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    const bounds = event.currentTarget.getBoundingClientRect();
    zoomBy(event.deltaY < 0 ? 1.15 : 1 / 1.15,
      { x: event.clientX - bounds.left, y: event.clientY - bounds.top });
  }, [zoomBy]);

  const onMapKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.target !== event.currentTarget || event.ctrlKey || event.altKey || event.metaKey) return;
    if (event.key === '+' || event.key === '=') zoomBy(1.4);
    else if (event.key === '-') zoomBy(1 / 1.4);
    else if (event.key === '0') setView({ k: 1, x: 0, y: 0 });
    else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
      if (view.k <= 1) return;
      const key = event.key;
      setView(old => ({ ...old, x: old.x + (key === 'ArrowLeft' ? 60 : key === 'ArrowRight' ? -60 : 0),
        y: old.y + (key === 'ArrowUp' ? 60 : key === 'ArrowDown' ? -60 : 0) }));
    } else return;
    event.preventDefault();
  };

  /** 双击就地放大：上游主图的同一种手感，不另写一套缩放。 */
  const onDoubleClick = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    zoomBy(2, { x: event.clientX - bounds.left, y: event.clientY - bounds.top });
  }, [zoomBy]);

  const onPointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || (event.target as Element).closest('button, input, select, textarea, a')) return;
    event.currentTarget.focus({ preventScroll: true });
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { x: event.clientX, y: event.clientY, ox: view.x, oy: view.y };
  }, [view.x, view.y]);

  const onPointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const held = drag.current;
    if (!held || view.k <= 1) return;
    setView((old) => ({ ...old, x: held.ox + (event.clientX - held.x),
                        y: held.oy + (event.clientY - held.y) }));
  }, [view.k]);

  const onPointerUp = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const held = drag.current;
    drag.current = null;
    if (!held || !loaded || planning || Math.hypot(event.clientX - held.x, event.clientY - held.y) > 5) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const scale = box.bw / loaded.world.width * view.k;
    const x = (event.clientX - rect.left - view.x - home.left * view.k) / scale;
    const y = (event.clientY - rect.top - view.y - home.top * view.k) / scale;
    const picked = pickMapPoint(loaded, visibleCityIds.current, x, y, scale);
    setSelection(picked);
    if (picked?.cityId != null) setStartCity(String(picked.cityId));
  }, [loaded, planning, box, view, home]);

  const locateCity = () => {
    if (!loaded || !chosenCity) return;
    const k = 4;
    const scale = box.bw / loaded.world.width;
    setView({ k, x: stage.sw / 2 - (home.left + loaded.world.mesh.x[chosenCity.cell] * scale) * k,
      y: stage.sh / 2 - (home.top + loaded.world.mesh.y[chosenCity.cell] * scale) * k });
    setSelection(selectCity(loaded, chosenCity.id, chosenCity.cell));
  };

  /** 生成一个新世界：上游 worker 干完活 → 打包 → 登记 → 直接当当前世界读回来画。 */
  const createWorld = useCallback(async () => {
    if (!author || creating) return;
    setCreating(true);
    setError('');
    setProgress({ stage: 'mesh', pct: 0 });
    setNotice('正在生成世界…（可以留在这一页，完成后地图会自己出现）');
    try {
      const made = await generateAndRegister(params, setProgress);
      // 新世界已经在服务端：拉清单、把它设为当前（这一步会触发上面的读取 effect）
      const rows = await listNativeWorlds();
      setWorlds(rows);
      setShowCreate(false);
      setNotice(`已生成并登记：${made.worldId}（${Math.round(made.bytes / 1024)} KB，`
        + `${made.parts.join('/')}）`);
      setImportId(made.importId);
    } catch (thrown: unknown) {
      setError(errorMessage(thrown));
      setNotice('');
    } finally {
      setCreating(false);
      setProgress(null);
    }
  }, [author, creating, params]);

  // `apiBase = ''` = 同源；能不能保存只看来源身份，两件事不混。
  const apiBase = '';
  const saveAllowed = loaded ? canSave(loaded.identity, mode) : false;

  const scene = useMemo<LandOverlayScene>(() => ({
    worldSource: loaded && loaded.identity.importId && loaded.identity.contentSha256
      ? { importId: loaded.identity.importId,
          sourceSha256: loaded.identity.contentSha256 }
      : null,
    sampling: null,
    authorToken: author ? authorToken() : '',
    /**
     * 选中的 civ 城市。类型跟 `landOverlay.tsx` 的 `LandOverlayScene` 走（只认稳定实体 id）：
     * `cityId` 必须是原件里的 `settlement:…`，不是数字下标、也不按名字猜。
     * 本阶段尚未接城市点选，所以它一直是 null——这个 null 是真实状态，不是占位假数据；
     * 接的时候从 `loaded.civ.settlements` 取实体 id 填进这里就行，保存路径不用改。
     */
    cityRef: null,
  }), [loaded, author]);

  const projection = useMemo(() => ({
    view: { k: view.k, x: view.x, y: view.y },
    stage: { sw: stage.sw, sh: stage.sh, bw: box.bw, bh: box.bh, padB: 0 },
    worldWidth: loaded ? loaded.raster.w : 2048,
    worldHeight: loaded ? loaded.raster.h : 1024,
    // 只接等距圆柱：landOverlay 的换算就是这个前提上的直线映射。
    linear: true,
  }), [view.k, view.x, view.y, stage.sw, stage.sh, box.bw, box.bh, loaded]);

  const label = (row: NativeWorldRow) =>
    `世界 ${worlds.indexOf(row) + 1} · ${row.worldId || row.importId}`;

  return (
    <div className="dream-host" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <header className="dream-atlas-heading">
        <span className="dream-atlas-kicker">DREAMTERRA / 世界图志</span>
        <h2>山川之间</h2>
        <span className="dream-atlas-subtitle">循山识水，沿路寻城</span>
      </header>
      <div className="dream-atlas-toolbar">
        <div className="dream-atlas-controls">
        <select value={importId || ''} onChange={(e) => setImportId(e.target.value || null)}
                disabled={!author || creating} aria-label="选择原件">
          {worlds.map((row) => (
            <option key={row.importId} value={row.importId}>{label(row)}</option>
          ))}
        </select>
        <div className="dream-atlas-layers" role="group" aria-label="地图图层">
          <button type="button" aria-pressed={!show.polities} onClick={() => setShow(old => ({ ...old, polities: false }))}>山川</button>
          <button type="button" aria-pressed={show.polities} onClick={() => setShow(old => ({ ...old, polities: true }))}>疆域</button>
          <button type="button" aria-pressed={show.routes} onClick={() => setShow(old => ({ ...old, routes: !old.routes }))}>道路</button>
          <button type="button" aria-pressed={show.labels} onClick={() => setShow(old => ({ ...old, labels: !old.labels }))}>地名</button>
        </div>
        </div>
        <details className="dream-atlas-journey">
        <summary>从城镇启程</summary>
        <select aria-label="探索起点城镇" value={chosenCity ? String(chosenCity.id) : ''}
                onChange={e => setStartCity(e.target.value)} disabled={!cities.length || starting}>
          {!cities.length && <option value="">该年份没有城镇</option>}
          {cities.map(city => <option key={city.id} value={city.id}>{city.name}</option>)}
        </select>
        <button type="button" onClick={locateCity} disabled={!chosenCity}>定位城镇</button>
        <button type="button" disabled={!author || !chosenCity || starting || busy || creating}
                onClick={beginExploration}>{starting ? '准备旅程…' : '开始探索'}</button>
        </details>
        <div className="dream-atlas-actions" role="group" aria-label="地图缩放">
        <button type="button" disabled={view.k <= MIN_K} onClick={() => zoomBy(1 / 1.4)} aria-label="缩小地图">−</button>
        <span className="dream-zoom-value">×{Math.round(view.k * 10) / 10}</span>
        <button type="button" disabled={view.k >= maxK} onClick={() => zoomBy(1.4)} aria-label="放大地图">＋</button>
        <button type="button" onClick={() => setView({ k: 1, x: 0, y: 0 })}>复位</button>
        </div>
        {busy ? <span role="status">读取中…</span> : null}
        {creating && progress ? (
          <span role="status">{STAGE_LABEL[progress.stage] || progress.stage} {Math.round(progress.pct)}%</span>
        ) : null}
      </div>

      {author && toolbox ? createPortal(
        <div className="dream-toolbox-content">
          <div className="dream-toolbox-head"><span>世界编辑</span><small>仅作者可见</small></div>
          <button type="button" className="dream-create-toggle" disabled={creating}
                  onClick={() => setShowCreate((old) => !old)} aria-expanded={showCreate}>
            <span>{showCreate ? '收起生成参数' : '生成一个新世界'}</span><span aria-hidden="true">{showCreate ? '−' : '＋'}</span>
          </button>
          {loaded && <button type="button" className="dream-plan-zoom" onClick={zoomToPlan}
            title="将当前视口放大到圈地尺度；地形数据精度仍取决于原件">
            圈地视图 <span>×{PLAN_JUMP_K}</span>
          </button>}
          {view.k > MAX_K && <p className="dream-pixel-note" role="status">当前为圈地尺度，显示细节不代表建筑级地形精度。</p>}
          <div id="dream-land-controls" className="dream-land-controls" ref={(node) => { if (node && node !== controlsTarget) setControlsTarget(node); }} />
        </div>, toolbox
      ) : null}

      {loadError && <p role="alert" className="dream-host-error">{loadError} <button type="button" onClick={retry}>重新读取世界</button></p>}
      {error ? <p role="alert" className="dream-host-error">{error}</p> : null}
      {notice ? <p className="dream-host-notice">{notice}</p> : null}

      {author && showCreate && (toolbox ? createPortal(
        <WorldGenerationForm params={params} setParams={setParams} creating={creating} progress={progress} onGenerate={createWorld} />, toolbox
      ) : <WorldGenerationForm params={params} setParams={setParams} creating={creating} progress={progress} onGenerate={createWorld} />)}

      <div ref={stageRef} className={`dream-host-stage dream-atlas-stage ${styles.stage}`}
           role="region" aria-label="世界地图，可用方向键平移，加减键缩放，0 键复位" tabIndex={0}
           onKeyDown={onMapKeyDown}
           style={{ position: 'relative', flex: 1, overflow: 'hidden',
                    cursor: view.k > 1 ? 'grab' : 'default' }}
           onWheel={onWheel} onPointerDown={onPointerDown}
           onDoubleClick={onDoubleClick}
           onPointerMove={onPointerMove} onPointerUp={onPointerUp}
           onPointerCancel={() => { drag.current = null; }}
           onLostPointerCapture={() => { drag.current = null; }}>
        {loaded && <WorldMapCanvas loaded={loaded} view={view} stage={stage} box={box} home={home} show={show} selectedPoint={selection} visibleCityIds={visibleCityIds} />}
        {!loaded ? (
          <p style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
                      margin: 0, textAlign: 'center', padding: 24 }}>
            {!author ? '玩家模式原生地图未接（not_ready）。'
              : creating ? '正在生成世界…'
              : showCreate ? '到左侧「地图与圈地工具」设置参数，再生成世界。'
              : '还没有可用的世界。到左侧「新建世界」开始。'}
          </p>
        ) : null}
        <div style={{ position: 'absolute', inset: 0 }}>
          <LandOverlay
            mode={mode}
            scene={scene}
            projection={projection}
            shapes={shapes}
            revision={null}
            onShapesChange={(next) => setShapes(next)}
            controlsHost={controlsTarget}
            onMoveIntent={(target) =>
              setNotice(`移动意图：${target.lon.toFixed(2)}, ${target.lat.toFixed(2)}`)}
            apiBase={apiBase}
          />
        </div>
        {loaded && <>
          <div className="dream-atlas-compass" aria-label="北方朝上">N ↑</div>
          <div className="dream-atlas-legend"><strong>{view.k < 2 ? '世界总览' : view.k < 6 ? '区域图' : '地方图'}</strong>
            <span>山脉 △ · 森林 ♧ · 河流 ─ · 道路 ┄</span>
            <small>滚轮缩放 · 拖动平移 · 点击查看</small></div>
          {selection !== null && <section className="dream-atlas-inspector" aria-label="地理详情"
            onPointerDown={e => e.stopPropagation()} onPointerUp={e => e.stopPropagation()}
            onWheel={e => e.stopPropagation()} onDoubleClick={e => e.stopPropagation()}>
            <button type="button" className="dream-inspector-close" aria-label="关闭地理详情" onClick={() => setSelection(null)}>×</button>
            <small>第 {loaded.civ?.endYear ?? 0} 年 · 地理札记</small>
            <h3>{selectedCity?.s.name || BIOMES[selection.biome]?.name || '山川'}</h3>
            {selectedCity && <p>{['村落', '城镇', '城市', '大城', '首都'][selectedCity.kind]} · {Math.round(selectedCity.pop * 1000).toLocaleString()} 人</p>}
            <dl>
              <div><dt>地貌</dt><dd>{BIOMES[selection.biome]?.name || '未知'}</dd></div>
              <div><dt>海拔</dt><dd>{Math.round(selection.elevation).toLocaleString()} m</dd></div>
              <div><dt>年均温</dt><dd>{selection.temperature.toFixed(1)} °C</dd></div>
              <div><dt>年降水</dt><dd>{Math.round(selection.precipitation)} mm</dd></div>
            </dl>
            <small>{selectedCity ? '城镇所在区域的地理记录。' : '所选位置的地理记录。'}地图缩放不改变地理。</small>
          </section>}
        </>}
      </div>

      <div className="dream-host-foot dream-atlas-status">
        {loaded ? (
          <>
            第 {loaded.civ?.endYear ?? 0} 年
            {' · '}{cities.length} 座城镇
            {' · '}×{view.k.toFixed(1)}
            {' · '}{show.polities ? '疆域图' : '山川图'}
            {saveAllowed ? '' : ' · 保存已禁用'}
          </>
        ) : (author ? `共 ${worlds.length} 个已登记世界` : '未选择原件')}
      </div>
    </div>
  );
}
