"""Mountain reinforcement (dream-world-skeleton-2): coverage hits the target, same seed gives identical output,
the land/sea split is untouched. Small CPU-only worlds."""
import hashlib

import numpy as np
import pytest

from app.world_gen import config as wc, mountains as mt, skeleton as sk


def _cfg(name='mtn-small', preset='multi-continent', size=800):
    return wc.normalize({'world_name': name, 'world': {'type': preset, 'size_km': size, 'ocean_fraction': 0.6}})


@pytest.fixture(scope='module')
def enhanced(tmp_path_factory):
    root = tmp_path_factory.mktemp('mtn')
    cfg = _cfg()
    m1 = sk.generate_skeleton(cfg, root / 'a', max_iterations=3, enhance=True)
    m2 = sk.generate_skeleton(cfg, root / 'b', max_iterations=3, enhance=True)
    return root, cfg, m1, m2


def test_coverage_close_to_target(enhanced):
    _, _, m, _ = enhanced
    assert m['algorithm'] == 'dream-world-skeleton-2'
    assert abs(m['actual']['mountain_deviation']) <= 0.02
    assert abs(m['actual']['ocean_deviation']) <= 0.015
    reuse = {r['file']: r for r in m['terragenesis_reuse']}
    assert len(reuse['terrain_pipeline/skeleton_mountains.py']['sha256']) == 64
    assert {'mountain-bend', 'plains-relief-fine'} <= set(m['subseeds'])


def test_same_seed_is_identical(enhanced):
    root, _, m1, m2 = enhanced
    with np.load(root / 'a' / 'skeleton.npz') as a, np.load(root / 'b' / 'skeleton.npz') as b:
        assert np.array_equal(a['final/elevation_m'], b['final/elevation_m'])
    assert m1['product']['plate_identity'] == m2['product']['plate_identity']
    assert m1['product']['sha256'] == m2['product']['sha256']


def test_enhancement_keeps_land_sea_split(enhanced):
    root, _, m, _ = enhanced
    te, _ = sk._terragenesis()
    cfg = _cfg()
    tc = sk.tectonic_config(cfg, speed_m_per_step=2000.0)
    field = sk.land_field('multi-continent', tc.shape, cfg['world_seed'])
    res = te.evolve(tc, sk._initial_state(te, tc, cfg, field, cfg['world']['ocean_fraction']))
    raw = np.asarray(te.surface_fields(res.final)['elevation_m'], dtype=np.float64)
    out, meta = mt.enhance_mountains(raw, res.final.plate_id if hasattr(res.final, 'plate_id') else te.surface_fields(res.final)['plate_id'],
                                     res.final.velocities_m_per_step, cell_m=tc.cell_size_m, world_seed=cfg['world_seed'],
                                     target_fraction=0.12)
    assert np.array_equal(raw > 0, out > 0)
    assert np.array_equal(raw[raw <= 0], out[raw <= 0])
    land = raw > 0
    assert abs(float((out > 1500)[land].mean()) - 0.12) <= 0.02
