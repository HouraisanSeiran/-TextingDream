"""Small saved-liquid replay fixtures; no real climate/glacier/world runs."""
import numpy as np
import pytest

from app.world_gen import climate_lake_stage as stage


def parameters(shape):
    return dict(soil_capacity_mm=np.full(shape, 150.), infiltration_fraction=np.full(shape, .625),
                quickflow_fraction=np.full(shape, .375), et_fraction=np.full(shape, .875))


def test_no_lake_stateful_12_months_bitwise_matches_native_bucket():
    from app.world_gen.climate_world_stage import climate_module
    native = climate_module()
    rng = np.random.default_rng(7)
    shape = (5, 7)
    liquid = rng.uniform(0, 300, (12,) + shape)
    pet = rng.uniform(0, 120, (12,) + shape)
    land = rng.uniform(size=shape) > .2
    p = parameters(shape)
    expected, _ = native._monthly_land_bucket(liquid, pet, p, land)
    soil = np.zeros(shape)
    for month in range(12):
        result = stage.land_bucket_step(liquid[month], pet[month], p, land, soil)
        for key, actual in (('monthly_soil_water_mm', result['soil_mm']),
                            ('monthly_runoff_mm', result['runoff_mm']),
                            ('monthly_actual_et_mm', result['actual_et_mm'])):
            np.testing.assert_array_equal(actual, expected[key][month])
        soil = result['soil_mm']


def test_step_does_not_reset_soil_or_discard_wet_stock():
    shape = (2, 3)
    land = np.ones(shape, bool); zero = np.zeros(shape)
    one = stage.land_bucket_step(np.full(shape, 100.), zero, parameters(shape), land, zero)
    two = stage.land_bucket_step(zero, np.full(shape, 10.), parameters(shape), land, one['soil_mm'])
    np.testing.assert_array_equal(two['soil_mm'], np.full(shape, 53.75))
    land[0, 0] = False
    with pytest.raises(ValueError, match='transferred'):
        stage.land_bucket_step(zero, zero, parameters(shape), land, one['soil_mm'])


def bowl_geometry():
    from types import SimpleNamespace
    from app.world_gen import lake_basin_geometry as core
    # Tiny CSR chain with a real bed depression, not D8 routing.
    bed = np.array([[0., 2., 0., 2., 0.]])
    mesh = SimpleNamespace(indptr=np.array([0, 1, 3, 5, 7, 8]),
                           indices=np.array([1, 0, 2, 1, 3, 2, 4, 3]))
    g = core.build_geometry(bed, mesh, [[True, False, False, False, True]], 1., 'a' * 64)
    return g, bed.shape


def test_lake_input_once_soil_transfer_and_pet_availability():
    g, shape = bowl_geometry()
    liquid = np.zeros((12,) + shape); liquid[:2, 0, 2] = 1000.
    pet = np.zeros_like(liquid); pet[1, 0, 2] = 10000.
    land = np.array([[False, True, True, True, False]])
    result = stage.compute_year(g, liquid, pet, parameters(shape), land)
    a = result['arrays']; first, second = result['accounts'][:2]
    assert first['liquid_input_m3'] == 1
    assert first['soil_transfer_m3'] == pytest.approx(.15)
    assert first['final_lake_m3'] == pytest.approx(1.)
    assert first['lake_et_m3'] == 0  # dry initial month gets no whole-month lake PET
    assert second['liquid_input_m3'] == 1
    assert a['direct_lake_liquid_m3'][1].sum() == 1
    assert a['runoff_mm'][1].sum() == 0  # wet liquid does not also enter old land runoff
    assert second['lake_et_m3'] == pytest.approx(2.)
    assert second['lake_et_unmet_m3'] == pytest.approx(8.)
    assert second['final_lake_m3'] == 0
    assert np.max(np.abs([v['residual_m3'] for v in result['accounts']])) < 1e-12
    assert result['publishable'] is True and result['channel_q_available'] is False
    assert a['lake_actual_et_m3'][1].sum() == pytest.approx(second['lake_et_m3'])


def test_retention_reduces_export_and_zero_source_stays_dry():
    g, shape = bowl_geometry()
    land = np.array([[False, True, True, True, False]])
    liquid = np.zeros((12,) + shape); liquid[0, 0, 2] = 1000.
    pet = np.zeros_like(liquid)
    result = stage.compute_year(g, liquid, pet, parameters(shape), land)
    assert result['accounts'][0]['terminal_overflow_m3'] == 0
    assert result['accounts'][0]['final_lake_m3'] == 1
    dry = stage.compute_year(g, np.zeros_like(liquid), pet, parameters(shape), land)
    assert not dry['arrays']['wet_mask'].any()
    assert dry['arrays']['lake_volume_m3'].sum() == 0


def test_water_account_failure_is_not_publishable(monkeypatch):
    from dataclasses import replace
    from app.world_gen import lake_basin_geometry as core
    g, shape = bowl_geometry()
    settle = core.settle
    def broken(*args, **kwargs):
        return replace(settle(*args, **kwargs), balance_error_m3=100.)
    monkeypatch.setattr(core, 'settle', broken)
    zero = np.zeros((12,) + shape)
    with pytest.raises(ValueError, match='account failed'):
        stage.compute_year(g, zero, zero, parameters(shape), np.ones(shape, bool))


@pytest.fixture
def saved_liquid_year(tmp_path):
    """Use native small climate fixture once, but never solve snow/glaciers."""
    from app.world_gen import climate_world_stage as cs, climate_hydrology_stage as hs
    from tests.test_climate_world_stage import world_map, reference
    from terrain_pipeline.common_infra import identity
    import json
    root, source_identity = world_map(tmp_path)
    from app import terrain_source as ts
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    lagoon = np.zeros((8, 8), bool); lagoon[3, 5] = True
    np.save(root / 'registered_lagoon.npy', lagoon)
    spec = dict(file='registered_lagoon.npy', dtype='bool', unit='1', nodata=None,
                sha256=cs._sha(root / 'registered_lagoon.npy'), meaning='explicit registered outlet')
    manifest['layers']['registered_lagoon'] = spec
    manifest['files'][spec['file']] = spec['sha256']
    manifest.pop('identity')
    manifest['identity'] = __import__('hashlib').sha256(ts._canon(manifest).encode()).hexdigest()
    (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    source = cs.climate_source_from_map(root, expected_identity=manifest['identity'])
    climate = tmp_path / 'climate'
    record = cs.prepare(source, climate, references=reference())
    hydro = tmp_path / 'hydro'; hydro.mkdir()
    fields = {}
    for name in ('monthly_liquid_input_mm', 'monthly_snow_swe_mm', 'monthly_ice_swe_mm'):
        value = np.zeros((12, 8, 8))
        if name == 'monthly_liquid_input_mm':
            value[:, :, 4:] = 40.
        np.save(hydro / (name + '.npy'), value)
        fields[name] = dict(file=name + '.npy', shape=[12, 8, 8], dtype='float64',
                            units='mm/month' if name == 'monthly_liquid_input_mm' else 'mm',
                            sha256=cs._sha(hydro / (name + '.npy')))
    h = dict(schema=hs.SCHEMA, status='complete', calendar='noleap365', month_days=list(stage.MONTH_DAYS),
             binding=dict(source_identity=manifest['identity'], climate_identity=record['identity'],
                          grid=dict(shape_zx=[8, 8], first_xz_m=source['first_xz_m'], spacing_m=source['spacing_m'])),
             fields=fields)
    h['identity'] = identity({}, h)
    (hydro / 'manifest.json').write_text(json.dumps(h), encoding='utf-8')
    options = dict(expected_source_identity=manifest['identity'], expected_climate_identity=record['identity'],
                   expected_hydrology_identity=h['identity'])
    return root, climate, hydro, options


def test_plan_does_not_read_monthly_or_solve_and_declares_original_seed(saved_liquid_year, monkeypatch):
    from app.world_gen.world_climate_adapter import SavedClimateMap
    def forbidden(*args, **kwargs):
        raise AssertionError('plan must not query monthly inputs')
    monkeypatch.setattr(SavedClimateMap, 'query', forbidden)
    root, climate, hydro, options = saved_liquid_year
    p = stage.plan(root, climate, hydro, **options)
    assert p['status'] == 'ready' and p['mesh_seed'] == 15386822478918853569
    assert p['bed'] == 'immutable elevation_m; NOT bed+ice'
    assert stage.plan(root, climate, hydro, max_cells=10, **options)['status'] == 'budget-exceeded'


def test_saved_prepare_never_recomputes_snow_or_glacier_and_preserves_parents(saved_liquid_year, monkeypatch, tmp_path):
    from app.world_gen import climate_world_stage as cs
    from terrain_pipeline import world_environment, world_glacier
    from app.world_gen import graph_hydro as gh
    drainage, _ = gh.load_terragenesis()
    accumulate = drainage.accumulate_graph
    calls = []
    def checked_accumulate(receiver, order, local):
        expected = np.array(local, dtype=float, copy=True)
        for cell in order[::-1]:
            if receiver[cell] >= 0:
                expected[receiver[cell]] += expected[cell]
        actual = accumulate(receiver, order, local)
        np.testing.assert_array_equal(actual, expected)
        calls.append(np.array(local, copy=True))
        return actual
    monkeypatch.setattr(drainage, 'accumulate_graph', checked_accumulate)
    root, climate, hydro, options = saved_liquid_year
    def forbidden(*args, **kwargs):
        raise AssertionError('immutable saved liquid: no snow/ice/glacier solve')
    monkeypatch.setattr(world_environment, 'diagnostic_snow_ice', forbidden)
    monkeypatch.setattr(world_glacier, 'generate_climate_slope_glacier', forbidden)
    parents = {str(p): cs._sha(p) for parent in (root, climate, hydro) for p in parent.iterdir() if p.is_file()}
    out = tmp_path / 'surface-water'
    m = stage.prepare(root, climate, hydro, out, **options)
    assert len(calls) == 13  # twelve wet-cut runoff maps plus geometrical route area
    np.testing.assert_array_equal(calls[-1], np.load(out / 'geometry_area_m2.npy').ravel())
    assert m['status'] == 'finite-year-surface-water' and m['publishable'] is True
    assert all(cs._sha(p) == digest for p, digest in parents.items())
    np.testing.assert_array_equal(np.load(out / 'monthly_liquid_input_mm.npy'), np.load(hydro / 'monthly_liquid_input_mm.npy'))
    assert not (out / 'monthly_discharge_m3_s.npy').exists()  # no pretend all-flow grid Q
    assert (out / 'hillslope_discharge_m3_s.npy').exists()
    assert (out / 'hillslope-draw.json').exists()
    assert m['lagoon_binding']['origin'] == 'saved registered_lagoon layer'
    g_source, _, _, _ = stage._saved_inputs(root, climate, hydro, **options)
    assert g_source['registered_lagoon'][3, 5]
    with pytest.raises(ValueError, match='budget'):
        stage.prepare(root, climate, hydro, tmp_path / 'too-large', max_cells=1, **options)
    assert not (tmp_path / 'too-large').exists()


def test_stream_sink_matches_inmemory_months_exactly():
    g, shape = bowl_geometry()
    liquid = np.zeros((12,) + shape); liquid[:2, 0, 2] = 1000.
    pet = np.zeros_like(liquid)
    land = np.array([[False, True, True, True, False]])
    expected = stage.compute_year(g, liquid, pet, parameters(shape), land)
    captured = {}
    def sink(month, values):
        for name, value in values.items():
            captured.setdefault(name, []).append(value.copy())
    streamed = stage.compute_year(g, liquid, pet, parameters(shape), land, output_sink=sink)
    assert streamed['arrays'] == {} and streamed['transfer_events'] == []
    for name, value in expected['arrays'].items():
        np.testing.assert_array_equal(np.stack(captured[name]), value)
    assert streamed['accounts'] == expected['accounts']


def test_spill_net_opposing_routes_hidden_wet_and_path_budget():
    from types import SimpleNamespace
    events = [[SimpleNamespace(path=[0, 1, 2], volume_m3=5.),
               SimpleNamespace(path=[2, 1, 0], volume_m3=3.)]]
    coords = np.array([[0, 0], [1, 2], [3, 4.]])
    routes = stage._spill_routes(events, [[False, False, False]], coords, [31])
    assert len(routes[0]) == 2
    assert [v['net_transferred_volume_m3'] for v in routes[0]] == [2, 2]
    hidden = stage._spill_routes(events, [[False, True, False]], coords, [31])
    assert hidden == [[]]
    with pytest.raises(ValueError, match='path node budget'):
        stage._spill_routes(events, [[False] * 3], coords, [31], max_path_nodes=2)


def test_prepare_failed_ledger_never_publishes_and_cleans_temp(saved_liquid_year, monkeypatch, tmp_path):
    root, climate, hydro, options = saved_liquid_year
    def failed(*args, **kwargs):
        raise ValueError('monthly water account failed; refusing publication')
    monkeypatch.setattr(stage, 'compute_year', failed)
    out = tmp_path / 'failed-sidecar'
    with pytest.raises(ValueError, match='account failed'):
        stage.prepare(root, climate, hydro, out, **options)
    assert not out.exists()
    assert not list(tmp_path.glob('.climate-lakes-*'))


def test_native_accumulation_is_bitwise_old_loop_and_stops_at_first_wet(monkeypatch):
    from app.world_gen import graph_hydro as gh, lake_basin_geometry as core
    from tests.test_lake_basin_geometry import mesh_for
    drainage, _ = gh.load_terragenesis()
    native = drainage.accumulate_graph
    bed = np.array([[0., 1., 3., 5., 0.]])
    g = core.build_geometry(bed, mesh_for(5), [[False, False, False, False, True]],
                            [2., 3., 4., 1., 1.], 'a' * 64)
    calls = []
    def checked(receiver, order, local):
        expected = np.array(local, dtype=float, copy=True)
        for cell in order[::-1]:
            target = receiver[cell]
            if target >= 0:
                expected[target] += expected[cell]
        actual = native(receiver, order, local)
        np.testing.assert_array_equal(actual, expected)  # exact addition order
        assert actual[receiver < 0].sum() == pytest.approx(np.sum(local))
        calls.append(receiver.copy())
        return actual
    monkeypatch.setattr(drainage, 'accumulate_graph', checked)
    liquid = np.zeros((12, 1, 5)); liquid[:2, 0, 2] = 1500.
    result = stage.compute_year(g, liquid, np.zeros_like(liquid), parameters(bed.shape),
                                [[True, True, True, True, False]])
    assert len(calls) == 12
    assert any(np.any((g.receiver >= 0) & (rec < 0)) for rec in calls)
    assert all(abs(a['residual_m3']) < 1e-12 for a in result['accounts'])
    np.testing.assert_array_equal(g.receiver, [ -1, 0, 1, 4, -1])


def test_geometry_probe_reports_unresolved_without_year_or_monthly_query(saved_liquid_year, monkeypatch):
    from app.world_gen import graph_hydro as gh
    from tests.test_lake_basin_geometry import mesh_for
    root, climate, hydro, options = saved_liquid_year
    source, _, _, _ = stage._saved_inputs(root, climate, hydro, **options)
    source = dict(source, elevation_m=np.array([[0., 2., 0., 5., 0.]]),
                  ocean_mask=np.array([[False, False, False, False, True]]),
                  registered_lagoon=np.zeros((1, 5), bool), first_xz_m=[0., 0.], spacing_m=1.)
    def static(*args, **kwargs):
        assert not kwargs.get('monthly', False)
        return source, None, {'identity': options['expected_hydrology_identity']}, {}
    monkeypatch.setattr(stage, '_saved_inputs', static)
    monkeypatch.setattr(gh, 'build_graph', lambda *args: mesh_for(5))
    monkeypatch.setattr(stage, 'compute_year', lambda *args, **kwargs: pytest.fail('no year in probe'))
    ordinary = stage.plan(root, climate, hydro, **options, finite_boundary=False)
    assert ordinary['status'] == 'ready' and ordinary['geometry_admission'].startswith('unchecked')
    probe = stage.plan_geometry(root, climate, hydro, **options, finite_boundary=False)
    assert probe['status'] == 'geometry-unresolved' and probe['year_computed'] is False
    assert probe['geometry_admission']['unresolved_pools'][0]['sink_cells'] == [0, 2]


def test_uncertified_geometry_cannot_publish_any_year_output():
    from dataclasses import replace
    g, shape = bowl_geometry()
    g = replace(g, certification={'status': 'unresolved'})
    zero = np.zeros((12,) + shape)
    with pytest.raises(ValueError, match='unresolved lake geometry'):
        stage.compute_year(g, zero, zero, parameters(shape), np.ones(shape, bool))
