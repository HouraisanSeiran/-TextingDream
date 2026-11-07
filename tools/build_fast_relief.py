"""Build the fast procedural 2 km world layer (terragenesis-fast-relief-v1) from a tectonic skeleton npz.

CPU only. Needs numba (Terragenesis venv):
  D:/codexwork/山川形意Terragenesis/runtime/venv/Scripts/python.exe tools/build_fast_relief.py --skeleton <skeleton.npz> --out <dir>
  ... --timing-only          compute everything, print timings/peak memory, write nothing (no product)
Refuses to start with < 2 GiB available memory. NUMBA_CACHE_DIR defaults to a folder under %TEMP%.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('NUMBA_CACHE_DIR', str(Path(tempfile.gettempdir()) / 'dream-nbcache'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--skeleton', required=True)
    ap.add_argument('--out', help='product directory to create (must not be an existing frozen product)')
    ap.add_argument('--expected-identity', default=None)
    ap.add_argument('--island-product-path', '--islands-product', dest='island_product_path',default=None)
    ap.add_argument('--expected-island-identity',default=None)
    ap.add_argument('--skeleton-run',default=None,help='strictly matching source run manifest with ocean target/tolerance')
    ap.add_argument('--mountain-input',default=None,help='frozen world island input with explicit TD/pending state')
    ap.add_argument('--no-erosion', action='store_true')
    ap.add_argument('--params', default=None, help='JSON object overriding DEFAULTS')
    ap.add_argument('--timing-only', action='store_true')
    ap.add_argument('--min-free-gib', type=float, default=2.0)
    ap.add_argument('--relief', choices=('skeleton', 'ridges', 'orogen'), default='skeleton',
                    help='skeleton = dream-fast-relief-1 (v1); ridges = dream-fast-relief-2 from a dream-world-skeleton-3 ridge network; '
                         'orogen = dream-fast-relief-3 from dream-world-skeleton-4 orogen belts')
    a = ap.parse_args(argv)
    if bool(a.island_product_path)!=bool(a.expected_island_identity):
        ap.error('--island-product-path and --expected-island-identity must be supplied together')
    if a.skeleton_run and not a.island_product_path:
        ap.error('--skeleton-run requires --island-product-path')
    island_options=dict(island_product_path=a.island_product_path,expected_island_identity=a.expected_island_identity,
                        skeleton_run_path=a.skeleton_run,mountain_input_path=a.mountain_input)
    from app.world_gen import fast_relief as fr
    params = json.loads(a.params) if a.params else None
    min_free = int(a.min_free_gib * 2 ** 30)
    if a.timing_only:
        t0 = time.perf_counter()
        fr.memory_guard(min_free)
        sk = fr.load_skeleton(a.skeleton, a.expected_identity)
        res = fr.compute(sk, params, not a.no_erosion, lambda d: print(d, flush=True), a.relief,**island_options)
        total = time.perf_counter() - t0
        print(json.dumps(dict(total_s=round(total, 2), peak_working_set_mb=round(fr.peak_memory_mb(), 1),
                              nodes=int(res['elevation'].size), timing={k: round(v, 2) for k, v in res['timing'].items()},
                              river_lines=len(res['rivers'])), indent=1))
        return 0
    if not a.out:
        ap.error('--out is required unless --timing-only')
    out = Path(a.out)
    if (out / 'manifest.json').exists():
        ap.error('refusing to overwrite an existing product: %s' % out)
    fr.freeze(a.skeleton, out, params, not a.no_erosion, a.expected_identity, min_free, relief=a.relief,**island_options)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
