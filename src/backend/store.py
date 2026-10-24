"""Local durable cases/cache/budget. One backend process owns the worker."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import MAX_CALLS, STATE


def utc():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path = STATE / 'pitchguard.sqlite3'):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, revision TEXT, scenario TEXT,
                    mode TEXT, state TEXT, created TEXT, payload TEXT, UNIQUE(revision,scenario,mode));
                CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY, case_id TEXT);
                CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, response TEXT);
                CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY, day TEXT, case_id TEXT,
                    role TEXT, reserved INTEGER, actual INTEGER, status TEXT);
                CREATE TABLE IF NOT EXISTS acknowledgements (id INTEGER PRIMARY KEY, case_id TEXT, at TEXT);
            ''')

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def recover(self):
        for row in self.list_cases():
            if row['state'] in ('queued', 'running'):
                payload = self.get(row['id'])
                payload.update(state='failed', error='Process restarted; analysis did not complete. No automatic paid retry.')
                self.save(payload)

    def list_cases(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,state,scenario,mode,created FROM cases ORDER BY created DESC')]

    def create(self, case, request_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT c.payload FROM requests r JOIN cases c ON c.id=r.case_id WHERE r.request_id=?', (request_id,)).fetchone()
            if not existing:
                existing = db.execute('SELECT payload FROM cases WHERE revision=? AND scenario=? AND mode=?',
                                      (case['input_revision'], case['scenario_id'], case['mode'])).fetchone()
            if existing:
                result = json.loads(existing['payload'])
                if (result['scenario_id'], result['mode'], result['input_revision']) != (case['scenario_id'], case['mode'], case['input_revision']):
                    raise ValueError('Request ID reused with different input')
                db.execute('INSERT OR IGNORE INTO requests VALUES (?,?)', (request_id, result['id']))
                return result, False
            if os.environ.get('PITCHGUARD_STORAGE_ACCOUNT_URL'):
                active = db.execute("SELECT COUNT(*) FROM cases WHERE state IN ('queued','running')").fetchone()[0]
                if active:
                    raise ValueError('Another hosted analysis is active; wait for it to finish')
            count = db.execute('SELECT COUNT(*) FROM cases WHERE created LIKE ?', (utc()[:10] + '%',)).fetchone()[0]
            if count >= int(os.environ.get('PITCHGUARD_DAILY_CASE_LIMIT', '16')):
                raise ValueError('Daily case budget exhausted')
            db.execute('INSERT INTO cases VALUES (?,?,?,?,?,?,?)', (case['id'], case['input_revision'], case['scenario_id'],
                       case['mode'], case['state'], case['created_at'], json.dumps(case)))
            db.execute('INSERT INTO requests VALUES (?,?)', (request_id, case['id']))
            return case, True

    def save(self, case):
        with self.connect() as db:
            db.execute('UPDATE cases SET state=?,payload=? WHERE id=?', (case['state'], json.dumps(case, allow_nan=False), case['id']))

    def get(self, case_id):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM cases WHERE id=?', (case_id,)).fetchone()
        if not row:
            raise KeyError(case_id)
        return json.loads(row['payload'])

    def patch(self, case_id, fields):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM cases WHERE id=?', (case_id,)).fetchone()
            if not row:
                raise KeyError(case_id)
            case = json.loads(row['payload'])
            case.update(fields)
            db.execute('UPDATE cases SET state=?,payload=? WHERE id=?', (case['state'],json.dumps(case),case_id))
            return case

    def cached(self, key):
        with self.connect() as db:
            row = db.execute('SELECT response FROM cache WHERE key=?', (key,)).fetchone()
        return json.loads(row['response']) if row else None

    def cache(self, key, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO cache VALUES (?,?)', (key, json.dumps(value)))

    def reserve(self, case_id, role, tokens):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            count = db.execute('SELECT COUNT(*) FROM usage WHERE case_id=?', (case_id,)).fetchone()[0]
            day = utc()[:10]
            daily = db.execute('SELECT COUNT(*),COALESCE(SUM(COALESCE(actual,reserved)),0) FROM usage WHERE day=?', (day,)).fetchone()
            if (count >= MAX_CALLS or daily[0] >= int(os.environ.get('PITCHGUARD_DAILY_CALL_LIMIT', '60'))
                    or daily[1] + tokens > int(os.environ.get('PITCHGUARD_DAILY_TOKEN_LIMIT', '300000'))):
                raise ValueError('Model call/token budget exhausted')
            return db.execute('INSERT INTO usage(day,case_id,role,reserved,status) VALUES (?,?,?,?,?)',
                              (day, case_id, role, tokens, 'reserved')).lastrowid

    def finish(self, usage_id, tokens, status):
        with self.connect() as db:
            db.execute('UPDATE usage SET actual=?,status=? WHERE id=?', (tokens, status, usage_id))

    def acknowledge(self, case_id):
        self.get(case_id)
        with self.connect() as db:
            db.execute('INSERT INTO acknowledgements(case_id,at) VALUES (?,?)', (case_id, utc()))
