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

# Audited frozen producers -> current reader with old paths retained. The
# complete stack is registered, so an unrelated live code change fails closed.
FROZEN_V3_STACK = {
    'terrain_pipeline/ocean_islands.py': '1c683938cf9d280b662c5cc1a29aa46f200dcfb3c03e5d09761df375e4a1d8ca',
    'terrain_pipeline/ocean_island_consumers.py': '0b80d6973286dd77bab6ad8eb4dc5ae17965a6584b0f5b706f39465fa371a4b5',
}
FROZEN_V4_STACK = dict(FROZEN_V3_STACK, **{
    'terrain_pipeline/ocean_islands.py': 'e6416975d97b494b3b6093e5eb180769e6870d9aae96ae72b62b8226223a9f78',
    'terrain_pipeline/island_volcanoes.py': 'fc9be55a1ec83bf8c84c08f6facc7ed12527e85e3f56b275214c39edfa6a848a',
})
FROZEN_V3_READER_STACK = dict(FROZEN_V4_STACK, **{
    'terrain_pipeline/ocean_islands.py': '81a4a36ba84d59817d84ce94e88e387f18a80dc1c75eaec06f2e90b612c3a34b',
    'terrain_pipeline/island_volcanoes.py': '07605199ac400516f1519a2d2f3428a9ad71a90736d7bc578b0f1539cc66c7ef',
    'terrain_pipeline/island_volcanoes_v4.py': 'fc9be55a1ec83bf8c84c08f6facc7ed12527e85e3f56b275214c39edfa6a848a',
})
# Current producer for ocean-islands-volcanic-edifices-v5 (audited 2026-11-08 against live TG).
# Same file digests as FROZEN_V3_READER_STACK today; kept as a named generation so later
# TG edits register a new stack instead of silently breaking v5 worlds.
FROZEN_V5_READER_STACK = dict(FROZEN_V3_READER_STACK)
_V5_ALGORITHM = 'ocean-islands-volcanic-edifices-v5'
_COMPATIBLE_READERS = (FROZEN_V3_READER_STACK, FROZEN_V5_READER_STACK)
# Audited 2026-11-10: the saved 10000x8000 v5 product cold-reads with the
# same full manifest, identity and every sampled query array bit-for-bit.
# Evidence: artifacts/island-cluster-improvement-20261110/legacy-reader-verification.json.
# Only this exact old -> new stack is admitted; unrelated source changes fail closed.
FROZEN_CLUSTERED_READER_STACK = dict(FROZEN_V5_READER_STACK, **{
    'terrain_pipeline/ocean_islands.py': 'f5d390920b3cce257b96f572965d19549de12cb9f9209c2052efda2ef1c2f517',
})
FROZEN_V5_TO_CLUSTERED_READER = {
    'saved': FROZEN_V5_READER_STACK,
    'current': FROZEN_CLUSTERED_READER_STACK,
}


def _audited_clustered_reader_transition(saved, current):
    """True only for the registered exact pair of reader stacks for the clustered layout.

    The clustered-provinces preset keeps v5 geometry for the old configuration (the layout
    selector defaults to 'absolute-slots-v1'), so an old sidecar can be read by the new
    reader; that is still a digest change and is allowed only for this measured pair.
    """
    registered = FROZEN_V5_TO_CLUSTERED_READER
    if not isinstance(registered, dict):
        return False
    return saved == registered.get('saved') and current == registered.get('current')


def validate_saved_binding(recorded, current):
    """Compare all data bindings; permit only registered frozen reader stacks."""
    for row in (recorded, current):
        if row.get('identity') != sha256_json({k: v for k, v in row.items() if k != 'identity'}):
            raise ValueError('ocean island binding identity mismatch')
    data = lambda row: {k: v for k, v in row.items() if k not in ('identity', 'imported_sha256')}
    if data(recorded) != data(current):
        raise ValueError('world mountain source/island/run binding differs')
    old, new = recorded.get('imported_sha256'), current.get('imported_sha256')
    algo = recorded.get('island_algorithm')
    if old == new:
        policy = 'identical-producer-stack'
    elif (algo == 'ocean-islands-metric-detail-smooth-seabed-v3' and
          ((old == FROZEN_V3_STACK and new in (FROZEN_V4_STACK, *_COMPATIBLE_READERS)) or
           (old == FROZEN_V4_STACK and new in _COMPATIBLE_READERS))):
        policy = 'audited-frozen-v3-reader-stack'
    elif (algo == 'ocean-islands-volcanic-stages-v4' and
          old == FROZEN_V4_STACK and new in _COMPATIBLE_READERS):
        policy = 'audited-frozen-v4-reader-stack'
    elif (algo == _V5_ALGORITHM and
          old in _COMPATIBLE_READERS and new in _COMPATIBLE_READERS):
        policy = 'audited-frozen-v5-reader-stack'
    elif (algo == _V5_ALGORITHM and _audited_clustered_reader_transition(old, new)):
        # Only the single registered old-v5 -> clustered-reader pair, and only while that
        # declared reader is byte-identical to the one an old v5 world was frozen against.
        policy = 'audited-v5-old-to-clustered-reader'
    else:
        raise ValueError('world mountain island producer stack changed without compatible frozen reader')
    return dict(policy=policy, saved_binding_identity=recorded['identity'],
                consumer_binding_identity=current['identity'], consumer_imported_sha256=new)


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
                  imported_sha256={rel:file_sha(root/rel) for rel in ('terrain_pipeline/ocean_islands.py','terrain_pipeline/ocean_island_consumers.py','terrain_pipeline/island_volcanoes.py','terrain_pipeline/island_volcanoes_v4.py')})
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
