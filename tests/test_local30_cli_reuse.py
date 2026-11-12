"""One lazily started model for a whole `tools/prepare_local30.py` run.

The CLI used to call `local30.prepare_tile` without a generator, so every tile built its own
`WorldPipeline` (that is what a run of uncached tiles paid per tile). It now passes one shared,
lazily started worker: a matching frozen tile is returned before the generator is touched, and the
model is loaded at the first real window.

Everything here is injected: the plate reader, the gates, the worker factory and the generator.
Counts are **model-initialisation counts under injection**, not GPU timings: these tests prove the
scheduling/deduplication logic and that the frozen product is unchanged, **not** real GPU throughput or
memory. No real 30 m model is loaded and no `saves/` or world artifact is written.
"""
import importlib.util
import json
import re
import types
from pathlib import Path

import numpy as np
import pytest

from app.world_gen import local30, sysmem

ROOT = Path(__file__).resolve().parents[1]
PLATE_IDENTITY = 'a' * 64
ISLAND_IDENTITY = 'c' * 64
CONDITION_POLICY = 'periodic-repeat-and-restore'
WORLD_SEED = 20260903
ENOUGH_BYTES = 8 * 2 ** 30
CLI = None


def cli():
    """`tools/prepare_local30.py` loaded as a module (it is a script, not part of the package)."""
    global CLI
    if CLI is None:
        spec = importlib.util.spec_from_file_location('prepare_local30_under_test', ROOT / 'tools' / 'prepare_local30.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        CLI = module
    return CLI


class Recorder:
    """Counts model initialisations and windows; can fail on demand like the real gates/model do."""

    def __init__(self):
        self.available_bytes = ENOUGH_BYTES
        self.inits = []
        self.windows = []
        self.gpu_gates = 0
        self.fail_at = None

    def default_generator(self, plate_path, terragenesis_root, **kwargs):
        self.inits.append(dict(plate_path=plate_path, terragenesis_root=terragenesis_root, **kwargs))
        if self.fail_at == 'factory':
            raise RuntimeError('CUDA out of memory while loading the 30 m model')

        def generate(origin, side):
            self.windows.append((tuple(origin), int(side)))
            if self.fail_at == 'window':
                raise RuntimeError('CUDA out of memory during decode')
            # A deterministic function of origin and side: two tiles never get the same field, so an
            # origin mix-up or a swapped window would show up as an array difference.
            z, x = np.mgrid[0:side, 0:side]
            return ((x + origin[0]) * 0.5 + (z + origin[1]) * 0.25).astype(np.float32)

        generate.__name__ = '_gpu_generate'
        return generate

    def gpu_gate(self):
        self.gpu_gates += 1
        if self.fail_at == 'gpu':
            raise RuntimeError('GPU gate: free 512 MiB < 4096 MiB')
        return dict(free_mib=8192, utilization_percent=0, td_processes=[])

    def reset_counts(self):
        self.inits.clear()
        self.windows.clear()
        self.gpu_gates = 0


@pytest.fixture
def rig(tmp_path, monkeypatch):
    """Injected plate + gates + worker factory. No GPU is ever queried and no real model is loaded."""
    rec = Recorder()
    plate = tmp_path / 'skeleton.npz'
    monkeypatch.setattr('app.world_relief.td_resident.read_plate',
                        lambda path: (np.zeros((2, 2), np.float32),
                                      dict(identity=PLATE_IDENTITY, config=dict(world_seed=WORLD_SEED))))
    monkeypatch.setattr(local30, '_default_generator', rec.default_generator)
    monkeypatch.setattr(local30, 'gpu_gate', rec.gpu_gate)
    monkeypatch.setattr(sysmem, 'available_memory_bytes', lambda: rec.available_bytes)
    monkeypatch.setattr(local30, 'world_cells_from_pages', lambda *a, **k: None)
    monkeypatch.setattr(cli(), 'TERRAGENESIS', tmp_path / 'Terragenesis')
    return types.SimpleNamespace(rec=rec, plate=plate, tmp=tmp_path, world_root=tmp_path / 'worlds',
                                 cli=cli(), config=config_for(tmp_path, plate))


def config_for(tmp_path, plate, *, center_m=10000, size_m=12000, world_name='cli-reuse', file_name=None):
    """A registered 30 m site; `size_m` picks how many native tiles its box covers."""
    cfg = dict(world_name=world_name, world_seed=WORLD_SEED,
               skeleton=dict(source='existing', path=str(plate), identity=PLATE_IDENTITY),
               local_sites=[dict(id='harbour-town', type='town', center_x_m=center_m, center_z_m=center_m,
                                 size_m=size_m, reason='explicit 30 m preparation for the harbour town')])
    path = tmp_path / f'{file_name or world_name}.json'
    path.write_text(json.dumps(cfg), encoding='utf-8')
    return path


def run(rig, *extra):
    return rig.cli.main(['--config', str(rig.config), '--site', 'harbour-town', '--out-root', str(rig.world_root),
                         '--td-dir', str(rig.tmp / 'td-world'), *extra])


def manifests(rig):
    root = rig.world_root / 'cli-reuse' / 'local30'
    return {p.parent.name: json.loads(p.read_text(encoding='utf-8')) for p in sorted(root.glob('*/manifest.json'))}


PROGRESS_LINE = re.compile(r'^(x[+-]\d+z[+-]\d+) identity ([0-9a-f]{64}) consistency (\S+)$')


def progress_lines(stdout):
    """The CLI's per-tile stdout lines: '<tile> identity <sha> consistency <mae|None>'."""
    return [m.groups() for m in map(PROGRESS_LINE.match, stdout.splitlines()) if m]


def indices(tile_id):
    """`x+001z-002` -> (1, -2), matching `tiles.tile_id`."""
    m = re.fullmatch(r'x([+-]\d+)z([+-]\d+)', tile_id)
    assert m, tile_id
    return int(m.group(1)), int(m.group(2))


def test_uncached_tiles_share_one_model_initialisation(rig, capsys):
    assert run(rig) == 0
    out = capsys.readouterr().out
    got = manifests(rig)
    # The site box covers four native tiles; each is a real generation of the shared worker.
    assert len(got) == 4, sorted(got)
    assert len(rig.rec.inits) == 1, rig.rec.inits               # one model, not one per tile
    assert len(rig.rec.windows) == 4
    assert {w[1] for w in rig.rec.windows} == {513}
    # Real generator kind, not 'fake/injected': the shared worker keeps the GPU identity.
    assert {m['generator']['kind'] for m in got.values()} == {'terragenesis-gpu'}
    assert len({m['identity'] for m in got.values()}) == 4
    # Per-window admission is still paid per tile (the cheaper stage); the worker start is not repeated.
    stats = [json.loads((rig.world_root / 'cli-reuse' / 'local30' / t / 'runtime-stats.json').read_text(encoding='utf-8'))
             for t in got]
    assert {s['gate']['stage'] for s in stats} == {'window'}
    assert all(s['gate']['required_bytes'] == local30.memory_requirement_bytes(starting_worker=False) for s in stats)
    # One documented pre-flight GPU/memory check plus one at the first real window.
    assert rig.rec.gpu_gates == 2
    # Original stdout contract: one '<tile> identity <id> consistency <mae>' line per prepared tile.
    lines = progress_lines(out)
    assert len(lines) == 4
    assert {row[0] for row in lines} == set(got)
    assert {row[1] for row in lines} == {m['identity'] for m in got.values()}
    assert {row[2] for row in lines} == {'None'}                 # no world-layer cells in this injected run


def test_fully_cached_site_initialises_no_model(rig, capsys):
    assert run(rig) == 0
    assert len(rig.rec.inits) == 1
    rig.rec.reset_counts()
    capsys.readouterr()
    assert run(rig) == 0                                        # nothing left to prepare
    assert rig.rec.inits == [] and rig.rec.windows == []
    assert progress_lines(capsys.readouterr().out) == []


def test_cache_hit_returns_before_the_generator_even_when_one_is_supplied(rig):
    assert run(rig) == 0
    first = manifests(rig)
    rig.rec.reset_counts()
    worker = rig.cli.shared_worker(rig.plate, rig.cli.TERRAGENESIS)
    for tile, cached in first.items():
        ix, iz = indices(tile)
        again = local30.prepare_tile(rig.world_root / 'cli-reuse', ix, iz,
                                     purpose='local-30m', reason='cached reuse', plate_path=rig.plate,
                                     world_cells=None, generator=worker)
        assert again['identity'] == cached['identity']
    assert rig.rec.inits == [] and rig.rec.windows == []         # the model was never built


def tile_products(world_root):
    """Per-tile frozen product: manifest plus the two arrays it froze."""
    out = {}
    for path in sorted((Path(world_root) / 'local30').glob('*/manifest.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        out[manifest['tile']['id']] = dict(
            manifest=manifest,
            elevation=np.load(path.parent / manifest['layers']['elevation_m']['file']),
            status=np.load(path.parent / manifest['layers']['status']['file']))
    return out


def gate_stage(world_root, tile):
    stats = json.loads((Path(world_root) / 'local30' / tile / 'runtime-stats.json').read_text(encoding='utf-8'))
    return stats['gate']['stage']


def test_per_tile_generator_and_shared_worker_agree_on_the_product(rig, capsys):
    """Lossless check: one worker for four tiles must freeze what four workers froze.

    Same site, same purpose/reason, same plate and world-layer binding, same world cells; only the generator
    plumbing differs (a model per tile before, one model per run now). So the frozen elevation, the derived
    status and the manifest identity must be equal — the run-time fields (gate stage, seconds) live in
    runtime-stats.json, outside the identity, and are expected to differ.
    """
    reason = 'explicit 30 m preparation for the harbour town'
    assert run(rig) == 0                                        # new path: one worker, four windows
    assert len(rig.rec.inits) == 1 and len(rig.rec.windows) == 4
    new = tile_products(rig.world_root / 'cli-reuse')
    rig.rec.reset_counts()
    capsys.readouterr()

    # Pre-change loop body: `prepare_tile` per tile with no generator=, hence a fresh model per tile.
    old_root = rig.tmp / 'worlds-old' / 'cli-reuse'
    todo = [(t['ix'], t['iz']) for t in local30.request_local(
        old_root, 10000, 10000, 12000, plate_identity=PLATE_IDENTITY)['tiles']]
    assert len(todo) == 4
    for ix, iz in todo:
        local30.prepare_tile(old_root, ix, iz, purpose='local-30m', reason=reason, plate_path=rig.plate,
                             world_cells=None, world_layer_identity=None,
                             terragenesis_root=rig.cli.TERRAGENESIS, reuse=True)
    assert len(rig.rec.inits) == 4                              # the old path really initialised per tile
    old = tile_products(old_root)

    assert set(old) == set(new) and len(old) == 4
    # The four tiles really are four different surfaces, so the equality below is not a constant field.
    assert len({new[t]['elevation'].tobytes() for t in new}) == 4
    for tile in new:
        assert np.array_equal(old[tile]['elevation'], new[tile]['elevation']), tile
        assert np.array_equal(old[tile]['status'], new[tile]['status']), tile
        assert old[tile]['manifest']['identity'] == new[tile]['manifest']['identity'], tile
        # Everything the identity is built from matches, including the recorded generator kind.
        for key in ('purpose', 'reason', 'plate_identity', 'world_layer_identity', 'world_seed', 'lineage',
                    'consistency', 'generator', 'algorithm_version', 'grid', 'layers'):
            assert old[tile]['manifest'][key] == new[tile]['manifest'][key], (tile, key)
        assert new[tile]['manifest']['generator']['kind'] == 'terragenesis-gpu'
        # The only difference is the run-time admission stage, which is deliberately outside the identity.
        assert gate_stage(old_root, tile) == 'start'
        assert gate_stage(rig.world_root / 'cli-reuse', tile) == 'window'


def test_partially_cached_site_initialises_once(rig, capsys):
    # Same world root, smaller box: only tile (0, 0) — one tile of the four the full site needs.
    warm = config_for(rig.tmp, rig.plate, center_m=7000, size_m=4000, file_name='warm-site')
    assert rig.cli.main(['--config', str(warm), '--site', 'harbour-town', '--out-root', str(rig.world_root),
                         '--td-dir', str(rig.tmp / 'td-world')]) == 0
    assert len(rig.rec.inits) == 1 and len(rig.rec.windows) == 1
    rig.rec.reset_counts()
    capsys.readouterr()
    assert run(rig) == 0
    assert len(rig.rec.inits) == 1                               # one model for the three missing tiles
    assert len(rig.rec.windows) == 3
    assert len(manifests(rig)) == 4


def test_source_parameters_reach_the_worker_and_the_manifest(rig, monkeypatch, capsys):
    binding = types.SimpleNamespace(product=types.SimpleNamespace(identity=ISLAND_IDENTITY),
                                    record=dict(schema='fake-island-binding-v1', island_identity=ISLAND_IDENTITY,
                                                condition_policy=CONDITION_POLICY))
    seen = []

    def load_binding(source_path, island_product_path, expected_identity, skeleton_run_path=None):
        seen.append(dict(source_path=source_path, island_product_path=island_product_path,
                         expected_identity=expected_identity, skeleton_run_path=skeleton_run_path))
        return binding

    monkeypatch.setattr('app.world_gen.ocean_island_adapter.load_binding', load_binding)
    island_path, run_path = rig.tmp / 'islands.npz', rig.tmp / 'skeleton-run.json'
    assert rig.cli.main(['--config', str(rig.config), '--site', 'harbour-town', '--out-root', str(rig.world_root),
                         '--td-dir', str(rig.tmp / 'td-world'), '--island-product-path', str(island_path),
                         '--expected-island-identity', ISLAND_IDENTITY,
                         '--skeleton-run', str(run_path), '--world-layer-identity', 'w' * 64]) == 0
    capsys.readouterr()
    assert len(rig.rec.inits) == 1
    init = rig.rec.inits[0]
    assert init['plate_path'] == rig.plate
    assert init['terragenesis_root'] == rig.cli.TERRAGENESIS
    assert init['island_product_path'] == str(island_path)
    assert init['expected_island_identity'] == ISLAND_IDENTITY
    assert init['skeleton_run_path'] == str(run_path)
    # The binding is still resolved once for the run and passed to every tile preparation.
    assert len(seen) >= 2                       # CLI pre-flight report + prepare_tile per tile
    assert {row['expected_identity'] for row in seen} == {ISLAND_IDENTITY}
    assert {row['skeleton_run_path'] for row in seen} == {str(run_path)}
    got = manifests(rig)
    assert len(got) == 4
    for manifest in got.values():
        assert manifest['island_identity'] == ISLAND_IDENTITY
        assert manifest['island_condition_policy'] == CONDITION_POLICY
        assert manifest['world_layer_identity'] == 'w' * 64
        assert manifest['lineage'] == [PLATE_IDENTITY, 'w' * 64, ISLAND_IDENTITY]
        assert manifest['world_seed'] == WORLD_SEED
        assert 'seconds' not in manifest['generator'] and 'gate' not in manifest['generator']


def test_worker_start_memory_gate_is_lazy_and_keeps_its_threshold(rig, capsys):
    rig.rec.available_bytes = 1 * 2 ** 30                        # far below the declared worker budget
    assert run(rig) == 2                                        # pre-flight report blocks, nothing generated
    assert rig.rec.inits == [] and rig.rec.windows == []
    worker = rig.cli.shared_worker(rig.plate, rig.cli.TERRAGENESIS)
    with pytest.raises(MemoryError, match='Thresholds are not lowered'):
        worker((0, 0), 513)
    assert rig.rec.inits == []                                  # no model behind a blocked gate
    capsys.readouterr()


def test_gpu_gate_error_propagates_unchanged(rig, capsys, monkeypatch):
    monkeypatch.setattr(local30, 'await_memory_gate', lambda **kw: dict(available_bytes=ENOUGH_BYTES,
                                                                      required_bytes=1, stage='start'))
    rig.rec.fail_at = 'gpu'
    assert run(rig) == 2                                        # the CLI pre-flight reports the block
    capsys.readouterr()
    assert rig.rec.inits == []
    worker = rig.cli.shared_worker(rig.plate, rig.cli.TERRAGENESIS)
    with pytest.raises(RuntimeError, match='GPU gate: free 512 MiB'):
        worker((0, 0), 513)
    assert rig.rec.inits == []
    with pytest.raises(RuntimeError, match='GPU gate: free 512 MiB'):
        local30.prepare_tile(rig.world_root / 'cli-reuse', 0, 0, purpose='local-30m', reason='gate error',
                             plate_path=rig.plate, generator=worker, reuse=False)
    assert not (rig.world_root / 'cli-reuse' / 'local30').exists()


def test_generator_error_stops_the_run_without_retrying_per_tile(rig, capsys):
    rig.rec.fail_at = 'factory'
    with pytest.raises(RuntimeError, match='CUDA out of memory'):
        run(rig)
    capsys.readouterr()
    assert len(rig.rec.inits) == 1                              # the first window fails; no per-tile retry
    assert rig.rec.windows == []
    assert not (rig.world_root / 'cli-reuse' / 'local30').exists()
    rig.rec.reset_counts()
    rig.rec.fail_at = 'window'
    with pytest.raises(RuntimeError, match='CUDA out of memory during decode'):
        run(rig)
    capsys.readouterr()
    assert len(rig.rec.inits) == 1 and len(rig.rec.windows) == 1
    assert not (rig.world_root / 'cli-reuse' / 'local30').exists()


def test_fully_cached_run_needs_no_gpu_at_all(rig, capsys):
    assert run(rig) == 0
    rig.rec.reset_counts()
    capsys.readouterr()
    # Nothing to prepare: the run returns before the blocked-GPU branch, so a prepared world is readable on a host
    # whose GPU is busy. Same as before the change (the `not todo` early exit); the lazy worker makes it literal.
    rig.rec.fail_at = 'gpu'
    rig.rec.available_bytes = 1 * 2 ** 30
    assert run(rig) == 0
    assert rig.rec.inits == [] and rig.rec.windows == []


def test_regenerate_stale_reuses_one_worker(rig, capsys):
    assert run(rig) == 0
    rig.rec.reset_counts()
    capsys.readouterr()
    # A different world-layer identity makes every cached tile stale; --regenerate-stale replaces them.
    assert run(rig, '--regenerate-stale', '--world-layer-identity', 'w' * 64) == 0
    out = capsys.readouterr().out
    assert len(rig.rec.inits) == 1                               # still one model, even though nothing is reused
    assert len(rig.rec.windows) == 4
    lines = progress_lines(out)
    assert len(lines) == 4 and {row[2] for row in lines} == {'None'}
    got = manifests(rig)
    assert {m['world_layer_identity'] for m in got.values()} == {'w' * 64}
    assert all(m['lineage'] == [PLATE_IDENTITY, 'w' * 64] for m in got.values())
    assert {m['generator']['kind'] for m in got.values()} == {'terragenesis-gpu'}


def test_unregistered_tile_branch_also_shares_one_worker(rig, capsys):
    # `--tile` (unregistered) takes its plate from the config and needs an explicit --reason. It is the same loop
    # body as `--site`, so it must use the shared worker too: injected generator, real generator kind, cache reuse.
    args = ['--config', str(rig.config), '--tile', '0', '0', '--reason', 'explicit neighbour',
            '--out-root', str(rig.world_root), '--td-dir', str(rig.tmp / 'td-world')]
    assert rig.cli.main(args) == 0
    out = capsys.readouterr().out
    assert len(rig.rec.inits) == 1
    assert len(rig.rec.windows) == 1
    got = manifests(rig)
    assert set(got) == {'x+000z+000'}
    assert got['x+000z+000']['reason'] == 'explicit neighbour'
    assert got['x+000z+000']['generator']['kind'] == 'terragenesis-gpu'
    assert len(progress_lines(out)) == 1
    # Second run: the tile is cached, so no model at all.
    rig.rec.reset_counts()
    assert rig.cli.main(args) == 0
    capsys.readouterr()
    assert rig.rec.inits == [] and rig.rec.windows == []


def test_dry_run_never_touches_the_worker(rig, capsys):
    assert run(rig, '--dry-run') == 0
    report = json.loads(capsys.readouterr().out)
    assert len(report['tiles_to_prepare']) == 4
    assert 'blocked' not in report['memory_gate'] and 'blocked' not in report['gpu_gate']
    assert rig.rec.inits == [] and rig.rec.windows == []
    assert not (rig.world_root / 'cli-reuse' / 'local30').exists()
