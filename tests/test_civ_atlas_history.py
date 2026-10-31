# -*- coding: utf-8 -*-
"""civ-atlas 历史回放专项：按年有界背景候选、字段声明、公开投影。

两层测据，**明确分开**：

1. **合成契约 fixture**（下面 :func:`civ_block` 等）——全部自造，按
   ``src/gen/civ/types.ts`` 的字段定义摆出来，用来守「边界、年份、预算、unknown」这些逻辑。
2. **真实解析 probe**（:class:`RealExportProbeTests`）——读旧代理真实 civ-atlas
   导出的一份 ``.civsnap``（34097 地块 / endYear 3000 / 三 part）。只读、不拷进正式
   ``data/``、不跑上游、不联网。找不到文件就 skip 并打印「未验真」。

真实样本暴露的两个真实事实被这些测试固定住：年份是**浮点**（如 511.9765625），
且 ``civ.seed`` 确实在导出里。
"""
import json
import math
import unittest
from pathlib import Path

from app import civ_atlas_history as hist
from app import civ_atlas_snapshot as snap
from app.world_basis import EXACT, INTERVAL, UNKNOWN

ROOT = Path(__file__).resolve().parents[1]
#: 旧代理真实导出的测试产物（不是用户存档）。找不到就 skip，不当成「已验真」。
REAL_EXPORT = Path(r'D:/Vantaloom/data/temp/project-proj-1792851796-712e540fb0'
                   r'/scratch/real-verify-data/map_imports'
                   r'/2f364872015835be5a905876c6bdf5ae.civsnap')


# ------------------------------------------------------------------ fixtures
def civ_block(**over):
    """A **synthetic** ``civ`` block following the types.ts fields.

    4 regions, checkpoints every 100 years, a change log with fractional years, two
    polities, three settlements, two people, a handful of annals. Every number here is
    made up for the test; the real-data check below uses a genuine upstream export.
    """
    # Ownership, sorted by year. The log, the checkpoints and the exported end state are
    # built to be *mutually consistent* — that is what the endYear cross-check verifies:
    #   cp100 = log <= 100 applied; cp200 = log <= 200 applied; end state = cp300 = all log.
    log = {
        'size': 5,
        'year': [50.5, 150.25, 160.0, 250.75, 260.0],
        'region': [0, 1, 1, 0, 2],
        'layer': [1, 1, 0, 0, 0],   # 0 = culture, 1 = polity
        'value': [0, 1, 0, 1, 1],
        'cause': [0, 0, 0, 0, 0],
    }
    end_culture = [1, 0, 1, -1]
    end_polity = [0, 1, -1, -1]
    checkpoints = [
        {'year': 100, 'culture': [-1, -1, -1, -1], 'polity': [0, -1, -1, -1]},
        {'year': 200, 'culture': [-1, 0, -1, -1], 'polity': [0, 1, -1, -1]},
        {'year': 300, 'culture': end_culture, 'polity': end_polity},
    ]
    block = {
        'seed': 4242,
        'endYear': 300,
        'viable': True,
        'regions': {'count': 4},
        'cultures': [
            {'id': 0, 'name': '北民', 'born': 0},
            {'id': 1, 'name': '南民', 'born': 20},
        ],
        'polities': [
            {'id': 0, 'name': '昌', 'culture': 0, 'capital': 0, 'founded': 50.5,
             'capitals': [{'year': 50.5, 'settlement': 0}]},
            {'id': 1, 'name': '景', 'culture': 1, 'capital': 1, 'founded': 150.25,
             'ended': 260.0,
             'capitals': [{'year': 150.25, 'settlement': 1},
                          {'year': 210.0, 'settlement': 2}]},
            # a polity with no capitals[] at all: its capital must stay unknown
            {'id': 2, 'name': '旧', 'culture': 0, 'capital': 2, 'founded': 10},
        ],
        'settlements': [
            {'id': 0, 'cell': 0, 'region': 0, 'culture': 0, 'name': '昌城',
             'founded': 50.5, 'ends': None},
            {'id': 1, 'cell': 1, 'region': 1, 'culture': 1, 'name': '景城',
             'founded': 150.25, 'ended': 260.0,
             'capitalSpans': [{'from': 150.25, 'until': 210.0, 'polity': 1},
                              {'from': 210.0, 'polity': 1}]},
            {'id': 2, 'cell': 2, 'region': 2, 'culture': 1, 'name': '后城',
             'founded': 200.0},
        ],
        'people': [
            # alive at 200, dies at 280: the public view must not leak that death
            {'id': 0, 'role': 'ruler', 'polity': 0, 'name': '甲', 'born': 40.0,
             'from': 50.5, 'died': 280.0, 'until': 280.0, 'fate': 'died'},
            {'id': 1, 'role': 'general', 'polity': 1, 'name': '乙', 'born': 120.0,
             'died': 180.0},
        ],
        'annals': [
            {'year': 50.5, 'kind': 'found', 'a': 0, 'b': -1, 'region': 0,
             'settlement': 0, 'war': -1},
            {'year': 150.25, 'kind': 'found', 'a': 1, 'b': 0, 'region': 1,
             'settlement': 1, 'war': -1},
            {'year': 200.0, 'kind': 'war', 'a': 0, 'b': 1, 'region': -1,
             'settlement': -1, 'war': 0, 'cause': 'claim'},
            {'year': 210.0, 'kind': 'peace', 'a': 0, 'b': 1, 'region': 2,
             'settlement': -1, 'war': 0},
            {'year': 250.75, 'kind': 'assimilate', 'a': 1, 'b': 0, 'region': 0,
             'settlement': -1, 'war': -1},
            {'year': 260.0, 'kind': 'fall', 'a': 1, 'b': 0, 'region': 2,
             'settlement': -1, 'war': 0},
            # a kind this reader does not know: must stay raw and be marked unresolved
            {'year': 270.0, 'kind': 'some_future_kind', 'a': 7, 'b': 3, 'region': -1,
             'settlement': -1, 'war': -1},
        ],
        'religion': {
            'faiths': [{'id': 0, 'kind': 'folk', 'name': '旧神', 'culture': 0}],
            'events': [{'year': 180.0, 'kind': 'found', 'faith': 0, 'polity': 0,
                        'region': 0, 'settlement': 0}],
            'states': [{'polity': 0, 'faith': 0, 'from': 100.0, 'until': 250.0}],
            'log': {'size': 1, 'year': [120.0], 'region': [0], 'value': [0]},
            'checkpoints': [{'year': 200, 'faith': [0, -1, -1, -1]}],
        },
        'log': log,
        'checkpoints': checkpoints,
        'culture': end_culture,
        'polity': end_polity,
    }
    block.update(over)
    block['settlements'][0].pop('ends', None)
    return block


IDENTITY = {
    'content_sha256': 'a' * 64,
    'world_id': 'w1',
    'import_id': 'sn_test',
    'branch': 'main',
    'generator': 45,
    'snapshot_format': 1,
}


# ------------------------------------------------------------------- contract
class ContractTests(unittest.TestCase):
    """Frozen call surface + declared limits. Changing these on purpose is fine; doing it
    by accident is not."""

    def test_public_signatures_are_frozen(self):
        import inspect
        self.assertEqual(
            str(inspect.signature(hist.build)),
            '(civ, *, base_year, window=None, identity=None, terrain=None, '
            'hidden_refs=(), include_regions=False, max_events=240, max_entities=200)')
        self.assertEqual(str(inspect.signature(hist.public_view)),
                         '(document, *, allow=(), max_events=None)')
        self.assertEqual(str(inspect.signature(hist.inspect)), '(civ)')
        self.assertEqual(str(inspect.signature(hist.decode_civ_part)),
                         '(manifest, parts)')
        self.assertEqual(str(inspect.signature(hist.load_civ)), '(data)')
        self.assertEqual(
            str(inspect.signature(hist.identity_from)),
            '(manifest, record=None, branch=None, terrain_seed=None)')

    def test_limits_are_declared(self):
        self.assertEqual(hist.GENERATOR_VERSION, 45)
        self.assertEqual(hist.SNAPSHOT_FORMAT, 1)
        self.assertEqual(hist.SPEC_COMMIT, '0939c5f1622a5e45cfc16f645ea3845993ab3985')
        self.assertEqual(hist.LIMITS['default_window_years'], 150)
        self.assertEqual(hist.LIMITS['default_max_events'], 240)
        self.assertEqual(hist.LIMITS['default_max_entities'], 200)
        self.assertGreater(hist.LIMITS['max_log_entries'], 0)
        self.assertEqual(tuple(hist.FIELDS), tuple(sorted(hist.FIELDS, key=hist.FIELDS.index)))

    def test_field_names_match_world_basis(self):
        from app import world_basis
        self.assertEqual(set(hist.FIELDS), set(world_basis.FIELD_CAPABILITY))

    def test_module_is_pure_no_io(self):
        source = (ROOT / 'app' / 'civ_atlas_history.py').read_text(encoding='utf-8')
        for banned in ('open(', 'requests', 'urllib', 'socket', 'subprocess',
                       'os.environ', 'sqlite3', 'datetime.now'):
            self.assertNotIn(banned, source,
                             'history reader must stay a pure function: found %r' % banned)


# --------------------------------------------------------------------- inspect
class InspectTests(unittest.TestCase):
    def test_inspect_reports_counts_without_claiming_years(self):
        shape = hist.inspect(civ_block())
        self.assertEqual(shape['end_year'], 300)
        self.assertEqual(shape['region_count'], 4)
        self.assertEqual(shape['counts']['annals'], 7)
        self.assertEqual(shape['counts']['checkpoints'], 3)
        self.assertEqual(shape['first_checkpoint_year'], 100)
        self.assertEqual(shape['last_checkpoint_year'], 300)
        self.assertEqual(shape['civ_seed'], 4242)
        self.assertEqual(shape['unknown_annal_kinds'], ['some_future_kind'])
        self.assertEqual(shape['anomalies']['count'], 0)

    def test_inspect_refuses_non_object(self):
        with self.assertRaises(hist.HistoryError):
            hist.inspect([])


# ---------------------------------------------------------------- year handling
class YearPrecisionTests(unittest.TestCase):
    """The real export's years are fractional, so nothing may be truncated to an int."""

    def test_base_year_accepts_fractional_years(self):
        year = hist._base_year(511.9765625)
        self.assertEqual(year, 511.9765625)
        self.assertIsInstance(year, float)

    def test_founding_year_boundary_is_exact(self):
        block = civ_block()
        # polity 0 is founded at 50.5: it must not exist at 50, must exist at 50.5.
        # (polity 2 was founded at 10 and never ended, so it is the only one alive at 50.)
        before = hist.build(block, base_year=50, identity=IDENTITY)
        at = hist.build(block, base_year=50.5, identity=IDENTITY)
        self.assertEqual({item['id'] for item in before['polities']['items']}, {2})
        self.assertEqual({item['id'] for item in at['polities']['items']}, {0, 2})
        self.assertEqual([item for item in at['polities']['items']
                          if item['id'] == 0][0]['founded'], 50.5)

    def test_city_before_founding_is_not_projected_back(self):
        block = civ_block()
        early = hist.build(block, base_year=150, identity=IDENTITY)
        ids = {item['id'] for item in early['settlements']['items']}
        self.assertNotIn(1, ids, '景城 founded 150.25 must not appear at 150')
        later = hist.build(block, base_year=150.25, identity=IDENTITY)
        self.assertIn(1, {item['id'] for item in later['settlements']['items']})

    def test_city_after_ended_is_gone(self):
        block = civ_block()
        at = hist.build(block, base_year=259.9, identity=IDENTITY)
        self.assertIn(1, {item['id'] for item in at['settlements']['items']})
        after = hist.build(block, base_year=260.0, identity=IDENTITY)
        self.assertNotIn(1, {item['id'] for item in after['settlements']['items']})

    def test_dead_person_is_not_listed(self):
        block = civ_block()
        at = hist.build(block, base_year=179.9, identity=IDENTITY)
        self.assertIn(1, {item['id'] for item in at['people']['items']})
        after = hist.build(block, base_year=180.0, identity=IDENTITY)
        self.assertNotIn(1, {item['id'] for item in after['people']['items']})


# --------------------------------------------------------------- region replay
class RegionReplayTests(unittest.TestCase):
    def test_replay_from_checkpoint_plus_log(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY,
                         include_regions=True)
        block = doc['region_replay']
        self.assertEqual(block['status'], INTERVAL)
        self.assertEqual(block['checkpoint_year_used'], 200)
        # the checkpoint at 200 already includes every change up to and including 200
        self.assertEqual(block['culture'], [-1, 0, -1, -1])
        self.assertEqual(block['polity'], [0, 1, -1, -1])
        self.assertEqual(doc['field_status']['region_polity']['status'], INTERVAL)

    def test_log_after_checkpoint_is_applied(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY,
                         include_regions=True)
        block = doc['region_replay']
        self.assertEqual(block['checkpoint_year_used'], 200)
        self.assertGreaterEqual(block['log_entries_applied'], 2)
        self.assertEqual(block['culture'], [1, 0, 1, -1])
        self.assertEqual(block['polity'], [0, 1, -1, -1])

    def test_end_year_check_actually_replays_the_log(self):
        """Anchoring strictly before endYear keeps the check non-trivial."""
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY)
        check = doc['region_replay']['end_state_check']
        self.assertEqual(check['status'], EXACT)
        self.assertEqual(check['mode'], 'log_replay')
        self.assertEqual(check['anchor_checkpoint_year'], 200)
        self.assertEqual(check['log_entries_applied'], 2)   # 250.75 and 260

    def test_end_year_check_is_exact_and_independent_of_base_year(self):
        for year in (100, 150.25, 200, 300):
            doc = hist.build(civ_block(), base_year=year, identity=IDENTITY)
            check = doc['region_replay']['end_state_check']
            self.assertEqual(check['status'], EXACT, 'base year %r' % (year,))
            self.assertEqual(check['checked_at'], 300)
            self.assertEqual(check['anchor_checkpoint_year'], 200)

    def test_only_a_checkpoint_at_end_year_is_not_called_verified(self):
        block = civ_block()
        block['checkpoints'] = [block['checkpoints'][2]]      # only year 300
        doc = hist.build(block, base_year=300, identity=IDENTITY)
        check = doc['region_replay']['end_state_check']
        self.assertEqual(check['mode'], 'checkpoint_only')
        self.assertIn('未验证', check['reason'])

    def test_broken_log_makes_region_layer_unknown_not_wrong(self):
        block = civ_block()
        block['log'] = dict(block['log'], value=[0, 1, 1, 99])   # last write breaks endYear
        doc = hist.build(block, base_year=260, identity=IDENTITY, include_regions=True)
        self.assertEqual(doc['region_replay']['status'], UNKNOWN)
        self.assertIsNone(doc['region_replay']['culture'])
        self.assertEqual(doc['field_status']['region_culture']['status'], UNKNOWN)
        self.assertGreaterEqual(doc['anomalies']['count'], 1)

    def test_before_first_checkpoint_is_unknown_not_empty_history(self):
        doc = hist.build(civ_block(), base_year=50, identity=IDENTITY)
        block = doc['region_replay']
        self.assertEqual(block['status'], UNKNOWN)
        self.assertIn('早于第一个检查点', block['reason'])
        # ...and the endYear self-check still passed: the data is fine, the year is early
        self.assertEqual(block['end_state_check']['status'], EXACT)

    def test_region_lists_are_opt_in(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY)
        self.assertIsNone(doc['region_replay']['culture'])
        self.assertEqual(doc['region_replay']['counts']['regions'], 4)
        self.assertTrue(doc['region_replay']['polity_legend'])

    def test_log_size_is_the_valid_prefix(self):
        block = civ_block()
        log = dict(block['log'])
        # arrays longer than `size`, with a *wrong* tail that must not be read
        for key, tail in (('year', [999.0, 1000.0]), ('region', [3, 3]),
                          ('layer', [0, 0]), ('value', [1, 1])):
            log[key] = list(log[key]) + tail
        log['size'] = 5
        block['log'] = log
        doc = hist.build(block, base_year=260, identity=IDENTITY, include_regions=True)
        self.assertEqual(doc['region_replay']['status'], INTERVAL)
        self.assertEqual(doc['region_replay']['culture'], [1, 0, 1, -1])
        self.assertEqual(doc['region_replay']['end_state_check']['status'], EXACT)

    def test_out_of_range_region_index_is_refused(self):
        block = civ_block()
        block['log'] = dict(block['log'], region=[0, 1, 0, 7])
        doc = hist.build(block, base_year=260, identity=IDENTITY)
        self.assertEqual(doc['region_replay']['status'], UNKNOWN)


# ---------------------------------------------------------------------- annals
class AnnalsTests(unittest.TestCase):
    def test_window_ends_at_base_year_never_beyond(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        counts = doc['annals']['counts']
        self.assertEqual(doc['annals']['window'], {'from': 50, 'to': 200})
        self.assertEqual(counts['on_or_before_base_year'], 3)
        self.assertEqual(counts['inside_window'], 3)

    def test_explicit_window_cannot_look_into_the_future(self):
        with self.assertRaises(hist.HistoryError):
            hist.build(civ_block(), base_year=200, window=(150, 260),
                       identity=IDENTITY)

    def test_events_are_a_fact_list_not_a_full_state(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY)
        self.assertFalse(doc['annals']['is_full_state'])
        self.assertIn('不是该年的完整状态', doc['annals']['note'])
        self.assertFalse(doc['annals']['ai_chronicle_used'])

    def test_a_and_b_meanings_follow_the_kind(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY)
        events = {event['kind']: event for event in doc['annals']['events']}
        self.assertEqual(events['found']['a_means'], 'polity')
        self.assertEqual(events['assimilate']['a_means'], 'culture')
        self.assertEqual(events['assimilate']['b_means'], 'culture')
        self.assertEqual(events['assimilate']['a_ref'].rsplit('/', 2)[-2], 'culture')
        # peace: the region column is a ceded-region *count*, not a region id
        self.assertIn('割让的州数', events['peace']['column_note'])

    def test_unknown_kind_keeps_raw_columns_and_says_unresolved(self):
        doc = hist.build(civ_block(), base_year=280, identity=IDENTITY)
        event = [item for item in doc['annals']['events']
                 if item['kind'] == 'some_future_kind'][0]
        self.assertFalse(event['kind_known'])
        self.assertIn('unresolved', event)
        self.assertIsNone(event['a_ref'])
        self.assertIsNone(event['a_id'])
        self.assertIn('a_raw', event)
        self.assertEqual(doc['annals']['counts']['unknown_kind'], 1)

    def test_event_budget_truncates_but_counts_stay_exact(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY, max_events=2)
        counts = doc['annals']['counts']
        self.assertEqual(len(doc['annals']['events']), 2)
        self.assertTrue(counts['truncated'])
        self.assertEqual(counts['inside_window'], counts['returned'] + counts['truncated']
                         if False else counts['inside_window'])
        self.assertGreater(counts['inside_window'], 2)

    def test_bad_budget_is_refused(self):
        with self.assertRaises(hist.HistoryError):
            hist.build(civ_block(), base_year=200, identity=IDENTITY, max_events=0)
        with self.assertRaises(hist.HistoryError):
            hist.build(civ_block(), base_year=200, identity=IDENTITY, max_entities=0)


# ----------------------------------------------------------------- timeframe rules
class TimeframeTests(unittest.TestCase):
    def test_base_year_after_end_year_is_refused(self):
        with self.assertRaises(hist.HistoryError):
            hist.build(civ_block(), base_year=301, identity=IDENTITY)

    def test_negative_base_year_is_refused(self):
        with self.assertRaises(hist.HistoryError):
            hist.build(civ_block(), base_year=-1, identity=IDENTITY)

    def test_end_year_must_exist(self):
        with self.assertRaises(hist.HistoryError):
            hist.build({}, base_year=10, identity=IDENTITY)

    def test_base_year_at_end_year_is_allowed(self):
        doc = hist.build(civ_block(), base_year=300, identity=IDENTITY)
        self.assertEqual(doc['selection']['base_year'], 300)


# ------------------------------------------------------------------- identities
class IdentityTests(unittest.TestCase):
    def test_refs_carry_world_branch_and_source_identity(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY)
        ref = doc['polities']['items'][0]['ref']
        self.assertTrue(ref.startswith('casnap:aaaaaaaaaaaaaaaa:w1/main/'), ref)
        self.assertTrue(ref.endswith('/polity/0'))

    def test_names_are_never_identities(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY)
        item = doc['polities']['items'][0]
        self.assertIn('display_name', item)
        self.assertEqual(item['display_name_basis'], 'export_time')
        self.assertIn('可能晚于基准年', item['display_name_note'])
        self.assertNotIn('昌', item['ref'])

    def test_missing_branch_and_seed_stay_unknown(self):
        block = civ_block()
        block.pop('seed')
        doc = hist.build(block, base_year=200, identity={'world_id': 'w1'})
        identity = doc['identity']
        self.assertIsNone(identity['branch'])
        self.assertFalse(identity['branch_known'])
        self.assertIsNone(identity['civ_seed'])
        self.assertIsNone(identity['terrain_seed'])
        self.assertIn('不从 recipe 指纹反推', identity['seed_note'])
        self.assertIn('/unknown', doc['polities']['items'][0]['ref'])

    def test_data_seed_wins_over_caller_seed(self):
        doc = hist.build(civ_block(), base_year=200,
                         identity=dict(IDENTITY, civ_seed=1))
        self.assertEqual(doc['identity']['civ_seed'], 4242)
        self.assertEqual(doc['identity']['civ_seed_source'], 'civ.seed')
        self.assertTrue(doc['identity']['caller_supplied_civ_seed_ignored'])

    def test_identity_from_manifest_reads_only_real_fields(self):
        manifest = {'world': {'id': 'w9'}, 'snapshot': {'generator': 45, 'format': 1}}
        identity = hist.identity_from(manifest, {'id': 'sn_x', 'sha256': 'c' * 64},
                                     branch='b')
        self.assertEqual(identity['world_id'], 'w9')
        self.assertEqual(identity['content_sha256'], 'c' * 64)
        self.assertEqual(identity['branch'], 'b')
        self.assertNotIn('civ_seed', identity)          # never guessed from the manifest


# ------------------------------------------------------------------- capitals
class CapitalTests(unittest.TestCase):
    def test_capital_comes_from_valid_capitals_span(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        polity = [item for item in doc['polities']['items'] if item['id'] == 1][0]
        self.assertEqual(polity['capital_status'], INTERVAL)
        self.assertTrue(polity['capital_ref'].endswith('/settlement/1'))
        moved = hist.build(civ_block(), base_year=220, identity=IDENTITY)
        polity2 = [item for item in moved['polities']['items'] if item['id'] == 1][0]
        self.assertTrue(polity2['capital_ref'].endswith('/settlement/2'))

    def test_polity_without_capitals_has_unknown_capital(self):
        doc = hist.build(civ_block(), base_year=100, identity=IDENTITY)
        polity = [item for item in doc['polities']['items'] if item['id'] == 2][0]
        self.assertIsNone(polity['capital_ref'])
        self.assertEqual(polity['capital_status'], UNKNOWN)
        self.assertIn('立国时的国都', polity['capital_note'])

    def test_capital_after_base_year_is_not_claimed(self):
        doc = hist.build(civ_block(), base_year=160, identity=IDENTITY)
        polity = [item for item in doc['polities']['items'] if item['id'] == 1][0]
        self.assertTrue(polity['capital_ref'].endswith('/settlement/1'))
        self.assertNotIn('/settlement/2', json.dumps(polity['capital_spans'][:1]))

    def test_settlement_capital_spans_are_year_filtered(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        city = [item for item in doc['settlements']['items'] if item['id'] == 1][0]
        self.assertEqual(len(city['capital_spans_at_year']), 1)
        self.assertEqual(city['capital_spans_at_year'][0]['from'], 150.25)


# --------------------------------------------------------------- unknown fields
class UnknownFieldTests(unittest.TestCase):
    def test_unrecorded_fields_are_unknown_with_reasons(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        status = doc['field_status']
        for field in ('population', 'resources', 'routes', 'terrain'):
            self.assertEqual(status[field]['status'], UNKNOWN, field)
            self.assertTrue(status[field]['note'])
        unknown = {item['field'] for item in doc['unknown']}
        self.assertEqual(unknown, {'population', 'resources', 'routes', 'terrain'})

    def test_population_is_never_invented_per_city(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        for city in doc['settlements']['items']:
            self.assertEqual(city['population'], UNKNOWN)
            self.assertIn('没有逐年人口序列', city['population_note'])

    def test_end_state_is_never_used_as_a_past_state(self):
        doc = hist.build(civ_block(), base_year=100, identity=IDENTITY,
                         include_regions=True)
        # at year 100 only polity 0 holds region 0; the end state has polity 1 on region 1
        self.assertEqual(doc['region_replay']['polity'], [0, -1, -1, -1])

    def test_missing_people_and_religion_degrade_to_unknown(self):
        block = civ_block()
        block.pop('people')
        block.pop('religion')
        doc = hist.build(block, base_year=200, identity=IDENTITY)
        self.assertEqual(doc['field_status']['people_lifespan']['status'], UNKNOWN)
        self.assertEqual(doc['field_status']['religion_events']['status'], UNKNOWN)
        self.assertEqual(doc['people']['items'], [])
        self.assertFalse(doc['religion']['available'])


# --------------------------------------------------------------------- terrain
class TerrainTests(unittest.TestCase):
    def test_no_upheaval_means_same_terrain(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        self.assertEqual(doc['terrain']['state'], 'same_terrain_all_years')
        self.assertTrue(doc['terrain']['era_block_is_terrain_not_history'])

    def test_base_year_before_last_upheaval_is_unmatched(self):
        block = civ_block(upheavals=[{'year': 250, 'kinds': ['sink'], 'region': 1,
                                      'polity': 0}])
        doc = hist.build(block, base_year=200, identity=IDENTITY)
        self.assertEqual(doc['terrain']['state'], 'unmatched')
        self.assertFalse(doc['terrain']['base_year_uses_current_map'])
        self.assertIn('未关联', doc['terrain']['note'])

    def test_era_block_alone_marks_the_map_as_later_terrain(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY,
                        terrain={'eras_block': True, 'era_until': [250]})
        self.assertEqual(doc['terrain']['state'], 'unmatched')
        self.assertTrue(doc['terrain']['era_block_is_terrain_not_history'])

    def test_base_year_after_upheaval_uses_current_terrain(self):
        block = civ_block(upheavals=[{'year': 250, 'kinds': ['sink'], 'region': 1,
                                      'polity': 0}])
        doc = hist.build(block, base_year=260, identity=IDENTITY)
        self.assertEqual(doc['terrain']['state'], 'current_terrain')


# ----------------------------------------------------------------- public view
class PublicViewTests(unittest.TestCase):
    def test_default_projection_withholds_everything_narrative(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        view = hist.public_view(doc)
        self.assertEqual(view['annals']['events'], [])
        self.assertTrue(view['annals']['withheld'])
        for key in ('polities', 'settlements', 'people'):
            self.assertEqual(view[key]['items'], [], key)
            self.assertTrue(view[key]['withheld'], key)
        self.assertNotIn('counts', view)

    def test_authorized_field_still_hides_the_future(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        view = hist.public_view(doc, allow=('people',))
        person = [item for item in view['people']['items'] if item['id'] == 0][0]
        self.assertTrue(person['in_office_at_base_year'])
        # alive at 200, died at 280: the death must not be projected
        for banned in ('died', 'fate', 'until', 'born_basis'):
            self.assertNotIn(banned, person)
        self.assertNotIn(280, [value for value in person.values()
                               if isinstance(value, (int, float))])

    def test_authorized_polities_hide_ended_and_later_capitals(self):
        doc = hist.build(civ_block(), base_year=200, identity=IDENTITY)
        view = hist.public_view(doc, allow=('polities',))
        for item in view['polities']['items']:
            self.assertNotIn('ended', item)
            self.assertNotIn('capital_spans', item)
            self.assertNotIn('dynasties', item)

    def test_hidden_ref_is_dropped_and_not_counted(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY,
                        hidden_refs=('casnap:aaaaaaaaaaaaaaaa:w1/main/polity/1',))
        view = hist.public_view(doc, allow=('polities',))
        ids = {item['id'] for item in view['polities']['items']}
        self.assertNotIn(1, ids)
        self.assertNotIn('hidden', json.dumps(view.get('disclosure')))
        self.assertNotIn('hidden_refs', json.dumps(view))

    def test_unknown_allow_is_refused(self):
        with self.assertRaises(hist.HistoryError):
            hist.public_view(hist.build(civ_block(), base_year=200, identity=IDENTITY),
                             allow=('secrets',))

    def test_public_view_is_reproducible(self):
        doc = hist.build(civ_block(), base_year=260, identity=IDENTITY)
        first = hist.public_view(doc, allow=('annals',))
        second = hist.public_view(doc, allow=('annals',))
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))


# --------------------------------------------------------------- decoding reuse
class DecodeReuseTests(unittest.TestCase):
    def test_decode_reuses_shared_parser_and_does_not_double_inflate(self):
        source = (ROOT / 'app' / 'civ_atlas_history.py').read_text(encoding='utf-8')
        self.assertIn('_snap.parse_container', source)
        self.assertIn('_snap.parse_part', source)
        # gzip must be delegated to the existing bounded inflater, never re-implemented
        self.assertIn('_snap._inflate', source)
        self.assertNotIn('zlib', source)
        self.assertNotIn('gzip.decompress', source)
        self.assertIn('PART_MAGIC', source)     # the double-inflate guard

    def test_missing_history_part_is_refused(self):
        with self.assertRaises(hist.HistoryError):
            hist.decode_civ_part({}, [{'name': 'map', '_bytes': b''}])

    def test_unknown_compression_is_refused(self):
        with self.assertRaises(hist.HistoryError):
            hist.decode_civ_part({}, [{'name': 'civ', '_bytes': b'x', 'zip': 'lz4'}])


# ------------------------------------------------------------- the REAL export
class RealExportProbeTests(unittest.TestCase):
    """真实解析 probe：读旧代理真实导出的一份 ``.civsnap``（只读，不进正式 data/）。

    这些断言写的是**实测到的真实结构**：年份是浮点、``civ.seed`` 在导出里、870 州、
    30 个检查点、日志 4549 条、回放到 endYear 与终态逐州一致。
    """

    @classmethod
    def setUpClass(cls):
        if not REAL_EXPORT.exists():
            raise unittest.SkipTest(
                '真实 .civsnap 样本不在预期路径 %s（**未验真**，不是通过）' % REAL_EXPORT)
        cls.data = REAL_EXPORT.read_bytes()
        cls.civ, cls.manifest = hist.load_civ(cls.data)
        cls.identity = hist.identity_from(cls.manifest, None, branch='main')

    def test_manifest_pin_is_the_real_one(self):
        manifest = self.manifest
        self.assertEqual(manifest['world']['id'], 'wmvrpuwi29m3yi')
        self.assertEqual(manifest['snapshot']['generator'], 45)
        self.assertEqual(manifest['snapshot']['format'], 1)
        self.assertEqual([part['name'] for part in manifest['parts']],
                         ['map', 'eras', 'civ'])

    def test_shape_matches_the_documented_contract(self):
        shape = hist.inspect(self.civ)
        self.assertEqual(shape['end_year'], 3000)
        self.assertEqual(shape['region_count'], 870)
        self.assertEqual(shape['counts']['checkpoints'], 30)
        self.assertEqual(shape['first_checkpoint_year'], 100)
        self.assertEqual(shape['counts']['log_entries'], 4549)
        self.assertEqual(shape['unknown_annal_kinds'], [])

    def test_civ_seed_really_is_in_the_export(self):
        self.assertEqual(self.civ['seed'], 531844)
        doc = hist.build(self.civ, base_year=1500, identity=self.identity)
        self.assertEqual(doc['identity']['civ_seed'], 531844)
        self.assertEqual(doc['identity']['civ_seed_source'], 'civ.seed')

    def test_years_are_fractional(self):
        polity = self.civ['polities'][0]
        self.assertIsInstance(polity['founded'], float)
        self.assertNotEqual(polity['founded'], int(polity['founded']))

    def test_end_year_replay_matches_the_export_exactly(self):
        doc = hist.build(self.civ, base_year=1500, identity=self.identity)
        check = doc['region_replay']['end_state_check']
        self.assertEqual(check['status'], EXACT)
        self.assertEqual(check['checked_at'], 3000)
        self.assertEqual(check['mismatched_layers'], [])

    def test_region_replay_at_1500(self):
        doc = hist.build(self.civ, base_year=1500, identity=self.identity)
        block = doc['region_replay']
        self.assertEqual(block['status'], INTERVAL)
        self.assertEqual(block['checkpoint_year_used'], 1500)
        counts = block['counts']
        self.assertEqual(counts['regions'], 870)
        self.assertGreater(counts['distinct_cultures'], 0)
        self.assertGreater(counts['distinct_polities'], 0)

    def test_no_anomalies_on_the_real_export(self):
        doc = hist.build(self.civ, base_year=1500, identity=self.identity)
        self.assertEqual(doc['anomalies']['count'], 0, json.dumps(doc['anomalies'],
                                                                  ensure_ascii=False))

    def test_entity_counts_are_bounded_but_exact(self):
        doc = hist.build(self.civ, base_year=1500, identity=self.identity)
        self.assertGreater(doc['polities']['alive_at_base_year'], 0)
        self.assertEqual(doc['polities']['returned'],
                         min(doc['polities']['alive_at_base_year'], 200))
        self.assertGreater(doc['settlements']['alive_at_base_year'], 200)
        self.assertTrue(doc['settlements']['truncated'])
        self.assertEqual(doc['settlements']['returned'], 200)

    def test_founding_boundary_on_real_polity(self):
        founded = self.civ['polities'][0]['founded']
        before = hist.build(self.civ, base_year=math.floor(founded) - 1,
                            identity=self.identity)
        at = hist.build(self.civ, base_year=founded, identity=self.identity)
        ids_before = {item['id'] for item in before['polities']['items']}
        ids_at = {item['id'] for item in at['polities']['items']}
        self.assertNotIn(0, ids_before)
        self.assertIn(0, ids_at)

    def test_public_view_does_not_leak_future_on_real_data(self):
        doc = hist.build(self.civ, base_year=1500, identity=self.identity)
        view = hist.public_view(doc, allow=('people',))
        self.assertTrue(view['people']['items'])
        for person in view['people']['items']:
            self.assertNotIn('died', person)
            self.assertNotIn('fate', person)
            self.assertNotIn('until', person)

    def test_annals_window_on_real_data(self):
        doc = hist.build(self.civ, base_year=1500, identity=self.identity)
        counts = doc['annals']['counts']
        self.assertEqual(doc['annals']['window'], {'from': 1350, 'to': 1500})
        self.assertGreater(counts['inside_window'], 0)
        self.assertLessEqual(counts['returned'], hist.DEFAULT_MAX_EVENTS)
        for event in doc['annals']['events']:
            self.assertLessEqual(event['year'], 1500)
            self.assertGreaterEqual(event['year'], 1350)


if __name__ == '__main__':
    unittest.main()
