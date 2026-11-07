"""World process integration uses actual saved tectonic history and read-only maps."""
import json
from pathlib import Path

import numpy as np
import pytest

from app.world_gen import config, fast_relief, skeleton, world_process_adapter


def test_new_skeleton_records_real_forward_states_and_history(tmp_path):
    cfg = config.normalize(dict(world_name='history-integration', world_seed=20260903,
        world=dict(type='archipelago', size_km=400, ocean_fraction=.6)))
    skeleton.generate_skeleton(cfg, tmp_path, max_iterations=1, record_history=True, available_bytes=8*2**30)
    sk = fast_relief.load_skeleton(tmp_path/'skeleton.npz')
    history = world_process_adapter.load_history(sk)
    with np.load(sk['path'], allow_pickle=False) as source:
        np.testing.assert_array_equal(source['initial/elevation_m'], source['history/elevation_m'][0])
        assert source['history/elevation_m'].shape[0] > 2
    assert history['metadata']['stages'] == 50
    assert 'no physical' in history['metadata']['time_mapping']
    assert history['metadata']['budgets']['rock_bulk_residual_m3'] == pytest.approx(0, abs=10.)


def test_old_world_cannot_invent_history(tmp_path):
    np.savez(tmp_path/'old.npz', manifest_json=np.array(json.dumps(dict(arrays={}))))
    with pytest.raises(ValueError, match='record-history'):
        world_process_adapter.load_history(dict(path=tmp_path/'old.npz'))


def test_default_job_enables_forward_history_and_world_processes(tmp_path):
    pytest.importorskip('pydantic')
    from app.world_gen.web_jobs import WorldGenManager, WorldGenRequest
    manager = WorldGenManager(tmp_path)
    job = dict(params=WorldGenRequest().model_dump(), paths=manager._paths('20261107-000000-aaaa'), name='test')
    stages = manager.default_stages(job)
    assert '--record-history' in next(s.argv for s in stages if s.name == 'skeleton')
    assert '--world-processes' in next(s.argv for s in stages if s.name == 'fast')
