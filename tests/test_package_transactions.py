"""Package commit reliability: journal validation, interruption, replay, cleanup.

Everything runs against a temporary database and a temporary StoryPackage copy; the
project's real data/ and StoryPackage/ folders are only read, never written, and no
model call is made (the provider stays offline).
"""
import asyncio
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import package_transaction
from app.contracts import DraftRequest, Turn
from app.service import Service, offline_surface
from app.storage import Store

ROOT = Path(__file__).resolve().parents[1]


class PackageCase(unittest.TestCase):
    """A Service on a temporary store, with its own copy of the package library."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.path = self.base / 'test.sqlite3'
        self.service = Service(Store(self.path), ROOT)
        self.service.provider.configure({'base_url': 'https://api.deepseek.com',
                                         'model': 'deepseek-chat', 'offline': True,
                                         'max_tokens': 1200})
        self.rt = self.service.runtime
        # Start every test from the pristine templates and never inherit a journal.
        ignore = shutil.ignore_patterns('.*')
        for source, target in ((ROOT / 'StoryPackage', self.rt.library),
                               (ROOT / 'character_packages', self.rt.character_directory)):
            shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore)
        self.journal = package_transaction.journal_path(self.rt.library)

    def tearDown(self):
        self.tmp.cleanup()

    def candidate(self, note='提交测试'):
        package = copy.deepcopy(self.rt.package())
        package['story']['worldview']['premise'] += ' ' + note
        return package

    def fingerprints(self):
        """Every committed file under the library and the character directory, by content.

        The journal itself is excluded: several tests install one on purpose, and the
        claim under test is that no *content* file is moved or rewritten.
        """
        result = {}
        for root in (self.rt.library, self.rt.character_directory):
            for path in sorted(root.rglob('*')):
                if path == self.journal:
                    continue
                result[str(path.relative_to(self.base))] = path.read_bytes() if path.is_file() else None
        return result

    def leftovers(self):
        names = [p.name for p in self.rt.library.iterdir() if p.name.startswith('.')]
        names += [p.name for p in self.rt.character_directory.iterdir() if p.name.startswith('.')]
        return sorted(names)

    def journal_state(self, **overrides):
        """A well-formed journal for the current package, with a made-up transaction."""
        package = self.rt.package()
        transaction = overrides.pop('transaction', 'a' * 16)
        target = self.rt.package_directory(package['folder'])
        char_id = package['characters']['id']
        data = {'version': package_transaction.VERSION, 'transaction': transaction,
                'target': target.name, 'stage': '.' + target.name + '.pending_' + transaction,
                'backup': '.' + target.name + '.backup_' + transaction, 'target_existed': True,
                'new_id': overrides.pop('new_id', 'b' * 16), 'character_id': char_id,
                'character_file': char_id + '.json',
                'character_backup': '.' + char_id + '.backup_' + transaction + '.json',
                'character_existed': True, 'phase': 'characters'}
        data.update(overrides)
        return data, target, target.parent / data['backup']

    def write_journal(self, data):
        self.journal.write_text(package_transaction.encode(data), encoding='utf-8')


class JournalValidationTests(PackageCase):
    def _write(self, payload):
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        self.journal.write_text(text, encoding='utf-8')

    def _valid(self):
        return self.journal_state()[0]

    def test_corrupt_journal_changes_nothing_and_is_kept(self):
        before = self.fingerprints()
        cases = {
            'not json': 'this is not json',
            'not an object': '[1, 2, 3]',
            'missing fields': {'version': 1, 'target': '玄陆'},
            'unknown field': {**self._valid(), 'evil': '../../etc'},
            'path traversal': {**self._valid(), 'target': '../../outside'},
            'absolute path': {**self._valid(), 'target': 'C:/Windows'},
            'hidden target': {**self._valid(), 'target': '.hidden'},
            'stage mismatch': {**self._valid(), 'stage': '.玄陆.pending_' + 'c' * 16},
            'character mismatch': {**self._valid(), 'character_file': 'other.json'},
            'int flag': {**self._valid(), 'target_existed': 1},
            'bool version': {**self._valid(), 'version': True},
            'unknown phase': {**self._valid(), 'phase': 'installed'},
            'bad revision': {**self._valid(), 'new_id': 'not-a-revision'},
        }
        for name, payload in cases.items():
            with self.subTest(name):
                self._write(payload)
                with self.assertRaises(ValueError):
                    self.rt._recover_package_transaction()
                # The journal is preserved for inspection and nothing moved.
                self.assertTrue(self.journal.exists(), name)
                self.assertEqual(self.fingerprints(), before, name)
                self.journal.unlink()

    def test_journal_symlink_is_rejected(self):
        outside = self.base / 'outside.json'
        outside.write_text(json.dumps(self._valid(), ensure_ascii=False), encoding='utf-8')
        before = self.fingerprints()
        try:
            self.journal.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('本机不支持创建符号链接')
        with self.assertRaises(ValueError):
            self.rt._recover_package_transaction()
        self.assertEqual(self.fingerprints(), before)
        self.assertTrue(self.journal.is_symlink())

    def test_staged_tree_with_symlink_is_rejected(self):
        data, _, _ = self.journal_state()
        self._write(data)
        stage = self.rt.library / data['stage']
        stage.mkdir()
        (stage / 'story.json').write_text('{}', encoding='utf-8')
        private = self.base / 'private.txt'
        private.write_text('secret', encoding='utf-8')
        try:
            (stage / 'link.md').symlink_to(private)
        except (OSError, NotImplementedError):
            self.skipTest('本机不支持创建符号链接')
        with self.assertRaises(ValueError):
            self.rt._recover_package_transaction()
        self.assertEqual(private.read_text(encoding='utf-8'), 'secret')
        self.assertTrue(self.journal.exists())

    def test_symlink_inside_package_blocks_commit(self):
        package = self.rt.package()
        folder = self.rt.package_directory(package['folder'])
        private = self.base / 'private.md'
        private.write_text('不应被复制', encoding='utf-8')
        try:
            (folder / '链接.md').symlink_to(private)
        except (OSError, NotImplementedError):
            self.skipTest('本机不支持创建符号链接')
        before = self.fingerprints()
        with self.assertRaises(ValueError):
            self.rt.commit_package(package['story'], package['characters'], '含链接')
        self.assertEqual(self.fingerprints(), before)
        self.assertFalse(self.journal.exists())


class CommitInterruptionTests(PackageCase):
    def test_database_failure_restores_previous_version(self):
        before_package = copy.deepcopy(self.rt.package())
        before_story = self.rt.files.read()
        candidate = self.candidate()
        with patch.object(self.rt.store, 'put_many', side_effect=RuntimeError('模拟数据库失败')):
            with self.assertRaisesRegex(RuntimeError, '数据库失败'):
                self.rt.commit_package(candidate['story'], candidate['characters'], '失败')
        self.assertEqual(self.rt.package(), before_package)
        self.assertEqual(self.rt.files.read(), before_story)
        self.assertFalse(self.journal.exists())
        self.assertEqual(self.leftovers(), [])

    def test_failed_commit_does_not_leave_draft_approved(self):
        draft = asyncio.run(self.service.generate(DraftRequest(kind='item', instruction='测试物品')))
        self.assertEqual(draft['status'], 'draft')
        candidate = self.candidate('批准失败')
        with patch.object(self.rt.store, 'put_many', side_effect=RuntimeError('模拟数据库失败')):
            with self.assertRaises(RuntimeError):
                self.rt.commit_package(candidate['story'], candidate['characters'], '批准失败',
                                       approved_draft=draft)
        # Neither the live dict nor the stored draft may look approved.
        self.assertEqual(draft['status'], 'draft')
        self.assertNotIn('revision', draft)
        self.assertEqual(self.rt.store.get('draft', draft['id'])['status'], 'draft')
        # The candidate is still usable once saving works again.
        revision = self.rt.approve(draft)
        self.assertNotEqual(revision, draft['base_revision'])

    def test_interrupt_after_staging_then_new_runtime_recovers(self):
        package = self.rt.package()
        before = copy.deepcopy(package['story'])
        real, calls = self.rt.validate_package, {'n': 0}

        def crash(*args, **kwargs):
            calls['n'] += 1
            if calls['n'] > 1:
                raise KeyboardInterrupt
            return real(*args, **kwargs)

        with patch.object(self.rt, 'validate_package', crash):
            with self.assertRaises(RuntimeError):
                self.rt.commit_package(self.candidate()['story'], package['characters'], '中断')
        self.assertFalse(self.journal.exists())
        self.assertEqual(self.leftovers(), [])
        restarted = Service(Store(self.path), ROOT).runtime
        self.assertEqual(restarted.files.read(), before)
        self.assertEqual(restarted.package()['id'], package['id'])

    def test_interrupt_at_swap_leaves_no_stale_copy(self):
        package = self.rt.package()
        before = copy.deepcopy(package['story'])
        real_rename = Path.rename

        def crash(self, target):
            # Fail exactly at the swap, after the stage has been fully written.
            if Path(self).name.startswith('.') and '.pending_' in Path(self).name:
                raise KeyboardInterrupt
            return real_rename(self, target)

        with patch.object(Path, 'rename', crash):
            with self.assertRaises(RuntimeError):
                self.rt.commit_package(self.candidate()['story'], package['characters'], '中断')
        self.assertFalse(self.journal.exists())
        self.assertEqual(self.rt.files.read(), before)
        self.assertEqual(self.leftovers(), [])

    def test_recovery_is_repeatable_after_interrupted_recovery(self):
        """A crash during recovery must not make the next recovery delete the restored tree."""
        package = self.rt.package()
        before = copy.deepcopy(package['story'])
        real_remove, real_unlink = package_transaction.remove, Path.unlink
        for crash_at in ('before_restore', 'after_restore'):
            with self.subTest(crash_at):
                data, target, backup = self.journal_state(new_id='f' * 16, transaction='f' * 16)
                # Reproduce the real "swap done" state: the old tree sits in the backup.
                target.rename(backup)
                self.write_journal(data)

                def remove(path, crash_at=crash_at, target=target):
                    if crash_at == 'before_restore' and Path(path) == target:
                        raise OSError('模拟恢复中断')
                    return real_remove(path)

                def unlink(path, crash_at=crash_at):
                    if crash_at == 'after_restore' and Path(path) == self.journal:
                        raise OSError('模拟日志删除失败')
                    return real_unlink(path)

                with patch.object(package_transaction, 'remove', remove), \
                        patch.object(Path, 'unlink', unlink):
                    with self.assertRaises(ValueError):
                        self.rt._recover_package_transaction()
                # Whatever point the crash hit, a second pass converges on the old tree
                # instead of deleting the directory the first pass had just restored.
                self.rt._recover_package_transaction()
                self.assertFalse(self.journal.exists())
                self.assertTrue(target.is_dir())
                self.assertEqual(self.rt.files.read(), before)
                self.assertFalse(backup.exists())

    def test_repeatedly_interrupted_recovery_stays_idempotent(self):
        package = self.rt.package()
        before = copy.deepcopy(package['story'])
        data, target, backup = self.journal_state(new_id='c' * 16, character_existed=False)
        target.rename(backup)
        self.write_journal(data)
        real_unlink = Path.unlink

        def crash(path, *args, **kwargs):
            if Path(path) == self.journal:
                raise OSError('模拟日志删除失败')
            return real_unlink(path, *args, **kwargs)

        for _ in range(3):
            with patch.object(Path, 'unlink', crash):
                with self.assertRaises(ValueError):
                    self.rt._recover_package_transaction()
            self.assertTrue(target.exists())
            self.assertFalse(backup.exists())
        self.rt._recover_package_transaction()
        self.assertFalse(self.journal.exists())
        self.assertEqual(self.rt.files.read(), before)


class CommitCleanupTests(PackageCase):
    def test_cleanup_failure_keeps_new_revision_and_next_start_finishes(self):
        candidate = self.candidate('清理失败测试')
        with patch.object(package_transaction, 'remove', side_effect=OSError('模拟清理失败')):
            with self.assertRaisesRegex(ValueError, '清理未完成'):
                self.rt.commit_package(candidate['story'], candidate['characters'], '清理')
        # The database and the on-disk package keep the new revision.
        pointer = self.rt.store.get('pointer', 'package')
        stored = self.rt.package()
        self.assertEqual(stored['id'], pointer['id'])
        self.assertEqual(stored['story']['worldview']['premise'],
                         candidate['story']['worldview']['premise'])
        self.assertTrue(self.journal.exists())
        self.assertTrue(self.rt.package_directory(pointer['folder']).exists())
        # A restart replays the journal as committed: it only retries the deletion.
        restarted = Service(Store(self.path), ROOT).runtime
        self.assertFalse(self.journal.exists())
        self.assertEqual(restarted.package()['id'], stored['id'])
        self.assertEqual(restarted.files.read()['worldview']['premise'],
                         candidate['story']['worldview']['premise'])
        self.assertEqual(self.leftovers(), [])

    def test_committed_replay_keeps_backup_when_target_is_damaged(self):
        data, target, backup = self.journal_state(phase='committed', new_id='b2' * 8)
        target.rename(backup)
        self.write_journal(data)
        self.rt.store.put('pointer', 'package', {'id': 'b2' * 8, 'folder': target.name})
        # Committed but the new tree is not on disk: fail closed, never delete the backup.
        with self.assertRaises(ValueError):
            self.rt._recover_package_transaction()
        self.assertTrue(backup.exists())
        self.assertTrue(self.journal.exists())

    def test_committed_replay_refuses_incomplete_tree(self):
        """A tree that merely contains story.json is not proof the commit is readable."""
        package = copy.deepcopy(self.rt.package())
        pristine = self.base / 'pristine'
        target = self.rt.package_directory(package['folder'])
        shutil.copytree(target, pristine)
        damages = {
            'empty story.json': lambda p: (p / 'story.json').write_text('', encoding='utf-8'),
            'broken story.json': lambda p: (p / 'story.json').write_text('{oops', encoding='utf-8'),
            'missing overview': lambda p: (p / '总概.md').unlink(),
            'missing knowledge': lambda p: next((p / '知识点').rglob('*.md')).unlink(),
            'missing character document': lambda p: (
                self.rt.character_directory / (package['characters']['id'] + '.json')).unlink(),
        }
        for name, damage in damages.items():
            with self.subTest(name):
                revision = 'b2' * 8
                committed = copy.deepcopy(package)
                committed['id'] = revision
                self.rt.store.put('package', revision, committed)
                for path in (target,):
                    if path.exists():
                        shutil.rmtree(path)
                shutil.copytree(pristine, target)
                data, _, backup = self.journal_state(phase='committed', new_id=revision)
                if backup.exists():
                    shutil.rmtree(backup)
                # The previous tree is the recovery point; the installed one is broken.
                shutil.copytree(pristine, backup)
                damage(target)
                self.write_journal(data)
                self.rt.store.put('pointer', 'package', {'id': revision, 'folder': target.name})
                with self.assertRaises(ValueError):
                    self.rt._recover_package_transaction()
                # The recovery point survives and the journal stays for inspection.
                self.assertTrue(backup.is_dir(), name)
                self.assertTrue(self.journal.exists(), name)
                # Restore a usable state and the original character document for the
                # next sub-case.
                self.journal.unlink()
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(pristine, target)
                shutil.rmtree(backup)
                shutil.rmtree(self.rt.character_directory)
                shutil.copytree(ROOT / 'character_packages', self.rt.character_directory,
                                dirs_exist_ok=True, ignore=shutil.ignore_patterns('.*'))
                self.rt.store.put('pointer', 'package', {'id': package['id'], 'folder': target.name})

    def test_committed_replay_refuses_same_id_with_different_content(self):
        """The comparison is whole-document: right ids with wrong bodies must not pass."""
        package = copy.deepcopy(self.rt.package())
        pristine = self.base / 'pristine_same_id'
        target = self.rt.package_directory(package['folder'])
        shutil.copytree(target, pristine)
        revision = 'b2' * 8
        committed = copy.deepcopy(package)
        committed['id'] = revision
        # The committed snapshot has a changed action label and knowledge body.
        committed['story']['events'][0]['actions'][0]['label'] += '（已提交版本）'
        committed['story']['knowledge'][0]['content'] += '\n已提交的补充。'
        committed['characters']['characters'][1]['attributes']['strength'] += 3
        self.rt.store.put('package', revision, committed)
        # Install the pristine tree as "target": same ids, different content.
        data, _, backup = self.journal_state(phase='committed', new_id=revision)
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(pristine, backup)
        self.write_journal(data)
        self.rt.store.put('pointer', 'package', {'id': revision, 'folder': target.name})
        with self.assertRaises(ValueError):
            self.rt._recover_package_transaction()
        self.assertTrue(backup.is_dir())
        self.assertTrue(self.journal.exists())

    def test_character_file_that_is_not_an_object_is_a_transaction_error(self):
        package = copy.deepcopy(self.rt.package())
        revision = 'b2' * 8
        committed = copy.deepcopy(package)
        committed['id'] = revision
        self.rt.store.put('package', revision, committed)
        data, target, backup = self.journal_state(phase='committed', new_id=revision)
        if not backup.exists():
            shutil.copytree(target, backup)
        self.rt.character_directory.joinpath(data['character_file']).write_text('[]', encoding='utf-8')
        self.write_journal(data)
        self.rt.store.put('pointer', 'package', {'id': revision, 'folder': target.name})
        # Must be a ValueError (fail closed), never an AttributeError from .get on a list.
        with self.assertRaises(ValueError):
            self.rt._recover_package_transaction()
        self.assertTrue(self.journal.exists())

    def test_character_backup_interruption_never_damages_live_file(self):
        package = self.rt.package()
        char_id = package['characters']['id']
        char_path = self.rt.character_directory / (char_id + '.json')
        original = char_path.read_bytes()
        real_write = package_transaction.write_atomic_bytes

        def crash(path, payload):
            if Path(path).name.startswith('.' + char_id + '.backup_'):
                raise KeyboardInterrupt
            return real_write(path, payload)

        with patch.object(package_transaction, 'write_atomic_bytes', crash):
            with self.assertRaises(RuntimeError):
                self.rt.commit_package(self.candidate('备份中断')['story'], package['characters'], '中断')
        # The live character document is untouched, and no partial backup is left behind.
        self.assertEqual(char_path.read_bytes(), original)
        self.assertFalse(any(p.name.startswith('.' + char_id + '.backup_')
                             for p in self.rt.character_directory.iterdir()))
        self.assertEqual(self.leftovers(), [])

    def test_partial_character_backup_is_not_used_for_restore(self):
        data, target, backup = self.journal_state(phase='characters')
        self.write_journal(data)
        # Simulate a truncated backup left by an older build: restore must not use it.
        char_backup = self.rt.character_directory / data['character_backup']
        char_backup.write_text('{"id": "xuanlu", "characters": [', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.rt._recover_package_transaction()
        self.assertTrue(self.journal.exists())
        self.assertEqual(char_backup.read_text(encoding='utf-8'), '{"id": "xuanlu", "characters": [')

    def test_disk_state_without_exception_handler_recovers(self):
        """Rebuild a Runtime over the on-disk intermediate state a dying process leaves.

        The in-process rollback is deliberately bypassed here: the files are arranged by
        hand exactly as the commit leaves them, then a fresh Runtime must converge.
        """
        package = self.rt.package()
        before = copy.deepcopy(package['story'])
        data, target, backup = self.journal_state(phase='characters', new_id='d3' * 8)
        # Swap done: the new tree is installed, the old one is in the backup.
        target.rename(backup)
        package['story']['worldview']['premise'] += ' 半途新版本'
        target.mkdir()
        shutil.copy2(backup / 'story.json', target / 'story.json')
        self.write_journal(data)
        # A stale on-disk journal with a pointer still at the old revision: roll back.
        restarted = Service(Store(self.path), ROOT).runtime
        self.assertFalse(self.journal.exists())
        self.assertEqual(restarted.files.read(), before)
        self.assertFalse(backup.exists())
        self.assertEqual(restarted.package()['id'], package['id'])

    def test_folder_name_with_spaces_still_commits_and_recovers(self):
        # The runtime accepts such a directory name, so the journal must accept it too:
        # a stricter validator would write a journal its own recovery then refuses.
        folder = '玄陆 副本'
        package = copy.deepcopy(self.rt.package())
        target = self.rt.library / folder
        shutil.copytree(self.rt.package_directory(package['folder']), target)
        self.rt.files = self.rt.files.__class__(target)
        revision = self.rt.commit_package(package['story'], package['characters'], '带空格目录')
        self.assertNotEqual(revision, package['id'])
        self.assertFalse(self.journal.exists())
        self.assertTrue(package_transaction.valid_folder(folder))
        self.rt._recover_package_transaction()
        self.assertEqual(self.leftovers(), [])


class PackageRegressionTests(PackageCase):
    def test_commit_writes_editable_directory_and_keeps_old_journeys_pinned(self):
        before = copy.deepcopy(self.rt.package())
        session = self.rt.new_session('绑定', 'protagonist')
        candidate = self.candidate('新版本')
        revision = self.rt.commit_package(candidate['story'], candidate['characters'], '新版本')
        self.assertNotEqual(revision, before['id'])
        # The existing journey stays bound to its own revision and folder.
        self.assertEqual(self.rt.package(session['revision'])['id'], before['id'])
        # And the editable package directory now holds the new story.
        self.assertEqual(self.rt.files.read()['worldview']['premise'],
                         candidate['story']['worldview']['premise'])
        self.assertIn('新版本', (self.rt.library / before['folder'] / '总概.md').read_text(encoding='utf-8'))
        self.assertFalse(self.journal.exists())
        self.assertEqual(self.leftovers(), [])

    def test_journal_is_created_exclusively(self):
        package = self.rt.package()
        self.journal.write_text('{}', encoding='utf-8')
        before = copy.deepcopy(self.rt.package())
        with self.assertRaisesRegex(ValueError, '待恢复'):
            self.rt.commit_package(package['story'], package['characters'], '并发')
        self.assertEqual(self.rt.package(), before)
        # The pre-existing journal is never overwritten by the losing commit.
        self.assertEqual(self.journal.read_text(encoding='utf-8'), '{}')


class OfflineNarrationTests(PackageCase):
    def test_special_dialogue_is_kept_and_cue_instructions_are_dropped(self):
        session = self.rt.new_session('离线', 'protagonist')
        request = Turn(message='收下行装', action_id='pack')
        decision = self.rt.prepare_turn(session, request)
        decision['special_dialogue'] = '守卫压低声音：往西三十里有一处断墙。'
        text = offline_surface(session, decision, request)
        self.assertIn('守卫压低声音：往西三十里有一处断墙。', text)
        self.assertIn(decision['outcome'], text)
        self.assertNotIn('依据本人的动机和语气回应', text)
        self.assertNotIn('别复制其他角色句式', text)

    def test_performances_carry_public_names_not_weights(self):
        session = self.rt.new_session('表现', 'protagonist')
        # Close the opening event, then stand where a guard is present.
        opening = Turn(message='收下行装', action_id='pack')
        self.rt.finish_turn(session, opening, '收起行囊。', self.rt.prepare_turn(session, opening), {})
        self.rt.move(session, 'western_pass')
        request = Turn(message='向守卫问候', channel='speech')
        decision = self.rt.prepare_turn(session, request)
        self.assertTrue(decision['performances'])
        public = {c['id']: c.get('public_name') or c['name']
                  for c in self.rt.package()['characters']['characters']}
        for item in decision['performances']:
            self.assertEqual(item['public_name'], public[item['character']])
            self.assertNotIn('personality', item)
            self.assertNotIn('cue', item)
            self.assertIsInstance(item['action'], str)
        text = offline_surface(session, decision, request)
        for item in decision['performances']:
            self.assertIn(item['public_name'], text)
        # The online protocol keeps its internal cue: the model still needs it.
        self.assertTrue(all(item.get('cue') for item in decision['reactions']))
        self.assertNotIn('依据本人的动机和语气回应', text)

    def test_unspoken_channels_do_not_answer_as_public_dialogue(self):
        session = self.rt.new_session('未出声', 'protagonist')
        decision = self.rt.prepare_turn(session, Turn(message='收下行装', action_id='pack'))
        decision['performances'] = [{'character': 'pass_guard', 'public_name': '关城守卫',
                                     'action': '接话反问', 'emotion': '', 'stance': 'neutral',
                                     'unverified_claim': False}]
        for channel in ('thought', 'note', 'action'):
            with self.subTest(channel):
                text = offline_surface(session, decision, Turn(message='沉默', channel=channel))
                self.assertIn('关城守卫', text)
                # Nothing unspoken may be narrated as an answer.
                for spoken in ('接了一句', '反问回来', '直接答', '把要求说清楚', '提了个交换条件'):
                    self.assertNotIn(spoken, text)
        spoken = offline_surface(session, decision, Turn(message='问候', channel='speech'))
        self.assertIn('接了一句', spoken)

    def test_observer_offline_text_never_speaks_as_the_hero(self):
        session = self.rt.new_session('旁观输出', 'observer')
        decision = {'outcome': '继续对话', 'performances': [
            {'character': 'pass_guard', 'public_name': '关城守卫', 'action': '直接回应',
             'emotion': '', 'stance': 'neutral', 'unverified_claim': False}]}
        text = offline_surface(session, decision, Turn(message='观望', channel='speech'))
        self.assertIn('我看着眼前这一幕', text)
        self.assertIn('关城守卫', text)
        self.assertNotIn('我把话说出口', text)
        self.assertNotIn('直接答了一句', text)


if __name__ == '__main__':
    unittest.main()
