"""Skeleton npz -> TD coarse-model elevation + mountain mask + ridge direction field (frozen product dir).

  <Terragenesis venv python> tools/td_coarse_ridges.py --skeleton <skeleton.npz> --out <dir> [--window CX_M,CZ_M,SIZE_M]
                                                      [--threshold-m 1000] [--preview preview.png] [--force]

Only the TD coarse U-Net runs (no latent/base/decoder). Device: CPU by default (--device auto picks CUDA when >= 1 GiB free).
--benchmark needs a usable CUDA device and exits with "无可用显卡" otherwise (it never measures on CPU).
Refuses to start below 2 GiB available memory. Terragenesis is imported read-only (TERRAGENESIS_ROOT overrides the location).
The skeleton is read via app.world_relief.td_resident.read_plate (identity and array hashes verified), so any skeleton npz with
the dream/Terragenesis manifest layout works. Output: manifest.json (identity, no timings), runtime-stats.json, *.npy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from app.world_gen import td_coarse as tc  # noqa: E402


def preview(out_png, product_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    d = Path(product_dir)
    m = json.loads((d / 'manifest.json').read_text(encoding='utf-8'))
    el = np.load(d / 'elevation_m.npy')
    mask = np.load(d / 'mountain_mask.npy').astype(bool)
    ang = np.load(d / 'ridge_angle_rad.npy')
    coh = np.load(d / 'ridge_coherence.npy')
    sp = m['grid']['spacing_m']
    x0, z0 = m['grid']['first_sample_xz_m']
    nz, nx = el.shape
    ext = ((x0 - sp / 2) / 1000, (x0 + (nx - .5) * sp) / 1000, (z0 + (nz - .5) * sp) / 1000, (z0 - sp / 2) / 1000)
    fig, ax = plt.subplots(1, 2, figsize=(16, 8 * nz / nx + 0.8))
    rgb = np.where(el[..., None] > 0, np.clip(0.9 - el[..., None] / 6000, 0.1, 0.9) * np.array([1, 1, .8]), np.array([.55, .72, .88]))
    ax[0].imshow(np.clip(rgb, 0, 1), extent=ext)
    ax[0].set_title('TD coarse elevation (km)')
    ax[1].imshow(np.where(el[..., None] > 0, 0.95, 0.85) * np.array([1, 1, 1]), extent=ext)
    ax[1].imshow(np.ma.masked_where(~mask, mask), extent=ext, cmap='Reds', alpha=.7)
    step = 3
    zz, xx = np.mgrid[0:nz:step, 0:nx:step]
    sel = mask[zz, xx] & (coh[zz, xx] > .3)
    a = ang[zz, xx][sel]
    cx, cz = (x0 + xx[sel] * sp) / 1000, (z0 + zz[sel] * sp) / 1000
    L = step * sp / 1000 * .4
    ax[1].plot(np.array([cx - L * np.cos(a), cx + L * np.cos(a)]), np.array([cz - L * np.sin(a), cz + L * np.sin(a)]), 'k-', lw=1)
    ax[1].set_xlim(ext[0], ext[1]); ax[1].set_ylim(ext[2], ext[3])
    ax[1].set_title('mountain mask + ridge axes (km)')
    fig.tight_layout(); fig.savefig(out_png, dpi=90); plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--skeleton', required=True)
    p.add_argument('--out', help='product directory (required unless --plan-only/--benchmark; then optional: plan.json / benchmark.json go there)')
    p.add_argument('--window', help='CX_M,CZ_M,SIZE_M square window (metres); default whole skeleton extent')
    p.add_argument('--threshold-m', type=float, default=1000.0, help='mountain mask threshold on smoothed coarse elevation')
    p.add_argument('--seed', type=int, help='override coarse sub-seed (default: derived from the skeleton world seed)')
    p.add_argument('--preview', help='optional PNG path')
    p.add_argument('--force', action='store_true', help='overwrite an existing product directory')
    g = p.add_argument_group('speed / cost options (defaults reproduce the frozen product)')
    g.add_argument('--skip-ocean-km', type=float, default=tc.DEFAULT_SKIP_OCEAN_KM,
                   help='skip tiles whose whole 64x64 window is farther than this from skeleton land (0 = compute all); skipped cells are NaN/"not computed"')
    g.add_argument('--stride', type=int, default=tc.STRIDE, help='tile stride in cells (default 48)')
    g.add_argument('--steps', type=int, default=tc.STEPS, help='DPM denoising steps (default 20)')
    g.add_argument('--batch-size', type=int, default=1, help='tiles per U-Net call (speed only)')
    g.add_argument('--threads', type=int, help='torch CPU threads (default env TD_COARSE_THREADS or 8)')
    g.add_argument('--precision', choices=tc.PRECISIONS, default='fp32', help='fp32 (default) or autocast (CPU bfloat16 / CUDA float16)')
    g.add_argument('--device', default='cpu', help='cpu (default, CPU only), auto (CUDA when >= 1 GiB free, else CPU), or cuda / cuda:0')
    g = p.add_argument_group('planning / benchmarking')
    g.add_argument('--plan-only', action='store_true', help='print tile counts (total / computed / skipped) without loading torch or the model')
    g.add_argument('--benchmark', type=int, metavar='N', help='run N evenly spread tiles, report seconds per tile, write no product')
    g.add_argument('--extent-km', type=float, help='plan a hypothetical square world of this size centred on the skeleton')
    g.add_argument('--mode', choices=('mosaic', 'stretch'), default='mosaic', help='--extent-km: tile the skeleton periodically or enlarge it')
    g.add_argument('--land-fraction', type=float, help='--plan-only: re-threshold sea level so this fraction of the skeleton is land')
    a = p.parse_args(argv)
    window = tuple(float(v) for v in a.window.split(',')) if a.window else None
    if window and len(window) != 3:
        raise SystemExit('--window needs CX_M,CZ_M,SIZE_M')
    try:
        options = tc.RunOptions(stride=a.stride, steps=a.steps, skip_ocean_km=a.skip_ocean_km, precision=a.precision,
                                batch_size=a.batch_size, threads=a.threads, device=a.device).validate()
    except ValueError as e:
        raise SystemExit(str(e))
    out = Path(a.out) if a.out else None
    if a.plan_only:
        plan = tc.plan_for_skeleton(a.skeleton, options, window=window, extent_km=a.extent_km, mode=a.mode, land_fraction=a.land_fraction)
        plan['skeleton'] = str(a.skeleton)
        plan['options'] = dict(stride=options.stride, steps=options.steps, pad=options.pad, skip_ocean_km=options.skip_ocean_km)
        text = json.dumps(plan, indent=2, ensure_ascii=False)
        if out:
            out.mkdir(parents=True, exist_ok=True)
            (out / 'plan.json').write_text(text, encoding='utf-8')
        print(text)
        return
    if a.benchmark:
        ok, gpu_info = tc.gpu_status()
        if not ok:
            raise SystemExit(f'{tc.NO_GPU_MESSAGE}. {json.dumps(gpu_info, ensure_ascii=False)}')
        options = tc.RunOptions(**{**options.__dict__, 'device': 'cuda'}).validate()
        res, st = tc.generate(a.skeleton, window=window, seed=a.seed, options=options, tile_limit=a.benchmark)
        bench = dict(tiles_run=st['tiles_run'], seconds_per_tile=st['seconds_per_tile'], generate_seconds=st['generate_seconds'],
                     model_load_seconds=st['model_load_seconds'], phase_seconds=st['phase_seconds'], batch_seconds=st['batch_seconds'],
                     device=st['device'], precision=st['precision'], options=st['options'], tiles_total=st['tiles_total'],
                     tiles_computed=st['tiles_computed'], free_memory_before_bytes=st['free_memory_before_bytes'],
                     peak_working_set_bytes=st['peak_working_set_bytes'],
                     note='cold start included: the first batch pays allocator / thread-pool warm-up; others are steady state')
        text = json.dumps(bench, indent=2, ensure_ascii=False, default=str)
        if out:
            out.mkdir(parents=True, exist_ok=True)
            (out / 'benchmark.json').write_text(text, encoding='utf-8')
        print(text)
        return
    if out is None:
        raise SystemExit('--out is required unless --plan-only or --benchmark')
    if (out / 'manifest.json').exists() and not a.force:
        raise SystemExit(f'{out} already has a product; use --force to overwrite')

    def prog(done, total, secs):
        if done % 5 == 0 or done == total:
            print(f'tile {done}/{total}  {secs:.0f} s', flush=True)

    res, st = tc.generate(a.skeleton, window=window, seed=a.seed, progress=prog, options=options)
    st['total_seconds_including_load'] = st['model_load_seconds'] + st['generate_seconds']
    m = tc.write_product(out, res, mask_threshold_m=a.threshold_m, stats=st)
    print(json.dumps(dict(identity=m['identity'], device=st['device'], shape_zx=m['grid']['shape_zx'],
                          generate_seconds=round(st['generate_seconds'], 1), peak_working_set_mib=(st['peak_working_set_bytes'] or 0) // 2**20,
                          out=str(out)), ensure_ascii=False))
    if a.preview:
        preview(a.preview, out)
        print('preview', a.preview)


if __name__ == '__main__':
    main()
