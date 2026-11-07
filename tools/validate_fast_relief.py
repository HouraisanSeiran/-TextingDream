"""Mountain-trend / coast validation of a fast 2 km world layer against the TD world layer (world-960m-v6) averaged to 2 km.

  <python with numpy scipy matplotlib> tools/validate_fast_relief.py --fast <product dir> --td artifacts/td-world/world-960m-v6 --out <dir>
Writes metrics.json and side-by-side PNGs into --out. Nothing is written into the products.

Definitions (written into metrics.json as well):
* TD at 2 km: elevation and ocean mask low-passed (gaussian sigma 0.94 TD cells) then linearly resampled to the 2 km cell centres.
* sea/land agreement: fraction of cells with equal land flag.
* coastline deviation: for each coast cell (land cell with an ocean 4-neighbour) of one layer, distance to the nearest coast cell
  of the other layer (euclidean distance transform); median over both directions (km).
* mountain extent: land and gaussian(elevation, 2.5 cells = 5 km) > 1500 m; IoU(fast, TD). Local-relief variant
  (7x7 max-min of 1.5-sigma smoothed elevation > 700 m, land) is reported too.
* main-ridge direction: gradient structure tensor of gaussian(elevation, 2 cells) weighted by the mountain mask, accumulated
  in 100 km blocks; ridge direction = perpendicular to the dominant gradient axis; deviation = axial angle difference
  (0..90 deg) over blocks where both layers have >= 25 % mountain cover. Also reported: per mountain component PCA axis deviation
  for the 6 largest common components.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import ndimage as nd

TD_SIGMA = 0.94
MOUNT_T = 1500.0
MOUNT_SMOOTH = 2.5
RELIEF_T = 700.0


def td_to_2km(td, shape, first, spacing):
    m = json.loads((Path(td) / 'manifest.json').read_text(encoding='utf-8'))
    g = m['grid']
    tsp = float(g['spacing_m']); tf = g['first_sample_xz_m']
    el = np.load(Path(td) / 'elevation_m.npy', mmap_mode='r')
    st = np.load(Path(td) / 'status.npy', mmap_mode='r')
    oc = (np.asarray(st) == 3).astype(np.float32)
    el = nd.gaussian_filter(np.asarray(el, np.float32), TD_SIGMA)
    oc = nd.gaussian_filter(oc, TD_SIGMA)
    tz = ((first[1] + np.arange(shape[0]) * spacing) - tf[1]) / tsp
    tx = ((first[0] + np.arange(shape[1]) * spacing) - tf[0]) / tsp
    zz, xx = np.meshgrid(tz, tx, indexing='ij')
    e2 = nd.map_coordinates(el, [zz, xx], order=1, mode='nearest').astype(np.float32)
    o2 = nd.map_coordinates(oc, [zz, xx], order=1, mode='nearest') > 0.5
    return e2, o2


def load_fast(fast):
    m = json.loads((Path(fast) / 'manifest.json').read_text(encoding='utf-8'))
    el = np.load(Path(fast) / 'elevation_m.npy')
    st = np.load(Path(fast) / 'status.npy')
    return m, el, st == 3


def coast_cells(ocean):
    land = ~ocean
    n = np.zeros_like(ocean)
    n[1:] |= ocean[:-1]; n[:-1] |= ocean[1:]; n[:, 1:] |= ocean[:, :-1]; n[:, :-1] |= ocean[:, 1:]
    return land & n


def coast_deviation(oa, ob, spacing):
    ca, cb = coast_cells(oa), coast_cells(ob)
    da = nd.distance_transform_edt(~cb)[ca] * spacing / 1000.0
    db = nd.distance_transform_edt(~ca)[cb] * spacing / 1000.0
    both = np.concatenate([da, db])
    return dict(median_km=float(np.median(both)), mean_km=float(both.mean()), p90_km=float(np.percentile(both, 90)),
                fast_to_td_median_km=float(np.median(da)), td_to_fast_median_km=float(np.median(db)))


def mountain_mask(el, ocean):
    return (~ocean) & (nd.gaussian_filter(el.astype(np.float32), MOUNT_SMOOTH) > MOUNT_T)


def relief_mask(el, ocean):
    s = nd.gaussian_filter(el.astype(np.float32), 1.5)
    r = nd.maximum_filter(s, 7) - nd.minimum_filter(s, 7)
    return (~ocean) & (r > RELIEF_T)


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else float('nan')


def block_orientation(el, mask, block):
    s = nd.gaussian_filter(el.astype(np.float32), 2.0)
    gz, gx = np.gradient(s)
    w = mask.astype(np.float32)
    nz, nx = (el.shape[0] // block) * block, (el.shape[1] // block) * block
    def bsum(a):
        return a[:nz, :nx].reshape(nz // block, block, nx // block, block).sum(axis=(1, 3))
    jxx, jzz, jxz, cov = bsum(w * gx * gx), bsum(w * gz * gz), bsum(w * gx * gz), bsum(w) / block ** 2
    th_grad = 0.5 * np.arctan2(2 * jxz, jxx - jzz)          # dominant gradient axis (x east, z south)
    ridge = th_grad + np.pi / 2
    return np.mod(ridge, np.pi), cov


def axial_diff_deg(a, b):
    d = np.abs(a - b) % np.pi
    return np.degrees(np.minimum(d, np.pi - d))


def pca_axis(mask):
    zz, xx = np.nonzero(mask)
    c = np.cov(np.vstack([xx, zz]).astype(np.float64))
    w, v = np.linalg.eigh(c)
    major = v[:, 1]
    return float(np.mod(np.arctan2(major[1], major[0]), np.pi)), float(np.sqrt(w[1] / max(w[0], 1e-9)))


def evaluate(fast_el, fast_oc, td_el, td_oc, spacing_m, block_km=100.0):
    r = {}
    r['land_fraction'] = dict(fast=float((~fast_oc).mean()), td=float((~td_oc).mean()))
    r['sea_land_agreement'] = float((fast_oc == td_oc).mean())
    r['coast_deviation'] = coast_deviation(fast_oc, td_oc, spacing_m)
    mf, mt = mountain_mask(fast_el, fast_oc), mountain_mask(td_el, td_oc)
    r['mountain'] = dict(definition='land and gaussian(elevation, 2.5 cells) > %g m' % MOUNT_T, iou=iou(mf, mt),
                         fraction_of_land=dict(fast=float(mf.sum() / max((~fast_oc).sum(), 1)), td=float(mt.sum() / max((~td_oc).sum(), 1))))
    rf, rt = relief_mask(fast_el, fast_oc), relief_mask(td_el, td_oc)
    r['relief_variant'] = dict(definition='land and 7x7 max-min of 1.5-sigma smoothed elevation > %g m' % RELIEF_T, iou=iou(rf, rt),
                               fraction_of_land=dict(fast=float(rf.sum() / max((~fast_oc).sum(), 1)), td=float(rt.sum() / max((~td_oc).sum(), 1))))
    block = max(int(round(block_km * 1000.0 / spacing_m)), 4)
    of, cf = block_orientation(fast_el, mf, block)
    ot, ct = block_orientation(td_el, mt, block)
    sel = (cf >= 0.25) & (ct >= 0.25)
    d = axial_diff_deg(of, ot)[sel]
    r['ridge_direction'] = dict(definition='gradient structure tensor in %g km blocks, blocks with >=25%% mountain cover in both' % block_km,
                                blocks=int(sel.sum()), median_deg=float(np.median(d)) if d.size else float('nan'),
                                mean_deg=float(d.mean()) if d.size else float('nan'),
                                p90_deg=float(np.percentile(d, 90)) if d.size else float('nan'),
                                weighted_mean_deg=float(np.average(d, weights=np.minimum(cf, ct)[sel])) if d.size else float('nan'))
    lab, n = nd.label(mt & mf)
    comps = []
    if n:
        sizes = np.bincount(lab.ravel())[1:]
        for k in np.argsort(sizes)[::-1][:6]:
            m_ = lab == (k + 1)
            if sizes[k] < 200:
                continue
            af, ef = pca_axis(mf & nd.binary_dilation(m_, iterations=3))
            at, et = pca_axis(mt & nd.binary_dilation(m_, iterations=3))
            comps.append(dict(cells=int(sizes[k]), fast_axis_deg=float(np.degrees(af)), td_axis_deg=float(np.degrees(at)),
                              diff_deg=float(axial_diff_deg(np.array(af), np.array(at))), elongation=(round(ef, 2), round(et, 2))))
    r['component_axes'] = comps
    r['elevation_correlation_land'] = float(np.corrcoef(fast_el[~fast_oc & ~td_oc], td_el[~fast_oc & ~td_oc])[0, 1]) if (~fast_oc & ~td_oc).any() else float('nan')
    r['targets'] = dict(sea_land='info', mountain_iou_min=0.80, ridge_direction_max_deg=15.0)
    r['pass'] = dict(mountain_iou=bool(r['mountain']['iou'] >= 0.80), ridge_direction=bool(r['ridge_direction']['median_deg'] <= 15.0))
    return r, mf, mt


def hillshade(el, spacing, az=315.0, alt=40.0, ve=6.0):
    gz, gx = np.gradient(el.astype(np.float32) * ve, spacing)
    slope = np.arctan(np.hypot(gx, gz)); aspect = np.arctan2(-gx, gz)
    a, h = np.radians(360 - az + 90), np.radians(alt)
    return np.clip(np.sin(h) * np.cos(slope) + np.cos(h) * np.sin(slope) * np.cos(a - aspect), 0, 1)


def render(fast_el, fast_oc, td_el, td_oc, mf, mt, path, spacing):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('h', [(0, '#3c6e3a'), (0.15, '#9bb061'), (0.35, '#d8c98a'), (0.6, '#a07a4a'), (0.85, '#d9d4cc'), (1, '#ffffff')])
    fig, axs = plt.subplots(2, 2, figsize=(16, 13.4), dpi=110)
    for ax, el, oc, title in ((axs[0, 0], fast_el, fast_oc, 'fast 2 km'), (axs[0, 1], td_el, td_oc, 'TD world-960m-v6 (to 2 km)')):
        v = np.clip(el, 0, 5000) / 5000.0
        rgb = cmap(v)[..., :3]
        hs = hillshade(el, spacing)[..., None]
        rgb = np.clip(rgb * (0.55 + 0.6 * hs), 0, 1)
        rgb[oc] = np.array([0.22, 0.38, 0.55])
        ax.imshow(rgb, interpolation='nearest'); ax.set_title(title); ax.axis('off')
    ov = np.zeros(mf.shape + (3,), np.float32)
    ov[mf & mt] = (0.9, 0.9, 0.9); ov[mf & ~mt] = (0.9, 0.2, 0.2); ov[~mf & mt] = (0.2, 0.3, 0.95)
    axs[1, 0].imshow(ov, interpolation='nearest'); axs[1, 0].set_title('mountain masks: grey both, red fast only, blue TD only'); axs[1, 0].axis('off')
    cv = np.zeros(fast_oc.shape + (3,), np.float32)
    cv[(~fast_oc) & (~td_oc)] = (0.8, 0.8, 0.8); cv[(~fast_oc) & td_oc] = (0.9, 0.2, 0.2); cv[fast_oc & (~td_oc)] = (0.2, 0.3, 0.95)
    axs[1, 1].imshow(cv, interpolation='nearest'); axs[1, 1].set_title('land: grey both, red fast only, blue TD only'); axs[1, 1].axis('off')
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--fast', required=True)
    ap.add_argument('--td', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    m, fe, fo = load_fast(a.fast)
    g = m['grid']
    shape = tuple(g['shape_zx']); first = g['first_sample_xz_m']; sp = float(g['spacing_m'])
    te, to = td_to_2km(a.td, shape, first, sp)
    res, mf, mt = evaluate(fe, fo, te, to, sp)
    res['fast_identity'] = m['identity']
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / 'metrics.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    render(fe, fo, te, to, mf, mt, out / 'side-by-side.png', sp)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
