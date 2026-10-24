"""Emergency stop from Telegram (2026-10-24, docs/EA_SYSTEM_PLAN.md: 急ぎの停止は Telegram から必ずできるように).

Send the bot one of:
  /stop  or 停止            -> every EA process stops new orders (demo and live)
  /stop demo | /stop live   -> only that account
  /status                   -> each process answers running / stopped
Stops only NEW orders: open positions keep their stop-loss on the MT5 server and are still managed.
To run again, press 稼働 in the app (the stop is also written to the app's settings).

How it is read (fast and light, 2026-10-25):
  Telegram allows only one reader of a bot at a time, so ONE of the EA processes on the PC (the "leader") waits for new
  messages with long polling (one request that stays open up to 50 s and returns as soon as a message arrives) and writes
  each command to TradeEA_data/tg_commands.jsonl. Every EA process (the leader too) reads that local file every few
  seconds. If the leader stops, another process takes over within 2 minutes (tg_leader.json is refreshed while it runs).
Only messages from the configured chat count. Commands sent while no EA was running are skipped.
"""
import json
import logging
import os
import re
import threading
import time
from pathlib import Path

import requests

LEASE_SEC = 120


def _cred():
    return os.getenv('EA_TELEGRAM_BOT_TOKEN', '').strip(), os.getenv('EA_TELEGRAM_CHAT_ID', '').strip()


def parse(text):
    """-> ('stop' | 'status', who) or None. who = '' (all), 'demo' or 'live'."""
    t = str(text or '').strip().lower()
    hit = re.match(r'^(/stop|停止|止めて|ストップ)(?:@\w+)?\s*(demo|live|デモ|本番)?$', t)
    if hit:
        return 'stop', {'デモ': 'demo', '本番': 'live'}.get(hit.group(2) or '', hit.group(2) or '')
    if re.match(r'^/status(?:@\w+)?$', t):
        return 'status', ''
    return None


class Relay:
    def __init__(self, kind, data_dir=None):
        self.kind = kind
        st = os.getenv('EA_STATE_FILE', '')
        self.dir = Path(data_dir or (Path(st).parent if st else Path.home() / 'TradeEA_data'))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cmd_f = self.dir / 'tg_commands.jsonl'
        self.lead_f = self.dir / 'tg_leader.json'
        self._stop = False
        self._warned = False

    # ---------------------------------------------------------------- leader (one process): Telegram -> local file
    def _leader(self):
        try:
            x = json.loads(self.lead_f.read_text(encoding='utf-8'))
        except Exception:
            x = {}
        if x.get('kind') not in (None, self.kind) and time.time() - float(x.get('ts', 0)) < LEASE_SEC:
            return False                                  # the other process is reading Telegram
        tmp = self.lead_f.with_suffix('.tmp')
        tmp.write_text(json.dumps(dict(kind=self.kind, ts=time.time())), encoding='utf-8'); tmp.replace(self.lead_f)
        try:                                              # both may have written at once: the file decides
            return json.loads(self.lead_f.read_text(encoding='utf-8')).get('kind') == self.kind
        except Exception:
            return False

    def _append(self, rows):
        with open(self.cmd_f, 'a', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        try:                                              # keep the file small
            lines = self.cmd_f.read_text(encoding='utf-8').splitlines()
            if len(lines) > 200:
                self.cmd_f.write_text('\n'.join(lines[-100:]) + '\n', encoding='utf-8')
        except Exception:
            pass

    def _run(self):
        nxt = None
        while not self._stop:
            tok, chat = _cred()
            if not tok or not chat:
                time.sleep(60); continue
            if not self._leader():
                nxt = None; time.sleep(20); continue
            try:
                if nxt is None:                           # start: skip anything sent before (offset -1 = only the newest)
                    r = requests.get(f'https://api.telegram.org/bot{tok}/getUpdates', params=dict(offset=-1, timeout=0), timeout=15)
                    if not r.ok:
                        raise RuntimeError(f'{r.status_code} {r.text[:150]}')
                    ups = r.json().get('result', [])
                    nxt = (ups[-1]['update_id'] + 1) if ups else 0
                    continue
                r = requests.get(f'https://api.telegram.org/bot{tok}/getUpdates',
                                 params=dict(offset=nxt, timeout=50, allowed_updates='["message"]'), timeout=65)
                if not r.ok:                              # 409: a webhook or another program reads this bot
                    raise RuntimeError(f'{r.status_code} {r.text[:150]}')
                rows = []
                for u in r.json().get('result', []):
                    nxt = int(u['update_id']) + 1
                    m = u.get('message') or {}
                    if str((m.get('chat') or {}).get('id')) != chat:
                        continue
                    p = parse(m.get('text'))
                    if p:
                        rows.append(dict(id=int(u['update_id']), cmd=p[0], who=p[1]))
                if rows:
                    self._append(rows)
            except Exception as ex:
                if not self._warned:
                    logging.warning('Telegram commands unavailable: %s', ex); self._warned = True
                time.sleep(30)

    def start(self):
        threading.Thread(target=self._run, daemon=True, name='telegram-commands').start()
        return self

    # ---------------------------------------------------------------- every process: local file -> commands
    def pending(self, state):
        """Commands for this process not handled yet (stop / status). Cheap: reads a small local file."""
        try:
            rows = [json.loads(l) for l in self.cmd_f.read_text(encoding='utf-8').splitlines() if l.strip()]
        except Exception:
            rows = []
        top = max((r['id'] for r in rows), default=0)
        if 'tg_cmd_seen' not in state:                    # first run of this account: older commands are skipped
            state['tg_cmd_seen'] = top
            return []
        seen = int(state['tg_cmd_seen'])
        out = [r['cmd'] for r in rows if r['id'] > seen and r.get('who') in ('', self.kind)]
        state['tg_cmd_seen'] = max(seen, top)
        return out
