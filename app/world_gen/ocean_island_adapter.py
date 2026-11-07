"""Optional frozen-island bridge. Geometry and sampling live in Terragenesis.

Loading never prepares islands or starts TD. Original skeletons are read-only.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from .config import sha256_json

CONDITION_POLICY = 'frozen-islands-metric-periodic-condition-v1'
SURFACE_POLICY = 'frozen-islands-before-after-erosion-v1'


def _public_api():
    root = Path(__file__).resolve().parents[3] / '山川形意Terragenesis'
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from terrain_pipeline import ocean_islands, ocean_island_consumers
    return root, ocean_islands, ocean_island_consumers


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class IslandBinding:
    product: object
    record: dict


def load_binding(source_path, island_product_path, expected_identity, skeleton_run_path=None):
    """Strictly bind an existing island sidecar to its original plate source."""
    if not expected_identity:
        raise ValueError('expected island identity is required for an island product')
    root, core, _ = _public_api()
    source_path = Path(source_path).resolve()
    island_path = Path(island_product_path).resolve()
    source_sha, island_sha = file_sha(source_path), file_sha(island_path)
    source = core.PlateOceanSource.from_npz(source_path)
    product = core.load_product(island_path, expected_identity=expected_identity)
    if product.source.identity != source.identity:
        raise ValueError('island product belongs to a different skeleton identity')
    # Identity verification above binds full original manifests/arrays. Check
    # consumed arrays too, so a forged or future incompatible binding fails.
    for name in core.SOURCE_FIELDS:
        if not np.array_equal(getattr(source, name), getattr(product.source, name)):
            raise ValueError('island/source array mismatch: ' + name)
    if source.world_seed != product.source.world_seed or dict(source.grid) != dict(product.source.grid):
        raise ValueError('island/source seed or coordinate grid mismatch')
    quota = dict(status='unknown', target_fraction=None, tolerance_abs=None,
                 reason='no explicitly bound world config or skeleton-run supplied')
    if skeleton_run_path is not None:
        path = Path(skeleton_run_path).resolve()
        run = json.loads(path.read_text(encoding='utf-8'))
        payload = {k:v for k,v in run.items() if k not in ('identity', 'seconds', 'peak_rss_bytes')}
        if sha256_json(payload) != run.get('identity'):
            raise ValueError('skeleton-run identity mismatch')
        if run['product']['plate_identity'] != source.identity or run['product']['sha256'] != source_sha:
            raise ValueError('skeleton-run does not bind this source file/identity')
        with np.load(source_path, allow_pickle=False) as archive:
            original = json.loads(str(archive['manifest_json']))
        if run.get('config_identity') != original.get('world_config_identity'):
            raise ValueError('skeleton-run world config identity mismatch')
        targets = run['targets']
        target, tolerance = targets['ocean_fraction'], targets.get('ocean_tolerance_abs')
        if (type(target) not in (int,float) or not np.isfinite(target) or not 0<=target<=1
                or (tolerance is not None and (type(tolerance) not in (int,float) or not np.isfinite(tolerance) or tolerance<0))):
            raise ValueError('invalid source ocean target/tolerance')
        quota = dict(status='bound', target_fraction=target, tolerance_abs=tolerance,
                     source_path=str(path), source_sha256=file_sha(path), source_identity=run['identity'])
    record = dict(schema='dream-ocean-island-binding-v1', source_path=str(source_path), source_file_sha256=source_sha,
                  plate_identity=source.identity, source_world_seed=source.world_seed,
                  island_product_path=str(island_path), island_file_sha256=island_sha, island_identity=product.identity,
                  island_algorithm=product.manifest['algorithm'], island_world_seed=product.config.world_seed,
                  coordinates='absolute X east/Z south metres; finite source; cell-centre raster',
                  ocean_quota=quota, surface_policy=SURFACE_POLICY, condition_policy=CONDITION_POLICY,
                  condition_limitations='Finite product explicitly repeated for TD boundary sampling; periodic seams and TD model response are not verified.',
                  imported_sha256={rel:file_sha(root/rel) for rel in ('terrain_pipeline/ocean_islands.py','terrain_pipeline/ocean_island_consumers.py','terrain_pipeline/island_volcanoes.py')})
    if file_sha(source_path)!=source_sha or file_sha(island_path)!=island_sha:
        raise ValueError('source or island product changed while loading')
    record['identity'] = sha256_json(record)
    return IslandBinding(product, record)


def compose_world(binding, elevation_m, first_xz_m, spacing_m):
    """Sample the public frozen geometry after original coast cleanup."""
    _, _, consumers = _public_api()
    shape = elevation_m.shape
    x = first_xz_m[0] + np.arange(shape[1])[None,:]*spacing_m
    z = first_xz_m[1] + np.arange(shape[0])[:,None]*spacing_m
    fields = consumers.compose_surface(binding.product,x,z,elevation_m)
    bounds = (first_xz_m[0]-spacing_m/2,first_xz_m[1]-spacing_m/2,
              first_xz_m[0]+(shape[1]-.5)*spacing_m,first_xz_m[1]+(shape[0]-.5)*spacing_m)
    fractions = consumers.rasterize(binding.product,bounds,spacing_m,2)
    return fields, fractions


def restore_after_erosion(initial_fields, eroded_elevation):
    """Restore saved island targets, never compose already-blended heights twice."""
    weight = initial_fields['protection_weight']
    elevation = np.asarray(eroded_elevation,dtype=float) + weight*(initial_fields['elevation_m']-eroded_elevation)
    elevation = elevation.astype(np.float32)
    lagoon = initial_fields['lagoon'] & (elevation<0)
    _, _, consumers = _public_api()
    return elevation, consumers.connected_ocean(elevation,lagoon), lagoon


def condition_height(binding, x_m, z_m, original_height):
    _, _, consumers = _public_api()
    return consumers.sample_td_condition(binding.product,x_m,z_m,original_height,periodic=True)['elevation_m']


def quota_statistics(binding, before_elevation, final_elevation):
    target = binding.record['ocean_quota']['target_fraction']
    tolerance = binding.record['ocean_quota']['tolerance_abs']
    before, after = float((before_elevation<0).mean()), float((final_elevation<0).mean())
    difference = None if target is None else after-target
    return dict(method='negative surface fraction on identical world cell centres; connected ocean reported separately',
                original_fraction=before, final_fraction=after, change_fraction=after-before,
                target_fraction=target,tolerance_abs=tolerance,target_deviation_fraction=difference,
                within_tolerance=None if difference is None or tolerance is None else abs(difference)<=tolerance,
                sea_level_adjusted=False)


def feature_records(binding):
    return [asdict(feature) for feature in binding.product.features]
