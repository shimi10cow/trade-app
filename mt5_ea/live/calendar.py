"""Economic event reminders on Telegram (2026-11-11, moved from the old EA mt5_ea/main.py process_calendar_reminders).

The app writes reminders to the EA_Calendar_Reminders sheet (EventKey, Title, Currency, EventTimeJST, ClientTimeZone,
NotifyMinutes, Enabled). Every minute the live EA reads them through GAS (getCalendarReminders; the last list is kept in a
local file for when GAS is down) and sends one Telegram message NotifyMinutes before the event.

Both EA processes (demo and live) run this. Each event is sent once: the first process to create its marker file in the
shared data folder sends it (os.O_EXCL), the other sees the file and skips. The sheet's Sent column is not used for this
(GAS saveCalendarReminder sets it back to NO whenever the reminder is ON).
"""
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import gas

POLL_SEC = 60
KEEP_DAYS = 30
JST = ZoneInfo('Asia/Tokyo')
FORMATS = ('%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M')


def parse_jst(raw):
    s = str(raw or '').strip()
    for f in FORMATS:
        try:
            return datetime.strptime(s, f).replace(tzinfo=JST)
        except ValueError:
            pass
    raise ValueError(f'unsupported EventTimeJST {s!r}')


def message(x, jst, minutes_left):
    tzname = str(x.get('ClientTimeZone') or 'Asia/Tokyo')
    try:
        local = jst.astimezone(ZoneInfo(tzname))
    except Exception:
        local = jst
    when = f'{local:%H:%M}（日本時間 {jst:%H:%M}）' if local.utcoffset() != jst.utcoffset() else f'{jst:%H:%M}'
    return f'⏰ 経済指標 あと {minutes_left} 分\n{when} {x.get("Currency", "")} {x.get("Title", "")}'.strip()


class CalendarReminders:
    def __init__(self, data_dir, fetch=None, now=None):
        self.dir = Path(data_dir) / 'calendar_sent'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cache = Path(data_dir) / 'calendar_reminders.json'
        self._fetch = fetch or (lambda: gas.call('getCalendarReminders', timeout=15))
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._t = 0.0
        self._cleaned = 0.0
        self._warned = set()

    def _rows(self):
        try:
            rows = self._fetch()
            if isinstance(rows, dict):                     # tolerate {data: [...]} / {reminders: [...]}
                rows = rows.get('data') or rows.get('reminders') or []
            if not isinstance(rows, list):
                raise ValueError(f'not a list: {type(rows).__name__}')
            tmp = self.cache.with_suffix('.tmp')
            tmp.write_text(json.dumps(rows, ensure_ascii=False, default=str), encoding='utf-8'); tmp.replace(self.cache)
            return rows
        except Exception as ex:
            logging.warning('calendar reminders: GAS read failed (%s), using the saved list', ex)
            try:
                return json.loads(self.cache.read_text(encoding='utf-8'))
            except Exception:
                return []

    def _claim(self, x, jst):
        """True for exactly one process per event (the marker file is created atomically)."""
        key = hashlib.sha1(f'{x.get("EventKey", "")}|{jst.isoformat()}'.encode('utf-8')).hexdigest()[:20]
        try:
            fd = os.open(self.dir / f'{key}.sent', os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(f'{x.get("EventKey", "")}\n')
        return True

    def _clean(self):
        if time.time() - self._cleaned < 86400:
            return
        self._cleaned = time.time()
        for f in self.dir.glob('*.sent'):
            try:
                if time.time() - f.stat().st_mtime > KEEP_DAYS * 86400:
                    f.unlink()
            except Exception:
                pass

    def step(self, send, force=False):
        """Call often (every loop); reads the sheet at most once a minute. send(text) -> True when queued. Returns the texts sent."""
        if not force and time.time() - self._t < POLL_SEC:
            return []
        self._t = time.time()
        self._clean()
        now = self._now(); out = []
        for x in self._rows():
            if not isinstance(x, dict) or str(x.get('Enabled', '')).upper() != 'ON':
                continue
            try:
                jst = parse_jst(x.get('EventTimeJST'))
                mins = float(x.get('NotifyMinutes') or 5)
                left = (jst - now).total_seconds() / 60
                if not (0 <= left <= mins) or not self._claim(x, jst):
                    continue
                text = message(x, jst, max(1, int(round(left))))
                if send(text):
                    logging.info('calendar reminder sent: %s', text.replace('\n', ' / '))
                    gas.enqueue('eaLog', dict(account='', level='info', message=f'指標通知: {text}'[:500]))
                else:
                    logging.warning('calendar reminder not sent (Telegram off or not set up): %s', x.get('Title'))
                out.append(text)
            except Exception as ex:
                k = f'{x.get("EventKey")}|{ex}'
                if k not in self._warned:                  # once per bad row, not every minute
                    self._warned.add(k); logging.warning('calendar reminder row skipped: %s', ex)
        return out
