"""CPU-only evidence that an existing island preparation is reused, not rebuilt.

Reuse republishes the frozen island sidecar and its mountain plans by reference
after strict identity/SHA/read checks; it never regenerates islands and never
re-qualifies mountains. A deferred analysis request records an explicit
pending-analysis state instead of lowering the analysis budget to look complete.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from app.world_gen import web_island_stage as stage, island_mountains as mountains, ocean_island_adapter as islands
from app.world_gen.config import sha256_json

_fixture_spec = importlib.util.spec_from_file_location('world_island_fixture', Path(__file__).with_name('test_ocean_island_integration.py'))
_fixture_module = importlib.util.module_from_spec(_fixture_spec)
_fixture_spec.loader.exec_module(_fixture_module)
frozen = _fixture_module.frozen

WORLD_TYPE = 'archipelago'
WORLD_SEED = 20260903


def _forbid_generation(monkeypatch):
    """Any island generation or mountain qualification during reuse is a defect."""
    def fail(*args, **kwargs):
        raise AssertionError('reuse regenerated islands or re-qualified island mountains')
    _, core, _ = islands._public_api()
    monkeypatch.setattr(core, 'prepare_ocean_islands', fail)
    monkeypatch.setattr(mountains._api(), 'analyze_island_mountains', fail)


def _count_generation(monkeypatch):
    _, core, _ = islands._public_api()
    real = core.prepare_ocean_islands
    calls = []

    def wrapper(plate, config=None):
        calls.append(config)
        return real(plate, config)

    monkeypatch.setattr(core, 'prepare_ocean_islands', wrapper)
    return calls


@pytest.fixture(scope='module')
def prepared(frozen, tmp_path_factory):
    """One real default preparation: island geometry plus fixed-1km plans."""
    out = tmp_path_factory.mktemp('island-prepared') / 'ocean-islands'
    stage.prepare(frozen.source_path, frozen.run_path, out, world_type=WORLD_TYPE, world_seed=WORLD_SEED)
    return out / 'prepared.json'


def test_default_prepare_still_qualifies_mountains(prepared):
    record = stage.read_record(prepared)
    assert record['analysis']['status'] == 'complete'
    assert record['island_density'] == stage.DEFAULT_ISLAND_DENSITY == 'medium'
    assert record['plans'] and not record['analysis']['pending']
    assert record['analysis']['qualification'].startswith('actual exposed connected area strictly >')
    assert 'reuse' not in record
    for entry in record['plans']:
        assert islands.file_sha(entry['path']) == entry['sha256']


def test_reuse_republishes_islands_and_plans_without_generation(frozen, prepared, tmp_path, monkeypatch):
    old = stage.read_record(prepared)
    _forbid_generation(monkeypatch)
    out = tmp_path/'reused'
    record = stage.prepare(frozen.source_path, frozen.run_path, out,
                          world_type=WORLD_TYPE, world_seed=WORLD_SEED, reuse_prepared=prepared)
    assert record['island_product_path'] == old['island_product_path']
    assert record['island_identity'] == old['island_identity']
    assert record['binding'] == old['binding']
    assert record['analysis'] == old['analysis']
    assert [entry['path'] for entry in record['plans']] == [entry['path'] for entry in old['plans']]
    assert record['mountains'] == dict(status='not-scheduled', products=[])
    assert record['reuse']['prepared'] == str(prepared.resolve())
    assert record['reuse']['prepared_identity'] == old['identity']
    assert record['reuse']['reused']['islands'] == old['island_product_path']
    assert record['reuse']['deferred_mountain_analysis'] is False
    # Only the new record exists; no island sidecar or plan was written again.
    assert sorted(p.name for p in out.iterdir()) == ['prepared.json']
    assert stage.read_record(out/'prepared.json')['identity'] == record['identity']


def test_reuse_with_defer_keeps_existing_complete_plans(frozen, prepared, tmp_path, monkeypatch):
    old = stage.read_record(prepared)
    _forbid_generation(monkeypatch)
    record = stage.prepare(frozen.source_path, frozen.run_path, tmp_path/'reused-defer',
                          world_type=WORLD_TYPE, world_seed=WORLD_SEED,
                          reuse_prepared=prepared, defer_mountain_analysis=True)
    # An existing complete qualification is preserved, never replaced by a pending one.
    assert record['analysis'] == old['analysis']
    assert record['analysis']['status'] == 'complete' and record['plans']
    assert record['reuse']['deferred_mountain_analysis'] is True


def test_island_density_reaches_the_frozen_config_and_the_record(frozen, tmp_path, monkeypatch):
    calls = _count_generation(monkeypatch)
    record = stage.prepare(frozen.source_path, frozen.run_path, tmp_path/'low-density',
                          world_type=WORLD_TYPE, world_seed=WORLD_SEED, island_density='low',
                          defer_mountain_analysis=True)
    assert [config.density for config in calls] == ['low']
    assert record['island_density'] == 'low'
    assert record['binding']['island_algorithm']
    assert stage.read_record(tmp_path/'low-density'/'prepared.json')['island_density'] == 'low'


def test_unknown_island_density_is_refused_before_any_output(frozen, tmp_path, monkeypatch):
    _forbid_generation(monkeypatch)
    out = tmp_path/'bad-density'
    with pytest.raises(ValueError, match='island density must be one of'):
        stage.prepare(frozen.source_path, frozen.run_path, out,
                      world_type=WORLD_TYPE, world_seed=WORLD_SEED, island_density='huge')
    assert not out.exists()


def test_reuse_records_matching_density_and_rejects_a_different_one(frozen, prepared, tmp_path, monkeypatch):
    _forbid_generation(monkeypatch)
    same = stage.prepare(frozen.source_path, frozen.run_path, tmp_path/'reused-medium',
                         world_type=WORLD_TYPE, world_seed=WORLD_SEED, island_density='medium',
                         reuse_prepared=prepared)
    assert same['island_density'] == 'medium'
    other = tmp_path/'reused-low'
    with pytest.raises(ValueError, match='island density differs'):
        stage.prepare(frozen.source_path, frozen.run_path, other,
                      world_type=WORLD_TYPE, world_seed=WORLD_SEED, island_density='low',
                      reuse_prepared=prepared)
    assert not other.exists()


def test_reuse_rejects_seed_and_world_type_mismatch(frozen, prepared, tmp_path, monkeypatch):
    _forbid_generation(monkeypatch)
    out = tmp_path/'seed-mismatch'
    with pytest.raises(ValueError, match='world seed'):
        stage.prepare(frozen.source_path, frozen.run_path, out,
                      world_type=WORLD_TYPE, world_seed=WORLD_SEED + 1, reuse_prepared=prepared)
    assert not out.exists()
    other = tmp_path/'type-mismatch'
    with pytest.raises(ValueError, match='world type'):
        stage.prepare(frozen.source_path, frozen.run_path, other,
                      world_type='pangaea', world_seed=WORLD_SEED, reuse_prepared=prepared)
    assert not other.exists()


def test_reuse_rejects_foreign_skeleton_identity(frozen, prepared, tmp_path, monkeypatch):
    _forbid_generation(monkeypatch)
    with np.load(frozen.source_path, allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    manifest = json.loads(str(arrays['manifest_json']))
    manifest['world_config_identity'] = 'd'*64
    manifest.pop('identity')
    manifest['identity'] = sha256_json(manifest)
    arrays['manifest_json'] = np.array(json.dumps(manifest))
    foreign = tmp_path/'foreign-skeleton.npz'
    np.savez_compressed(foreign, **arrays)
    out = tmp_path/'foreign'
    with pytest.raises(ValueError, match='different skeleton identity'):
        stage.prepare(foreign, frozen.run_path, out,
                      world_type=WORLD_TYPE, world_seed=WORLD_SEED, reuse_prepared=prepared)
    assert not out.exists()


def test_reuse_rejects_a_different_source_path(frozen, prepared, tmp_path, monkeypatch):
    """Same bytes, other path: the recorded source path is part of the contract."""
    _forbid_generation(monkeypatch)
    moved = tmp_path/'elsewhere'/'skeleton.npz'
    moved.parent.mkdir(parents=True)
    moved.write_bytes(Path(frozen.source_path).read_bytes())
    out = tmp_path/'moved-source'
    with pytest.raises(ValueError, match='different skeleton source path'):
        stage.prepare(moved, frozen.run_path, out,
                      world_type=WORLD_TYPE, world_seed=WORLD_SEED, reuse_prepared=prepared)
    assert not out.exists()


def test_reuse_rejects_tampered_plan_and_record(frozen, prepared, tmp_path, monkeypatch):
    _forbid_generation(monkeypatch)
    old = stage.read_record(prepared)
    entry = old['plans'][0]
    plan_path = Path(entry['path'])
    original = plan_path.read_bytes()
    try:
        plan_path.write_bytes(original + b' ')
        out = tmp_path/'tampered-plan'
        with pytest.raises(ValueError, match='plan SHA changed'):
            stage.prepare(frozen.source_path, frozen.run_path, out,
                          world_type=WORLD_TYPE, world_seed=WORLD_SEED, reuse_prepared=prepared)
        assert not out.exists()
    finally:
        plan_path.write_bytes(original)
    forged = json.loads(prepared.read_text(encoding='utf-8'))
    forged['analysis']['status'] = 'complete'
    forged['plans'] = []
    forged['policy'] = 'forged-reuse'
    forged_path = tmp_path/'forged.json'
    forged_path.write_text(json.dumps(forged), encoding='utf-8')
    with pytest.raises(ValueError, match='identity/schema mismatch'):
        stage.prepare(frozen.source_path, frozen.run_path, tmp_path/'forged-out',
                      world_type=WORLD_TYPE, world_seed=WORLD_SEED, reuse_prepared=forged_path)
    assert not (tmp_path/'forged-out').exists()


def test_defer_prepares_geometry_once_and_schedule_stays_cpu_pending(frozen, tmp_path, monkeypatch):
    calls = _count_generation(monkeypatch)
    def fail(*args, **kwargs):
        raise AssertionError('deferred coarse-map request analysed island mountains')
    monkeypatch.setattr(mountains._api(), 'analyze_island_mountains', fail)
    out = tmp_path/'deferred'
    record = stage.prepare(frozen.source_path, frozen.run_path, out,
                          world_type=WORLD_TYPE, world_seed=WORLD_SEED, defer_mountain_analysis=True)
    assert len(calls) == 1
    assert (out/'islands.npz').exists()
    assert record['plans'] == []
    assert record['analysis']['status'] == 'pending-analysis'
    assert record['analysis']['status'] not in ('complete', 'empty')
    assert record['analysis']['qualification'] == stage.DEFERRED_ANALYSIS_QUALIFICATION
    assert record['analysis']['pending'][0]['reason'] == stage.DEFERRED_ANALYSIS_REASON
    assert 'coarse-map' in record['analysis']['pending'][0]['reason']
    # No budget was widened or lowered to fake a qualification.
    api = mountains._api()
    assert record['analysis']['pending'][0].get('analysis_cells') is None
    assert api.IslandMountainConfig().max_analysis_cells == 4000000
    assert record['mountains'] == dict(status='not-scheduled', products=[])
    cpu = stage.schedule(out/'prepared.json', tmp_path/'cpu', use_gpu=False)
    assert cpu['analysis']['status'] == 'pending-analysis'
    assert cpu['mountains']['status'] == 'pending-analysis'
    assert not cpu['mountains']['products'] and not cpu['mountains']['model_started']
    assert not (tmp_path/'cpu'/'tiles').exists()
