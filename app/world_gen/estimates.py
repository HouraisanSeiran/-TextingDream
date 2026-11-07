"""Time / memory estimates for the world-generation chain (skeleton -> fast 2 km world layer -> TD coarse ridges -> atlas).

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


def _power(points, x):
    (x0, y0), (x1, y1) = points
    k = math.log(y1 / y0) / math.log(x1 / x0)
    return y0 * (x / x0) ** k


def skeleton_cell_km(size_km):
    """Orogen skeletons rasterize at 2 km, so the cell must be a whole multiple of 2 km (config default 25 km above 6000 km is not)."""
    return 10 if size_km <= 2000 else 20


def fast_layer(width_km, height_km=None):
    """2 km fast world layer: nodes, CPU seconds, peak memory. Exact at the two measured sizes, power/linear fit between/beyond."""
    height_km = width_km if height_km is None else height_km
    nodes = int(round(width_km * 1000 / FAST_SPACING_M)) * int(round(height_km * 1000 / FAST_SPACING_M))
    (n0, t0, m0), (n1, t1, m1) = _FAST_POINTS
    hit = next((p for p in _FAST_POINTS if p[0] == nodes), None)
    if hit:
        seconds, mb, basis = hit[1], hit[2], MEASURED
    else:
        seconds = _power(((n0, t0), (n1, t1)), nodes)
        mb = m0 + (m1 - m0) / (n1 - n0) * (nodes - n0)          # linear in nodes (~324 B/node + ~170 MB)
        basis = EXTRAPOLATED
    return dict(spacing_m=FAST_SPACING_M, nodes=nodes, cpu_seconds=float(seconds), peak_mb=float(max(mb, 200.0)), basis=basis,
                how='time ~ nodes^1.18 and memory linear in nodes, fitted to the 1600 km (66 s / 367 MB) and 5000 km (~16 min / ~2.1 GB) runs')


def skeleton(size_km):
    cell = skeleton_cell_km(size_km)
    cells = int(round(size_km / cell)) ** 2
    hit = next((p for p in _SKELETON_POINTS if p[0] == cells), None)
    seconds = hit[1] if hit else _power(_SKELETON_POINTS, cells)
    return dict(cell_km=cell, cells=cells, seconds=float(seconds), basis=MEASURED if hit else EXTRAPOLATED)


def td_coarse(size_km, device):
    lo_t, hi_t = TD_TILES.get(int(size_km), TD_TILES[min(TD_TILES, key=lambda s: abs(s - size_km))])
    per = TD_GPU_S_PER_TILE if device == 'cuda' else TD_CPU_S_PER_TILE
    lo, hi = lo_t * per[0] + TD_LOAD_S[0], hi_t * per[1] + TD_LOAD_S[1]
    out = dict(device=device, tiles=[lo_t, hi_t], seconds=[float(lo), float(hi)], basis=EXTRAPOLATED,
               how='tiles (plan-only, skip deep ocean > 120 km, 15 steps) x seconds per tile + model load; GPU s/tile from '
                   'artifacts/td-coarse-opt/estimate.json (not benchmarked)')
    if device != 'cuda' and int(size_km) == 5000:
        out['seconds'] = [14 * 60.0, 14 * 60.0]
    if device == 'cuda':
        out['gpu_free_mib_required'] = TD_GPU_MIN_FREE_MIB
    return out


def atlas(size_km):
    if int(size_km) == 1600:
        return dict(seconds=[140.0, 140.0], basis=MEASURED)
    if int(size_km) <= 5000:
        return dict(seconds=[180.0, 480.0], basis=EXTRAPOLATED)
    return dict(seconds=[600.0, 1800.0], basis=EXTRAPOLATED)


def chain(size_km, use_gpu):
    """Per-stage estimate for the web job (seconds as [low, high]) and the memory gate."""
    sk, fl = skeleton(size_km), fast_layer(size_km)
    stages = [dict(stage='skeleton', label='板块骨架 (orogen)', seconds=[sk['seconds']] * 2, basis=sk['basis']),
              dict(stage='fast', label='快速世界层 2 km (CPU)', seconds=[fl['cpu_seconds']] * 2, peak_mb=fl['peak_mb'], basis=fl['basis'])]
    process_seconds = 180. * (fl['nodes'] / 640000.)
    stages.append(dict(stage='world-processes', label='世界水沙、地质与季节环境 (CPU)',
                       seconds=[process_seconds, process_seconds], basis=EXTRAPOLATED,
                       how='180 seconds at 1600km is an unverified target for current final implementation; fixed precision, linear cell-count budget; TD preparation and existing stages excluded'))
    if use_gpu:
        td = td_coarse(size_km, 'cuda')
        stages.append(dict(stage='td', label='TD 粗模型山脉走向 (GPU)', seconds=td['seconds'], basis=td['basis'], tiles=td['tiles']))
    at = atlas(size_km)
    stages.append(dict(stage='render', label='成图', seconds=at['seconds'], basis=at['basis']))
    stages.append(dict(stage='final-render', label='续算版本成图', seconds=at['seconds'], basis=at['basis']))
    total = [sum(s['seconds'][0] for s in stages), sum(s['seconds'][1] for s in stages)]
    return dict(size_km=int(size_km), stages=stages, total_seconds=total, peak_mb=world_process_peak_mb(size_km),
                basis=MEASURED if all(s['basis'] == MEASURED for s in stages) else EXTRAPOLATED,
                td_cpu_reference=td_coarse(size_km, 'cpu'))


def world_process_peak_mb(size_km):
    """Conservative author-process gate, including history and monthly arrays.

    2563 MiB was observed at 1600 km before the final coupling changes. The
    gate reserves 3200 MiB there; the final runtime report remains authoritative.
    """
    nodes = fast_layer(size_km)['nodes']
    return max(fast_layer(size_km)['peak_mb'], 512. + 2688. * nodes / 640000.)
