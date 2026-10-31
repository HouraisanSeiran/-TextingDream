# -*- coding: utf-8 -*-
"""World basis 单测：能力 vs 实现、真实 part pin、不可变保存、待解析状态。

这些测试守的是「不要多说话」：格式能带 ≠ 已经回放；part sum 必须服务端真算；
同身份不同内容不得静默覆盖；未回放的选年只能是 unresolved 草稿。
"""
import tempfile
import unittest
from pathlib import Path

from app import world_basis as wb
from app.storage import Store


def import_record(**over):
    """A record shaped like what the parser really returns (sum is server-computed)."""
    record = {
        'id': 'sn_abcdef123456',
        'format': 'civ_atlas_snapshot_v1',
        'sha256': 'b' * 64,
        'bytes': 4609307,
        'stats': {'lake_cells': 73},
        'units': {},
        'parts': [
            {'name': 'map', 'sum': 'c' * 64, 'sum_verified_by': 'server',
             'bytes': 2675727, 'zip': 'gzip'},
            {'name': 'eras', 'sum': 'd' * 64, 'sum_verified_by': 'server',
             'bytes': 190, 'zip': 'gzip'},
            {'name': 'civ', 'sum': 'e' * 64, 'sum_verified_by': 'server',
             'bytes': 1932123, 'zip': 'gzip'},
        ],
        'source': {
            'project': 'civ-atlas',
            'commit': '0939c5f1622a5e45cfc16f645ea3845993ab3985',
            'spec_commit': '0939c5f1622a5e45cfc16f645ea3845993ab3985',
            'generator_version': 45,
            'snapshot_format': 1,
            'recipe': 'dc9e079d0cb8',
            'world_id': 'wmvrpuwi29m3yi',
            'exported_at': '2026-10-28T06:11:28.837Z',
            'extractor': '织梦 tools/civ_atlas_export.js',
        },
    }
    record.update(over)
    return record


class BuildingTests(unittest.TestCase):
    def test_identity_and_source_pin_come_from_the_record(self):
        basis = wb.build(import_record(), base_year=1500)
        self.assertEqual(basis['world']['source_world_id'], 'wmvrpuwi29m3yi')
        self.assertEqual(basis['world']['generator'], 45)
        self.assertEqual(basis['source']['content_sha256'], 'b' * 64)
        self.assertEqual([p['name'] for p in basis['source']['parts']],
                         ['map', 'eras', 'civ'])
        # part sum 来自服务端计算，并标明来源
        for part in basis['source']['parts']:
            self.assertEqual(len(part['sum']), 64)
            self.assertEqual(part['sum_verified_by'], 'server')

    def test_seeds_are_null_and_explained(self):
        basis = wb.build(import_record(), base_year=1500)
        self.assertIsNone(basis['world']['terrain_seed'])
        self.assertIsNone(basis['world']['civ_seed'])
        self.assertIn('recipe', basis['world']['seed_note'])
        self.assertNotEqual(basis['world']['recipe'], basis['world']['terrain_seed'])

    def test_missing_branch_becomes_unknown(self):
        basis = wb.build(import_record(), base_year=1500)
        self.assertEqual(basis['selection']['branch'], 'unknown')
        self.assertFalse(basis['selection']['branch_known'])

    def test_base_year_must_be_a_real_int(self):
        for bad in (True, '1500', 1.5, None):
            with self.assertRaises(ValueError):
                wb.build(import_record(), base_year=bad)
        with self.assertRaises(ValueError):
            wb.build(import_record(), base_year=-1)

    def test_bad_hex_parts_sum_is_refused(self):
        broken = import_record()
        broken['parts'][0]['sum'] = 'not-a-hash'
        with self.assertRaises(ValueError):
            wb.build(broken, base_year=1500)

    def test_client_supplied_sum_without_server_marker_is_not_trusted(self):
        # 没有 sum_verified_by=server 的 sum 不会被当作已核对
        sneaky = import_record()
        for part in sneaky['parts']:
            part.pop('sum_verified_by', None)
        basis = wb.build(sneaky, base_year=1500)
        self.assertIsNone(basis['source']['parts'][0]['sum_verified_by'])


class CapabilityVersusImplementationTests(unittest.TestCase):
    def test_capability_and_history_are_separate_fields(self):
        basis = wb.build(import_record(), base_year=1500)
        # 格式能力：annals 是 exact
        self.assertEqual(basis['capability']['annals'], wb.EXACT)
        # 但实现状态是 unresolved，且 field_status 全部回落为 unknown
        self.assertEqual(basis['history']['state'], wb.STATE_UNRESOLVED)
        self.assertEqual(basis['field_status']['annals'], wb.UNKNOWN)
        self.assertEqual(basis['restorable'], [], '未实现回放时不应声称任何字段可恢复')

    def test_no_field_claims_replay(self):
        basis = wb.build(import_record(), base_year=1500)
        self.assertEqual(basis['history']['replayed_fields'], [])
        self.assertTrue(basis['history']['not_replayed_fields'])
        self.assertIn('不能当作可运行', basis['history']['note'])

    def test_unrecoverable_fields_stay_unknown(self):
        basis = wb.build(import_record(), base_year=1500)
        for field in ('population', 'resources', 'routes', 'terrain'):
            self.assertEqual(basis['capability'][field], wb.UNKNOWN, field)
            self.assertIn(field, basis['not_restorable'])

    def test_limits_do_not_claim_unimplemented_rejection(self):
        basis = wb.build(import_record(), base_year=1500)
        joined = ' '.join(basis['limits'])
        # 不能写“会明确拒绝”，因为现在根本没有回放实现
        self.assertIn('尚未实现回放', joined)


class VersioningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'x.sqlite3')

    def test_same_selection_is_idempotent(self):
        record = import_record()
        first = wb.build(record, base_year=1500)
        second = wb.build(record, base_year=1500)
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(first['digest'], second['digest'])
        a = wb.save(self.store, first)
        b = wb.save(self.store, second)
        self.assertTrue(a['created'])
        self.assertFalse(b['created'])

    def test_new_base_year_is_a_new_version(self):
        record = import_record()
        early = wb.build(record, base_year=800)
        late = wb.build(record, base_year=2000)
        self.assertNotEqual(early['id'], late['id'])
        wb.save(self.store, early)
        wb.save(self.store, late)
        self.assertEqual(len(wb.list_all(self.store)), 2)
        self.assertEqual(wb.get(self.store, early['id'])['selection']['base_year'], 800)

    def test_different_branch_is_different_identity(self):
        record = import_record()
        a = wb.build(record, base_year=1500, branch='main')
        b = wb.build(record, base_year=1500, branch='alt')
        self.assertNotEqual(a['id'], b['id'])

    def test_same_identity_different_content_is_refused(self):
        record = import_record()
        basis = wb.build(record, base_year=1500)
        wb.save(self.store, basis)
        # 同一 world/branch/year/sha，但内容（part sum）不同
        tampered = wb.build(import_record(), base_year=1500)
        tampered['source']['parts'][0]['sum'] = 'f' * 64
        tampered['digest'] = wb.digest_of(tampered)
        self.assertEqual(tampered['id'], basis['id'])
        with self.assertRaises(ValueError) as ctx:
            wb.save(self.store, tampered)
        self.assertIn('拒绝覆盖', str(ctx.exception))

    def test_forged_digest_is_refused(self):
        basis = wb.build(import_record(), base_year=1500)
        basis['digest'] = '0' * 64
        with self.assertRaises(ValueError):
            wb.save(self.store, basis)

    def test_forged_id_is_refused(self):
        basis = wb.build(import_record(), base_year=1500)
        basis['id'] = 'wb_deadbeefdeadbeef'
        with self.assertRaises(ValueError):
            wb.save(self.store, basis)

    def test_stale_source_hash_is_refused(self):
        record = import_record()
        basis = wb.build(record, base_year=1500)
        changed = import_record(sha256='f' * 64)
        with self.assertRaises(ValueError) as ctx:
            wb.refuse_stale(self.store, basis, changed)
        self.assertIn('拒绝关联', str(ctx.exception))
        self.assertTrue(wb.refuse_stale(self.store, basis, record))

    def test_part_sum_mismatch_is_refused(self):
        record = import_record()
        basis = wb.build(record, base_year=1500)
        altered = import_record()
        altered['parts'][0]['sum'] = 'a' * 64
        with self.assertRaises(ValueError) as ctx:
            wb.refuse_stale(self.store, basis, altered)
        self.assertIn('part map', str(ctx.exception))

    def test_unknown_id_is_refused(self):
        with self.assertRaises(ValueError):
            wb.get(self.store, 'nope')
        with self.assertRaises(ValueError):
            wb.get(self.store, 'wb_doesnotexist')


if __name__ == '__main__':
    unittest.main()
