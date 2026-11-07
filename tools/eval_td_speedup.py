"""Trade-off metrics for fast/scaled Terragenesis latent runs against the production world-960m window.

CPU only. Reads artifacts/td-world/speedup-test/<tag>/mosaic_960m.npy (210x210 cells of 960 m), compares it with the
same window of artifacts/td-world/world-960m/elevation_m.npy after averaging both to 1.92 km (2x2 mean), writes
eval/<tag>.json and a side-by-side picture eval/<tag>.png. Never writes outside speedup-test.

Metrics (targets from the plan): sea/land agreement >=98 %, coast offset median <=2 km, mountain (local relief >=900 m)
IoU >=85 %, main ridge direction error <=15 deg, land elevation quantile deviation <=10 %, basin layout agreement.
"""
from __future__ import annotations
import argparse
import heapq
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scipy import ndimage as ndi

OUT = ROOT / 'artifacts/td-world/speedup-test'
WORLD = ROOT / 'artifacts/td-world/world-960m'
CELL_KM = 1.92
RELIEF_WINDOW = 5          # 5 x 1.92 km ~ 9.6 km neighbourhood
RELIEF_THRESHOLD_M = 900.0
QUANTILES = (.1, .25, .5, .75, .9, .99)


def mean_pool(a, f=2):
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def coast_cells(land):
    sea = ~land
    near_sea = ndi.binary_dilation(sea, structure=ndi.generate_binary_structure(2, 1))
    return land & near_sea


def coast_offset_km(a_land, b_land):
    """Median distance from coast cells of a to the nearest coast cell of b, both directions, km."""
    ca, cb = coast_cells(a_land), coast_cells(b_land)
    if not ca.any() or not cb.any():
        return dict(median_km=None, p90_km=None)
    db = ndi.distance_transform_edt(~cb) * CELL_KM
    da = ndi.distance_transform_edt(~ca) * CELL_KM
    d = np.concatenate([db[ca], da[cb]])
    return dict(median_km=float(np.median(d)), p90_km=float(np.quantile(d, .9)))


def relief_mask(z):
    size = RELIEF_WINDOW
    rel = ndi.maximum_filter(z, size=size) - ndi.minimum_filter(z, size=size)
    return (rel >= RELIEF_THRESHOLD_M) & (z >= 0), rel


def ridge_axis(z, mask):
    """Dominant ridge direction in degrees [0,180) (angle of the ridge line, x to the right, z down) of masked cells."""
    s = ndi.gaussian_filter(z, 1.0)
    gz, gx = np.gradient(s)
    m = mask
    if m.sum() < 30:
        return None
    jxx, jzz, jxz = (gx[m] ** 2).sum(), (gz[m] ** 2).sum(), (gx[m] * gz[m]).sum()
    grad_angle = 0.5 * np.degrees(np.arctan2(2 * jxz, jxx - jzz))
    return float((grad_angle + 90.0) % 180.0)


def axis_diff(a, b):
    if a is None or b is None:
        return None
    d = abs(a - b) % 180.0
    return float(min(d, 180.0 - d))


def tile_ridge_diff(z_a, m_a, z_b, m_b, tile=15):
    diffs = []
    for i in range(0, z_a.shape[0] - tile + 1, tile):
        for j in range(0, z_a.shape[1] - tile + 1, tile):
            sl = (slice(i, i + tile), slice(j, j + tile))
            if m_a[sl].sum() < 20 or m_b[sl].sum() < 20:
                continue
            d = axis_diff(ridge_axis(z_a[sl], m_a[sl]), ridge_axis(z_b[sl], m_b[sl]))
            if d is not None:
                diffs.append(d)
    if not diffs:
        return dict(tiles=0, median_deg=None, p90_deg=None)
    return dict(tiles=len(diffs), median_deg=float(np.median(diffs)), p90_deg=float(np.quantile(diffs, .9)))


def basins(z):
    """Priority-flood D8 basin labelling: outlets are sea cells (z<0) and window border. Returns outlet index per cell
    (flat index of the outlet cell) so that two grids can be compared outlet by outlet; cells z<0 are their own outlet."""
    h, w = z.shape
    root = -np.ones((h, w), dtype=np.int64)
    done = np.zeros((h, w), dtype=bool)
    heap = []
    for i in range(h):
        for j in range(w):
            if z[i, j] < 0 or i in (0, h - 1) or j in (0, w - 1):
                root[i, j] = i * w + j
                done[i, j] = True
                heapq.heappush(heap, (float(z[i, j]), i, j))
    nbr = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    while heap:
        level, i, j = heapq.heappop(heap)
        for di, dj in nbr:
            a, b = i + di, j + dj
            if 0 <= a < h and 0 <= b < w and not done[a, b]:
                done[a, b] = True
                root[a, b] = root[i, j]
                heapq.heappush(heap, (max(float(z[a, b]), level), a, b))
    return root


def basin_agreement(z_a, z_b, top=8, near_cells=3):
    """Compare river basin layout. Land cells drain (priority flood) to a root outlet; roots are coast/border cells.
    Returns share of land cells whose outlet lies within near_cells of the other grid's outlet for the same cell, and the
    mean best IoU of the top basins of b (reference) against basins of a."""
    ra, rb = basins(z_a), basins(z_b)
    land = (z_a >= 0) & (z_b >= 0)
    w = z_a.shape[1]
    ya, xa = np.divmod(ra, w)
    yb, xb = np.divmod(rb, w)
    dist = np.hypot(ya - yb, xa - xb)
    near = float((dist[land] <= near_cells).mean()) if land.any() else None
    # basin IoU for the largest reference basins (land cells only)
    land_b = z_b >= 0
    ids, counts = np.unique(rb[land_b], return_counts=True)
    order = np.argsort(-counts)[:top]
    ious = []
    weights = []
    land_a = z_a >= 0
    for k in order:
        mb = land_b & (rb == ids[k])
        # candidate basins overlapping this one
        cand_ids, cand_counts = np.unique(ra[mb & land_a], return_counts=True)
        best = 0.0
        for cid in cand_ids:
            ma = land_a & (ra == cid)
            inter = float((ma & mb).sum())
            union = float((ma | mb).sum())
            best = max(best, inter / union if union else 0.0)
        ious.append(best)
        weights.append(float(counts[k]))
    wiou = float(np.average(ious, weights=weights)) if ious else None
    return dict(outlet_near_share=near, near_cells=near_cells, top_basin_iou_weighted=wiou,
        top_basin_ious=[round(v, 3) for v in ious], top_basin_cells=[int(counts[k]) for k in order])


def quantile_deviation(z_a, z_b):
    la, lb = z_a[z_a >= 0], z_b[z_b >= 0]
    if la.size == 0 or lb.size == 0:
        return dict(max_rel_dev=None)
    qa, qb = np.quantile(la, QUANTILES), np.quantile(lb, QUANTILES)
    rel = (qa - qb) / np.maximum(np.abs(qb), 1.0)
    p = np.quantile(la, [.95, .99]), np.quantile(lb, [.95, .99])
    peak = dict(p95_cand_m=float(p[0][0]), p95_ref_m=float(p[1][0]), p95_rel=float((p[0][0] - p[1][0]) / p[1][0]),
                p99_cand_m=float(p[0][1]), p99_ref_m=float(p[1][1]), p99_rel=float((p[0][1] - p[1][1]) / p[1][1]),
                max_cand_m=float(la.max()), max_ref_m=float(lb.max()), max_rel=float((la.max() - lb.max()) / lb.max()))
    return dict(quantiles=list(QUANTILES), candidate_m=[float(v) for v in qa], reference_m=[float(v) for v in qb],
                rel_dev=[float(v) for v in rel], max_rel_dev=float(np.abs(rel).max()),
                p99_rel_dev=float(rel[-1]), peaks=peak)


def evaluate(cand, ref):
    """cand, ref: 1.92 km grids of equal shape."""
    land_c, land_r = cand >= 0, ref >= 0
    mount_c, rel_c = relief_mask(cand)
    mount_r, rel_r = relief_mask(ref)
    inter, union = float((mount_c & mount_r).sum()), float((mount_c | mount_r).sum())
    ridge_global = axis_diff(ridge_axis(cand, mount_c), ridge_axis(ref, mount_r))
    result = dict(
        sea_land_agreement=float((land_c == land_r).mean()),
        coast=coast_offset_km(land_c, land_r),
        mountain_iou=inter / union if union else None,
        mountain_cells=dict(candidate=int(mount_c.sum()), reference=int(mount_r.sum())),
        ridge_direction_global_deg=ridge_global,
        ridge_direction_tiles=tile_ridge_diff(cand, mount_c, ref, mount_r),
        elevation=quantile_deviation(cand, ref),
        basins=basin_agreement(cand, ref),
        mae_m=float(np.abs(cand - ref).mean()),
    )
    c, r = result['coast']['median_km'], result['sea_land_agreement']
    result['pass'] = dict(
        sea_land=bool(r >= .98),
        coast=bool(c is not None and c <= 2.0),
        mountain=bool(result['mountain_iou'] is not None and result['mountain_iou'] >= .85),
        ridge=bool(ridge_global is not None and ridge_global <= 15.0),
        elevation=bool(result['elevation']['max_rel_dev'] is not None and result['elevation']['max_rel_dev'] <= .10),
    )
    result['pass']['all'] = all(result['pass'].values())
    return result


def reference_window(region, factor=2):
    z0, z1, x0, x1 = region
    e = np.load(WORLD / 'elevation_m.npy', mmap_mode='r')
    return mean_pool(np.asarray(e[z0:z1, x0:x1], dtype=np.float64), factor)


def picture(path, ref, cand, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    fig, ax = plt.subplots(1, 4, figsize=(20, 5.4))
    vmin, vmax = min(ref.min(), cand.min()), max(ref.max(), cand.max())
    ls = LightSource(azdeg=315, altdeg=40)
    for a, z, name in ((ax[0], ref, 'world-960m reference'), (ax[1], cand, title)):
        rgb = ls.shade(z, cmap=plt.get_cmap('terrain'), vmin=vmin, vmax=vmax, blend_mode='overlay', vert_exag=0.02, dx=1920, dy=1920)
        a.imshow(rgb)
        a.contour(z, levels=[0], colors='k', linewidths=.6)
        a.set_title(name)
    d = cand - ref
    lim = max(200.0, float(np.quantile(np.abs(d), .98)))
    im = ax[2].imshow(d, cmap='RdBu_r', vmin=-lim, vmax=lim)
    ax[2].set_title('candidate - reference (m)')
    fig.colorbar(im, ax=ax[2], fraction=.046)
    ax[3].imshow((cand >= 0).astype(int) - (ref >= 0).astype(int), cmap='bwr', vmin=-1, vmax=1)
    ax[3].contour(ref, levels=[0], colors='k', linewidths=.5)
    ax[3].set_title('land mismatch (red = extra land)')
    for a in ax:
        a.set_xticks([])
        a.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=70)
    plt.close(fig)


def candidate_scale(tag):
    f = OUT / tag / 'summary.json'
    if f.exists():
        return int(json.loads(f.read_text(encoding='utf-8')).get('scale', 1))
    return 1


def to_common_grid(mosaic, k, factor):
    """Bring a candidate of spacing 960*k m to the factor*960 m comparison grid (pool when finer, linear zoom when coarser)."""
    if k == 1:
        return mean_pool(mosaic.astype(np.float64), factor)
    if k == factor:
        return mosaic.astype(np.float64)
    if k < factor:
        return mean_pool(mosaic.astype(np.float64), factor // k)
    return ndi.zoom(mosaic.astype(np.float64), k / factor, order=1, mode='nearest')


def load_candidate(tag):
    m = OUT / tag / 'mosaic_960m.npy'
    if not m.exists():
        raise FileNotFoundError(m)
    return np.load(m)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('tags', nargs='*', help='run tags; default every directory with a mosaic_960m.npy')
    p.add_argument('--no-picture', action='store_true')
    p.add_argument('--factor', type=int, default=2, help='pooling factor for the comparison grid (2 = 1.92 km)')
    a = p.parse_args(argv)
    info = json.loads((OUT / 'region.json').read_text(encoding='utf-8'))
    ref = reference_window(info['region'], a.factor)
    tags = a.tags or sorted(d.name for d in OUT.iterdir() if (d / 'mosaic_960m.npy').exists())
    (OUT / 'eval').mkdir(exist_ok=True)
    table = {}
    for tag in tags:
        mosaic = load_candidate(tag)
        k = candidate_scale(tag)
        if mosaic.shape != tuple(np.array(ref.shape) * a.factor // k):
            print('SKIP shape mismatch', tag, mosaic.shape, flush=True)
            continue
        if not np.isfinite(mosaic).all():
            print('SKIP non-finite', tag, flush=True)
            continue
        cand = to_common_grid(mosaic, k, a.factor)
        ref_t = ref
        if cand.shape != ref.shape:
            if cand.shape[0] <= ref.shape[0] and cand.shape[1] <= ref.shape[1] and ref.shape[0] - cand.shape[0] < k and ref.shape[1] - cand.shape[1] < k:
                ref_t = ref[:cand.shape[0], :cand.shape[1]]   # k does not divide the window: compare the covered part
            else:
                print('SKIP grid mismatch', tag, cand.shape, ref.shape, flush=True)
                continue
        res = evaluate(cand, ref_t)
        (OUT / 'eval' / (tag + '.json')).write_text(json.dumps(res, indent=1), encoding='utf-8')
        if not a.no_picture:
            picture(OUT / 'eval' / (tag + '.png'), ref_t, cand, tag)
        table[tag] = res
        print('EVAL %s sea/land %.4f coast_med %.2f km mount_iou %.3f ridge %.1f deg qdev %.3f basins_near %.3f pass=%s' % (
            tag, res['sea_land_agreement'], res['coast']['median_km'] or -1, res['mountain_iou'] or -1,
            res['ridge_direction_global_deg'] if res['ridge_direction_global_deg'] is not None else -1,
            res['elevation']['max_rel_dev'] or -1, res['basins']['outlet_near_share'] or -1, res['pass']['all']), flush=True)
    (OUT / 'eval' / 'summary.json').write_text(json.dumps(table, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
