import copy
import tempfile
import unittest
from pathlib import Path
from app.service import Service
from app.storage import Store
from app.contracts import Turn
from app.knowledge import notebook
from app.runtime import chars, trim_context
from app.summary import event_summary, has_excerpt, strip_excerpt, with_stage

ROOT = Path(__file__).resolve().parents[1]

CONFIRMED = '关城要求商队出示通行文书。'


def segment(summary, head):
    return next((line for line in summary.split('\n') if line.startswith(head)), '')


class EventSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = Service(Store(Path(self.temp.name) / 'test.sqlite3'), ROOT)
        self.rt = self.service.runtime
        self.s = self.rt.new_session('摘要测试', 'protagonist')

    def tearDown(self):
        self.temp.cleanup()

    def close_first_event(self, reply='我把万言机收进行囊，商人的说法我暂且不判断。'):
        # The engine writes a witnessed fact through `effects()`; only what the player
        # actually learned may appear as confirmed.
        self.rt.effects(self.s, [{'op': 'fact', 'text': CONFIRMED, 'visible': True}], 'test:confirmed')
        request = Turn(message='我把万言机收进行囊。', action_id='pack')
        result = self.rt.prepare_turn(self.s, request)
        # `pack` ends the event, so finish_turn already settles the archive.
        self.rt.finish_turn(self.s, request, reply, result, {})
        self.assertIsNone(self.s['active'])
        return self.s['archives'][-1]

    def test_settlement_comes_from_the_state_diff_and_stays_traceable(self):
        archive = self.close_first_event()
        summary = archive['summary']
        self.assertIn('【事件】', summary)
        self.assertIn('【经过】', summary)
        confirmed = segment(summary, '【已确认】')
        fact_id = next(f['id'] for f in self.s['facts'] if f['text'] == CONFIRMED)
        self.assertIn(CONFIRMED, confirmed)
        self.assertIn('record:' + fact_id, confirmed)
        self.assertIn('行囊 +万言机', segment(summary, '【变化】'))
        # The exit flag is bookkeeping, not a change the player can see.
        self.assertNotIn('completed_departure', summary)
        excerpt = segment(summary, '【原文】')
        self.assertIn('我把万言机收进行囊。', excerpt)
        self.assertIn('turn:' + archive['id'] + ':0', excerpt)

    def test_unverified_reply_never_becomes_a_confirmed_line(self):
        archive = self.close_first_event(reply='商人说道路封闭九天，但这只是传闻，尚未证实。')
        summary = archive['summary']
        self.assertNotIn('九天', segment(summary, '【已确认】'))
        self.assertNotIn('九天', segment(summary, '【变化】'))
        self.assertIn('九天', segment(summary, '【原文】'))

    def test_hidden_truth_stays_out_of_the_summary(self):
        # A rumor's real number lives in `facts` (engine truth) while the player only
        # hears the distorted retelling, so the truth must never be summarised.
        self.rt.effects(self.s, [{'op': 'rumor', 'truth': '西行道路封闭3天。',
                                  'character': 'oasis_merchant'}], 'test:rumor')
        self.assertTrue(any('3天' in f['text'] for f in self.s['facts']))
        request = Turn(message='打听道路。')
        result = self.rt.prepare_turn(self.s, request)
        self.rt.finish_turn(self.s, request, '商人说路要封好一阵子。', result, {})
        self.rt.close_event(self.s)
        summary = self.s['archives'][-1]['summary']
        self.assertNotIn('3天', summary)
        self.assertNotIn('【已确认】', summary)

    def test_summary_is_deterministic(self):
        archive = self.close_first_event()
        package = self.rt.package()
        first = event_summary(archive['after'], archive, package)
        self.assertEqual(first, archive['summary'])
        self.assertEqual(first, event_summary(archive['after'], archive, package))
        self.assertEqual(first, event_summary(dict(reversed(list(archive['after'].items()))), archive, package))

    def test_excerpt_can_be_dropped_as_one_segment(self):
        summary = self.close_first_event()['summary']
        self.assertTrue(has_excerpt(summary))
        structured = strip_excerpt(summary)
        self.assertFalse(has_excerpt(structured))
        self.assertIn('【已确认】', structured)
        self.assertNotIn('turn:', structured)
        self.assertNotIn('【原文】', structured)
        self.assertEqual(with_stage(structured, ''), structured)
        self.assertEqual(with_stage(structured, '上一阶段原文摘录'), structured + '\n上一阶段原文摘录')

    def test_old_archive_without_structured_fields_does_not_crash(self):
        event = {'id': 'legacy', 'title': '旧事件', 'turns': [{'input': '问', 'reply': '答'}]}
        summary = event_summary({}, event, self.rt.package())
        self.assertIn('【事件】旧事件', summary)
        self.assertNotIn('【已确认】', summary)
        self.assertIn('【原文】', summary)
        self.assertEqual(strip_excerpt('旧存档摘要'), '旧存档摘要')

    def test_settlement_reaches_the_next_context(self):
        archive = self.close_first_event()
        context = self.rt.context(self.s, 'player', '万言机', self.service.preferences())
        self.assertIn(archive['summary'], context['last_summary'])
        self.assertIn('record:', context['last_summary'])

    def test_model_notes_are_dropped_before_world_canon(self):
        base = {
            'dialogue_knowledge': [{'summary': '模型派生的叙述' * 40, 'status': '对话所闻，未独立核实'}],
            'recalled_dialogue': [{'input': '问', 'reply': '答' * 120}],
            'history': [{'input': '甲', 'reply': '乙'}],
            'memories': [{'text': '所闻' * 60}],
            'elements': [{'mark': '物' * 80}],
            'knowledge': [{'id': 'k1', 'content': '世界正典' * 60}],
            'last_summary': '【事件】某事\n【已确认】确认过的事（record:1）\n【原文】玩家：问 / 回应：答（turn:x:0）',
        }
        without_notes = {**base, 'dialogue_knowledge': []}
        budget = chars(without_notes) + 5
        self.assertGreater(chars(base), budget)
        trimmed = trim_context(copy.deepcopy(base), budget)
        self.assertEqual(trimmed['dialogue_knowledge'], [])
        self.assertEqual(trimmed['knowledge'], base['knowledge'])
        self.assertEqual(trimmed['recalled_dialogue'], base['recalled_dialogue'])
        self.assertEqual(trimmed['last_summary'], base['last_summary'])
        # Even a tight budget strips the prose segment before it drops the settlement.
        bare = {**base, 'dialogue_knowledge': [], 'recalled_dialogue': [], 'history': [],
                'memories': [], 'elements': [], 'knowledge': [],
                'last_summary': strip_excerpt(base['last_summary'])}
        tight = trim_context(copy.deepcopy(base), chars(bare) + 5)
        self.assertEqual(tight['knowledge'], [])
        self.assertFalse(has_excerpt(tight['last_summary']))
        self.assertIn('【已确认】', tight['last_summary'])

    def test_confirmed_record_outranks_prose_in_the_notebook(self):
        # Only engine-written confirmed evidence qualifies; `pack` alone is a state
        # change without a witnessed record, so seed one the way effects do.
        self.rt.effects(self.s, [{'op': 'fact', 'text': '关城要求商队出示通行文书。', 'visible': True}],
                        'test:confirmed')
        request = Turn(message='继续赶路。')
        result = self.rt.prepare_turn(self.s, request)
        self.rt.finish_turn(self.s, request, '关城要求商队出示通行文书，可谁知道这是不是真的。', result, {})
        notes = notebook(self.s)
        self.assertEqual(notes[0]['origin'], 'confirmed')
        self.assertEqual(notes[0]['status'], '状态层已确认')
        self.assertIn('通行文书', notes[0]['summary'])
        prose = [n for n in notes if n['origin'] == 'prose']
        self.assertTrue(prose)
        self.assertTrue(all(n['status'] == '对话所闻，未独立核实' for n in prose))


if __name__ == '__main__':
    unittest.main()
