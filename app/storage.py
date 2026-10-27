"""SQLite transactions keep session state and three information layers together."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


class ConcurrentUpdateError(ValueError):
    """Raised when a stale session tries to overwrite a newer save."""


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
            ''')

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
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)', ('trace', trace['id'], dumps(trace)))
            db.execute('DELETE FROM documents WHERE kind=? AND id NOT IN (SELECT id FROM documents WHERE kind=? ORDER BY rowid DESC LIMIT ?)', ('trace', 'trace', limit))

    def clear_traces(self):
        with self.connect() as db:
            db.execute('DELETE FROM documents WHERE kind=?', ('trace',))

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
                raise ValueError('存档不存在')
            state = json.loads(row[0])
            state.setdefault('state_version', 0)
            for table in ('facts', 'beliefs', 'heard'):
                state[table] = [json.loads(r[0]) for r in db.execute(f'SELECT body FROM {table} WHERE session=? ORDER BY rowid', (id,))]
        return state
