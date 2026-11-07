"""Adaptive memory wait never lowers gates; it only polls until the budget is free."""
import time

import numpy as np
import pytest

from app.world_gen import local30, sysmem


def test_await_memory_gate_polls_until_budget_without_lowering_threshold(monkeypatch):
    samples = [3 * 2 ** 30, 3 * 2 ** 30, 5 * 2 ** 30]
    monkeypatch.setattr(sysmem, 'available_memory_bytes', lambda: samples.pop(0))
    sleeps = []
    monkeypatch.setattr(time, 'sleep', lambda seconds: sleeps.append(seconds))
    gate = local30.await_memory_gate(starting_worker=True, wait_s=30., poll_s=1.)
    assert gate['required_bytes'] == local30.HOST_WORKER_BYTES + local30.staging_bytes()
    assert gate['available_bytes'] == 5 * 2 ** 30
    assert gate['polls'] == 3
    assert sleeps == [1., 1.]
    assert gate['adaptive'] == 'wait-for-declared-budget'
    assert gate['min_available_bytes'] == 3 * 2 ** 30
    assert gate['peak_available_bytes'] == 5 * 2 ** 30


def test_await_memory_gate_times_out_without_lowering(monkeypatch):
    monkeypatch.setattr(sysmem, 'available_memory_bytes', lambda: 1 * 2 ** 30)
    monkeypatch.setattr(time, 'sleep', lambda seconds: None)
    with pytest.raises(MemoryError, match='Thresholds are not lowered'):
        local30.await_memory_gate(starting_worker=True, wait_s=2., poll_s=.5)


def test_prepare_tile_reuses_caller_generator_as_window_stage(tmp_path, monkeypatch):
    plate = tmp_path / 'plate.npz'
    calls = []

    def fake_gen(origin, side):
        calls.append((origin, side))
        return np.zeros((side, side), np.float32)

    fake_gen.__name__ = '_gpu_generate'
    monkeypatch.setattr('app.world_relief.td_resident.read_plate', lambda path: (None, {
        'identity': 'plate', 'config': {'world_seed': 20260903}}))
    monkeypatch.setattr(local30, 'freeze_tile', lambda *a, **k: dict(
        identity='tile', generator=dict(kind='terragenesis-gpu'), layers={}, runtime=k.get('runtime')))
    man = local30.prepare_tile(tmp_path, 0, 0, purpose='t', reason='r', plate_path=plate,
                               generator=fake_gen, available_bytes=2 * 2 ** 30, reuse=False)
    assert calls and man['runtime']['gate']['stage'] == 'window'
    assert man['runtime']['gate']['required_bytes'] == local30.memory_requirement_bytes(starting_worker=False)
