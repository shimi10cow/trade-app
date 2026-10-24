"""Emergency stop from Telegram (2026-10-24, docs/EA_SYSTEM_PLAN.md: 急ぎの停止は Telegram から必ずできるように).

Send the bot one of:
  /stop  or 停止            -> every EA process stops new orders (demo and live)
  /stop demo | /stop live   -> only that account
  /status                   -> each process answers running / stopped
Stops only NEW orders: open positions keep their stop-loss on the MT5 server and are still managed.
To run again, press 稼働 in the app (the stop is also written to the app's settings).
Only messages from the configured chat count. Updates are read without confirming them, so the demo and the live process
both see every command (each remembers the last update id it handled in its state file).
"""
import logging
import os
import re

import requests


def _cred():
    return os.getenv('EA_TELEGRAM_BOT_TOKEN', '').strip(), os.getenv('EA_TELEGRAM_CHAT_ID', '').strip()


def poll(state, kind):
    """Returns a list of commands for this process: 'stop' / 'status'. Never raises."""
    tok, chat = _cred()
    if not tok or not chat:
        return []
    try:
        r = requests.get(f'https://api.telegram.org/bot{tok}/getUpdates', params=dict(timeout=0, limit=100, allowed_updates='["message"]'), timeout=8)
        ups = r.json().get('result', []) if r.ok else []
    except Exception as ex:
        logging.debug('telegram poll failed: %s', ex)
        return []
    last = int(state.get('tg_last_update') or 0)
    first_run = not last
    out = []
    for u in ups:
        uid = int(u.get('update_id', 0))
        if uid <= last:
            continue
        state['tg_last_update'] = uid
        m = u.get('message') or {}
        if str((m.get('chat') or {}).get('id')) != chat or first_run:      # first run: only remember where we are
            continue
        text = str(m.get('text') or '').strip().lower()
        hit = re.match(r'^(/stop|停止|止めて|ストップ)(?:@\w+)?\s*(demo|live|デモ|本番)?$', text)
        if hit:
            who = {'デモ': 'demo', '本番': 'live'}.get(hit.group(2) or '', hit.group(2) or '')
            if not who or who == kind:
                out.append('stop')
        elif re.match(r'^/status(?:@\w+)?$', text):
            out.append('status')
    return out
