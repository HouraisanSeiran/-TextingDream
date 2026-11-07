"""Small CPU-only pipeline checks: new skeleton -> TD-readable plate -> world_plan page list -> local30 tile -> map_source."""
import json
from pathlib import Path

import numpy as np
import pytest

from app import map_source as ms
from app.world_gen import config as wc, local30, planner, skeleton as sk, tiles as T


@pytest.fixture(scope='module')
def small_world(tmp_path_factory):
    root = tmp_path_factory.mktemp('worlds')
    cfg = wc.normalize({'world_name': 'small', 'world': {'type': 'archipelago', 'size_km': 400, 'ocean_fraction': 0.6}})
    manifest = sk.generate_skeleton(cfg, root / 'small', max_iterations=2)
    return cfg, root, manifest


def test_skeleton_manifest_records_targets_and_actuals(small_world):
    cfg, root, m = small_world
    assert m['targets']['ocean_fraction'] == 0.6
    assert abs(m['actual']['ocean_deviation']) < 0.08
    assert m['world_seed'] == 20260903 and m['subseeds']
    assert (root / 'small' / 'preview.png').is_file()
    assert any('deep-ocean' in s for s in m['limitations'])


def test_td_reader_accepts_skeleton_and_plans_pages(small_world):
    cfg, root, m = small_world
    from app.world_relief import td_resident as tr
    path = root / 'small' / 'skeleton.npz'
    elev, pm = tr.read_plate(path)
    assert pm['config']['world_seed'] == 20260903
    assert pm['identity'] == m['product']['plate_identity']
    spec, skel, weight = tr.world_plan(path)
    assert spec['plate_identity'] == pm['identity'] and spec['world_seed'] == 20260903
    assert len(spec['pages']) >= 1 and skel.shape == tuple(spec['shape_zx'])
    assert tr.world_plan(path)[0]['plan_identity'] == spec['plan_identity']      # deterministic
    # identity check is real: a tampered array is refused
    with np.load(path, allow_pickle=False) as a:
        data = {k: a[k] for k in a.files}
    data['final/elevation_m'] = data['final/elevation_m'] + 1
    bad = root / 'bad.npz'
    np.savez(bad, **data)
    with pytest.raises(ValueError, match='mismatch'):
        tr.read_plate(bad)


def test_local30_request_prepare_load(small_world, tmp_path):
    cfg, root, m = small_world
    plate = root / 'small' / 'skeleton.npz'
    req = local30.request_local(tmp_path, 15, 15, 400)
    assert not req['all_prepared'] and req['tiles'][0]['status'] == 'unprepared'
    assert not list(tmp_path.rglob('*.npy'))                       # a query never writes
    win = T.tile_window(0, 0)
    calls = []

    def fake(origin, side):
        calls.append((origin, side))
        z, x = np.mgrid[0:side, 0:side]
        return (x - 200.0).astype(np.float32)                     # sea on the west, land on the east

    with pytest.raises(MemoryError):
        local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=fake, available_bytes=1 * 2 ** 30)
    assert not calls
    man = local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=fake, available_bytes=8 * 2 ** 30)
    assert calls == [(tuple(win['origin_native_xz']), T.TILE_SAMPLES)]
    again = local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=fake, available_bytes=8 * 2 ** 30)
    assert len(calls) == 1 and again['identity'] == man['identity']   # cache reused
    assert local30.request_local(tmp_path, 200, 200, 300)['all_prepared']       # box lies inside tile (0,0)
    assert not local30.request_local(tmp_path, 15, 15, 400)['all_prepared']     # straddles three unprepared neighbours
    src = ms.load_source(local30.KIND, tmp_path / 'local30' / win['id'], expected_identity=man['identity'])
    assert src.info.kind == local30.KIND and src.info.spacing_m == 30
    res = src.sample([0.0, 30 * 300.0], [0.0, 30 * 10.0])
    assert res['status'][0] == ms.OCEAN and res['status'][1] == ms.LAND


def test_planner_example_config_without_generation():
    from pathlib import Path
    ex = Path(__file__).resolve().parents[1] / 'docs' / 'examples' / 'world-config.example.json'
    cfg = wc.load_config(ex)
    p1 = planner.build_plan(cfg, verify_skeleton=False)
    p2 = planner.build_plan(cfg, verify_skeleton=False)
    assert p1['identity'] == p2['identity']
    assert p1['local']['tiles_unique'] >= 3 and p1['local']['unregistered_regions'].startswith('not scheduled')
    assert p1['local']['gpu_estimate']['inference_seconds_total'] > 0
    assert p1['skeleton']['will_run_here'] is False
    json.dumps(p1)


def _fake_gen(side_calls=None):
    def fake(origin, side):
        if side_calls is not None:
            side_calls.append((origin, side))
        z, x = np.mgrid[0:side, 0:side]
        return (x - 200.0).astype(np.float32)
    return fake


def test_local30_identity_ignores_run_time_fields(small_world, tmp_path, monkeypatch):
    cfg, root, m = small_world
    plate = root / 'small' / 'skeleton.npz'

    class Clock:                                                   # every call advances by a different amount
        t = 0.0

        @classmethod
        def perf_counter(cls):
            cls.t += 1.0 + 7.5 * cls.t
            return cls.t

    monkeypatch.setattr(local30, 'time', Clock)
    a = local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=_fake_gen(), available_bytes=8 * 2 ** 30)
    stats_a = json.loads((tmp_path / 'local30' / 'x+000z+000' / 'runtime-stats.json').read_text(encoding='utf-8'))
    b = local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=_fake_gen(),
                             available_bytes=64 * 2 ** 30, reuse=False)
    stats_b = json.loads((tmp_path / 'local30' / 'x+000z+000' / 'runtime-stats.json').read_text(encoding='utf-8'))
    assert stats_a['seconds'] != stats_b['seconds'] and stats_a['available_bytes'] != stats_b['available_bytes']
    assert 'gate' in stats_a and 'seconds' not in a['generator'] and 'gate' not in a['generator']
    assert a['identity'] == b['identity'] and a == b
    assert not (tmp_path / 'local30' / 'x+000z+000.bak').exists()
    with pytest.raises(ValueError, match='run-time'):
        local30.freeze_tile(tmp_path, 0, 0, np.zeros((513, 513), np.float32), purpose='t', reason='r', world_layer_identity=None,
                            world_seed=1, plate_identity='p', consistency_report={}, generator_info=dict(seconds=1.0))


def test_local30_stale_cache_is_not_reused(small_world, tmp_path, monkeypatch):
    from app.world_relief import td_resident
    cfg, root, m = small_world
    plate = root / 'small' / 'skeleton.npz'
    calls = []
    old = local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=_fake_gen(calls), available_bytes=8 * 2 ** 30)
    pid = old['plate_identity']
    assert local30.request_local(tmp_path, 200, 200, 300, plate_identity=pid)['all_prepared']
    # a different world layer identity is also a mismatch
    st = local30.tile_state(tmp_path, 'x+000z+000', plate_identity=pid, world_layer_identity='w' * 64)
    assert st['status'] == 'stale'

    real = td_resident.read_plate
    new_id = 'f' * 64
    monkeypatch.setattr(td_resident, 'read_plate', lambda p: (lambda r: (r[0], {**r[1], 'identity': new_id}))(real(p)))
    req = local30.request_local(tmp_path, 200, 200, 300, plate_identity=new_id)
    row = req['tiles'][0]
    assert not req['all_prepared'] and row['status'] == 'stale' and row['path'] is None and 'plate identity changed' in row['message']
    with pytest.raises(local30.StaleTile, match='plate identity changed'):
        local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=_fake_gen(calls), available_bytes=8 * 2 ** 30)
    assert len(calls) == 1                                       # nothing regenerated, nothing returned
    assert json.loads(local30.tile_manifest_path(tmp_path, 'x+000z+000').read_text(encoding='utf-8'))['identity'] == old['identity']
    fresh = local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=_fake_gen(calls),
                                 available_bytes=8 * 2 ** 30, reuse=False)
    assert len(calls) == 2 and fresh['plate_identity'] == new_id and fresh['identity'] != old['identity']
    assert local30.request_local(tmp_path, 200, 200, 300, plate_identity=new_id)['all_prepared']


def test_local30_legacy_manifest_with_run_time_identity_is_stale(small_world, tmp_path):
    cfg, root, m = small_world
    plate = root / 'small' / 'skeleton.npz'
    man = local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate, generator=_fake_gen(), available_bytes=8 * 2 ** 30)
    mp = local30.tile_manifest_path(tmp_path, 'x+000z+000')
    legacy = dict(man, generator=dict(man['generator'], seconds=12.3, gate=dict(stage='start')))
    legacy['identity'] = local30._identity(legacy)               # self-consistent, but the old rule
    mp.write_text(json.dumps(legacy), encoding='utf-8')
    st = local30.tile_state(tmp_path, 'x+000z+000', plate_identity=man['plate_identity'])
    assert st['status'] == 'stale' and any('legacy format' in r for r in st['reasons'])


def test_local30_swap_dir_keeps_old_until_new_lands(tmp_path, monkeypatch):
    root, tmp = tmp_path / 'tile', tmp_path / 'tile.tmp'
    root.mkdir(); (root / 'old.txt').write_text('old')
    tmp.mkdir(); (tmp / 'new.txt').write_text('new')
    local30._swap_dir(tmp, root)
    assert (root / 'new.txt').is_file() and not (root / 'old.txt').exists() and not (tmp_path / 'tile.bak').exists()
    # a failure while moving the new directory in puts the old one back
    tmp.mkdir(); (tmp / 'newer.txt').write_text('newer')
    real_replace = Path.replace

    def flaky(self, target):
        if self == tmp:
            raise OSError('interrupted')
        return real_replace(self, target)
    monkeypatch.setattr(Path, 'replace', flaky)
    with pytest.raises(OSError):
        local30._swap_dir(tmp, root)
    assert (root / 'new.txt').is_file() and not (tmp_path / 'tile.bak').exists()
