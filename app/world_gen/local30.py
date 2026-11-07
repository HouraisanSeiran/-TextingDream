"""Local 30 m windows: read-only request, explicit preparation, frozen product (kind terragenesis-local30).

`request_local` never generates. It reports which 30 m tiles of a box are prepared and describes the missing ones.
`prepare_tile` is the explicit step: two-stage memory check, generator call, freeze to the world-map-product layout
(manifest.json + layers/*.npy, schema terragenesis-local30-v1), consistency check against the 960 m world layer.
The default generator needs the GPU and the Terragenesis tree; tests inject a fake generator.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from . import tiles as T
from .planner import local_cache_dir

SCHEMA = 'terragenesis-local30-v1'
KIND = 'terragenesis-local30'
HOST_RESERVE_BYTES = 1024 * 2 ** 20                      # same margin as td_resident.resident_headroom
GPU_FREE_MIB = 4096                                      # upstream BUDGETS gpu gate; not lowered here
HOST_WORKER_BYTES = 4096 * 2 ** 20                       # upstream BUDGETS host_rss at start


RUNTIME_KEYS = frozenset({'seconds', 'gate', 'available_bytes'})   # run-time facts: never part of manifest/identity


class NotPrepared(LookupError):
    """Raised when a prepared product is required but absent."""


class StaleTile(LookupError):
    """Raised when a cached tile exists but no longer matches the current plate / world layer / identity rules."""

    def __init__(self, tile, reasons):
        self.tile, self.reasons = tile, list(reasons)
        super().__init__(f'cached tile {tile} is stale: ' + '; '.join(self.reasons)
                         + '. It is not reused; regenerate explicitly with prepare_tile(..., reuse=False) (needs the GPU).')


def staging_bytes(side=T.TILE_SAMPLES):
    return 300_000_000 + side * side * 160


def memory_requirement_bytes(*, starting_worker=True, side=T.TILE_SAMPLES):
    """Declared host budgets. Thresholds are fixed; callers adapt by waiting or reusing a worker."""
    if starting_worker:
        return HOST_WORKER_BYTES + staging_bytes(side)
    return staging_bytes(side) + HOST_RESERVE_BYTES


def memory_gate(available_bytes, *, starting_worker=True, side=T.TILE_SAMPLES):
    """Two-stage check. Stage 1 (worker start): worker budget + staging. Stage 2 (each window): staging + 1 GiB margin."""
    need = memory_requirement_bytes(starting_worker=starting_worker, side=side)
    if available_bytes < need:
        raise MemoryError(f'available host memory {int(available_bytes)} < required {need} bytes '
                          f'({"worker start" if starting_worker else "per window"}); not starting. Thresholds are not lowered.')
    return dict(available_bytes=int(available_bytes), required_bytes=need, stage='start' if starting_worker else 'window')


def await_memory_gate(*, starting_worker=True, side=T.TILE_SAMPLES, wait_s=0., poll_s=5.,
                      available_bytes=None, clock=None, sleeper=None):
    """Poll until the declared budget is free. Never lowers thresholds.

    `available_bytes` freezes a single sample (tests). Production callers leave it
    unset so each poll re-reads host memory. `wait_s<=0` is a single attempt.
    """
    from .sysmem import available_memory_bytes
    # Prefer the module `time` so existing Clock test doubles that only expose
    # perf_counter keep working; fall back to stdlib sleep when absent.
    import time as std_time
    clock = time.perf_counter if clock is None else clock
    sleeper = sleeper or getattr(time, 'sleep', None) or std_time.sleep
    deadline = clock() + max(0., float(wait_s))
    polls = 0
    started = clock()
    samples = []
    while True:
        polls += 1
        available = int(available_bytes) if available_bytes is not None else int(available_memory_bytes())
        samples.append(available)
        try:
            gate = memory_gate(available, starting_worker=starting_worker, side=side)
        except MemoryError:
            if available_bytes is not None or clock() >= deadline or float(wait_s) <= 0:
                raise
            sleeper(max(0.05, min(float(poll_s), deadline - clock())))
            continue
        gate = dict(gate, waited_s=float(clock() - started), polls=polls,
                    peak_available_bytes=max(samples), min_available_bytes=min(samples),
                    adaptive='wait-for-declared-budget')
        return gate


def gpu_gate():
    """Free GPU memory and absence of build_td_* processes. Returns a dict; raises RuntimeError when blocked."""
    import subprocess
    try:
        q = subprocess.run(['nvidia-smi', '--query-gpu=memory.free,utilization.gpu', '--format=csv,noheader,nounits'],
                           capture_output=True, text=True, timeout=20, check=True).stdout.strip().splitlines()[0]
        free, util = [int(v) for v in q.split(',')]
    except Exception as exc:
        raise RuntimeError(f'GPU gate: nvidia-smi unavailable: {exc}') from exc
    if free < GPU_FREE_MIB:
        raise RuntimeError(f'GPU gate: free {free} MiB < {GPU_FREE_MIB} MiB')
    from .sysmem import command_lines
    busy = [pid for pid, cmd in command_lines() if 'build_td_' in cmd or 'eval_td_speedup' in cmd]
    if busy:
        raise RuntimeError(f'GPU gate: build_td_*/speedup processes running: {busy}')
    if util > 10:
        raise RuntimeError(f'GPU gate: utilization {util}% > 10%')
    return dict(free_mib=free, utilization_percent=util, td_processes=[])


def tile_manifest_path(world_root, tile):
    return local_cache_dir(world_root, tile) / 'manifest.json'


def _identity(manifest):
    return hashlib.sha256(json.dumps({k: v for k, v in manifest.items() if k not in ('identity', 'source_path')},
                                     sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def tile_state(world_root, tile, *, plate_identity, world_layer_identity=None,island_identity=None,island_condition_policy=None,
               mountain_plan_identity=None,mountain_blend_policy=None):
    """Read-only. status 'unprepared' (no manifest), 'prepared' (matches the current plate/world layer) or 'stale'.

    A stale tile lists its reasons: other plate identity, other lineage / world-layer identity, a manifest whose own
    identity does not recompute, or the legacy format that put run-time fields (seconds, gate) into the identity.
    """
    mp = tile_manifest_path(world_root, tile)
    if not mp.is_file():
        return dict(status='unprepared', reasons=[])
    try:
        m = json.loads(mp.read_text(encoding='utf-8'))
        if not isinstance(m, dict):
            raise ValueError('manifest is not an object')
    except (OSError, ValueError) as exc:
        return dict(status='stale', reasons=[f'manifest unreadable: {exc}'])
    reasons = []
    if m.get('schema') != SCHEMA:
        reasons.append(f'schema {m.get("schema")!r} != {SCHEMA!r}')
    if m.get('plate_identity') != plate_identity:
        reasons.append(f'plate identity changed (cached {m.get("plate_identity")}, current {plate_identity})')
    expected_lineage = ([plate_identity] + ([world_layer_identity] if world_layer_identity else [])
                        + ([island_identity] if island_identity else [])
                        + ([mountain_plan_identity] if mountain_plan_identity else []))
    if m.get('mountain_plan_identity') != mountain_plan_identity:
        reasons.append('mountain plan identity changed (including removal)')
    if m.get('mountain_blend_policy') != mountain_blend_policy:
        reasons.append('mountain blend policy changed')
    if m.get('island_identity') != island_identity:
        reasons.append('island identity changed (including removal of an island product)')
    if m.get('island_condition_policy') != island_condition_policy:
        reasons.append('island condition policy changed')
    if m.get('lineage') != expected_lineage:
        reasons.append('lineage differs from the current plate/world-layer lineage')
    if m.get('world_layer_identity') != world_layer_identity:
        reasons.append(f'world layer identity changed (cached {m.get("world_layer_identity")}, current {world_layer_identity})')
    gen = m.get('generator')
    if isinstance(gen, dict) and RUNTIME_KEYS & set(gen):
        reasons.append('legacy format: run-time fields (' + ', '.join(sorted(RUNTIME_KEYS & set(gen))) + ') are inside the identity')
    try:
        if _identity(m) != m.get('identity'):
            reasons.append('manifest identity does not recompute')
    except (TypeError, ValueError) as exc:
        reasons.append(f'manifest identity not computable: {exc}')
    return dict(status='stale' if reasons else 'prepared', reasons=reasons)


def request_local(world_root, center_x_m, center_z_m, size_m, *, plate_identity=None, world_layer_identity=None,
                  island_identity=None,island_condition_policy=None,mountain_plan_identity=None,mountain_blend_policy=None):
    """Read-only. Returns per-tile status; unprepared tiles carry their window description and no data.

    With `plate_identity` the cached manifests are also compared with the current plate (and world layer) and
    mismatching tiles are reported as 'stale' (no path, never counted as prepared). Without it only presence is checked.
    """
    box = T.box_from_center(center_x_m, center_z_m, size_m)
    tl = T.tiles_for_box(*box)
    if len(tl) > T.MAX_TILES_PER_REQUEST:
        raise ValueError(f'request needs {len(tl)} tiles > {T.MAX_TILES_PER_REQUEST}')
    rows = []
    for t in tl:
        mp = tile_manifest_path(world_root, t['id'])
        if plate_identity is None and (island_identity is not None or mountain_plan_identity is not None):
            raise ValueError('plate identity is required to check island lineage')
        if plate_identity is None:
            st = dict(status='prepared' if mp.is_file() else 'unprepared', reasons=[])
            if mp.is_file():
                try:
                    cached = json.loads(mp.read_text(encoding='utf-8'))
                    if cached.get('island_identity') is not None or cached.get('mountain_plan_identity') is not None:
                        st = dict(status='stale',reasons=['cached island product is not selected; supply the current plate/island lineage'])
                except (OSError,ValueError,AttributeError):
                    st = dict(status='stale',reasons=['cached manifest unreadable'])
        else:
            st = tile_state(world_root, t['id'], plate_identity=plate_identity, world_layer_identity=world_layer_identity,
                            island_identity=island_identity,island_condition_policy=island_condition_policy,
                            mountain_plan_identity=mountain_plan_identity,mountain_blend_policy=mountain_blend_policy)
        if st['status'] == 'prepared':
            message = None
        elif st['status'] == 'stale':
            message = 'stale: ' + '; '.join(st['reasons']) + '; not usable, regenerate explicitly (tools/prepare_local30.py --regenerate-stale, GPU)'
        else:
            message = 'not prepared: run tools/prepare_local30.py (GPU) for this tile; queries never generate'
        rows.append(dict(t, status=st['status'], path=str(mp.parent) if st['status'] == 'prepared' else None,
                         message=message, stale_reasons=st['reasons']))
    return dict(box_m=list(box), tiles=rows, all_prepared=all(r['status'] == 'prepared' for r in rows))


def world_cells_from_pages(td_dir, ix, iz):
    """The 16 x 16 world-layer (960 m) elevation cells covered by tile (ix, iz), read from td-world pages. None if absent."""
    td_dir = Path(td_dir)
    plan = json.loads((td_dir / 'world-plan.json').read_text(encoding='utf-8'))
    fx, fz = plan['first_sample_xz_m']
    # world cell i has centre fx + 960*i and covers native [32*i + n0x, ...) with n0x = (fx-465)/30
    n0x, n0z = (fx - 465) // 30, (plan['first_sample_xz_m'][1] - 465) // 30
    cx0 = (ix * T.TILE_NATIVE - n0x) // T.WORLD_CELL_NATIVE
    cz0 = (iz * T.TILE_NATIVE - n0z) // T.WORLD_CELL_NATIVE
    n = T.TILE_NATIVE // T.WORLD_CELL_NATIVE
    shape = plan['shape_zx']
    core = plan['core_cells']
    out = np.full((n, n), np.nan)
    if cz0 < 0 or cx0 < 0 or cz0 + n > shape[0] or cx0 + n > shape[1]:
        return None
    for dz in range(n):
        for dx in range(n):
            cz, cx = cz0 + dz, cx0 + dx
            gz, gx = cz // core * core, cx // core * core
            page = td_dir / 'world-pages' / f'z{gz:04d}-x{gx:04d}' / 'elevation_960m.npy'
            if not page.is_file():
                return None
            out[dz, dx] = np.load(page, mmap_mode='r')[cz - gz, cx - gx]
    return out


def consistency(local_elev, world_cells):
    """Block-mean the 512 x 512 native core to 16 x 16 world cells and compare. Reported, never hidden."""
    n = T.TILE_NATIVE // T.WORLD_CELL_NATIVE
    core = np.asarray(local_elev, dtype=np.float64)[:T.TILE_NATIVE, :T.TILE_NATIVE]
    avg = core.reshape(n, T.WORLD_CELL_NATIVE, n, T.WORLD_CELL_NATIVE).mean(axis=(1, 3))
    w = np.asarray(world_cells, dtype=np.float64)
    d = avg - w
    return dict(cells=int(d.size), mae_m=float(np.abs(d).mean()), max_abs_m=float(np.abs(d).max()), bias_m=float(d.mean()),
                land_sea_agreement=float(np.mean((avg >= 0) == (w >= 0))),
                note='local 30 m is a decoded terrain; the world layer is the latent low-frequency field (about 100 m MAE between them upstream), so differences of this size are expected, not a defect')


def _status(elev):
    from scipy import ndimage
    below = elev < 0
    labels, count = ndimage.label(below)
    status = np.full(elev.shape, 5, dtype=np.uint8)           # land
    if count:
        edge = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
        edge = edge[edge > 0]
        status[below] = 4                                     # closed below sea unless it reaches the tile border
        status[np.isin(labels, edge)] = 3                     # ocean (connected to the border; may continue outside the tile)
    return status


def freeze_tile(world_root, ix, iz, elevation, *, purpose, reason, world_layer_identity, world_seed, plate_identity,
                consistency_report, generator_info, runtime=None,island_binding=None,mountain_binding=None):
    """Write the frozen product. Returns the manifest.

    `generator_info` is part of the identity and must be deterministic (no timings, no memory gates); run-time facts go
    in `runtime` and are written to runtime-stats.json next to the manifest, outside the identity.
    """
    bad = RUNTIME_KEYS & set(generator_info or {})
    if bad:
        raise ValueError(f'generator_info is part of the tile identity; run-time fields {sorted(bad)} belong in runtime=')
    if mountain_binding is not None and (island_binding is None
            or mountain_binding['island_identity'] != island_binding['island_identity']):
        raise ValueError('mountain plan requires its matching island binding')
    elev = np.ascontiguousarray(elevation, dtype=np.float32)
    if elev.shape != (T.TILE_SAMPLES, T.TILE_SAMPLES) or not np.isfinite(elev).all():
        raise ValueError('tile elevation must be finite 513 x 513')
    win = T.tile_window(ix, iz)
    root = local_cache_dir(world_root, win['id'])
    tmp = root.with_name(root.name + '.tmp')
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / 'layers').mkdir(parents=True)
    layers = {}
    for name, arr, meaning in (('elevation_m', elev, 'decoded 30 m terrain bed height; not water surface'),
                               ('status', _status(elev), '3 ocean(border-connected), 4 closed-below-sea, 5 land')):
        np.save(tmp / 'layers' / f'{name}.npy', arr)
        h = hashlib.sha256((tmp / 'layers' / f'{name}.npy').read_bytes()).hexdigest()
        layers[name] = dict(file=f'layers/{name}.npy', sha256=h, dtype=str(arr.dtype), unit='m' if name == 'elevation_m' else '1',
                            meaning=meaning, nodata=None)
    manifest = dict(
        schema=SCHEMA, ready=True, producer='terragenesis', algorithm_version='dream-td-periodic-decoded-1',
        lineage=[plate_identity] + ([world_layer_identity] if world_layer_identity else []), world_seed=world_seed,
        subseed_method='Terragenesis WorldPipeline seed = world_seed', subseeds={'terragenesis_pipeline': world_seed},
        declared_generated=['30 m elevation (decoded) for this tile', 'status derived from elevation<0'],
        limitations=['no rivers/lakes vectors in this product', 'status 4 vs 3 decided inside the tile only',
                     'last row/column duplicate the neighbour tile', 'differs from the 960 m world layer by the latent/decoded gap (see consistency)'],
        vectors={}, purpose=purpose, reason=reason, tile=win, world_layer_identity=world_layer_identity, plate_identity=plate_identity,
        consistency=consistency_report, generator=generator_info,
        grid=dict(first_sample_xz_m=win['first_sample_xz_m'], spacing_m=T.NATIVE_M, shape_zx=[T.TILE_SAMPLES, T.TILE_SAMPLES],
                  semantics='native-sample', axes='X east, Z south; arrays [z,x]', length_unit='m', sea_level_m=0),
        layers=layers)
    if island_binding is not None:
        manifest['island_identity'] = island_binding['island_identity']
        manifest['island_condition_policy'] = island_binding['condition_policy']
        manifest['lineage'].append(island_binding['island_identity'])
        manifest['ocean_island_binding'] = island_binding
        manifest['declared_generated'].append('TD condition samples the same frozen island product; output remains decoded/injected generator result')
        manifest['limitations'].append('Vector-aware condition is verified separately from TD model response; narrow islands/reefs may remain unresolved')
    if mountain_binding is not None:
        manifest['mountain_plan_identity'] = mountain_binding['plan_identity']
        manifest['mountain_blend_policy'] = mountain_binding['blend_policy']
        manifest['lineage'].append(mountain_binding['plan_identity'])
        manifest['mountain_binding'] = mountain_binding
        manifest['algorithm_version'] = 'dream-island-td-interior-derived-v1'
        manifest['declared_generated'] = ['Derived island interior: base + weight * (max(raw decoded, land floor) - base)',
                                          'Analytic frozen-island base exactly retained where weight is zero']
        manifest['limitations'] = ['Raw TD is an independent immutable product, referenced by identity and file SHA',
            'Frozen analytic island base, not a measured 30m surface; only qualified buffered interior contains TD detail',
            'Qualification uses fixed-grid approximate area and buffered-interior inscribed diameter, not exact island short axis',
            'Status 4 vs 3 decided inside tile; final boundary row/column duplicates neighbour samples']
        if 'peak_normalization' in mountain_binding:
            manifest['algorithm_version']='dream-island-area-peak-derived-v3'
            manifest['declared_generated']=['Whole-island native30m raw range and common scale: base*(1-w)+w*land_floor+scale*w*u',
                'Only complete ready components receive peak normalization; pending components retain analytic base']
            manifest['limitations']=['Peak is calibrated at complete island native30m samples, not continuous extrema',
                'Coast protection constraints and effective peak are recorded in the immutable normalization',
                'Raw TD immutable; final 2km world sampling may miss a 30m peak']
    manifest['identity'] = _identity(manifest)
    (tmp / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    stats = dict(note='run-time fields, deliberately outside manifest/identity', python=sys.version.split()[0],
                 numpy=np.__version__, **(runtime or {}))
    (tmp / 'runtime-stats.json').write_text(json.dumps(stats, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    _swap_dir(tmp, root)
    return manifest


def _swap_dir(tmp, root):
    """Put `tmp` in place of `root` without a window in which no copy exists: old -> backup, new -> root, then drop backup."""
    if not root.exists():
        tmp.replace(root)
        return
    backup = root.with_name(root.name + '.bak')
    if backup.exists():                                       # leftover of an earlier interrupted swap; root still exists
        shutil.rmtree(backup)
    root.replace(backup)
    try:
        tmp.replace(root)
    except BaseException:
        backup.replace(root)                                  # new directory did not land: put the old one back
        raise
    shutil.rmtree(backup, ignore_errors=True)


def prepare_tile(world_root, ix, iz, *, purpose, reason, plate_path, world_layer_identity=None, world_cells=None,
                 generator=None, available_bytes=None, terragenesis_root=None, reuse=True,island_product_path=None,
                 expected_island_identity=None,skeleton_run_path=None, memory_wait_s=0., memory_poll_s=5.):
    """Explicit preparation of one 513 x 513 tile.

    A cached tile is reused only when it matches the current plate identity, lineage and world-layer identity
    (see `tile_state`). A mismatching cache raises StaleTile and is not returned; pass reuse=False to regenerate it.
    When `memory_wait_s>0` and `available_bytes` is unset, the declared gate is polled until free; budgets are never lowered.
    Passing an existing `generator` uses the cheaper per-window stage so one worker can serve many tiles.
    """
    win = T.tile_window(ix, iz)
    from app.world_relief import td_resident
    _, plate_manifest = td_resident.read_plate(plate_path)
    binding = None
    if island_product_path is not None:
        from . import ocean_island_adapter as islands
        binding = islands.load_binding(plate_path,island_product_path,expected_island_identity,skeleton_run_path)
    elif expected_island_identity is not None or skeleton_run_path is not None:
        raise ValueError('island identity/run binding requires island_product_path')
    if reuse:
        st = tile_state(world_root, win['id'], plate_identity=plate_manifest['identity'], world_layer_identity=world_layer_identity,
                        island_identity=None if binding is None else binding.product.identity,
                        island_condition_policy=None if binding is None else binding.record['condition_policy'])
        if st['status'] == 'prepared':
            return json.loads(tile_manifest_path(world_root, win['id']).read_text(encoding='utf-8'))
        if st['status'] == 'stale':
            raise StaleTile(win['id'], st['reasons'])
    gate = await_memory_gate(starting_worker=generator is None, wait_s=memory_wait_s, poll_s=memory_poll_s,
                             available_bytes=available_bytes)
    started = time.perf_counter()
    if generator is None:
        gate['gpu'] = gpu_gate()
        generator = _default_generator(plate_path, terragenesis_root,island_product_path=island_product_path,
                                       expected_island_identity=expected_island_identity,skeleton_run_path=skeleton_run_path)
    elev = np.asarray(generator(tuple(win['origin_native_xz']), T.TILE_SAMPLES), dtype=np.float32)
    report = consistency(elev, world_cells) if world_cells is not None else dict(status='not-checked', reason='no world-layer cells supplied')
    return freeze_tile(world_root, ix, iz, elev, purpose=purpose, reason=reason, world_layer_identity=world_layer_identity,
                       world_seed=int(plate_manifest['config']['world_seed']), plate_identity=plate_manifest['identity'],
                       consistency_report=report,
                       generator_info=dict(kind='fake/injected' if getattr(generator, '__name__', '') != '_gpu_generate' else 'terragenesis-gpu'),
                       runtime=dict(seconds=time.perf_counter() - started, gate=gate, available_bytes=int(gate['available_bytes'])),
                       island_binding=None if binding is None else binding.record)


def _default_generator(plate_path, terragenesis_root, *, island_product_path=None,expected_island_identity=None,skeleton_run_path=None):
    """Single-process generator using the same periodic conditioning as the world layer. Needs GPU and the Terragenesis tree."""
    from app.world_relief import td_resident, td_pages
    root = td_pages.add_upstream(terragenesis_root or Path(__file__).resolve().parents[3] / '山川形意Terragenesis')
    import torch
    from diffusion.physical_config import PhysicalGenerationConfig
    from terrain_diffusion.inference.world_pipeline import WorldPipeline
    factory, manifest = td_resident.periodic_factory(plate_path, PhysicalGenerationConfig(),island_product_path=island_product_path,
                                                    expected_island_identity=expected_island_identity,skeleton_run_path=skeleton_run_path)
    seed = int(manifest['config']['world_seed'])

    class PlatePipeline(WorldPipeline):
        def _init_conditioning(self):
            self.synthetic_map_factory = factory

    pipeline = PlatePipeline.from_pretrained(str(Path(root) / 'models/terrain-diffusion-30m'), seed=seed, latents_batch_size=1,
                                             torch_compile=False, dtype=None, caching_strategy='direct', cache_limit=64 * 1024 * 1024,
                                             cond_snr=list(PhysicalGenerationConfig().cond_snr), log_mode='info')
    pipeline.to('cuda')
    pipeline.bind()

    def _gpu_generate(origin, side):
        x, z = origin
        with torch.inference_mode():
            out = pipeline.get(z, x, z + side, x + side, with_climate=False)['elev']
        return np.asarray(out.cpu().numpy() if hasattr(out, 'cpu') else out, dtype=np.float32)
    return _gpu_generate
