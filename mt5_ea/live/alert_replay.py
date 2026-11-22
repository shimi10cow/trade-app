"""Alerts answer check (2026-11-22, user: "this week AUD / NZD / cross-yen had many entries; would the alerts and the stars have come?").
Replays the alerts window over past days with the settings it uses (the app's, else the presets): every Telegram alert that would have
been sent, and when the ⭐ 「もうすぐ」 was on, per pair. Read only, never orders.
  python -m mt5_ea.live.alert_replay [--from 2026-11-09] [--to 2026-11-22] [--pairs AUDJPY,NZDJPY]
Writes TradeEA_data/reports/alert_replay.csv too."""
import argparse
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd

from mt5_ea.live import alerts


def jst(t):
    return pd.Timestamp(t).tz_localize(alerts.SERVER_TZ if hasattr(alerts, 'SERVER_TZ') else 'Europe/Athens', ambiguous=True,
                                       nonexistent='shift_forward').tz_convert('Asia/Tokyo').strftime('%m/%d %H:%M')


def replay(b, pairs, frm, to, cfg, say=print):
    A = (cfg or {}).get('alerts') or {}
    profs = [p for p in (A.get('profiles') if A.get('v') == alerts.ALERTS_V and A.get('profiles') else alerts.PRESETS) if p.get('on')]
    star = A.get('star')
    rows = []
    for sym in pairs:
        try:
            m = b.bars(sym, alerts.DAYS + int((pd.Timestamp.now() - frm) / pd.Timedelta(days=1)) + 2)
            m = m[pd.to_datetime(m.t) <= to].reset_index(drop=True)
            mk = alerts.Market(sym, m)
        except Exception as ex:
            say(f'  {sym:7s} とばした（{str(ex)[:60]}）'); continue
        fired = [a for a in alerts.evaluate(mk, profs, frm) if frm <= pd.Timestamp(a['t']) <= to]
        for a in fired:
            rows.append(dict(pair=sym, what='通知', time=jst(a['t']), side='買' if a['side'] > 0 else '売', method=a.get('method'), kind=a.get('kind'),
                             line=a.get('line'), timing=a.get('timing'), uscore=a.get('uscore')))
        # ⭐ episodes: hourly over the period
        i0 = int(np.searchsorted(mk.CL, np.datetime64(frm))); on = {}
        for i in range(max(i0, 1), len(mk.TM), 4):
            cur = {(x['side'], x['kind'], x['line']): x for x in alerts.armed(mk, profs, at=i, star=star)}
            for k, x in cur.items():
                if k not in on:
                    on[k] = [mk.CL[i], mk.CL[i], x]
                else:
                    on[k][1] = mk.CL[i]
            for k in [k for k in on if k not in cur]:
                s0, s1, x = on.pop(k); rows.append(dict(pair=sym, what='⭐', time=jst(s0), until=jst(s1), side='買' if x['side'] > 0 else '売', method=x['method'], kind=x['kind'], line=x['line']))
        for k, (s0, s1, x) in on.items():
            rows.append(dict(pair=sym, what='⭐', time=jst(s0), until='今も', side='買' if x['side'] > 0 else '売', method=x['method'], kind=x['kind'], line=x['line']))
        n1 = sum(1 for r in rows if r['pair'] == sym and r['what'] == '通知'); n2 = sum(1 for r in rows if r['pair'] == sym and r['what'] == '⭐')
        say(f'  {sym:7s} 通知 {n1} 回 · ⭐ {n2} 回')
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    now = pd.Timestamp.now(tz='UTC').tz_localize(None)
    ap.add_argument('--from', dest='frm', default=str((now - pd.Timedelta(days=14)).date()))
    ap.add_argument('--to', default=str((now + pd.Timedelta(days=1)).date()))
    ap.add_argument('--pairs', default='')
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    from mt5_ea.live import gas
    from mt5_ea.live.broker import MT5Broker
    path = os.getenv('EA_ALERT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or ''
    if path:
        os.environ['EA_MT5_PATH'] = path
    say = lambda x: print(x, flush=True)
    say(f'通知の答え合わせ：{a.frm} 〜 {a.to}（注文はしません）')
    try:
        cfg = (gas.call('eaReportData', {}, timeout=120).get('config') or {}).get('demo') or {}
    except Exception as ex:
        say(f'  アプリの設定を読めなかったので初期設定で（{ex}）'); cfg = {}
    pairs = [p.strip().upper() for p in a.pairs.split(',') if p.strip()] or list(alerts.PAIRS)
    rows = replay(MT5Broker(), pairs, pd.Timestamp(a.frm), pd.Timestamp(a.to), cfg, say)
    df = pd.DataFrame(rows)
    out = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data') / 'reports'; out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / 'alert_replay.csv', index=False, encoding='utf-8-sig')
    say('')
    for what in ('通知', '⭐'):
        g = df[df.what == what] if len(df) else df
        say(f'== {what} {len(g)} 回 ==')
        for _, r in g.iterrows():
            say(f"  {r.pair:7s} {r.time}{(' 〜 ' + str(r.until)) if what == '⭐' else ''}  {r.side}  手法{r.method or '-'} {r.kind} {r.line}")
    say(f'\n保存: {out / "alert_replay.csv"}')


if __name__ == '__main__':
    main()
