"""GAS (Google Apps Script) client for the live EA (2026-10-24): every call carries the EA key; posts go through a small
SQLite outbox so a network failure never blocks trading (sent again later, oldest first).
Env: EA_GAS_URL, EA_GAS_KEY.
"""
import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path

import requests

URL = os.getenv('EA_GAS_URL', '')
KEY = os.getenv('EA_GAS_KEY', '')
DB = Path(os.getenv('EA_OUTBOX_DB', Path(__file__).with_name('live_outbox.sqlite3')))
NON_BLOCKING = {'eaTradeImage'}       # failures of these are retried a few times, then dropped, without stopping the queue


def call(action, payload=None, timeout=20):
    if not URL:
        raise RuntimeError('EA_GAS_URL not set')
    r = requests.post(URL, json={'action': action, 'key': KEY, **(payload or {})}, timeout=timeout)
    r.raise_for_status()
    x = r.json()
    if isinstance(x, dict) and x.get('success') is False:
        raise RuntimeError(str(x.get('error', x))[:300])
    return x


def _db():
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, payload TEXT, attempts INTEGER DEFAULT 0, next REAL DEFAULT 0, err TEXT DEFAULT "")')
    return db


def enqueue(action, payload):
    with _db() as db:
        db.execute('INSERT INTO outbox(action, payload) VALUES (?, ?)', (action, json.dumps(payload, ensure_ascii=False, default=str)))


def flush(max_items=50):
    """Send queued posts (oldest first). Called from the main loop; returns the number sent."""
    sent = 0
    if not URL:
        return 0
    with _db() as db:
        rows = db.execute('SELECT id, action, payload, attempts FROM outbox WHERE next <= ? ORDER BY id LIMIT ?', (time.time(), max_items)).fetchall()
    for oid, action, payload, att in rows:
        try:
            call(action, json.loads(payload))
            with _db() as db:
                db.execute('DELETE FROM outbox WHERE id = ?', (oid,))
            sent += 1
        except Exception as e:
            if action in NON_BLOCKING:              # an image must never hold up the trade records behind it
                with _db() as db:
                    if att + 1 >= 5:
                        db.execute('DELETE FROM outbox WHERE id = ?', (oid,))
                    else:
                        db.execute('UPDATE outbox SET attempts = attempts + 1, next = ?, err = ? WHERE id = ?', (time.time() + 300, str(e)[:500], oid))
                logging.warning('GAS post %s failed (%s): %s', action, 'dropped' if att + 1 >= 5 else 'later', e)
                continue
            with _db() as db:
                db.execute('UPDATE outbox SET attempts = attempts + 1, next = ?, err = ? WHERE id = ?', (time.time() + min(600, 2 ** min(att + 1, 9)), str(e)[:500], oid))
            logging.warning('GAS post %s failed (queued): %s', action, e)
            break
    return sent


def pending_count():
    with _db() as db:
        return db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]
