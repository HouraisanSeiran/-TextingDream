"""Fast Terragenesis latent-world path: region picking, fast/old runs, comparison, run-time estimates.

Never touches artifacts/td-world/world-pages. Test products go to artifacts/td-world/speedup-test.
GPU stages (fast, old, world) must only run when no other generation is using the GPU.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from app.world_relief.td_pages import add_upstream, stats, write_json
from app.world_relief import td_fast
from app.world_relief.source import identity

CORE = 30  # cells per old page core


def load_world(world):
    plan = json.loads((Path(world) / 'world-plan.json').read_text(encoding='utf-8'))
    weight = np.load(Path(world) / 'world-td-weight.npy')
    skeleton = np.load(Path(world) / 'world-skeleton-960m.npy')
    return plan, weight, skeleton


def source_path(terra):
    return Path(terra) / '.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'


def pick_region(plan, weight, skeleton, pages_side=7):
    """Aligned window of pages_side x pages_side old page cores: all pages exist, coast + mountains, best relief."""
    have = {tuple(p['grid_zx']) for p in plan['pages']}
    side = pages_side * CORE
    best = None
    for z in range(0, weight.shape[0] - side + 1, CORE):
        for x in range(0, weight.shape[1] - side + 1, CORE):
            if not all((z + i * CORE, x + j * CORE) in have for i in range(pages_side) for j in range(pages_side)):
                continue
            h = skeleton[z:z + side, x:x + side]
            sea = float((h < 0).mean())
            if not .15 <= sea <= .4:
                continue
            land = h[h >= 0]
            score = float(np.quantile(land, .99))
            if best is None or score > best[0]:
                best = (score, z, x, sea)
    if best is None:
        raise ValueError('no coast+mountain window found')
    score, z, x, sea = best
    return dict(region=[z, z + side, x, x + side], pages_side=pages_side, sea_fraction=sea, land_p99_skeleton_m=score,
                area_km2=side * side * 0.9216)


def fast_spec(plan, region, block_cells, scale=1):
    spec = dict(algorithm=td_fast.ALGORITHM, plate_identity=plan['plate_identity'], world_seed=plan['world_seed'],
                first_sample_xz_m=plan['first_sample_xz_m'], shape_zx=plan['shape_zx'], region=list(region),
                block_cells=int(block_cells))
    if int(scale) != 1:
        spec['scale'] = int(scale)
    spec['plan_identity'] = identity(spec)
    return spec


def cmd_pick(a):
    plan, weight, skeleton = load_world(a.world)
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    info = pick_region(plan, weight, skeleton)
    write_json(out / 'region.json', info)
    print('REGION ' + json.dumps(info), flush=True)


def region_info(a):
    return json.loads((Path(a.output) / 'region.json').read_text(encoding='utf-8'))


def cmd_fast(a):
    plan, weight, _ = load_world(a.world)
    out = Path(a.output)
    info = region_info(a)
    k = int(a.scale)
    z0, z1, x0, x1 = info['region']
    # scale k: output grid spacing 960*k m; model region keeps the plate region's first cell and has 1/k the cells per side
    region = [z0, z0 + (z1 - z0) // k, x0, x0 + (x1 - x0) // k] if k > 1 else info['region']
    spec = fast_spec(plan, region, a.block_cells, k)
    wt = weight if k == 1 else None
    blocks = td_fast.plan_blocks(region, a.block_cells, wt)
    td_fast.check_coverage(blocks, region, wt)
    tag = a.tag or f'fast-{a.precision}-b{a.batch}-k{a.block_cells}' + (f'-s{k}' if k > 1 else '')
    directory = out / tag
    options = dict(precision=a.precision, batch=a.batch, cache_mib=a.cache_mib, threads=a.threads,
                   cudnn_benchmark=not a.no_cudnn_benchmark, profile=a.profile, onestep=a.onestep,
                   coarse_steps=a.coarse_steps, warm_coarse=a.warm_coarse, slice_channels=a.slice_channels, scale=k,
                   cuda_graph=a.cuda_graph, noise_cache=a.noise_cache, channels_last=a.channels_last, writer_thread=a.writer_thread)
    terra = Path(a.terra)
    monitor = td_fast.GpuMonitor()
    started = time.perf_counter()
    records = td_fast.generate_blocks(terra, source_path(terra), spec, blocks, directory, purpose='speedup-test',
                                      options=options, monitor=monitor)
    wall = time.perf_counter() - started
    mosaic = td_fast.assemble(directory, blocks, region)
    np.save(directory / 'mosaic_960m.npy', mosaic, allow_pickle=False)
    run = json.loads((directory / 'run-summary.json').read_text(encoding='utf-8'))
    infer = sum(r['inference_seconds'] for r in records)
    cells = int(sum(r['cells'] for r in records))
    area = cells * 0.9216 * k * k   # plate area the model cells stand for
    summary = dict(tag=tag, options=options, blocks=len(records), cells=cells, area_km2=area, scale=k,
                   output_spacing_m=960 * k, region=region,
                   inference_seconds=infer, seconds_per_km2=infer / area, wall_seconds_total=wall,
                   gpu=run.get('gpu'), peak_child_rss_mib=run['peak_child_rss_mib'],
                   min_available_host_gib=run['min_available_host_bytes'] / 2 ** 30,
                   reserved_peak_mib=max(r['reserved_peak_mib'] for r in records),
                   allocated_peak_mib=max(r['allocated_peak_mib'] for r in records),
                   worker_stats=[r['worker_stats'] for r in records[:3]])
    write_json(directory / 'summary.json', summary)
    print('FAST ' + json.dumps({k: v for k, v in summary.items() if k != 'worker_stats'}), flush=True)


def cmd_old(a):
    from app.world_relief.td_resident import generate_pages
    plan, weight, _ = load_world(a.world)
    out = Path(a.output)
    info = region_info(a)
    z0, z1, x0, x1 = info['region']
    pages = [p for p in plan['pages'] if z0 <= p['grid_zx'][0] < z1 and x0 <= p['grid_zx'][1] < x1]
    directory = out / 'old'
    terra = Path(a.terra)
    add_upstream(terra)
    monitor = td_fast.GpuMonitor().start()
    t0 = time.time()
    started = time.perf_counter()
    records = generate_pages(terra, source_path(terra), pages, directory, purpose='speedup-test',
                             plan_identity=plan['plan_identity'])
    wall = time.perf_counter() - started
    session = json.loads((directory / 'session.json').read_text(encoding='utf-8'))
    gpu = monitor.stop(since=t0 + session['model_loading_seconds'] + 3)
    canvas = np.full((z1 - z0, x1 - x0), np.nan, dtype=np.float32)
    for p in pages:
        z, x = p['grid_zx']
        canvas[z - z0:z - z0 + CORE, x - x0:x - x0 + CORE] = np.load(directory / p['id'] / 'elevation_960m.npy')[:CORE, :CORE]
    np.save(directory / 'mosaic_960m.npy', canvas, allow_pickle=False)
    infer = sum(r['inference_seconds'] for r in records)
    cells = len(records) * CORE * CORE
    summary = dict(tag='old', pages=len(records), cells=cells, area_km2=cells * 0.9216, inference_seconds=infer,
                   seconds_per_km2=infer / (cells * 0.9216), wall_seconds_total=wall, gpu=gpu,
                   peak_child_rss_mib=max(r['peak_child_rss_mib'] for r in records),
                   reserved_peak_mib=max(r['reserved_peak_mib'] for r in records),
                   allocated_peak_mib=max(r['allocated_peak_mib'] for r in records))
    write_json(directory / 'summary.json', summary)
    print('OLD ' + json.dumps(summary), flush=True)


def cmd_compare(a):
    out = Path(a.output)
    old = np.load(out / 'old/mosaic_960m.npy')
    result = {}
    for d in sorted(out.glob('fast-*')):
        m = d / 'mosaic_960m.npy'
        if m.exists():
            new = np.load(m)
            result[d.name] = stats(new, old)
            result[d.name]['old_range_m'] = [float(old.min()), float(old.max())]
    write_json(out / 'compare.json', result)
    print('COMPARE ' + json.dumps(result), flush=True)


def cmd_estimate(a):
    plan, weight, skeleton = load_world(a.world)
    out = Path(a.output)
    covered_cells = int((weight > 0).sum())
    land_cells = int((skeleton >= 0).sum())
    ratio = covered_cells / land_cells
    rows = {}
    for d in sorted(out.glob('fast-*')) + [out / 'old']:
        f = d / 'summary.json'
        if not f.exists():
            continue
        s = json.loads(f.read_text(encoding='utf-8'))
        rate = s['seconds_per_km2']
        w1 = covered_cells * 0.9216 * rate / 3600
        land_world = 10000 * 10000 * 0.30
        w2 = land_world * ratio * rate / 3600
        rows[d.name] = dict(seconds_per_km2=rate, hours_1600x1280=w1,
                            hours_10000x10000_30pct_land_with_buffer=w2)
    info = dict(world_covered_km2=covered_cells * 0.9216, world_land_km2=land_cells * 0.9216,
                covered_over_land=ratio, rows=rows,
                assumption='inference time only; excludes model load; 10000x10000: land = 30% of area, covered = land * (covered/land of the 1600x1280 world)')
    write_json(out / 'estimate.json', info)
    print('ESTIMATE ' + json.dumps(info), flush=True)


def cmd_world(a):
    """Full fast world into a separate directory (never world-pages)."""
    plan, weight, _ = load_world(a.world)
    if Path(a.output).resolve() == (Path(a.world) / 'world-pages').resolve():
        raise ValueError('refusing to write into world-pages')
    region = [0, weight.shape[0], 0, weight.shape[1]]
    spec = fast_spec(plan, region, a.block_cells)
    blocks = td_fast.plan_blocks(region, a.block_cells, weight)
    td_fast.check_coverage(blocks, region, weight)
    options = dict(precision=a.precision, batch=a.batch, cache_mib=a.cache_mib, threads=a.threads,
                   cudnn_benchmark=not a.no_cudnn_benchmark, profile=False, onestep=a.onestep,
                   coarse_steps=a.coarse_steps, warm_coarse=a.warm_coarse, slice_channels=a.slice_channels,
                   cuda_graph=a.cuda_graph, noise_cache=a.noise_cache, channels_last=a.channels_last, writer_thread=a.writer_thread)
    terra = Path(a.terra)
    print(f'FAST WORLD {len(blocks)} blocks; plan {spec["plan_identity"]}', flush=True)
    source = Path(a.source) if a.source else source_path(terra)
    td_fast.generate_blocks(terra, source, spec, blocks, Path(a.output) / a.world_dir_name, purpose='world',
                            options=options, monitor=td_fast.GpuMonitor())


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('stage', choices=['pick', 'fast', 'old', 'compare', 'estimate', 'world'])
    p.add_argument('--terra', default=str(ROOT.parent / '山川形意Terragenesis'))
    p.add_argument('--world', default=str(ROOT / 'artifacts/td-world'))
    p.add_argument('--output', default=str(ROOT / 'artifacts/td-world/speedup-test'))
    p.add_argument('--precision', default='fp32', choices=td_fast.PRECISIONS)
    p.add_argument('--batch', type=int, default=8)
    p.add_argument('--block-cells', type=int, default=120)
    p.add_argument('--cache-mib', type=int, default=512)
    p.add_argument('--threads', type=int, default=2)
    p.add_argument('--no-cudnn-benchmark', action='store_true')
    p.add_argument('--profile', action='store_true')
    p.add_argument('--onestep', action='store_true')
    p.add_argument('--coarse-steps', type=int, default=20)
    p.add_argument('--warm-coarse', action='store_true')
    p.add_argument('--slice-channels', action='store_true')
    p.add_argument('--cuda-graph', action='store_true')
    p.add_argument('--noise-cache', action='store_true')
    p.add_argument('--channels-last', action='store_true')
    p.add_argument('--writer-thread', action='store_true')
    p.add_argument('--scale', type=int, default=1, help='k: one model metre stands for k plate metres; output spacing 960*k m')
    p.add_argument('--tag', default='')
    p.add_argument('--source', default='', help='plate skeleton npz; default = Terragenesis shaped-run-v4 product (old 1600 km world)')
    p.add_argument('--world-dir-name', default='fast-world', help='world stage: sub-directory of --output')
    a = p.parse_args()
    {'pick': cmd_pick, 'fast': cmd_fast, 'old': cmd_old, 'compare': cmd_compare,
     'estimate': cmd_estimate, 'world': cmd_world}[a.stage](a)


if __name__ == '__main__':
    main()
