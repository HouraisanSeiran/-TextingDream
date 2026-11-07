"""CPU simulation of 'TD only where needed': mountains + narrow coast band get TD, flat interior keeps the skeleton.

Takes an existing full-TD mosaic (default fast-autocast-onestep-b8-k120), replaces cells outside the TD mask with the
world skeleton (960 m, optionally smoothed), and scores the result with the same metrics as eval_td_speedup. Also reports the
TD coverage share for the test window and for the whole world (same rule, 40 km coast buffer weight), and plain-only basin
agreement. Writes speedup-test/hybrid/<name>.json|png. CPU only; never touches world-pages / world-960m.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from scipy import ndimage as ndi
import eval_td_speedup as ev

W = ROOT / 'artifacts/td-world'
OUT = ev.OUT / 'hybrid'


def td_mask(sk, relief_m, relief_win, coast_km, block, dilate_cells):
    """Boolean per-cell TD mask on a skeleton grid (960 m cells), rounded up to block x block tiles."""
    rel = ndi.maximum_filter(sk, size=relief_win) - ndi.minimum_filter(sk, size=relief_win)
    mount = (rel >= relief_m) & (sk >= 0)
    if dilate_cells:
        mount = ndi.binary_dilation(mount, iterations=dilate_cells)
    sea = sk < 0
    dist_sea = ndi.distance_transform_edt(~sea) * 0.96            # km to sea (land cells)
    dist_land = ndi.distance_transform_edt(sea) * 0.96            # km to land (sea cells)
    coast = (~sea & (dist_sea <= coast_km)) | (sea & (dist_land <= coast_km))
    m = mount | coast
    if block > 1:
        h, w = m.shape
        hp, wp = -(-h // block) * block, -(-w // block) * block
        pad = np.zeros((hp, wp), bool)
        pad[:h, :w] = m
        t = pad.reshape(hp // block, block, wp // block, block).any(axis=(1, 3))
        m = np.kron(t, np.ones((block, block), bool))[:h, :w]
    return m


def world_share(relief_m, relief_win, coast_km, block, dilate_cells, buffer_m=40000):
    sk = np.load(W / 'world-skeleton-960m.npy')
    dist = ndi.distance_transform_edt(sk < 0) * 960
    t = np.clip((dist - buffer_m / 2) / (buffer_m / 2), 0, 1)
    covered = (1 - t * t * (3 - 2 * t)) > 0
    m = td_mask(sk, relief_m, relief_win, coast_km, block, dilate_cells) & covered
    return float(m.sum() / covered.sum()), int(covered.sum()), int(m.sum())


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--tag', default='fast-autocast-onestep-b8-k120')
    p.add_argument('--relief', type=float, nargs='+', default=[300, 500, 900])
    p.add_argument('--relief-win', type=int, default=5)
    p.add_argument('--coast-km', type=float, nargs='+', default=[20])
    p.add_argument('--block', type=int, nargs='+', default=[30])
    p.add_argument('--dilate', type=int, default=2)
    p.add_argument('--smooth', type=float, default=0.0, help='gaussian sigma (cells) applied to the skeleton fill')
    p.add_argument('--no-picture', action='store_true')
    a = p.parse_args(argv)
    OUT.mkdir(exist_ok=True)
    info = json.loads((ev.OUT / 'region.json').read_text(encoding='utf-8'))
    z0, z1, x0, x1 = info['region']
    sk_all = np.load(W / 'world-skeleton-960m.npy')
    sk = sk_all[z0:z1, x0:x1].astype(np.float64)
    td = np.load(ev.OUT / a.tag / 'mosaic_960m.npy').astype(np.float64)
    ref = ev.reference_window(info['region'], 2)
    fill = ndi.gaussian_filter(sk, a.smooth) if a.smooth else sk
    rows = {}
    for rl in a.relief:
        for ck in a.coast_km:
            for b in a.block:
                # mask computed on the window with 'wrap' context from the surrounding world so edges are not distorted
                pad = 40
                zs, ze, xs, xe = max(z0 - pad, 0), min(z1 + pad, sk_all.shape[0]), max(x0 - pad, 0), min(x1 + pad, sk_all.shape[1])
                big = td_mask(sk_all[zs:ze, xs:xe].astype(np.float64), rl, a.relief_win, ck, b, a.dilate)
                m = big[z0 - zs:z1 - zs, x0 - xs:x1 - xs]
                hybrid = np.where(m, td, fill)
                cand = ev.mean_pool(hybrid, 2)
                res = ev.evaluate(cand, ref)
                # plain-only basin check: cells outside the TD mask (pooled)
                mp = ev.mean_pool(m.astype(float), 2) < .5
                ra, rb = ev.basins(cand), ev.basins(ref)
                land = (cand >= 0) & (ref >= 0) & mp
                ya, xa = np.divmod(ra, cand.shape[1])
                yb, xb = np.divmod(rb, cand.shape[1])
                near = float((np.hypot(ya - yb, xa - xb)[land] <= 3).mean()) if land.any() else None
                share_win = float(m.mean())
                share_world, cov_w, td_w = world_share(rl, a.relief_win, ck, b, a.dilate)
                name = 'relief%d-coast%d-blk%d' % (rl, ck, b) + ('-sm%g' % a.smooth if a.smooth else '')
                res['plain'] = dict(cells=int(land.sum()), outlet_near_share=near, share_of_window_plain=float(mp.mean()))
                res['coverage'] = dict(window_td_share=share_win, world_td_share_40km=share_world,
                                       world_covered_cells_40km=cov_w, world_td_cells=td_w)
                (OUT / (name + '.json')).write_text(json.dumps(res, indent=1), encoding='utf-8')
                if not a.no_picture:
                    ev.picture(OUT / (name + '.png'), ref, cand, name)
                rows[name] = res
                pk = res['elevation'].get('peaks', {})
                print('HYB %s td_window %.2f td_world %.2f sea/land %.4f coast %.2f mount %.3f ridge %.1f qdev %.3f basins %.3f plain_basin %s p99 %.3f max %.3f pass=%s' % (
                    name, share_win, share_world, res['sea_land_agreement'], res['coast']['median_km'] or 0, res['mountain_iou'] or 0,
                    res['ridge_direction_global_deg'] or 0, res['elevation']['max_rel_dev'], res['basins']['outlet_near_share'],
                    'n/a' if near is None else '%.3f' % near, pk.get('p99_rel', 0), pk.get('max_rel', 0), res['pass']['all']), flush=True)
    (OUT / 'summary.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
