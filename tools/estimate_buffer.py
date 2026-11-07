"""CPU estimate: coast buffer 80 km vs 40 km (and others) -> covered cells, old pages, TD area. Writes speedup-test/buffer-estimate.json."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scipy import ndimage

W = ROOT / 'artifacts/td-world'
sk = np.load(W / 'world-skeleton-960m.npy')
dist = ndimage.distance_transform_edt(sk < 0) * 960
land = int((sk >= 0).sum())
rows = {}
for buf in (80000, 60000, 40000, 20000):
    t = np.clip((dist - buf / 2) / (buf / 2), 0, 1)
    w = 1 - t * t * (3 - 2 * t)
    cov = w > 0
    pages = sum(1 for z in range(0, sk.shape[0], 30) for x in range(0, sk.shape[1], 30) if cov[z:z + 30, x:x + 30].any())
    rows[str(buf // 1000) + 'km'] = dict(covered_cells=int(cov.sum()), covered_km2=float(cov.sum() * 0.9216), pages=pages,
                                         page_area_km2=pages * 900 * 0.9216, covered_over_land=float(cov.sum() / land))
base = rows['80km']
for r in rows.values():
    r['area_vs_80km'] = r['covered_km2'] / base['covered_km2']
    r['pages_vs_80km'] = r['pages'] / base['pages']
out = dict(land_cells=land, land_km2=land * 0.9216, rows=rows)
(ROOT / 'artifacts/td-world/speedup-test/buffer-estimate.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out, indent=1))
