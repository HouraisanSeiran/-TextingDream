import { useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react';
import type { NativeWorld } from './bridge';
import { drawMapCiv, drawMapTerrain, type ExportMapParams } from '../render/export';
import { CIV_SHOW_OFF, type CivShow } from '../render/civ/show';
import { drawTerrainDetail, DETAIL_K } from '../render/detail';
import { drawCivDetail, detailCache, releaseDetailCache } from '../render/civ/detail';
import { civMapLayer, civLabelItems, labelViewExtras, civLabelChars } from '../render/civ/labels';
import { settlementsAt, drawSettlementMarks } from '../render/civ/settlements';
import { placeMap, drawPlacedLabels } from '../render/labels/draw';
import { ensureFonts } from '../render/labels/fonts';
import { ErrorBoundary } from '../ui/ErrorBoundary';
import type { CivStyle } from '../render/civ/overlay';

const STYLE: CivStyle = 'fantasy';
export interface Viewport { k: number; x: number; y: number; }
interface MapProps {
  loaded: NativeWorld; view: Viewport; stage: { sw: number; sh: number };
  box: { bw: number; bh: number }; home: { left: number; top: number };
  show: CivShow; selectedPoint: { x: number; y: number } | null;
  visibleCityIds: MutableRefObject<ReadonlySet<number>>;
}

/** Screen-sized native layers; zoom reveals existing settlements, never creates new ones. */
function WorldViewport({ loaded, view, stage, box, home, show, selectedPoint, visibleCityIds }: MapProps) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [fontsReady, setFontsReady] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const data = useMemo(() => {
    if (!loaded.civ) return null;
    const p = { world: loaded.world, raster: loaded.raster, civ: loaded.civ,
      style: STYLE, year: loaded.civ.endYear, show };
    // Settlement visibility is independent of the road ink toggle.
    const layer = civMapLayer({ ...p, show: { ...show, routes: true } });
    // Keep only twelve important cities in the overview; stable population order.
    const major = new Set(settlementsAt(p.civ, p.year).filter(e => e.kind >= 3).slice(0, 12).map(e => e.s.id));
    const marks = layer.marks.map(m => ({ ...m, forced: false,
      minZoom: m.kind <= 4 ? (major.has(m.id) ? 1 : [6, 3.2, 2, 1.5, 1.5][m.kind]) : Math.max(3.2, m.minZoom) }));
    const thresholds = new Map(marks.map(m => [m.id, m.minZoom]));
    const items = (show.labels ? [...civLabelItems(p), ...layer.items] : []).map(item => item.mark === undefined ? item :
      { ...item, minZoom: Math.max(item.minZoom, thresholds.get(item.mark) ?? 1) });
    return { p, marks, items, extras: labelViewExtras(p) };
  }, [loaded, show]);
  useEffect(() => {
    let active = true;
    setFontsReady(false);
    if (loaded.civ) void ensureFonts(STYLE, civLabelChars(loaded.civ), 15000).then(() => {
      if (active) setFontsReady(true);
    }).catch(error => { if (active) setFailure(error); });
    return () => { active = false; };
  }, [loaded]);
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      try {
        const started = performance.now();
        visibleCityIds.current = new Set();
        const canvas = ref.current;
        if (!canvas) return;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.round(stage.sw * dpr);
        canvas.height = Math.round(stage.sh * dpr);
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const s = box.bw / loaded.world.width * view.k * dpr;
        const ox = (view.x + home.left * view.k) * dpr;
        const oy = (view.y + home.top * view.k) * dpr;
        const v = { s, ox, oy, k: view.k };
        ctx.save();
        ctx.beginPath();
        ctx.rect(ox, oy, loaded.world.width * s, loaded.world.height * s);
        ctx.clip();
        if (view.k > DETAIL_K) {
          drawTerrainDetail(ctx, loaded.world, loaded.raster, 'fantasy', v);
          if (data) {
            const cache = detailCache();
            const civil = document.createElement('canvas');
            civil.width = canvas.width; civil.height = canvas.height;
            try {
              drawCivDetail(civil.getContext('2d')!, data.p, { ...v, mp: null, cw: canvas.width, ch: canvas.height, dpr }, dpr, cache);
              ctx.drawImage(civil, 0, 0);
            }
            finally { releaseDetailCache(cache); }
          }
        }
        if (data && fontsReady) {
          const lv = { ...data.extras, wrap: 0, scale: s, ox, oy, dpr, k: view.k,
            mapCss: box.bw, canvasW: canvas.width, canvasH: canvas.height };
          const placed = placeMap(data.items, data.marks, lv);
          const activeCities = new Set(settlementsAt(data.p.civ, data.p.year).map(e => e.s.id));
          visibleCityIds.current = new Set(placed.marks.map(m => m.mark.id).filter(id => activeCities.has(id)));
          drawSettlementMarks(ctx, placed.marks, STYLE);
          drawPlacedLabels(ctx, placed.labels, lv);
          canvas.dataset.marks = String(placed.marks.length);
          canvas.dataset.eligible = String(data.marks.filter(m => m.minZoom <= view.k).length);
          canvas.dataset.k = String(view.k);
        }
        if (selectedPoint !== null) {
          const x = selectedPoint.x * s + ox;
          const y = selectedPoint.y * s + oy;
          ctx.beginPath(); ctx.arc(x, y, 11 * dpr, 0, Math.PI * 2);
          ctx.strokeStyle = '#997449'; ctx.lineWidth = 1.5 * dpr; ctx.stroke();
        }
        ctx.restore();
        canvas.dataset.source = loaded.identity.contentSha256 || loaded.identity.importId || '';
        canvas.dataset.drawMs = (performance.now() - started).toFixed(2);
      } catch (error) { setFailure(error); }
    });
    return () => cancelAnimationFrame(frame);
  }, [loaded, data, fontsReady, view, stage, box, home, selectedPoint, visibleCityIds]);
  if (failure !== null) throw failure;
  return <canvas ref={ref} className="dream-world-detail" aria-label="世界城镇与地形细节"
    style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }} />;
}


function WorldCanvas(props: MapProps) {
  const { loaded, view, stage, box, home, show, selectedPoint, visibleCityIds } = props;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const civilRef = useRef<HTMLCanvasElement>(null);
  // 真地图：画进位图尺寸 = raster 尺寸的 canvas，由 CSS 等比缩。
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (!loaded) { canvas.width = 0; canvas.height = 0; return; }
    canvas.width = loaded.raster.w;
    canvas.height = loaded.raster.h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const make = (w: number, h: number) => typeof OffscreenCanvas !== 'undefined'
      ? new OffscreenCanvas(w, h) : Object.assign(document.createElement('canvas'), { width: w, height: h });
    const base: ExportMapParams = {
      world: loaded.world,
      raster: loaded.raster,
      civ: loaded.civ,
      style: STYLE,
      layer: 'elevation',
      year: loaded.civ ? (loaded.civ.endYear ?? 0) : 0,
      show: CIV_SHOW_OFF,
    };
    drawMapTerrain(ctx, base, make);
  }, [loaded]);

  // Toggling labels or political ink does not regenerate the terrain bitmap.
  useEffect(() => {
    const canvas = civilRef.current;
    if (!canvas) return;
    canvas.width = loaded.raster.w; canvas.height = loaded.raster.h;
    const ctx = canvas.getContext('2d');
    if (!ctx || !loaded.civ) return;
    drawMapCiv(ctx, { world: loaded.world, raster: loaded.raster, civ: loaded.civ, style: STYLE,
      layer: 'elevation', year: loaded.civ.endYear,
      show: { ...CIV_SHOW_OFF, polities: show.polities, routes: show.routes } },
      (width, height) => Object.assign(document.createElement('canvas'), { width, height }));
  }, [loaded, show.polities, show.routes]);

  return <>
        {/* 外层只负责平移 + 缩放（原点 0 0），内层按居中位置摆地图框：
            屏幕 X = v.x + (boxLeft + wx/W·bw)·k，和 `stageToWorld` 的反式一致。 */}
        <div style={{ position: 'absolute', left: 0, top: 0,
                      transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})`,
                      transformOrigin: '0 0' }}>
          <div style={{ position: 'absolute', left: home.left, top: home.top,
                        width: box.bw, height: box.bh }}>
            <canvas ref={canvasRef}
                    style={{ width: '100%', height: '100%', display: 'block' }} />
            <canvas ref={civilRef} aria-hidden="true"
                    style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }} />
          </div>
        </div>
        <WorldViewport loaded={loaded} view={view} stage={stage} box={box} home={home} show={show} selectedPoint={selectedPoint} visibleCityIds={visibleCityIds} />
  </>;
}

export function WorldMapCanvas(props: MapProps) {
  return <ErrorBoundary key={props.loaded.identity.contentSha256 ?? props.loaded.identity.importId}
    title="地图显示失败" retry="remount"><WorldCanvas {...props} /></ErrorBoundary>;
}
