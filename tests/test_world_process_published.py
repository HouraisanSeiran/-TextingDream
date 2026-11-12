"""Causal end-to-end small world acceptance through the public map consumer."""
import json

import numpy as np

from app.map_source import load_source
from app.world_gen import config, fast_relief, skeleton, world_process_details


def test_forward_world_processes_publish_readable_same_source_layers(tmp_path, monkeypatch):
    # This bounded fixture tests publication, independently of other desktop
    # workloads. Real-world acceptance retains the production resource gates.
    import psutil
    from app.world_gen import sysmem
    memory = psutil.virtual_memory()
    monkeypatch.setattr(sysmem, 'available_memory_bytes', lambda: 8*2**30)
    monkeypatch.setattr(psutil, 'virtual_memory', lambda: memory._replace(available=8*2**30))
    cfg = config.normalize(dict(world_name='process-map', world_seed=20260903,
        world=dict(type='archipelago', size_km=400, ocean_fraction=.6)))
    source = tmp_path/'skeleton'
    skeleton.generate_skeleton(cfg, source, max_iterations=1, record_history=True)
    out, manifest = fast_relief.freeze(source/'skeleton.npz', tmp_path/'world',
        process_config=dict(shaping_rounds=2), log=lambda value: None)
    product = load_source('world-map-product', out, expected_identity=manifest['identity'])
    assert product.info.world_seed == 20260903
    assert {'discharge_m3_s', 'temperature_c', 'rock_index', 'erosion_m'} <= set(product.info.layers)
    coarse = np.load(out/'elevation_m.npy')
    process = np.load(out/'world-processes/elevation_m.npy')
    np.testing.assert_allclose(coarse, process, atol=.001)
    receiver = np.load(out/'receiver.npy')
    np.testing.assert_array_equal(receiver, np.load(out/'world-processes/receiver.npy'))
    saved = json.loads((out/'world-processes/manifest.json').read_text())
    assert abs(saved['metadata']['water_budget']['residual_m3']) < .01
    assert abs(saved['metadata']['solid_budget']['residual_m3']) < .01
    assert saved['metadata']['shaping']['old_unbudgeted_erosion_replaced']
    assert (out/'world-processes/checkpoint.json').is_file()
    assert saved['metadata']['geology']['stages'] == 50
    np.testing.assert_array_equal(np.load(out/'status.npy') == 3, np.load(out/'world-processes/ocean_mask.npy'))
    assert manifest['world_processes']['environment_status']['status'] == 'partial-or-pending'
    import pytest
    with pytest.raises(FileExistsError, match='immutable'):
        fast_relief.freeze(source/'skeleton.npz', out, process_config=dict(shaping_rounds=2))
    preview_bytes = (out/'manifest.json').read_bytes()
    revision = tmp_path/'revision'
    delivery = world_process_details.continue_world(out, revision, use_gpu=False, memory_wait_s=0.)
    final_manifest = json.loads((revision/'manifest.json').read_text())
    final_source = load_source('world-map-product', revision, expected_identity=final_manifest['identity'])
    assert final_source.info.identity != product.info.identity
    assert final_manifest['parent_preview_identity'] == manifest['identity']
    assert delivery['adaptive_resources']['model_started'] is False
    assert all(row['status'] == 'pending-terrain' for row in delivery['terrain'])
    assert (out/'manifest.json').read_bytes() == preview_bytes
    np.testing.assert_array_equal(np.load(revision/'elevation_m.npy'), coarse)
    assert world_process_details.continue_world(out, revision, use_gpu=False, memory_wait_s=0.) == delivery
    # Waiting policy is operational and may change during recovery, including
    # recovery of an early preparation marker without terrain_roots.
    marker = json.loads((revision/'preparation.json').read_text())
    marker.pop('terrain_roots', None)
    (revision/'preparation.json').write_text(json.dumps(marker), encoding='utf-8')
    assert world_process_details.continue_world(out, revision, use_gpu=False, memory_wait_s=10., memory_poll_s=1.) == delivery
    assert final_manifest['world_processes']['environment_status']['status'] == 'partial-or-pending'
    # Public map loading verifies the process binding without importing its
    # solver or generating any missing data.
    process_manifest = revision/'world-processes/manifest.json'
    original = process_manifest.read_bytes()
    process_manifest.write_bytes(original + b' ')
    from app.map_source import MapSourceError
    with pytest.raises(MapSourceError, match='SHA|sha|hash'):
        load_source('world-map-product', revision, expected_identity=final_manifest['identity'])
    process_manifest.write_bytes(original)
