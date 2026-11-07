"""Compare a td-coarse-ridges product with a reference (frozen) product on the same grid.

  python tools/td_coarse_compare.py --new <dir> --ref <dir> [--json out.json]

Metrics (acceptance for numeric-parameter changes: median ridge-direction deviation <= 2 deg, mountain-mask IoU drop <= 0.03):
  ridge_axis_deviation_deg_median/p90 : axial difference of ridge_angle_rad over cells that are mountain in both products and have
                                        coherence > 0.3 in both (the "main ridge" cells)
  mountain_iou                        : IoU of the 1000 m mountain masks (cells not computed in the new product count as 0)
  land_agreement                      : fraction of computed cells with the same sea/land sign
  elevation_corr / elevation_mae_m    : over computed cells
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from app.world_gen import td_coarse as tc  # noqa: E402


def load(d):
    d = Path(d)
    out = dict(manifest=json.loads((d / 'manifest.json').read_text(encoding='utf-8')))
    for name in ('elevation_m', 'mountain_mask', 'ridge_angle_rad', 'ridge_coherence'):
        out[name] = np.load(d / f'{name}.npy')
    cm = d / 'computed_mask.npy'
    out['computed'] = np.load(cm).astype(bool) if cm.exists() else np.ones(out['elevation_m'].shape, bool)
    return out


def compare(new_dir, ref_dir, coherence_min=0.3):
    a, b = load(new_dir), load(ref_dir)
    if a['elevation_m'].shape != b['elevation_m'].shape or a['manifest']['grid']['first_sample_xz_m'] != b['manifest']['grid']['first_sample_xz_m']:
        raise SystemExit('products are not on the same grid')
    ok = a['computed'] & b['computed']
    ma, mb = a['mountain_mask'].astype(bool) & a['computed'], b['mountain_mask'].astype(bool) & b['computed']
    union = int((ma | mb).sum())
    iou = float((ma & mb).sum() / union) if union else 1.0
    both = ma & mb & (a['ridge_coherence'] > coherence_min) & (b['ridge_coherence'] > coherence_min)
    dev = tc.axial_diff_deg(a['ridge_angle_rad'][both], b['ridge_angle_rad'][both]) if both.any() else np.array([0.0])
    ea, eb = a['elevation_m'][ok], b['elevation_m'][ok]
    return dict(
        new=str(new_dir), ref=str(ref_dir), cells=int(ok.size), cells_computed_new=int(a['computed'].sum()),
        ridge_cells_compared=int(both.sum()), ridge_axis_deviation_deg_median=float(np.median(dev)),
        ridge_axis_deviation_deg_p90=float(np.percentile(dev, 90)), mountain_iou=iou,
        mountain_cells_new=int(ma.sum()), mountain_cells_ref=int(mb.sum()),
        land_agreement=float(((ea > 0) == (eb > 0)).mean()),
        elevation_corr=float(np.corrcoef(ea, eb)[0, 1]) if ea.size > 1 else 1.0,
        elevation_mae_m=float(np.abs(ea - eb).mean()),
        identical_elevation=bool(np.array_equal(a['elevation_m'], b['elevation_m'], equal_nan=True)),
        accept=dict(median_dev_le_2deg=bool(np.median(dev) <= 2.0), iou_drop_le_0p03=bool(iou >= 0.97)))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--new', required=True)
    p.add_argument('--ref', required=True)
    p.add_argument('--json')
    a = p.parse_args(argv)
    r = compare(a.new, a.ref)
    text = json.dumps(r, indent=2, ensure_ascii=False)
    if a.json:
        Path(a.json).write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
