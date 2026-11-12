"""Time / memory estimates for the world-generation chain (skeleton -> fast world layer -> TD coarse ridges -> atlas).

Pure standard library. Every number says whether it is measured (实测) or extrapolated (推算) and from what.
Measured points (2026-11-05, this machine, Ryzen 7 7735HS / RTX 2080 SUPER):
  skeleton orogen     1600 km  ~20 s;  5000 km ~134 s
  fast relief orogen  1600 km  66 s / 367 MB peak working set (artifacts/fast-world/world1600-pangaea-fast-v3/runtime-stats.json);
                      5000 km  ~16 min / ~2.1 GB
  TD coarse CPU       1600 km  171 s (20 steps, every tile; artifacts/worlds/world1600-v4-shaped/td-coarse-ridges/runtime-stats.json)
  atlas render        1600 km  140 s (tools/render_world_relief_atlas.py, width 2400, incl. detail and reserved pages)
TD coarse GPU seconds per tile (0.21-2.83 s) and model load (10-25 s) are 推算 from artifacts/td-coarse-opt/estimate.json.
"""
from __future__ import annotations

import math

FAST_SPACING_M = 2000.0
MEASURED = 'measured'          # 实测
EXTRAPOLATED = 'extrapolated'  # 推算

# (nodes, seconds, peak MB) of the 2 km fast layer
_FAST_POINTS = ((800 * 800, 66.0, 367.0), (2500 * 2500, 960.0, 2100.0))
# (skeleton cells, seconds)
_SKELETON_POINTS = ((160 * 160, 20.0), (250 * 250, 134.0))
TD_TILES = {1600: (23, 23), 5000: (155, 155), 10000: (441, 620)}   # computed tiles with skip 120 km (plan-only)
TD_GPU_S_PER_TILE = (0.21, 2.83)
TD_CPU_S_PER_TILE = (2.08, 3.27)
TD_LOAD_S = (10.0, 25.0)
TD_GPU_MIN_FREE_MIB = 4096
OVERVIEW_WIDTH_PX = 1200          # 概览快档的出图宽度（像素），比完整图册的 2400 少一半
QUICK_ATLAS_SHARE = 0.5           # 概览快档磁盘只动 atlas 项：单图 1200 px、无 detail / reserved 页，保守按一半算
QUICK_RENDER_SECONDS = (15.0, 45.0)   # 概览 1200 px 无附页：保守推算，非保证；等实测再校正


def quick_overview(quality='speed', pipeline='playable'):
    """True only for the default pair (quality=speed + pipeline=playable).

    Single source of truth for the quick-overview policy: web_jobs renders with
    ``--overview-only --width 1200`` exactly when this is True, and the estimates follow the same flag.
    """
    return quality == 'speed' and (pipeline or 'playable') == 'playable'


def _power(points, x):
    (x0, y0), (x1, y1) = points
    k = math.log(y1 / y0) / math.log(x1 / x0)
    return y0 * (x / x0) ** k


def _dims(width_km, height_km):
    """(width, height) in km; height defaults to width, i.e. a square (旧 size_km 写法)."""
    width = float(width_km)
    height = width if height_km is None else float(height_km)
    return width, height


def skeleton_cell_km(size_km, height_km=None):
    """Orogen skeletons rasterize at 2 km, so the cell must be a whole multiple of 2 km.

    The cell class comes from the **longest** side of the rectangle (config.skeleton_cell_km uses
    the same rule): 10 km <=2000, 20 km <=6000, 40 km above. 10000 km uses 40 km cells (~62500 cells,
    the same count as the measured 5000 km @ 20 km) so author drafts finish in minutes;
    play-start regions can later refine with a finer local skeleton.
    """
    size = max(int(size_km), int(size_km if height_km is None else height_km))
    if size <= 2000:
        return 10
    if size <= 6000:
        return 20
    return 40


def fast_layer(width_km, height_km=None, spacing_m=FAST_SPACING_M):
    """Fast world layer: nodes, CPU seconds, peak memory. Calibrated at 2 km; other spacings extrapolate by node count.

    Nodes are the real width x height grid, so a rectangle is never estimated as its square side.
    """
    width, height = _dims(width_km, height_km)
    spacing_m = float(spacing_m)
    if spacing_m <= 0:
        raise ValueError('spacing_m must be positive')
    nodes = int(round(width * 1000 / spacing_m)) * int(round(height * 1000 / spacing_m))
    (n0, t0, m0), (n1, t1, m1) = _FAST_POINTS
    hit = next((p for p in _FAST_POINTS if p[0] == nodes), None)
    if hit and abs(spacing_m - FAST_SPACING_M) < 1e-9:
        seconds, mb, basis = hit[1], hit[2], MEASURED
    else:
        seconds = _power(((n0, t0), (n1, t1)), max(nodes, 1))
        mb = m0 + (m1 - m0) / (n1 - n0) * (nodes - n0)          # linear in nodes (~324 B/node + ~170 MB)
        basis = EXTRAPOLATED
    return dict(spacing_m=spacing_m, nodes=nodes, cpu_seconds=float(seconds), peak_mb=float(max(mb, 200.0)), basis=basis,
                how='time ~ nodes^1.18 and memory linear in nodes, fitted to the 1600 km (66 s / 367 MB) and 5000 km (~16 min / ~2.1 GB) runs at 2 km')


def skeleton(size_km, height_km=None):
    """Skeleton cells/time; cell class from the longest side, cells = real width x height grid."""
    width, height = _dims(size_km, height_km)
    cell = skeleton_cell_km(width, height)
    cells = int(round(width / cell)) * int(round(height / cell))
    hit = next((p for p in _SKELETON_POINTS if p[0] == cells), None)
    seconds = hit[1] if hit else _power(_SKELETON_POINTS, cells)
    return dict(cell_km=cell, cells=cells, seconds=float(seconds), basis=MEASURED if hit else EXTRAPOLATED,
                width_km=width, height_km=height)


def td_coarse(size_km, device, *, height_km=None):
    """TD coarse tiles/seconds. The table is keyed by the longest side; a rectangle scales the tile count by area."""
    width, height = _dims(size_km, height_km)
    # smallest table class that covers the longest side (a 10000x8000 rectangle uses the 10000 class and
    # scales the tile count by area; the four measured table entries themselves are untouched)
    key = next((s for s in sorted(TD_TILES) if s >= max(width, height)), max(TD_TILES))
    lo_t, hi_t = TD_TILES[key]
    if (width, height) != (key, key):
        share = (width * height) / (key * key)
        lo_t, hi_t = max(1, int(round(lo_t * share))), max(1, int(round(hi_t * share)))
    per = TD_GPU_S_PER_TILE if device == 'cuda' else TD_CPU_S_PER_TILE
    lo, hi = lo_t * per[0] + TD_LOAD_S[0], hi_t * per[1] + TD_LOAD_S[1]
    out = dict(device=device, tiles=[lo_t, hi_t], seconds=[float(lo), float(hi)], basis=EXTRAPOLATED,
               how='tiles (plan-only, skip deep ocean > 120 km, 15 steps) x seconds per tile + model load; GPU s/tile from '
                   'artifacts/td-coarse-opt/estimate.json (not benchmarked)')
    if device != 'cuda' and (width, height) == (5000, 5000):
        out['seconds'] = [14 * 60.0, 14 * 60.0]
    if device == 'cuda':
        out['gpu_free_mib_required'] = TD_GPU_MIN_FREE_MIB
    return out


def atlas(size_km, *, height_km=None):
    """Atlas render seconds; a rectangle uses the equivalent side (sqrt of the area) for the class."""
    width, height = _dims(size_km, height_km)
    span = math.sqrt(width * height)
    if abs(span - 1600.0) < 1e-9:
        return dict(seconds=[140.0, 140.0], basis=MEASURED)
    if span <= 5000.0:
        return dict(seconds=[180.0, 480.0], basis=EXTRAPOLATED)
    return dict(seconds=[600.0, 1800.0], basis=EXTRAPOLATED)


def disk_product_bytes(size_km, spacing_m=FAST_SPACING_M, pipeline='playable', *, quick_render=False, height_km=None):
    """Approximate on-disk footprint for one web worldgen product tree (推算).

    Aligns grid term with planner.fast_layer_2km (7×float32×nodes); skeleton / atlas /
    islands / vectors are scaled from 1600 km product sizes. ``playable`` keeps one atlas;
    ``full`` doubles atlas and keeps the details product footprint in the islands term.
    ``quick_render`` (speed + playable only) changes nothing but the atlas term: one 1200 px
    overview page, no detail / reserved pages.
    """
    fl = fast_layer(size_km, height_km=height_km, spacing_m=spacing_m)
    sk = skeleton(size_km, height_km)
    nodes = fl['nodes']
    span = math.sqrt(sk['width_km'] * sk['height_km'])       # rectangle: scale by the equivalent side
    grids = int(nodes * 4 * 7)
    skeleton_b = int(25e6 * (sk['cells'] / (160 * 160)))
    vectors = int(8e6 * math.sqrt(max(nodes, 1) / 640000.))
    atlas_copies = 2 if pipeline == 'full' else 1
    atlas_b = int(atlas_copies * 35e6 * (span / 1600) ** 1.2)
    islands = int(80e6 * (span / 1600))
    if pipeline == 'full':
        islands = int(islands * 1.35)  # detail continuation product
    quick_atlas = bool(quick_render) and pipeline == 'playable'
    if quick_atlas:
        atlas_b = int(atlas_b * QUICK_ATLAS_SHARE)
    total = grids + skeleton_b + vectors + atlas_b + islands
    return dict(bytes=int(total), basis=EXTRAPOLATED, nodes=nodes, pipeline=pipeline, quick_render=quick_atlas,
                breakdown=dict(grids=grids, skeleton=skeleton_b, vectors=vectors, atlas=atlas_b, islands=islands),
                how='grids ≈ 7×float32×nodes; skeleton/atlas/islands extrapolated from 1600 km products; '
                    'quick_render 只缩小 atlas 项（1200 px 概览单图、无附页）')


def chain(size_km, use_gpu, spacing_m=FAST_SPACING_M, pipeline='playable', *, quick_render=False, height_km=None):
    """Per-stage estimate for the web job (seconds as [low, high]) and the memory gate.

    ``height_km`` (keyword only) keeps the old square call signature working; pass it together with
    ``size_km`` as the width to estimate a rectangle from its real width x height grid.

    ``playable`` (default): skeleton + fast + one overview render — enough for player basemap.
    ``full``: adds world-processes, details, second atlas, and optional GPU TD.
    ``quick_render`` (speed + playable only, see quick_overview): the render stage becomes the
    ``--overview-only --width 1200`` quick overview, estimated conservatively at
    QUICK_RENDER_SECONDS (推算, not measured). Nothing else changes — no physical rounds,
    no spacing table, no stage sequence.
    """
    if pipeline not in ('playable', 'full'):
        raise ValueError(f'unsupported pipeline {pipeline!r}')
    quick = bool(quick_render) and pipeline == 'playable'
    sk, fl = skeleton(size_km, height_km), fast_layer(size_km, height_km=height_km, spacing_m=spacing_m)
    spacing_km = fl['spacing_m'] / 1000.0
    disk = disk_product_bytes(size_km, spacing_m, pipeline=pipeline, quick_render=quick, height_km=height_km)
    stages = [dict(stage='skeleton', label='板块骨架 (orogen)', seconds=[sk['seconds']] * 2, basis=sk['basis']),
              dict(stage='fast', label=f'快速世界层 {spacing_km:g} km (CPU)', seconds=[fl['cpu_seconds']] * 2,
                   peak_mb=fl['peak_mb'], basis=fl['basis'], spacing_m=fl['spacing_m'])]
    if pipeline == 'full':
        process_seconds = 180. * (fl['nodes'] / 640000.)
        stages.append(dict(stage='world-processes', label='世界水沙、地质与季节环境 (CPU)',
                           seconds=[process_seconds, process_seconds], basis=EXTRAPOLATED,
                           how='180 seconds at 1600km/2km is an unverified target; linear in node count'))
    if use_gpu and pipeline == 'full':
        td = td_coarse(size_km, 'cuda', height_km=height_km)
        stages.append(dict(stage='td', label='TD 粗模型山脉走向 (GPU)', seconds=td['seconds'], basis=td['basis'], tiles=td['tiles']))
    at = atlas(size_km, height_km=height_km)
    if quick:
        stages.append(dict(stage='render', label='概览成图（1200 px，无附页）', seconds=list(QUICK_RENDER_SECONDS),
                           basis=EXTRAPOLATED, width_px=OVERVIEW_WIDTH_PX, overview_only=True,
                           how='概览 1200 px 单图、无 detail / reserved 页：保守推算，非保证；实测后再校正'))
    else:
        stages.append(dict(stage='render', label='成图', seconds=at['seconds'], basis=at['basis']))
    if pipeline == 'full':
        stages.append(dict(stage='final-render', label='续算版本成图', seconds=at['seconds'], basis=at['basis']))
    total = [sum(s['seconds'][0] for s in stages), sum(s['seconds'][1] for s in stages)]
    return dict(size_km=int(size_km), spacing_m=fl['spacing_m'], pipeline=pipeline, stages=stages, total_seconds=total,
                quick_render=quick,
                peak_mb=world_process_peak_mb(size_km, spacing_m, height_km=height_km),
                disk_bytes=disk['bytes'], disk=disk,
                basis=MEASURED if all(s['basis'] == MEASURED for s in stages) else EXTRAPOLATED,
                td_cpu_reference=td_coarse(size_km, 'cpu', height_km=height_km))


def world_process_peak_mb(size_km, spacing_m=FAST_SPACING_M, *, height_km=None):
    """Conservative author-process recommendation, including history and monthly arrays.

    2563 MiB was observed at 1600 km / 2 km before the final coupling changes. The
    recommendation reserves 3200 MiB there; the final runtime report remains authoritative.
    Soft scheduling may still start below this figure and run slower.
    """
    fl = fast_layer(size_km, height_km=height_km, spacing_m=spacing_m)
    nodes = fl['nodes']
    return max(fl['peak_mb'], 512. + 2688. * nodes / 640000.)


def scale_chain_time(chain_est, time_scale):
    """Return a shallow copy of a chain estimate with stage/total seconds stretched."""
    scale = float(max(time_scale, 1.0))
    if abs(scale - 1.0) < 1e-9:
        return chain_est
    out = dict(chain_est)
    out['stages'] = [dict(s, seconds=[s['seconds'][0] * scale, s['seconds'][1] * scale]) for s in chain_est['stages']]
    out['total_seconds'] = [chain_est['total_seconds'][0] * scale, chain_est['total_seconds'][1] * scale]
    out['time_scale'] = scale
    return out
