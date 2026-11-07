# -*- coding: utf-8 -*-
"""价格审计（tools/price_audit.py）：只挑同类同单位里明显偏离的估价。"""
import unittest

from tools import price_audit as pa


def row(ident, klass, per, high):
    return {'group': 'g', 'id': ident, 'name': ident, 'class': klass, 'per': per,
            'min': 1, 'max': high, 'tier': 'x'}


class AuditCase(unittest.TestCase):
    def test_outlier_in_same_class_and_unit_is_flagged(self):
        rows = [row('a', 'spice', '一盎司', 12), row('b', 'spice', '一盎司', 16),
                row('c', 'spice', '一盎司', 14), row('d', 'spice', '一盎司', 200)]
        found = pa.audit(rows, ratio=4, min_group=4)
        self.assertEqual([item['id'] for item in found], ['d'])
        self.assertEqual(found[0]['direction'], 'high')

    def test_different_units_are_not_compared(self):
        rows = [row('a', 'meat', '一磅', 4), row('b', 'meat', '一磅', 5), row('c', 'meat', '一磅', 6),
                row('d', 'meat', '一头', 900)]
        self.assertEqual(pa.audit(rows, ratio=4, min_group=3), [])

    def test_small_groups_are_skipped(self):
        rows = [row('a', 'fruit', '一个', 1), row('b', 'fruit', '一个', 100)]
        self.assertEqual(pa.audit(rows, ratio=4, min_group=4), [])

    def test_real_library_collects_prices(self):
        """有价条目数 = 全部带 game 且不是 not_for_sale/priceless 的元素数，不写死数字。"""
        import json
        from tools import encyclopedia_build as build
        from tools import game_fields as gf
        expected = 0
        for relative in build.groups_for(**build.ALL_FLAGS):
            document = json.loads((pa.ROOT / relative).read_text(encoding='utf-8-sig'))
            for element in gf.overlay(document).get('elements') or []:
                tier = ((element.get('game') or {}).get('price') or {}).get('tier')
                if tier and tier not in gf.NO_PRICE_TIERS:
                    expected += 1
        rows = pa.collect()
        self.assertGreater(expected, 0)
        self.assertEqual(len(rows), expected)
        self.assertTrue(all(isinstance(item['max'], int) for item in rows))


class LibraryCase(unittest.TestCase):
    def test_no_unreviewed_anomalies(self):
        """真实库里所有价格异常要么已修，要么登记在已审清单里并写了理由。"""
        rows = pa.collect()
        accepted = pa.load_accepted()
        self.assertTrue(all(isinstance(reason, str) and reason for reason in accepted.values()))
        self.assertFalse(set(accepted) - {row['id'] for row in rows}, '已审清单有过期 id')
        pending = [item['id'] for item in pa.audit(rows) if item['id'] not in accepted]
        self.assertEqual(pending, [])


if __name__ == '__main__':
    unittest.main()
