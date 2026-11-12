"""Historical producer compatibility preserves every frozen source binding."""
from copy import deepcopy

import pytest

from app.world_gen import ocean_island_adapter as islands
from app.world_gen.config import sha256_json


def seal(row):
    row['identity'] = sha256_json({k: v for k, v in row.items() if k != 'identity'})
    return row


def stacks():
    old = seal(dict(schema='dream-ocean-island-binding-v1',
        island_algorithm='ocean-islands-metric-detail-smooth-seabed-v3',
        source_file_sha256='source', island_file_sha256='island', plate_identity='plate',
        island_identity='frozen', source_world_seed=20260903, island_world_seed=20260903,
        coordinates='absolute', ocean_quota=dict(target_fraction=.6, source_identity='run'),
        surface_policy=islands.SURFACE_POLICY, condition_policy=islands.CONDITION_POLICY,
        imported_sha256=dict(islands.FROZEN_V3_STACK)))
    current = deepcopy(old)
    current['imported_sha256'] = dict(islands.FROZEN_V3_READER_STACK)
    return old, seal(current)


def test_only_registered_v3_stack_has_reader_compatibility():
    old, current = stacks()
    assert islands.validate_saved_binding(old, current)['policy'] == 'audited-frozen-v3-reader-stack'
    assert islands.validate_saved_binding(old, old)['policy'] == 'identical-producer-stack'
    for row in (old, current):
        before = deepcopy(row)
        row['identity'] = 'forged'
        with pytest.raises(ValueError, match='identity mismatch'):
            islands.validate_saved_binding(old, current)
        row.update(before)


@pytest.mark.parametrize('algorithm', [
    'ocean-islands-metric-detail-smooth-seabed-v3',
    'ocean-islands-volcanic-stages-v4',
])
def test_frozen_v4_producer_stack_replays_through_registered_v5_reader(algorithm):
    old, current = stacks()
    old['island_algorithm'] = current['island_algorithm'] = algorithm
    old['imported_sha256'] = dict(islands.FROZEN_V4_STACK)
    seal(old)
    seal(current)
    version = 'v4' if algorithm.endswith('v4') else 'v3'
    assert islands.validate_saved_binding(old, current)['policy'] == f'audited-frozen-{version}-reader-stack'
    current['imported_sha256']['terrain_pipeline/island_volcanoes_v4.py'] = '0'*64
    seal(current)
    with pytest.raises(ValueError, match='producer stack changed'):
        islands.validate_saved_binding(old, current)


@pytest.mark.parametrize('key', ['source_file_sha256', 'island_file_sha256', 'plate_identity',
    'island_identity', 'source_world_seed', 'island_world_seed', 'coordinates', 'ocean_quota',
    'surface_policy', 'condition_policy', 'island_algorithm'])
def test_registered_producer_does_not_relax_any_data_binding(key):
    old, current = stacks()
    current[key] = 'changed'
    seal(current)
    with pytest.raises(ValueError, match='binding differs'):
        islands.validate_saved_binding(old, current)


def test_unknown_producer_change_and_added_dependency_are_rejected():
    for key, value in [('terrain_pipeline/ocean_islands.py', '0'*64), ('unregistered.py', '1'*64)]:
        old, current = stacks()
        current['imported_sha256'][key] = value
        seal(current)
        with pytest.raises(ValueError, match='producer stack changed'):
            islands.validate_saved_binding(old, current)


def test_frozen_v5_edifices_reader_stack(monkeypatch):
    old, current = stacks()
    old['island_algorithm'] = current['island_algorithm'] = 'ocean-islands-volcanic-edifices-v5'
    old['imported_sha256'] = dict(islands.FROZEN_V5_READER_STACK)
    seal(old)
    # Live digests currently match FROZEN_V3_READER_STACK, so same-stack replay is identical.
    assert islands.validate_saved_binding(old, old)['policy'] == 'identical-producer-stack'
    sibling = dict(islands.FROZEN_V5_READER_STACK)
    sibling['terrain_pipeline/ocean_islands.py'] = 'f' * 64
    monkeypatch.setattr(islands, '_COMPATIBLE_READERS', (islands.FROZEN_V5_READER_STACK, dict(sibling)))
    current['imported_sha256'] = dict(sibling)
    seal(current)
    assert islands.validate_saved_binding(old, current)['policy'] == 'audited-frozen-v5-reader-stack'
    current['imported_sha256']['terrain_pipeline/ocean_islands.py'] = '0' * 64
    seal(current)
    with pytest.raises(ValueError, match='producer stack changed'):
        islands.validate_saved_binding(old, current)


def test_old_mountain_reader_is_only_compatible_with_empty_v3_corrections():
    from app.world_gen.web_island_stage import validate_mountain_reader
    old, _ = stacks()
    record = dict(binding=old, mountains=dict(products=[]),
        imported_sha256='6ad03099ff2b2eccd59fb02183e2b56494b974f7faaf285eb858aa28ff342879')
    current = 'c1cf6326a9a093a2a5f08dde76d906b075921f410cbef911998db0ba75e4db92'
    compatibility = dict(policy='audited-frozen-v3-reader-stack')
    assert validate_mountain_reader(record, current, compatibility)['policy'] == 'audited-v3-empty-correction-reader'
    record['mountains']['products'] = [dict(tile='real-derived-tile')]
    with pytest.raises(ValueError, match='mountain algorithm changed'):
        validate_mountain_reader(record, current, compatibility)
    record['mountains']['products'] = []
    with pytest.raises(ValueError, match='mountain algorithm changed'):
        validate_mountain_reader(record, '0'*64, compatibility)
