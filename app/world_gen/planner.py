"""Read a normalized world config and produce a deterministic generation plan (plan.json). CPU only, no generation.

The plan lists: world layer (960 m, pages, GPU time estimate with its basis), skeleton (reuse or new + plan() pre-check),
and 30 m local regions (only the sites registered in the config; nothing unregistered is scheduled).
Identity = SHA-256 of the canonical plan JSON without volatile fields (created_at, free-memory readings).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from . import tiles as T
from .config import SCHEMA as CONFIG_SCHEMA, sha256_json

PLAN_SCHEMA = 'dream-world-plan-v1'
ROOT = Path(__file__).resolve().parents[2]
TD_DIR = ROOT / 'artifacts' / 'td-world'
LAND_WARNING = 'Estimates are inference time only (model loading excluded unless stated); not a wall-clock guarantee.'


def local_cache_dir(world_root, tile):
    return Path(world_root) / 'local30' / tile


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _skeleton_section(cfg, td_dir, verify):
    sk = cfg['skeleton']
    if sk['source'] == 'new':
        from . import skeleton
        pre = skeleton.plan_skeleton(cfg)
        return dict(source='new', action='generate (explicit CLI; the planner never starts it)',
                    command="python tools/generate_world_skeleton.py --config <config.json>",
                    plates=sk['plates'], cell_size_km=sk['cell_size_km'], steps=sk['steps'],
                    precheck=pre, will_run_here=False)
    path = Path(sk['path'])
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    out = dict(source='existing', path=str(path), expected_identity=sk['identity'], exists=path.is_file(), action='reuse',
               will_run_here=False, verified_by_load_product=None)
    if verify and path.is_file():
        try:
            from . import skeleton
            _, tp = skeleton._terragenesis()
            tp.load_product(path, expected_identity=sk['identity'])
            out['verified_by_load_product'] = True
        except Exception as exc:                       # identity mismatch or unreadable product
            out['verified_by_load_product'] = False
            out['verify_error'] = f'{type(exc).__name__}: {exc}'[:300]
    return out


def _world_layer_section(cfg, skeleton, td_dir):
    layer, w = cfg['world_layer'], cfg['world']
    wp = _load_json(td_dir / 'world-plan.json')
    summ = _load_json(td_dir / 'generation-summary.json')
    est = _load_json(td_dir / 'speedup-test' / 'estimate.json')
    area = w['width_km'] * w['height_km']
    out = dict(spacing_m=layer['spacing_m'], coast_buffer_km=layer['coast_buffer_km'], algorithm='dream-td-periodic-latent-1',
               product_format='world-map-product (layers read by map_source adapter)', will_run_here=False)
    reuse = bool(wp and skeleton['source'] == 'existing' and wp.get('plate_identity') == skeleton['expected_identity']
                 and layer['spacing_m'] == wp.get('spacing_m'))
    if reuse:
        pages = wp['pages']
        done = len(list((td_dir / 'world-pages').glob('z*-x*/elevation_960m.npy'))) if (td_dir / 'world-pages').is_dir() else 0
        out.update(status='existing-plan-matches-skeleton', plan_identity=wp['plan_identity'], world_seed=wp['world_seed'],
                   pages_total=len(pages), pages_on_disk=done, page_side_native=wp['page_side_native'],
                   core_cells=wp['core_cells'], shape_zx=wp['shape_zx'], pages_remaining=len(pages) - done)
        per_page = (summ or {}).get('sum_page_inference_seconds', 0) / max(1, (summ or {}).get('completed_pages', 0))
        if per_page:
            out['gpu_estimate'] = dict(basis=f'generation-summary.json: {summ["completed_pages"]} pages, sum_page_inference_seconds={summ["sum_page_inference_seconds"]:.1f}',
                                       seconds_per_page_measured=per_page, remaining_hours=out['pages_remaining'] * per_page / 3600,
                                       full_world_hours_measured=summ['elapsed_seconds_this_invocation'] / 3600,
                                       peak_rss_mib=summ.get('peak_child_rss_mib'), reserved_gpu_mib=summ.get('reserved_peak_mib'))
    else:
        out['status'] = 'needs-generation'
    if est:
        rows = est['rows']
        ratio = est['covered_over_land']
        land = area * (1 - w['ocean_fraction'])
        covered = min(area, land * ratio)
        out['gpu_estimate_by_area'] = dict(
            basis='speedup-test/estimate.json seconds_per_km2 (inference only, 1600x1280 reference world), covered area = land * %.3f' % ratio,
            land_km2=land, covered_km2=covered,
            hours_fast_fp32_b8_k120=covered * rows['fast-fp32-b8-k120']['seconds_per_km2'] / 3600,
            hours_old=covered * rows['old']['seconds_per_km2'] / 3600,
            estimated_pages=math.ceil(covered * (1175 / est['world_covered_km2'])))
    out['disk_estimate_bytes'] = None if not reuse else sum(1 for _ in range(len(wp['pages']))) * (32 * 32 * 4 + 2048)
    # The world layer that is actually built now is the fast procedural 2 km layer (terrain-generation-rules.md section 6);
    # the 960 m TD fields above are kept for the legacy TD world plan only.
    from . import estimates
    fl = estimates.fast_layer(w['width_km'], w['height_km'])
    out['fast_layer_2km'] = dict(algorithm='dream-fast-relief-3 (relief=orogen)', device='cpu', spacing_m=fl['spacing_m'],
                                 nodes=fl['nodes'], cpu_seconds=fl['cpu_seconds'], peak_memory_mb=fl['peak_mb'],
                                 disk_bytes_approx=fl['nodes'] * 4 * 7, basis=fl['basis'], how=fl['how'],
                                 command='<Terragenesis venv python> tools/build_fast_relief.py --skeleton <skeleton.npz> --out <dir> --relief orogen')
    return out


def _local_section(cfg, world_root, rate):
    sites, all_tiles = [], {}
    problems = []
    for s in cfg['local_sites']:
        box = T.box_from_center(s['center_x_m'], s['center_z_m'], s['size_m'])
        tl = T.tiles_for_box(*box)
        entry = dict(id=s['id'], type=s['type'], reason=s['reason'], center_xz_m=[s['center_x_m'], s['center_z_m']],
                     size_m=s['size_m'], request_box_m=list(box), tiles=[t['id'] for t in tl], tile_count=len(tl))
        if len(tl) > T.MAX_TILES_PER_REQUEST:
            entry['status'] = 'rejected-too-large'
            problems.append(f"{s['id']}: {len(tl)} tiles > {T.MAX_TILES_PER_REQUEST}")
        else:
            entry['status'] = 'planned'
            for t in tl:
                all_tiles.setdefault(t['id'], t)
        sites.append(entry)
    tile_rows = []
    for tid, t in sorted(all_tiles.items()):
        ready = (local_cache_dir(world_root, tid) / 'manifest.json').is_file()
        tile_rows.append(dict(t, prepared=ready))
    todo = [t for t in tile_rows if not t['prepared']]
    cost = T.tile_cost(rate, len(todo))
    return dict(
        lattice=dict(spacing_m=T.NATIVE_M, tile_native=T.TILE_NATIVE, tile_samples=T.TILE_SAMPLES,
                     world_cells_per_tile=T.TILE_NATIVE // T.WORLD_CELL_NATIVE, max_tiles_per_request=T.MAX_TILES_PER_REQUEST,
                     semantics='native sample n at X = 30*n m; last row/column duplicate the neighbour tile'),
        sites=sites, tiles=tile_rows, tiles_unique=len(tile_rows), tiles_to_generate=len(todo),
        gpu_estimate=dict(basis=rate['basis'] + ('  [FALLBACK constants]' if rate['fallback'] else ''),
                          seconds_per_tile=T.TILE_SAMPLES ** 2 * rate['seconds_per_native_px'],
                          inference_seconds_total=cost['inference_seconds'],
                          model_loading_seconds_warm=rate['model_loading_seconds'],
                          model_loading_seconds_cold=rate['cold_model_loading_seconds'],
                          reserved_gpu_mib=rate['reserved_peak_mib'], disk_bytes=cost['disk_bytes']),
        unregistered_regions='not scheduled: only registered local_sites are planned',
        problems=problems)


def build_plan(cfg, *, out_root=None, td_dir=None, verify_skeleton=True, benchmark_path=None):
    td_dir = Path(td_dir) if td_dir else TD_DIR
    out_root = Path(out_root) if out_root else ROOT / 'artifacts' / 'worlds'
    world_root = out_root / cfg['world_name']
    skeleton = _skeleton_section(cfg, td_dir, verify_skeleton)
    plan = dict(schema=PLAN_SCHEMA, config_schema=CONFIG_SCHEMA, config_identity=cfg['identity'], world_name=cfg['world_name'],
                world_seed=cfg['world_seed'], world=cfg['world'], map_style=cfg['map_style'],
                skeleton=skeleton, world_layer=_world_layer_section(cfg, skeleton, td_dir),
                local=_local_section(cfg, world_root, T.decoded_rate(benchmark_path)),
                notes=[LAND_WARNING,
                       'Planning does not generate anything; every GPU step is a separate explicit command with a memory/GPU gate.',
                       'World-layer and local 30 m heights come from the same generator but different outputs (latent vs decoded); '
                       'their means differ by a measured tens-to-~100 m, reported by the consistency check, not hidden.'])
    plan['identity'] = sha256_json(plan)
    return plan


def write_plan(plan, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding='utf-8')
    return path
