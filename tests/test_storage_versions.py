"""Independent storage tests: legacy saves, compare-and-swap versions, no side effects."""
import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.contracts import Turn
from app.service import Service
from app.storage import ConcurrentUpdateError, Store, dumps

ROOT = Path(__file__).resolve().parents[1]


class StorageCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'store.sqlite3'
        self.store = Store(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def session(self, identity='s1', **extra):
        state = {'id': identity, 'title': '测试', 'revision': 'r1', 'mode': 'protagonist',
                 'hero': 'p', 'location': 'a', 'time': 8, 'turn_index': 0,
                 'facts': [], 'beliefs': [], 'heard': [], 'active': None, 'archives': []}
        state.update(extra)
        return state

    def raw_session(self, identity='s1'):
        """Write a pre-version document straight to SQLite, as an old build would."""
        with self.store.connect() as db:
            body = {k: v for k, v in self.session(identity).items()
                    if k not in ('facts', 'beliefs', 'heard')}
            db.execute('INSERT INTO documents VALUES(?,?,?)', ('session', identity, dumps(body)))

    def layers(self):
        with self.store.connect() as db:
            return {table: [r[0] for r in db.execute(f'SELECT body FROM {table} ORDER BY rowid')]
                    for table in ('facts', 'beliefs', 'heard')}


class LegacySaveTests(StorageCase):
    def test_old_save_without_version_reads_as_zero(self):
        self.raw_session()
        state = self.store.session('s1')
        self.assertEqual(state['state_version'], 0)
        self.assertEqual(state['facts'], [])

    def test_first_save_over_legacy_document_moves_to_version_one(self):
        self.raw_session()
        state = self.store.session('s1')
        state['time'] = 9
        self.store.save_session(state)
        self.assertEqual(self.store.session('s1')['state_version'], 1)
        self.assertEqual(self.store.session('s1')['time'], 9)

    def test_new_session_starts_at_zero(self):
        self.store.save_session(self.session())
        self.assertEqual(self.store.session('s1')['state_version'], 0)


class CompareAndSwapTests(StorageCase):
    def test_two_stores_reading_one_version_only_one_commits(self):
        self.store.save_session(self.session())
        first, second = Store(self.path), Store(self.path)
        a, b = first.session('s1'), second.session('s1')
        self.assertEqual(a['state_version'], b['state_version'])
        expected = a['state_version']
        a['time'] = 10
        first.save_session(a)
        b['time'] = 11
        with self.assertRaises(ConcurrentUpdateError):
            second.save_session(b)
        saved = self.store.session('s1')
        self.assertEqual(saved['time'], 10)
        self.assertEqual(saved['state_version'], expected + 1)

    def test_explicit_expected_version_rejects_stale_writer(self):
        self.store.save_session(self.session())
        state = self.store.session('s1')
        stale = dict(state, time=12)
        state['time'] = 10
        self.store.save_session(state)
        with self.assertRaises(ConcurrentUpdateError):
            self.store.save_session(stale, expected_version=0)
        self.assertEqual(self.store.session('s1')['time'], 10)

    def test_conflict_leaves_layers_and_records_untouched(self):
        self.store.save_session(self.session('s1', facts=[{'id': 'f1', 'text': '旧事实'}]))
        winner, loser = Store(self.path), Store(self.path)
        a, b = winner.session('s1'), loser.session('s1')
        a['facts'].append({'id': 'f2', 'text': '赢家写入'})
        a['heard'] = [{'id': 'h1', 'text': '赢家所闻'}]
        winner.save_session(a, [('draft', 'd1', {'id': 'd1', 'status': 'approved'})])
        before_layers = self.layers()
        b['facts'] = [{'id': 'f3', 'text': '输家写入'}]
        b['beliefs'] = [{'id': 'b1', 'text': '输家信念'}]
        b['heard'] = [{'id': 'h2', 'text': '输家所闻'}]
        with self.assertRaises(ConcurrentUpdateError):
            loser.save_session(b, [('draft', 'd1', {'id': 'd1', 'status': 'rejected'}),
                                   ('draft', 'd9', {'id': 'd9', 'status': 'draft'})])
        # No layer row and no attached record was written by the losing writer.
        self.assertEqual(self.layers(), before_layers)
        self.assertEqual(self.store.get('draft', 'd1')['status'], 'approved')
        self.assertIsNone(self.store.get('draft', 'd9'))
        self.assertEqual(len(self.store.session('s1')['facts']), 2)

    def test_total_failure_rolls_back_every_table(self):
        self.store.save_session(self.session('s1', facts=[{'id': 'f1', 'text': '原始'}],
                                            heard=[{'id': 'h0', 'text': '原始所闻'}]))
        before = self.store.session('s1')
        before_layers = self.layers()
        state = self.store.session('s1')
        state['facts'] = [{'id': 'f2', 'text': '半途'}]
        state['beliefs'] = [{'id': 'b1', 'text': '半途'}]
        state['heard'] = [{'id': 'h1', 'text': '半途'}]
        # Force a failure inside the transaction so a partially written save must be
        # rolled back as a whole, including the version bump.
        with self.store.connect() as db:
            db.execute('CREATE TRIGGER fail_heard BEFORE INSERT ON heard '
                       'BEGIN SELECT RAISE(ABORT, "模拟中途失败"); END')
        with self.assertRaises(sqlite3.Error):
            self.store.save_session(state)
        self.assertEqual(self.store.session('s1'), before)
        self.assertEqual(self.layers(), before_layers)
        self.assertEqual(self.store.session('s1')['state_version'], before['state_version'])

    def test_rollback_keeps_version_monotonic(self):
        self.store.save_session(self.session('s1', facts=[{'id': 'f1', 'text': '原始'}]))
        a = self.store.session('s1')
        a['time'] = 12
        self.store.save_session(a)
        versions = [self.store.session('s1')['state_version']]
        # Rolling back replays older game state; the version must still rise.
        for _ in range(3):
            current = self.store.session('s1')
            rollback = dict(current, time=8, flags={})
            self.store.save_session(rollback)
            versions.append(self.store.session('s1')['state_version'])
        self.assertEqual(versions, sorted(set(versions)))
        self.assertEqual(len(versions), 4)
        self.assertEqual(self.store.session('s1')['time'], 8)


class ServiceConcurrencyTests(unittest.TestCase):
    """The lock is released while a model call is in flight; a stale result is rejected."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'service.sqlite3'
        self.service = Service(Store(self.path), ROOT)
        self.service.provider.configure({'base_url': 'https://api.deepseek.com',
                                         'model': 'deepseek-chat', 'offline': False,
                                         'max_tokens': 1200})
        self.runtime = self.service.runtime
        self.first = self.runtime.new_session('甲', 'protagonist')
        self.second = self.runtime.new_session('乙', 'protagonist')

    def tearDown(self):
        self.tmp.cleanup()

    def test_other_journey_finishes_while_model_is_waiting(self):
        started, release = asyncio.Event(), asyncio.Event()
        calls = {'n': 0}

        async def complete(system, context, **kwargs):
            calls['n'] += 1
            if calls['n'] == 1:
                # Only the first journey blocks, and it blocks inside a real await.
                started.set()
                await release.wait()
            return '模型写的正文', {'prompt_tokens': 1, 'completion_tokens': 1}

        async def run():
            pending = None
            with patch.object(self.service.provider, 'complete', complete):
                try:
                    pending = asyncio.create_task(
                        self.service.turn(self.first['id'], Turn(message='收下行装', action_id='pack')))
                    # Bounded wait: a lock regression must fail this test, not hang the suite.
                    await asyncio.wait_for(started.wait(), timeout=5)
                    self.assertFalse(pending.done())
                    await asyncio.wait_for(
                        self.service.turn(self.second['id'], Turn(message='收下行装', action_id='pack')),
                        timeout=5)
                    done = self.service.store.session(self.second['id'])
                    self.assertFalse(pending.done())
                    release.set()
                    return await asyncio.wait_for(pending, timeout=5), done
                finally:
                    release.set()
                    if pending is not None and not pending.done():
                        pending.cancel()
                        try:
                            await pending
                        except (asyncio.CancelledError, Exception):
                            pass

        result, other = asyncio.run(run())
        self.assertEqual(result['id'], self.first['id'])
        # The other journey completed while the first one was still waiting.
        self.assertEqual([t['reply'] for t in other['archives'][-1]['turns']], ['模型写的正文'])
        saved = self.service.store.session(self.first['id'])
        self.assertEqual([t['reply'] for t in saved['archives'][-1]['turns']], ['模型写的正文'])
        self.assertGreater(saved['state_version'], 0)

    def test_stale_model_result_is_rejected_without_side_effects(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def complete(system, context, **kwargs):
            started.set()
            await release.wait()
            return '过期的模型正文', {'prompt_tokens': 1, 'completion_tokens': 1}

        async def run():
            pending = None
            with patch.object(self.service.provider, 'complete', complete):
                try:
                    pending = asyncio.create_task(
                        self.service.turn(self.first['id'], Turn(message='收下行装', action_id='pack')))
                    await asyncio.wait_for(started.wait(), timeout=5)
                    # Someone else changes the same journey while the model is thinking.
                    changed = self.service.store.session(self.first['id'])
                    changed['time'] += 1
                    self.service.store.save_session(changed)
                    release.set()
                    with self.assertRaisesRegex(ValueError, '被其他操作更新'):
                        await asyncio.wait_for(pending, timeout=5)
                    return changed
                finally:
                    release.set()
                    if pending is not None and not pending.done():
                        pending.cancel()
                        try:
                            await pending
                        except (asyncio.CancelledError, Exception):
                            pass

        before = self.service.store.session(self.first['id'])
        changed = asyncio.run(run())
        after = self.service.store.session(self.first['id'])
        # The concurrent write survives and the stale reply was never persisted.
        self.assertEqual(after['time'], before['time'] + 1)
        self.assertEqual(after['active'], changed['active'])
        self.assertEqual(after['active']['turns'], [])


if __name__ == '__main__':
    unittest.main()
