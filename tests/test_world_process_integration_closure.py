"""Focused default-flow, cache and truthful-status regression checks."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from app.world_gen import graph_hydro as gh, world_process_adapter as adapter


def test_environment_aggregation_preserves_conditional_pending():
    metadata = dict(generation_environment=dict(status='complete'), environment=dict(processes={
        'snow': dict(status='computed'), 'glacier': dict(status='not-triggered'),
        'groundwater': dict(status='pending-input', reason='missing aquifer')}))
    before = json.dumps(metadata, sort_keys=True)
    result = adapter.environment_status(metadata)
    assert result['status'] == 'partial-or-pending'
    assert set(result['pending_processes']) == {'groundwater'}
    assert json.dumps(metadata, sort_keys=True) == before
    metadata['environment']['processes'].pop('groundwater')
    assert adapter.environment_status(metadata)['status'] == 'complete'


def test_cached_process_checks_numerical_config_and_updates_resume_budget(tmp_path, monkeypatch):
    pytest.importorskip('numba')
    gh.load_terragenesis()
    from terrain_pipeline import drainage, world_processes
    bed = np.ones((2, 2))
    route = SimpleNamespace(receiver=np.array([-1, 0, 0, 1]), order=np.arange(4))
    monkeypatch.setattr(drainage, 'route_graph', lambda *args: route)
    monkeypatch.setattr(drainage, 'accumulate_graph', lambda *args: bed)
    monkeypatch.setattr(adapter, 'load_history', lambda *args: {})
    monkeypatch.setattr(world_processes, 'compute', lambda source, cfg: dict(metadata=dict(
        source_identity=source['source_identity'], config=world_processes.plan(source, cfg)['config'])))
    args = (dict(world_seed=20260903, identity='plate'), bed, bed < 0, None, bed < 0, (0., 0.), 2000.)
    saved = adapter.compute(*args, config=dict(shaping_rounds=2))
    saved['metadata']['config'] = adapter.numerical_config(saved['metadata']['config'])
    (tmp_path/'manifest.json').write_text('{}')
    monkeypatch.setattr(world_processes, 'query', lambda *args: saved)
    assert adapter.compute(*args, config=dict(shaping_rounds=2, wallclock_budget_seconds=99), out_dir=tmp_path) is saved
    with pytest.raises(ValueError, match='numerical configuration differs'):
        adapter.compute(*args, config=dict(shaping_rounds=3), out_dir=tmp_path)
    (tmp_path/'manifest.json').unlink()
    (tmp_path/'checkpoint.json').write_text(json.dumps(dict(source=dict(source_identity=saved['metadata']['source_identity']),
        config=dict(saved['metadata']['config'], pause_after_round=1))))
    observed = []
    monkeypatch.setattr(world_processes, 'resume', lambda *args, **kw: observed.append(kw) or dict(status='published-coarse'))
    adapter.compute(*args, config=dict(shaping_rounds=2, wallclock_budget_seconds=99), out_dir=tmp_path)
    assert observed == [dict(config=dict(wallclock_budget_seconds=99))]


def test_publish_rejects_different_existing_process_identity(tmp_path, monkeypatch):
    pytest.importorskip('numba')
    gh.load_terragenesis()
    from terrain_pipeline import world_processes
    (tmp_path/'manifest.json').write_text('{}')
    monkeypatch.setattr(world_processes, 'query', lambda *args: dict(identity='different'))
    result = dict(arrays=dict(elevation_m=np.ones((2, 2))), metadata=dict(config={}, cpu_seconds=1))
    with pytest.raises(ValueError, match='differ from requested result'):
        adapter.publish(result, tmp_path)


def test_default_job_publishes_preview_before_automatic_detail(tmp_path):
    pytest.importorskip('pydantic')
    from app.world_gen.web_jobs import WorldGenManager, WorldGenRequest
    manager = WorldGenManager(tmp_path)
    draft = dict(params=WorldGenRequest().model_dump(), paths=manager._paths('20261108-000000-aaaa'), name='test')
    draft_names = [stage.name for stage in manager.default_stages(draft)]
    assert draft_names == ['skeleton', 'islands', 'island-mountains', 'fast', 'render', 'summary']
    job = dict(params=WorldGenRequest(pipeline='full').model_dump(), paths=manager._paths('20261108-000000-bbbb'), name='test')
    stages = manager.default_stages(job)
    names = [stage.name for stage in stages]
    assert names.index('fast') < names.index('render') < names.index('details') < names.index('final-render')
    assert '--use-gpu' not in next(stage.argv for stage in stages if stage.name == 'details')
    assert job['params']['seed'] == 20260903
