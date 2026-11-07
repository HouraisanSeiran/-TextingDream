"""Compare the TD coarse ridge field with the fast 2 km world layer on the TD lattice (7.68 km point samples).

  python app/world_gen/td_fast_compare.py --td <td-coarse-ridges dir> --fast <fast-world dir> [--json out.json]

The fast elevation is Gaussian-smoothed (sigma = half a TD cell) and sampled bilinearly at the TD lattice points; then the same
mountain mask (1000 m on smoothed elevation) and structure-tensor ridge axis as td_coarse are computed and compared over TD cells
that were computed and lie inside the fast domain. Numpy + scipy only (runs with the web interpreter, no torch).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.world_gen import td_coarse as tc  # noqa: E402  (pure helpers only; torch is imported lazily there)


def compare(td_dir, fast_dir, threshold_m=1000.0, coherence_min=0.3):
    td_dir, fast_dir = Path(td_dir), Path(fast_dir)
    tm = json.loads((td_dir / 'manifest.json').read_text(encoding='utf-8'))
    fm = json.loads((fast_dir / 'manifest.json').read_text(encoding='utf-8'))
    te = np.load(td_dir / 'elevation_m.npy').astype(np.float32)
    tmask = np.load(td_dir / 'mountain_mask.npy').astype(bool)
    tang, tcoh = np.load(td_dir / 'ridge_angle_rad.npy'), np.load(td_dir / 'ridge_coherence.npy')
    cm = td_dir / 'computed_mask.npy'
    computed = np.load(cm).astype(bool) if cm.exists() else np.isfinite(te)
    tsp = float(tm['grid']['spacing_m']); tx0, tz0 = tm['grid']['first_sample_xz_m']
    fe = np.load(fast_dir / 'elevation_m.npy').astype(np.float32)
    fsp = float(fm['grid']['spacing_m']); fx0, fz0 = fm['grid']['first_sample_xz_m']
    smooth = ndimage.gaussian_filter(fe, 0.5 * tsp / fsp)
    nz, nx = te.shape
    zz, xx = np.mgrid[0:nz, 0:nx]
    rows, cols = (tz0 + zz * tsp - fz0) / fsp, (tx0 + xx * tsp - fx0) / fsp
    inside = (rows >= 0) & (rows <= fe.shape[0] - 1) & (cols >= 0) & (cols <= fe.shape[1] - 1)
    fs = ndimage.map_coordinates(smooth, [rows.ravel(), cols.ravel()], order=1, mode='nearest').reshape(te.shape)
    fmask = tc.mountain_mask(fs, threshold_m)
    fang, fcoh = tc.ridge_orientation_field(fs, fmask)
    ok = computed & inside & np.isfinite(te)
    a, b = tmask & ok, fmask & ok
    union = int((a | b).sum())
    both = a & b & (tcoh > coherence_min) & (fcoh > coherence_min)
    dev = tc.axial_diff_deg(tang[both], fang[both]) if both.any() else np.array([], np.float32)
    return dict(
        td=str(td_dir), fast=str(fast_dir), td_identity=tm.get('identity'), fast_identity=fm.get('identity'),
        lattice_spacing_m=tsp, cells_compared=int(ok.sum()), threshold_m=threshold_m,
        mountain_cells_td=int(a.sum()), mountain_cells_fast=int(b.sum()),
        mountain_iou=float((a & b).sum() / union) if union else None,
        land_agreement=float(((te[ok] > 0) == (fs[ok] > 0)).mean()) if ok.any() else None,
        ridge_cells_compared=int(both.sum()),
        ridge_axis_deviation_deg_median=float(np.median(dev)) if dev.size else None,
        ridge_axis_deviation_deg_p90=float(np.percentile(dev, 90)) if dev.size else None,
        within_20deg=float((dev <= 20).mean()) if dev.size else None, random_expectation_mean_deg=45.0,
        method='fast elevation gaussian(sigma=0.5 TD cell) + bilinear at TD lattice; td_coarse.mountain_mask / ridge_orientation_field')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--td', required=True)
    p.add_argument('--fast', required=True)
    p.add_argument('--json')
    a = p.parse_args(argv)
    r = compare(a.td, a.fast)
    text = json.dumps(r, indent=1, ensure_ascii=False)
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
