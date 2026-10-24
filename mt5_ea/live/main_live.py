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
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mt5_ea import telegram_notify as telegram  # noqa: E402
from mt5_ea.live import gas  # noqa: E402
from mt5_ea.live.broker import MT5Broker  # noqa: E402
from mt5_ea.live.runner import MAGIC, Runner  # noqa: E402

LOG = Path(__file__).with_name('live.log')
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
    logging.info('live EA started: account %s (%s) kind=%s, %d EAs, magic %s-%s', a['login'], a['server'], kind, len(MAGIC), min(MAGIC.values()), max(MAGIC.values()))
    note('info', f'EA 起動 {kind} 口座 {a["login"]}')
    last_hb = 0.0; last_slot = None
    while True:
        try:
            now = b.server_now() or pd.Timestamp.utcnow().tz_localize(None)
            slot = now.floor('15min')
            daily_slot = now.hour == 23 and 45 <= now.minute <= 55
            if (slot != last_slot and (now - slot).total_seconds() >= BAR_DELAY_SEC) or daily_slot:
                for line in R.step():
                    logging.info(line)
                R.sweep_closed(deal_reader(b))
                last_slot = slot
            if time.time() - last_hb >= HEARTBEAT_SEC:
                R.heartbeat(); last_hb = time.time()
            gas.flush()
        except Exception as ex:
            logging.exception('loop error')
            note('error', f'EA エラー: {ex}')
        time.sleep(3)


if __name__ == '__main__':
    main()
