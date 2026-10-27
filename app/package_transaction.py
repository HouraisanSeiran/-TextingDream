"""Story-package commit journal: strict validation, exclusive creation, idempotent replay.

The journal is the only record that a package commit is in flight. Everything in it is
re-validated from scratch before any file is deleted or moved, so a corrupt or hostile
journal can never steer the recovery into an arbitrary path. Whether a commit is
committed is decided by the pointer in SQLite; everything else is decided by what is on
disk, which keeps recovery repeatable when an earlier recovery was itself interrupted.

Phase markers are written *before* the destructive step they describe, never after: a
crash can therefore only leave "marker set, action not started", which replays as a
harmless no-op. The opposite window ("action done, marker missing") cannot exist, so no
test or operator ever has to reason about it.

Scope: this is a local single-author workbench. The journal serialises one commit at a
time inside one process; it does not implement multi-process package editing and cannot
promise absolute safety against physical power loss.
"""
import json
import os
import re
import shutil
from pathlib import Path

from .knowledge import PackageFiles, atomic_text, fsync_directory

JOURNAL = '.package_transaction.json'
VERSION = 1
# Ordered: a later phase implies every earlier step may already have run.
PHASES = ('prepared', 'staged', 'characters', 'committed')
_FIELDS = {'version', 'transaction', 'target', 'stage', 'backup', 'target_existed', 'new_id',
           'character_id', 'character_file', 'character_backup', 'character_existed', 'phase'}
_REVISION = re.compile(r'[0-9a-f]{16}\Z')
_ID = re.compile(r'[A-Za-z0-9_-]{1,80}\Z')
# The folder rule has to be the *same* one the runtime accepts, otherwise a package
# directory that legitimately exists (spaces, long CJK names) could be written into a
# journal that recovery then refuses — leaving a legal commit permanently stuck.
FOLDER_LIMIT = 100


def valid_folder(name):
    """Same rule as Runtime.package_directory: no separator, no drive colon, no dot-lead."""
    if not isinstance(name, str) or not name or len(name) > FOLDER_LIMIT:
        return False
    if name.startswith('.') or '\x00' in name:
        return False
    return not any(character in name for character in '/\\:')


class TransactionError(ValueError):
    """A package transaction is unsafe, corrupt or cannot be replayed."""


def journal_path(library):
    return Path(library) / JOURNAL


def encode(data):
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def write_exclusive(path, text):
    """Create the journal only if it does not exist yet: no check-then-write window."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
    handle = os.open(path, flags, 0o600)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(text.encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        remove(path)
        raise
    fsync_directory(path.parent)


def fsync_file(path):
    """Flush a file's bytes; best effort because Windows needs a writable handle."""
    try:
        handle = os.open(path, os.O_RDWR | getattr(os, 'O_BINARY', 0))
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)


def write_atomic_bytes(path, payload):
    """Publish bytes with one rename, so a crash can never leave a partial file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / ('.' + path.name + '.tmp_' + os.urandom(6).hex())
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
    handle = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except BaseException:
        remove(temp)
        raise
    fsync_directory(path.parent)


def assert_no_symlinks(root):
    """Refuse to copy or stage a tree that contains links: a staged write must never be
    redirected into a file elsewhere on the user's disk."""
    root = Path(root)
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            if os.path.islink(os.path.join(current, name)):
                raise TransactionError('故事包目录含符号链接，已拒绝提交：' + name)


def _text(data, field, pattern):
    value = data.get(field)
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise TransactionError('故事包事务日志的 ' + field + ' 不合法')
    return value


def _flag(data, field):
    value = data.get(field)
    # bool is an int subclass, so check the exact type: 1 must not pass as a flag.
    if not isinstance(value, bool):
        raise TransactionError('故事包事务日志的 ' + field + ' 不合法')


def parse(library, character_directory, journal):
    """Validate a journal completely, then resolve its paths.

    No file outside the journal is touched before every check passes, so a journal that
    fails any of them leaves the filesystem exactly as it was and is kept for inspection.
    """
    journal = Path(journal)
    if journal.is_symlink():
        raise TransactionError('故事包事务日志不能是符号链接，已保留原文件')
    try:
        data = json.loads(journal.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        raise TransactionError('故事包事务日志无法读取或已损坏，已保留原文件') from error
    if not isinstance(data, dict):
        raise TransactionError('故事包事务日志格式不正确，已保留原文件')
    if set(data) != _FIELDS:
        raise TransactionError('故事包事务日志字段不完整或含未知字段，已保留原文件')
    version = data['version']
    if not isinstance(version, int) or isinstance(version, bool) or version != VERSION:
        raise TransactionError('故事包事务日志版本不受支持，已保留原文件')
    transaction = _text(data, 'transaction', _REVISION)
    target_name = data.get('target')
    if not valid_folder(target_name):
        raise TransactionError('故事包事务日志的 target 不合法')
    if data['stage'] != '.' + target_name + '.pending_' + transaction:
        raise TransactionError('故事包暂存目录名与事务不匹配')
    if data['backup'] != '.' + target_name + '.backup_' + transaction:
        raise TransactionError('故事包备份目录名与事务不匹配')
    character_id = _text(data, 'character_id', _ID)
    if data['character_file'] != character_id + '.json':
        raise TransactionError('角色包文件名与事务不匹配')
    if data['character_backup'] != '.' + character_id + '.backup_' + transaction + '.json':
        raise TransactionError('角色包备份文件名与事务不匹配')
    _flag(data, 'target_existed')
    _flag(data, 'character_existed')
    _text(data, 'new_id', _REVISION)
    if data['phase'] not in PHASES:
        raise TransactionError('故事包事务阶段标记不合法')
    library, characters = Path(library), Path(character_directory)
    state = {'data': data,
             'target': library / target_name,
             'stage': library / data['stage'],
             'backup': library / data['backup'],
             'char_path': characters / data['character_file'],
             'char_backup': characters / data['character_backup']}
    for key, root in (('target', library), ('stage', library), ('backup', library),
                      ('char_path', characters), ('char_backup', characters)):
        path = state[key]
        if path.parent.resolve() != root.resolve():
            raise TransactionError('故事包事务路径越界，已拒绝执行')
        if path.is_symlink():
            raise TransactionError('故事包事务路径不能是符号链接')
    for key in ('target', 'stage', 'backup'):
        path = state[key]
        if path.exists() and not path.is_dir():
            raise TransactionError('故事包事务目录被非目录占用：' + path.name)
    for key in ('char_path', 'char_backup'):
        path = state[key]
        if path.exists() and path.is_dir():
            raise TransactionError('角色包事务路径被目录占用：' + path.name)
    # Transaction-owned trees must not smuggle links into a later copy or rename.
    for key in ('stage', 'backup'):
        if state[key].is_dir():
            assert_no_symlinks(state[key])
    return state


def remove(path):
    """Delete a file, link or directory tree; a missing path is already done."""
    path = Path(path)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def mark(journal, data, phase):
    """Record progress *before* the step it describes, so a replay never has to guess
    whether a destructive action already ran."""
    if PHASES.index(phase) < PHASES.index(data['phase']):
        raise TransactionError('故事包事务阶段不能倒退')
    if data['phase'] == phase:
        return data
    data = {**data, 'phase': phase}
    atomic_text(journal, encode(data))
    return data


def _reached(data, phase):
    return PHASES.index(data['phase']) >= PHASES.index(phase)


def _looks_like_package(path):
    return path.is_dir() and (path / 'story.json').is_file()


def restore(state):
    """Undo an uncommitted commit.

    Every decision comes from the disk, so running it twice (or after an interrupted
    run) converges on the previous package instead of deleting a tree that an earlier
    pass had already restored.
    """
    data, target, stage, backup = state['data'], state['target'], state['stage'], state['backup']
    char_path, char_backup = state['char_path'], state['char_backup']
    if backup.is_dir() and not data['target_existed']:
        # A backup can only exist if a previous tree was moved aside, so the journal
        # contradicts the disk. Fail closed instead of guessing which tree to delete.
        raise TransactionError('故事包事务日志与磁盘状态矛盾，已保留文件与事务日志')
    # Validate every source *before* touching anything: a restore that dies halfway
    # through would otherwise leave a state the next pass cannot reason about.
    if backup.is_dir() and not _looks_like_package(backup):
        raise TransactionError('故事包备份不完整，已保留文件与事务日志供人工检查')
    if char_backup.exists():
        try:
            json.loads(char_backup.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            # The character backup is produced by an atomic rename, so a broken one can
            # only come from outside; never let it replace the live document.
            raise TransactionError('角色包备份无法读取，已保留文件与事务日志') from error
    if backup.is_dir():
        # The swap happened: the previous tree lives in the backup, and moving it back
        # consumes the marker, so a later pass cannot mistake it for the new tree.
        remove(target)
        backup.rename(target)
        fsync_directory(target.parent)
    elif not data['target_existed'] and target.exists():
        # No previous tree existed, so this target can only be the installed stage;
        # after the first pass it is gone, which makes a replay a no-op.
        remove(target)
    remove(stage)
    if char_backup.exists():
        remove(char_path)
        char_backup.rename(char_path)
        fsync_file(char_path)
    elif not data['character_existed'] and _reached(data, 'characters') and char_path.exists():
        # The phase proves the write was started; only this transaction could have
        # created the file (the journal was created exclusively).
        remove(char_path)


def verify_committed(state, expected):
    """Check a package directory equals the snapshot that was committed.

    `expected` is the committed package document (story + characters) — exactly what the
    staging read produced. The comparison is whole-document, not by id: a tree with the
    right ids but wrong actions, knowledge bodies or character attributes is a different
    package and must keep the backup. Returning here means this directory *is* the
    revision the database points at.
    """
    target = state['target']
    if not _looks_like_package(target):
        raise TransactionError('故事包已提交但目录缺少 story.json，已保留备份与事务日志')
    if not (target / '总概.md').is_file():
        raise TransactionError('故事包已提交但缺少 总概.md，已保留备份与事务日志')
    try:
        installed = PackageFiles(target).read()
    except (OSError, ValueError, KeyError) as error:
        raise TransactionError('故事包已提交但目录无法读取，已保留备份与事务日志') from error
    if installed != expected['story']:
        raise TransactionError('故事包已提交但目录内容与提交版本不一致，已保留备份与事务日志')
    try:
        characters = json.loads(state['char_path'].read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise TransactionError('角色包无法读取，已保留备份与事务日志') from error
    if not isinstance(characters, dict) or characters != expected['characters']:
        raise TransactionError('角色包与提交版本不一致，已保留备份与事务日志')


def finish(state, expected):
    """Complete a committed commit: keep the new tree, drop the pre-commit copies.

    The new tree is verified against the committed snapshot first. If it is missing or
    damaged, the backup and the journal are kept so the author still has a recovery
    point to inspect; nothing is deleted on a guess. A staging tree is only promoted
    after it verified, so `remove(target)` can never destroy the last good copy.
    """
    target, stage, backup = state['target'], state['stage'], state['backup']
    if not _looks_like_package(target) and _looks_like_package(stage):
        verify_committed({**state, 'target': stage}, expected)
        remove(target)
        stage.rename(target)
        fsync_directory(target.parent)
    verify_committed(state, expected)
    remove(backup)
    remove(state['char_backup'])
    remove(stage)
