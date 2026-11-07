"""SQLite transactions keep session state and three information layers together."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .token_usage import _time, summarize

USAGE_RETENTION_DAYS = 90


def _usage_record(trace):
    """Metering stays independent of prompt/response retention."""
    record = {key: trace[key] for key in ('id', 'scope', 'status', 'usage') if key in trace}
    created = _time(trace.get('created'))
    record['created'] = created.isoformat() if created else None
    return record


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


class ConcurrentUpdateError(ValueError):
    """Raised when a stale session tries to overwrite a newer save."""


class SessionNotFound(ValueError):
    """The requested save does not exist (HTTP 404, not a generic 400)."""


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS documents(kind TEXT, id TEXT, body TEXT, PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS facts(session TEXT, id TEXT, body TEXT, PRIMARY KEY(session,id));
                CREATE TABLE IF NOT EXISTS beliefs(session TEXT, id TEXT, body TEXT, PRIMARY KEY(session,id));
                CREATE TABLE IF NOT EXISTS heard(session TEXT, id TEXT, body TEXT, PRIMARY KEY(session,id));
                CREATE TABLE IF NOT EXISTS model_usage(id TEXT PRIMARY KEY, created TEXT, body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS model_usage_created ON model_usage(created);
            ''')
            # Backfill available legacy traces once. Deleted historical traces cannot
            # be reconstructed, so earlier windows are explicitly marked incomplete.
            db.execute('BEGIN IMMEDIATE')
            metadata = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                  ('settings', 'token_usage_history')).fetchone()
            if metadata is None:
                for row in db.execute('SELECT body FROM documents WHERE kind=?', ('trace',)).fetchall():
                    record = _usage_record(json.loads(row[0]))
                    db.execute('INSERT OR IGNORE INTO model_usage VALUES(?,?,?)',
                               (record['id'], record['created'], dumps(record)))
                db.execute('INSERT INTO documents VALUES(?,?,?)',
                           ('settings', 'token_usage_history', dumps({
                               'complete_since': datetime.now(timezone.utc).isoformat()})))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transact(self):
        """One short write transaction that takes the write lock immediately.

        Callers must not await anything inside: the lock is held until the block ends.
        Town publication uses this only for its own bookkeeping rows, never while a
        story-package commit is running (that has its own connection and journal).
        """
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            yield db

    def get(self, kind, id, default=None):
        with self.connect() as db:
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?', (kind, id)).fetchone()
        return json.loads(row[0]) if row else default

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM documents WHERE kind=? ORDER BY rowid', (kind,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def record_trace(self, trace, limit=200):
        usage = _usage_record(trace)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=USAGE_RETENTION_DAYS)).isoformat()
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO model_usage VALUES(?,?,?)',
                       (usage['id'], usage['created'], dumps(usage)))
            db.execute('DELETE FROM model_usage WHERE created < ?', (cutoff,))
            db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)', ('trace', trace['id'], dumps(trace)))
            db.execute('DELETE FROM documents WHERE kind=? AND id NOT IN (SELECT id FROM documents WHERE kind=? ORDER BY rowid DESC LIMIT ?)', ('trace', 'trace', limit))

    def clear_traces(self):
        """Clear debug bodies; independently retained usage remains available."""
        with self.connect() as db:
            db.execute('DELETE FROM documents WHERE kind=?', ('trace',))

    def token_usage_summary(self, hours=24, now=None):
        now = now or datetime.now(timezone.utc)
        retention_start = now - timedelta(days=USAGE_RETENTION_DAYS)
        cutoff = max(now - timedelta(hours=hours), retention_start) if hours is not None else retention_start
        with self.connect() as db:
            rows = db.execute('SELECT body FROM model_usage WHERE created >= ? AND created <= ? ORDER BY created,id',
                              (cutoff.isoformat(), now.isoformat())).fetchall()
            metadata = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                  ('settings', 'token_usage_history')).fetchone()
        report = summarize([json.loads(row[0]) for row in rows], hours=hours, now=now)
        started = _time(json.loads(metadata[0]).get('complete_since')) if metadata else now
        complete_since = max(started or now, retention_start)
        report['coverage'] = {
            'complete_since': complete_since.isoformat(),
            'window_complete': hours is not None and now - timedelta(hours=hours) >= complete_since,
            'retention_days': USAGE_RETENTION_DAYS,
        }
        return report

    def put(self, kind, id, value):
        self.put_many([(kind, id, value)])

    def put_many(self, records):
        with self.connect() as db:
            db.executemany('INSERT OR REPLACE INTO documents VALUES(?,?,?)', [(kind, id, dumps(value)) for kind, id, value in records])

    def save_session(self, session, records=(), expected_version=None):
        state = dict(session)
        layers = {table: state.pop(table) for table in ('facts', 'beliefs', 'heard')}
        requested = state.get('state_version', 0)
        if expected_version is None:
            expected_version = requested
        with self.connect() as db:
            # Serialize the short read/check/write transaction. The remote model is
            # never awaited while this SQLite write lock is held.
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?', ('session', state['id'])).fetchone()
            if row is None:
                if expected_version not in (None, 0):
                    raise ConcurrentUpdateError('旅程版本已变化，请刷新后重试')
                version = 0
            else:
                current = json.loads(row[0]).get('state_version', 0)
                if current != expected_version:
                    raise ConcurrentUpdateError('旅程已被其他操作更新，请刷新后重试')
                version = current + 1
            state['state_version'] = version
            db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)', ('session', state['id'], dumps(state)))
            db.executemany('INSERT OR REPLACE INTO documents VALUES(?,?,?)',[(kind,id,dumps(value)) for kind,id,value in records])
            for table, values in layers.items():
                db.execute(f'DELETE FROM {table} WHERE session=?', (state['id'],))
                db.executemany(f'INSERT INTO {table} VALUES(?,?,?)', [(state['id'], str(i), dumps(v)) for i, v in enumerate(values)])
        session['state_version'] = version

    def session(self, id):
        # A single read transaction prevents mixing different revisions of layers.
        with self.connect() as db:
            db.execute('BEGIN')
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?', ('session', id)).fetchone()
            if not row:
                raise SessionNotFound('存档不存在')
            state = json.loads(row[0])
            state.setdefault('state_version', 0)
            for table in ('facts', 'beliefs', 'heard'):
                state[table] = [json.loads(r[0]) for r in db.execute(f'SELECT body FROM {table} WHERE session=? ORDER BY rowid', (id,))]
        return state

    def rename_session(self, id, title):
        """Change only the title. state_version is left alone on purpose: bumping it
        would make a page that already holds the old version (move/turn confirm tokens)
        fail its next write. A turn already in flight can still write the old title back."""
        with self.transact() as db:
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?', ('session', id)).fetchone()
            if row is None:
                raise SessionNotFound('存档不存在')
            state = json.loads(row[0])
            state['title'] = title
            db.execute('UPDATE documents SET body=? WHERE kind=? AND id=?', (dumps(state), 'session', id))
        return {'id': id, 'title': title}

    def delete_session(self, id):
        """Remove one save and every row keyed to it, in one transaction.

        Keyed by the session id: documents(session, session_notes_pending), the
        facts/beliefs/heard layers, recall_vectors, and development_draft documents
        whose body carries session_id. Story packages and files on disk are untouched.
        """
        with self.transact() as db:
            if db.execute('SELECT 1 FROM documents WHERE kind=? AND id=?', ('session', id)).fetchone() is None:
                raise SessionNotFound('存档不存在')
            db.execute('DELETE FROM documents WHERE kind IN (?,?) AND id=?', ('session', 'session_notes_pending', id))
            for table in ('facts', 'beliefs', 'heard'):
                db.execute(f'DELETE FROM {table} WHERE session=?', (id,))
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='recall_vectors'").fetchone():
                db.execute('DELETE FROM recall_vectors WHERE session=?', (id,))
            for row in db.execute('SELECT id, body FROM documents WHERE kind=?', ('development_draft',)).fetchall():
                if json.loads(row[1]).get('session_id') == id:
                    db.execute('DELETE FROM documents WHERE kind=? AND id=?', ('development_draft', row[0]))

    def record_unmatched_intent(self, record, limit=500):
        """Append an author-only diagnostic without changing any session version."""
        with self.transact() as db:
            db.execute('INSERT INTO documents VALUES(?,?,?)',
                       ('unmatched_intent', record['id'], dumps(record)))
            db.execute('DELETE FROM documents WHERE kind=? AND id NOT IN '
                       '(SELECT id FROM documents WHERE kind=? ORDER BY rowid DESC LIMIT ?)',
                       ('unmatched_intent', 'unmatched_intent', limit))
