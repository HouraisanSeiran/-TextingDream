"""Bridge between the Dream island stage and the Terragenesis clustered island layout.

The clustered-provinces preset is an explicit OceanIslandConfig keyword set inside the same
v5 geometry. These tests prove the Dream side of that contract:

* the old layout stays the default and passes no keyword, so every existing call is unchanged
  and its frozen record keeps the historical shape (and therefore its identity);
* a clustered preparation records the *actual* config it asked for;
* reuse compares that config strictly: a different layout is refused and never re-derived from
  a new quality or size, and an old record keeps reusing as the old layout;
* a clustered request is refused before any output when the Terragenesis core lacks the fields;
* the fast-layer island timings are reported through runtime-stats and change no geometry,
  no manifest and no identity.

The real Terragenesis producer and the shared synthetic plate fixture are used throughout; no
dependency is installed and no world is generated.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from app.world_gen import web_island_stage as stage, ocean_island_adapter as islands

_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    'island_layout_fixture', Path(__file__).with_name('test_ocean_island_integration.py'))
_fixture = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_fixture)
frozen = _fixture.frozen

WORLD_TYPE = 'archipelago'
WORLD_SEED = 20260903


def _prepare(frozen, out, **kwargs):
    """A preparation that never spends the 1 km qualification budget."""
    return stage.prepare(frozen.source_path, frozen.run_path, out, world_type=WORLD_TYPE,
                         world_seed=WORLD_SEED, defer_mountain_analysis=True, **kwargs)


def test_old_layout_is_the_default_and_adds_no_keyword():
    assert stage.DEFAULT_ISLAND_LAYOUT == 'old'
    assert stage.ISLAND_LAYOUTS == ('old', 'clustered')
    assert stage.island_config_kwargs('old') == {}
    assert stage.island_config_record('old', world_type=WORLD_TYPE, world_seed=WORLD_SEED,
                                      island_density='medium') == dict(
        world_type=WORLD_TYPE, world_seed=WORLD_SEED, density='medium')


def test_old_layout_record_keeps_the_historical_shape():
    """An old-layout preparation must not gain keys: its identity stays what it was."""
    assert stage._layout_record('old', {'any': 'config'}) == {}
    clustered = stage._layout_record('clustered', {'layout_policy': 'clustered-provinces-v1'})
    assert clustered == dict(island_layout='clustered',
                             island_config={'layout_policy': 'clustered-provinces-v1'})


def test_clustered_preset_is_explicit_and_exactly_declared():
    kwargs = stage.island_config_kwargs('clustered')
    assert kwargs == dict(
        layout_policy='clustered-provinces-v1', province_count=5, province_radius_m=600000.,
        province_hotspots=6, isolated_hotspot_count=3, max_age_steps=300.,
        max_chain_length_m=600000., stages=8, boundary_spacing_m=150000., ridge=False)
    # A global ridge toggle must never leak into the preset as a truthy default.
    assert kwargs['ridge'] is False
    # The preset goes through the real config class unchanged, and old keeps its old policy.
    _, core, _ = islands._public_api()
    config = core.OceanIslandConfig(world_type=WORLD_TYPE, world_seed=WORLD_SEED,
                                   density='medium', **kwargs)
    for name, value in kwargs.items():
        assert getattr(config, name) == value, name
    old = core.OceanIslandConfig(world_type=WORLD_TYPE, world_seed=WORLD_SEED, density='medium')
    assert getattr(old, 'layout_policy', None) == stage.OLD_LAYOUT_POLICY


def test_unknown_layout_is_refused_before_any_output(frozen, tmp_path):
    out = tmp_path / 'bad-layout'
    with pytest.raises(ValueError, match='island layout must be one of'):
        _prepare(frozen, out, island_layout='spiral')
    assert not out.exists()


def test_clustered_is_refused_before_any_output_when_the_core_lacks_the_fields(frozen, tmp_path, monkeypatch):
    """A core without the fields must refuse, never fake a preset or a product."""
    _, core, _ = islands._public_api()
    fields = getattr(core.OceanIslandConfig, '__dataclass_fields__', {})
    monkeypatch.delattr(core.OceanIslandConfig, '__dataclass_fields__', raising=False)
    monkeypatch.setattr(core, 'OceanIslandConfig', _bare_config_class(core))
    out = tmp_path / 'missing-fields'
    with pytest.raises(ValueError, match='lacks the clustered layout fields'):
        _prepare(frozen, out, island_layout='clustered')
    assert not out.exists()
    assert fields


def _bare_config_class(core):
    """A stand-in core config that only knows the historical fields."""
    class Bare:
        __dataclass_fields__ = {name: None for name in ('world_seed', 'world_type', 'density')}

        def __init__(self, **kwargs):
            for name, value in kwargs.items():
                setattr(self, name, value)

    return Bare


def test_clustered_prepare_records_the_actual_config(frozen, tmp_path):
    record = _prepare(frozen, tmp_path / 'clustered', island_layout='clustered')
    expected = stage.island_config_record('clustered', world_type=WORLD_TYPE,
                                          world_seed=WORLD_SEED, island_density='medium')
    assert record['island_layout'] == 'clustered'
    assert record['island_config'] == expected
    # The recorded values are the real preset, not a placeholder for a future quality.
    assert record['island_config']['layout_policy'] == stage.CLUSTERED_LAYOUT_POLICY
    assert record['island_config']['province_count'] == 5
    assert record['island_config']['province_radius_m'] == 600000.
    assert record['island_config']['province_hotspots'] == 6
    assert record['island_config']['isolated_hotspot_count'] == 3
    assert record['island_config']['stages'] == 8
    assert record['island_config']['ridge'] is False
    assert stage.read_record(tmp_path / 'clustered' / 'prepared.json') == record
    # Clustered geometry is a different product, but the source/run binding is not relaxed.
    assert record['binding']['plate_identity'] == frozen.source.identity


def test_old_prepare_records_no_layout_keys_and_still_binds(frozen, tmp_path):
    record = _prepare(frozen, tmp_path / 'old-layout')
    assert 'island_layout' not in record and 'island_config' not in record
    assert record['island_density'] == 'medium'
    assert record['binding']['island_algorithm']
    assert record['binding']['plate_identity'] == frozen.source.identity
    assert record['binding']['island_identity'] == record['island_identity']


def test_reuse_refuses_a_different_layout_and_never_rederives_it(frozen, tmp_path):
    """Reuse compares the recorded config strictly; a layout mismatch fails closed."""
    old = _prepare(frozen, tmp_path / 'old-src')
    prepared = tmp_path / 'old-src' / 'prepared.json'
    same = _prepare(frozen, tmp_path / 'old-same', reuse_prepared=prepared)
    assert 'island_layout' not in same and same['island_identity'] == old['island_identity']
    other = tmp_path / 'old-as-clustered'
    with pytest.raises(ValueError, match='island layout differs'):
        _prepare(frozen, other, reuse_prepared=prepared, island_layout='clustered')
    assert not other.exists()


def test_reuse_of_a_clustered_preparation_requires_the_same_config(frozen, tmp_path):
    clustered = _prepare(frozen, tmp_path / 'clustered-src', island_layout='clustered')
    prepared = tmp_path / 'clustered-src' / 'prepared.json'
    again = _prepare(frozen, tmp_path / 'clustered-again', reuse_prepared=prepared,
                     island_layout='clustered')
    assert again['island_config'] == clustered['island_config']
    assert again['island_identity'] == clustered['island_identity']
    plain = tmp_path / 'clustered-as-old'
    with pytest.raises(ValueError, match='island layout differs'):
        _prepare(frozen, plain, reuse_prepared=prepared)
    assert not plain.exists()


def test_reuse_preserves_an_old_record_from_the_historic_schema(frozen, tmp_path):
    """A preparation frozen before the selector existed still reuses as the old layout."""
    _prepare(frozen, tmp_path / 'legacy')
    path = tmp_path / 'legacy' / 'prepared.json'
    record = stage.read_record(path)
    assert 'island_layout' not in record
    rewritten = _prepare(frozen, tmp_path / 'legacy-reuse', reuse_prepared=path)
    assert 'island_layout' not in rewritten
    assert rewritten['reuse']['prepared_identity'] == record['identity']


def test_fast_relief_reports_island_timings_without_touching_geometry(frozen, tmp_path):
    """Island timings live in runtime-stats only; manifest, identity and bytes stay put."""
    from app.world_gen import fast_relief as fr
    pytest.importorskip('numba', reason='fast_relief hydrology needs Terragenesis runtime/venv (numba)')
    params = dict(spacing_m=4000., erosion_iterations=1, smooth_rivers=False, breach_passes=1)
    options = _fixture.options(frozen)
    plain = fr.compute(fr.load_skeleton(frozen.source_path, frozen.source.identity), params,
                       erosion=True, log=None, **options)
    out, manifest = fr.freeze(frozen.source_path, tmp_path / 'timed', params=params, erosion=True,
                              expected_identity=frozen.source.identity, min_free_bytes=1,
                              log=lambda *_: None, **options)
    stats = json.loads((out / 'runtime-stats.json').read_text(encoding='utf-8'))
    # No mountain input is bound here, so the correction step never claims a duration.
    for name in ('island_binding_s', 'island_compose_s', 'island_restore_s',
                 'island_quota_s', 'freeze_write_s'):
        assert name in stats, name
        assert stats[name] >= 0
    assert 'identity' not in stats
    # Timing is run data, never manifest data or an identity input.
    text = json.dumps(manifest).lower()
    for word in ('compose_s', 'correction_s', 'binding_s', 'freeze_write_s', 'restore_s'):
        assert word not in text, word
    assert manifest['identity'] == fr.identity_of(manifest)
    # The published product still carries exactly the geometry that was computed.
    assert np.array_equal(plain['elevation'].astype(np.float32), np.load(out / 'elevation_m.npy'))
    published = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    # Round-trip the bound metadata so the published list/tuple form compares like for like.
    assert published['ocean_islands']['area_sampling'] == _metadata_roundtrip(plain['ocean_islands']['fractions'].metadata)
    assert published['statistics']['land_fraction'] == float((plain['elevation'] >= 0).mean())
    # A no-island compute grows no island timing keys at all.
    bare = fr.compute(fr.load_skeleton(frozen.source_path, frozen.source.identity), params,
                      erosion=True, log=None)
    for name in ('island_binding_s', 'island_compose_s', 'island_correction_s',
                 'island_restore_s', 'island_quota_s'):
        assert name not in bare['timing'], name
    assert bare['timing']['mesh_s'] >= 0 and bare['timing']['hydrology_s'] >= 0

def _metadata_roundtrip(metadata):
    """The metadata as JSON would carry it, so tuples/lists and NaN compare like for like."""
    return json.loads(json.dumps(metadata, allow_nan=True))
