"""Explicit CPU ocean overlay: plan, bounded solve, or PIL-only render.

Defaults point to the selected immutable 2026-11-11 products, not world defaults.
The supervisor kills the worker at 120 seconds / 2 GiB; failed thermal CFL or
sparse LU budgets are reported, never replaced with hand-drawn currents.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--plan-only', action='store_true')
    action.add_argument('--solve', action='store_true')
    action.add_argument('--render-only', action='store_true')
    p.add_argument('--world', type=Path, default=ROOT/'artifacts/mountain-glacier-hydrology-20261111/world')
    shared = ROOT/'artifacts/world-climate-integration-20261111'
    p.add_argument('--climate', type=Path, default=shared/'climate-dry-continuous-year')
    p.add_argument('--atlas', type=Path, default=shared/'atlas-final/simple-atlas.png')
    p.add_argument('--atlas-metadata', type=Path, default=shared/'atlas-final/atlas-source.json')
    p.add_argument('--output', type=Path, default=ROOT/'artifacts/ocean-current-overlay-20261111')
    p.add_argument('--max-substeps-per-month', type=int, default=128)
    p.add_argument('--max-routes', type=int, default=18)
    p.add_argument('--months', type=int, nargs='+', default=[1,7])
    p.add_argument('--font', type=Path)
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    return p


def supervise(args):
    import psutil
    from app.world_gen.ocean_current_overlay import write_json
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError('Solve requires a new empty output directory')
    if psutil.virtual_memory().available < 2*1024**3:
        raise RuntimeError('Less than 2 GiB free memory: refusing to start')
    if not 1 <= args.max_substeps_per_month <= 128:
        raise ValueError('Thermal budget must be 1..128; do not disable heat to label warm/cold')
    command = [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), *sys.argv[1:], '--worker']
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='-1',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    start, peak, reason = time.perf_counter(), 0, None
    with tempfile.TemporaryFile(mode='w+b') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=ROOT)
        process = psutil.Process(child.pid)
        while child.poll() is None:
            try:
                rss = process.memory_info().rss+sum(p.memory_info().rss for p in process.children(recursive=True) if p.is_running())
                peak = max(peak, rss)
            except psutil.NoSuchProcess:
                break
            if time.perf_counter()-start > 120:
                reason = 'wall budget exceeded (120 s); sparse LU/trace not completed'
            elif peak > 2*1024**3:
                reason = 'RSS budget exceeded (2 GiB); sparse LU fill can be nonlinear'
            if reason:
                for descendant in process.children(recursive=True):
                    descendant.kill()
                child.kill()
                break
            time.sleep(.1)
        code = child.wait()
        log.seek(0)
        output = log.read().decode('utf-8', errors='replace')
    args.output.mkdir(parents=True, exist_ok=True)
    stats = dict(device='cpu', wall_seconds=time.perf_counter()-start, peak_rss_bytes=peak,
        peak_gpu_memory_bytes=0, max_wall_seconds=120, max_rss_bytes=2*1024**3,
        success=code == 0 and reason is None, returncode=code,
        failure=reason or (f'worker exit code {code}; see run.log for solver/CFL error' if code else None),
        note='RSS sampled at 0.1s; limit is supervisory, transient allocation overshoot possible')
    write_json(args.output/'runtime-stats.json', stats)
    (args.output/'run.log').write_text(output, encoding='utf-8')
    print(output, end='')
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if not stats['success']:
        raise RuntimeError(reason or 'Ocean worker failed; see run.log (no fallback or climate change)')


def main():
    args = parser().parse_args()
    if any(m < 1 or m > 12 for m in args.months) or len(set(args.months)) != len(args.months):
        raise ValueError('Distinct months in 1..12 required')
    if not 1 <= args.max_routes <= 24:
        raise ValueError('Use 1..24 major routes per month')
    if args.solve and not args.worker:
        supervise(args)
        return
    from app.world_gen import ocean_current_overlay as overlay
    if args.render_only:
        stats_path = args.output/'runtime-stats.json'
        if stats_path.exists() and not json.loads(stats_path.read_text(encoding='utf-8'))['success']:
            raise RuntimeError('Failed/incomplete ocean worker cannot be rendered')
    source, metadata, winds = overlay.load_inputs(args.world,args.climate)
    if args.plan_only:
        print(json.dumps(overlay.plan(source,metadata,winds),ensure_ascii=False,indent=2))
    elif args.solve:
        manifest = overlay.prepare(source,metadata,winds,args.output,
            max_substeps_per_month=args.max_substeps_per_month,months=tuple(args.months),max_routes=args.max_routes)
        manifest['source_paths'] = dict(world=str(args.world.resolve()),climate=str(args.climate.resolve()))
        overlay.write_json(args.output/'manifest.json',manifest)
        print(f"Saved {args.output}; finite year, converged={manifest['solver']['converged']}")
    else:
        print('\n'.join(overlay.render(args.output,source,args.atlas,args.atlas_metadata,font_path=args.font)))


if __name__ == '__main__':
    main()
