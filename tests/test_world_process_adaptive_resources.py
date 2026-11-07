"""Detail continuation adapts resource use: one worker, cache first, declared waits."""
from pathlib import Path

import numpy as np

from app.world_gen import local30, tiles


def test_shared_worker_policy_orders_cache_before_missing(tmp_path, monkeypatch):
    raw_root = tmp_path / 'raw'
    cached_tile = tiles.tile_window(0, 0)
    missing_tile = tiles.tile_window(1, 0)
    cached_path = local30.tile_manifest_path(raw_root, cached_tile['id'])
    cached_path.parent.mkdir(parents=True)
    cached_path.write_text('{}', encoding='utf-8')
    unique = [(1, 0), (0, 0)]
    ordered = []
    for ix, iz in unique:
        tile = tiles.tile_window(ix, iz)
        cached = local30.tile_manifest_path(raw_root, tile['id'])
        ordered.append((0 if cached.exists() else 1, ix, iz, tile, cached))
    ordered.sort()
    assert [row[1:3] for row in ordered] == [(0, 0), (1, 0)]

    starts = []

    def fake_default(*args, **kwargs):
        starts.append('start')

        def generate(origin, side):
            return np.zeros((side, side), np.float32)

        generate.__name__ = '_gpu_generate'
        return generate

    monkeypatch.setattr(local30, '_default_generator', fake_default)
    monkeypatch.setattr(local30, 'await_memory_gate', lambda **kw: dict(
        available_bytes=8 * 2 ** 30, required_bytes=1,
        stage='start' if kw.get('starting_worker') else 'window', waited_s=0., polls=1))
    monkeypatch.setattr(local30, 'gpu_gate', lambda: {})

    producer = None

    def shared_generator(origin, side):
        nonlocal producer
        if producer is None:
            local30.await_memory_gate(starting_worker=True, wait_s=1., poll_s=.1)
            local30.gpu_gate()
            producer = local30._default_generator('plate', None)
        return producer(origin, side)

    shared_generator.__name__ = '_gpu_generate'
    prepared = []
    for _, ix, iz, tile, cached in ordered:
        if cached.exists():
            prepared.append(('cache', tile['id']))
            continue
        shared_generator((0, 0), 4)
        prepared.append(('gpu', tile['id']))
    assert starts == ['start']
    assert prepared == [('cache', cached_tile['id']), ('gpu', missing_tile['id'])]


def test_continue_world_cli_exposes_memory_wait_flags():
    text = Path(__file__).resolve().parents[1].joinpath('app/world_gen/world_process_details.py').read_text(encoding='utf-8')
    assert '--memory-wait-s' in text
    assert 'reuse-one-worker' in text
    assert 'Thresholds are not lowered' in Path(local30.__file__).read_text(encoding='utf-8')
