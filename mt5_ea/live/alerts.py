"""Discretionary alerts (2026-11-21): 'そろそろ' notices for the trader's own setups, wider than the EAs. No orders, ever.

Rule (first version, to be tuned after the trader's chart check, docs/DISCRETIONARY_RULES.md 11/21):
  lines  gateway  (methods 1 / 6) = the last protected swing broken by an H4 major reversal, alive 30 days after the reversal
         fortress (methods 2 / 7) = the protected swing of the current H4 major trend (breakout_protect), alive 30 days
  alert  the H4 major trend points the same way, price has been >= 1 ATR(H4) beyond the line (on the trade side) and then
         comes back within 0.3 ATR of it: the first such M15 bar (none if an M15 close went 0.5 ATR through before)
  method D1 close above SMA75 and SMA75 rising over 10 days (sell: below / falling) = 〇 -> 1 / 2, else 6 / 7
Same logic as the research scan (scratchpad q21/alerts.py), so the check page list ALR is what this sends.

Run (desktop, its own window, read only): ALERTS_START.bat -> python -m mt5_ea.live.alerts
  every new M15 bar: scan the FX pairs (last 400 days of bars from MT5), send new alerts to Telegram and to GAS (eaAlert ->
  sheet EA_Alerts, shown in the app). The app's settings (on / off, which methods) come back from GAS on every call.
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from mt5_ea.live.core import Frames
from mt5_ea.live.eas import dsc

PAIRS = ('EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'CHFJPY',
         'AUDCAD', 'AUDCHF', 'AUDNZD', 'CADCHF', 'EURAUD', 'EURNZD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPNZD', 'NZDCAD', 'NZDCHF')
DAYS, WARM = 400, 250
NEAR, AWAY, THROUGH, LIFE = 0.3, 1.0, 0.5, 30
DAY = np.timedelta64(1, 'D')
METHOD_JA = {'1': '手法1（日足〇・H4 出入口）', '6': '手法6（日足✕・H4 出入口）', '2': '手法2（日足〇・H4 砦）', '7': '手法7（日足✕・H4 砦）'}


def space(sym, px):
    return np.asarray(px, float) / (100.0 if sym.endswith('JPY') else 1.0)


def scan(sym, m, since=None):
    """m: M15 bars (t, o, h, l, c) in broker prices. Returns the alerts (dicts) whose bar time >= since (all when None)."""
    m = m[['t', 'o', 'h', 'l', 'c']].copy(); m['t'] = pd.to_datetime(m.t).astype('datetime64[us]')
    k = 100.0 if sym.endswith('JPY') else 1.0
    for z in 'ohlc':
        m[z] = space(sym, m[z].to_numpy())
    start = m.t.iat[0] + pd.Timedelta(days=WARM)
    F = Frames(m, start, h_days=WARM, m_days=WARM); cx = dsc._Ctx(F)
    TM, MH, ML, MC, C4 = cx.TM, cx.MH, cx.ML, cx.MC, cx.C4
    a4 = lambda t: cx.a4[max(0, int(np.searchsorted(C4, t, side='right')) - 1)]
    s75, T1, P4 = cx.s75, cx.T1, cx.raw['H4']
    Td, cd = cx.Td, cx.cd; s75d = pd.Series(cd).rolling(75).mean().to_numpy()
    pv = sorted((C4[e['idx']], e['to']) for e in F.R4['all_events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL')
    pvt = np.array([a for a, _ in pv], dtype='datetime64[ns]')
    t_from = np.datetime64(pd.Timestamp(start)) if since is None else np.datetime64(pd.Timestamp(since))

    def h4dir(t):
        j = int(np.searchsorted(pvt, t, side='right')) - 1
        return 0 if j < 0 else (1 if pv[j][1] == 'up' else -1)

    def d1dir(t):
        j = int(np.searchsorted(Td, t, side='right')) - 2
        if j < 10 or np.isnan(s75d[j]) or np.isnan(s75d[j - 10]):
            return 0
        return 1 if (cd[j] > s75d[j] and s75d[j] > s75d[j - 10]) else (-1 if (cd[j] < s75d[j] and s75d[j] < s75d[j - 10]) else 0)

    def h1ma(t, s):
        j = int(np.searchsorted(T1, t, side='right')) - 2
        if j < 10 or np.isnan(s75[j]) or np.isnan(s75[j - 10]):
            return 0
        return int(s * (cx.c1[j] - s75[j]) > 0 and s * (s75[j] - s75[j - 10]) > 0)

    def touches(L, t, A):
        return int(((P4[0] <= t) & (P4[0] >= t - 90 * DAY) & (np.abs(P4[2] - L) <= 0.25 * A)).sum())

    def first_near(L, s, t0, A):
        q0 = int(np.searchsorted(TM, t0)); q1 = int(np.searchsorted(TM, t0 + LIFE * DAY))
        if q1 <= q0:
            return None
        far = np.nonzero(s * (MC[q0:q1] - L) >= AWAY * A)[0]
        if not len(far):
            return None
        a = q0 + far[0]; hit = np.nonzero(s * ((ML if s > 0 else MH)[a:q1] - L) <= NEAR * A)[0]
        if not len(hit):
            return None
        q = a + hit[0]
        return None if len(np.nonzero(s * (MC[a:q + 1] - L) < -THROUGH * A)[0]) else q

    out, seen = [], set()
    for e in F.R4['all_events']:
        if e.get('machine') != 'major':
            continue
        if e['action'] == 'REVERSAL' and e.get('broken_price') is not None:
            kind, s, L = '出入口', (1 if e['to'] == 'up' else -1), float(e['broken_price'])
        elif e.get('action') == 'breakout_protect':
            kind, s, L = '砦', (1 if e['trend'] == 'up' else -1), float(e['prot_price'])
            if (round(L, 6), s) in seen:
                continue
            seen.add((round(L, 6), s))
        else:
            continue
        t = C4[e['idx']]
        if t + LIFE * DAY < t_from:
            continue
        A = a4(t); q = first_near(L, s, t, A)
        if q is None or TM[q] < t_from or h4dir(TM[q]) != s:
            continue
        d1 = d1dir(TM[q]); meth = ('1' if d1 == s else '6') if kind == '出入口' else ('2' if d1 == s else '7')
        out.append(dict(sym=sym, kind=kind, side=s, method=meth, t=pd.Timestamp(TM[q]), line=round(L * k, 6), atr=round(A * k, 6),
                        price=round(float(MC[q]) * k, 6), born=pd.Timestamp(t), d1=int(d1), h1=h1ma(TM[q], s), touch=touches(L, TM[q], A)))
    return out


def text(a):
    dj = '買い' if a['side'] > 0 else '売り'; o = lambda v: '〇' if v else '✕'
    return (f"🔔 裁量 {a['sym']} {dj}：{a['kind']}に接近（{METHOD_JA[a['method']]}）\n"
            f"線 {a['line']:g}・今 {a['price']:g}（{abs(a['price'] - a['line']) / a['atr']:.1f}ATR）\n"
            f"日足 {o(a['d1'] == a['side'])}・H1 MA75 {o(a['h1'])}・線の山谷 {a['touch']} 個\n"
            f"足 {a['jst']}（日本時間）")


def jst(t):
    return pd.Timestamp(t).tz_localize('Europe/Athens', ambiguous=True, nonexistent='shift_forward').tz_convert('Asia/Tokyo').strftime('%Y-%m-%d %H:%M')


def main():
    from mt5_ea.live import gas
    from mt5_ea.live.broker import MT5Broker
    from mt5_ea import telegram_notify as tg
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    data = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data'); data.mkdir(exist_ok=True)
    stf = data / 'alerts_state.json'
    st = json.loads(stf.read_text(encoding='utf-8')) if stf.exists() else {'sent': [], 'last_bar': ''}
    path = os.getenv('EA_ALERT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or ''
    if path:
        os.environ['EA_MT5_PATH'] = path
    b = MT5Broker()
    cfg = {'on': True, 'methods': ['1', '6', '2', '7']}
    print('裁量の通知を始めました（注文はしません）。この窓を閉じると止まります。', flush=True)
    first = True
    while True:
        try:
            last = b.bars('EURUSD', 2).t.iat[-1]
            if str(last) != st['last_bar']:
                since = pd.Timestamp(last) - pd.Timedelta(hours=1) if not first else pd.Timestamp(last) - pd.Timedelta(minutes=15)
                new = []
                for sym in PAIRS:
                    try:
                        m = b.bars(sym, DAYS)
                        for a in scan(sym, m, since=since):
                            aid = f"{a['sym']}|{a['kind']}|{a['line']}|{a['born']}"
                            if aid in st['sent']:
                                continue
                            a['jst'] = jst(a['t']); a['id'] = aid; new.append(a)
                    except Exception as ex:
                        logging.warning('%s: %s', sym, ex)
                try:      # GAS: record the alerts, get the app's settings back
                    r = gas.call('eaAlert', {'alerts': [dict({k: (str(v) if isinstance(v, pd.Timestamp) else v) for k, v in a.items()}) for a in new]}, timeout=60)
                    if isinstance(r, dict) and isinstance(r.get('settings'), dict):
                        cfg.update(r['settings'])
                except Exception as ex:
                    logging.warning('GAS: %s', ex)
                for a in new:
                    if cfg.get('on', True) and a['method'] in set(cfg.get('methods') or []):
                        tg.send('alert', text(a), {'notifyAlert': True})
                    st['sent'].append(a['id'])
                st['sent'] = st['sent'][-3000:]; st['last_bar'] = str(last); first = False
                stf.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
                logging.info('bar %s: %d new alerts', last, len(new))
        except Exception as ex:
            logging.exception('alerts loop: %s', ex)
        time.sleep(20)


if __name__ == '__main__':
    sys.exit(main())
