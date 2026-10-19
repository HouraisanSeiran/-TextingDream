"""SQLite transactions keep session state and three information layers together."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


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

    def save_session(self, session, records=()):
        state = dict(session)
        layers = {table: state.pop(table) for table in ('facts', 'beliefs', 'heard')}
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)', ('session', state['id'], dumps(state)))
            db.executemany('INSERT OR REPLACE INTO documents VALUES(?,?,?)',[(kind,id,dumps(value)) for kind,id,value in records])
            for table, values in layers.items():
                db.execute(f'DELETE FROM {table} WHERE session=?', (state['id'],))
                db.executemany(f'INSERT INTO {table} VALUES(?,?,?)', [(state['id'], str(i), dumps(v)) for i, v in enumerate(values)])

    def session(self, id):
        # A single read transaction prevents mixing different revisions of layers.
        with self.connect() as db:
            db.execute('BEGIN')
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?', ('session', id)).fetchone()
            if not row:
                raise ValueError('存档不存在')
            state = json.loads(row[0])
            for table in ('facts', 'beliefs', 'heard'):
                state[table] = [json.loads(r[0]) for r in db.execute(f'SELECT body FROM {table} WHERE session=? ORDER BY rowid', (id,))]
        return state
