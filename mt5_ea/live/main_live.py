"""Start the live EA on the MT5 terminal this Python talks to (2026-10-24).

  py -m mt5_ea.live.main_live            (from the repository folder, MT5 terminal logged in to the EA account)

Env:
  EA_ACCOUNT_KIND = demo | live         which EA account this terminal is (settings in the app are per account)
  EA_LIVE_LOGIN   = the account number this process may trade (refuses to start on any other account)
  EA_GAS_URL / EA_GAS_KEY               app backend + key
  EA_TELEGRAM_BOT_TOKEN / EA_TELEGRAM_CHAT_ID
New orders need the app setting 'running' = on AND the EA in mode 'auto'. Until the app sends settings, nothing is traded.
"""
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mt5_ea import telegram_notify as telegram  # noqa: E402
from mt5_ea.live import gas, tg_stop  # noqa: E402
from mt5_ea.live.broker import MT5Broker  # noqa: E402
from mt5_ea.live.runner import MAGIC, Runner  # noqa: E402

LOG = Path(os.getenv('EA_LOG_FILE') or Path(__file__).with_name('live.log'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[logging.FileHandler(LOG, encoding='utf-8'), logging.StreamHandler()])
HEARTBEAT_SEC = 300
BAR_DELAY_SEC = 5          # wait a few seconds after the M15 close so the bar is final


def deal_reader(b):
    def read(ticket):
        ds = [d for d in b.deals_for(ticket) if int(d.entry) in (1, 3)]      # DEAL_ENTRY_OUT / OUT_BY
        if not ds:
            return None, None, None
        d = ds[-1]
        profit = sum(x.profit + x.swap + x.commission for x in b.deals_for(ticket))
        return d.price, profit, pd.to_datetime(d.time, unit='s')
    return read


def start_import(req, started):
    """The app asked for an MT5 import (heartbeat reply): run the importer as its own process (it uses other MT5 terminals)."""
    rid = str(req.get('id') or '')
    if not rid or rid in started:
        return
    started.add(rid)
    st = req.get('settings') or {}
    cmd = [sys.executable, '-m', 'mt5_ea.live.importer', '--request', rid, '--group-hours', str(st.get('groupHours', 24)),
           '--merge-across', '1' if st.get('mergeAcross', True) else '0'] + (['--reread90'] if st.get('reread90') else [])
    log = open(Path(os.getenv('EA_DATA_DIR') or (Path.home() / 'TradeEA_data')) / 'import.log', 'a', encoding='utf-8')
    subprocess.Popen(cmd, cwd=str(Path(__file__).resolve().parents[2]), stdout=log, stderr=subprocess.STDOUT,
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    logging.info('MT5 import started (%s)', rid)


def main():
    b = MT5Broker()
    a = b.account()
    lock = os.getenv('EA_LIVE_LOGIN', '').strip()
    if lock and str(a['login']) != lock:
        raise SystemExit(f'account {a["login"]} is not EA_LIVE_LOGIN {lock}: refusing to run')
    kind = os.getenv('EA_ACCOUNT_KIND', 'demo')
    if kind == 'live' and a.get('trade_mode') == 0:
        raise SystemExit('EA_ACCOUNT_KIND=live but this is a demo account')
    R = None

    def note(k, t):
        # quiet policy: entry / exit / signal per the app's switches; errors at most once per 15 min per message
        logging.info('[%s] %s', k, t)
        cfg = {**dict(notifySignal=True, notifyEntry=True, notifyExit=True, notifyError=True), **((R.config.get('notify') or {}) if R else {})}
        if k == 'error':
            telegram.error(t, cfg)
        elif k in ('signal', 'entry', 'exit'):
            telegram.send(k, t, cfg)
        else:
            telegram.send('error', t, dict(cfg, notifyError=True)) if k == 'info' and telegram.configured() else None
    R = Runner(b, notify=note, account_kind=kind)
    from mt5_ea.live.registry import SYMBOLS
    for s_ in SYMBOLS:                       # show the symbol mapping once; a missing symbol only skips that instrument
        try:
            logging.info('symbol %s -> %s', s_, b.name(s_))
        except Exception as ex:
            logging.warning('symbol %s not available: %s', s_, ex)
    logging.info('live EA started: account %s (%s) kind=%s, %d EAs, magic %s-%s', a['login'], a['server'], kind, len(MAGIC), min(MAGIC.values()), max(MAGIC.values()))
    note('info', f'EA 起動 {kind} 口座 {a["login"]}')
    last_hb = 0.0; last_slot = None; imports_started = set(); last_tg = 0.0
    while True:
        try:
            now = b.server_now() or pd.Timestamp.utcnow().tz_localize(None)
            slot = now.floor('15min')
            daily_slot = now.hour == 23 and 45 <= now.minute <= 55
            if (slot != last_slot and (now - slot).total_seconds() >= BAR_DELAY_SEC) or daily_slot:
                R.refresh_reservations()             # reservations made in the app just before this bar closed
                for line in R.step():
                    logging.info(line)
                R.sweep_closed(deal_reader(b))
                last_slot = slot
            if time.time() - last_hb >= HEARTBEAT_SEC:
                R.heartbeat(); last_hb = time.time()
                if R.import_request and kind == 'demo':     # only one EA process runs imports
                    start_import(R.import_request, imports_started)
            gas.flush()
            if time.time() - last_tg >= 30:                 # Telegram emergency stop (/stop, /stop demo, /stop live, /status)
                last_tg = time.time()
                for cmd in tg_stop.poll(R.state, kind):
                    if cmd == 'stop':
                        R.emergency_stop()
                        telegram.send('error', f'EA（{kind}）を停止しました。新しい注文は出しません（保有中の損切りはそのまま）。再開はアプリで「稼働」', dict(notifyError=True))
                    elif cmd == 'status':
                        telegram.send('error', f'EA（{kind}）{"稼働中" if R.config.get("running") else "停止中"} 口座 {a["login"]}', dict(notifyError=True))
                R.save()
        except Exception as ex:
            logging.exception('loop error')
            note('error', f'EA エラー: {ex}')
        time.sleep(3)


if __name__ == '__main__':
    main()
