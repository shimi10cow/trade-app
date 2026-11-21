"""Trend direction per pair and timeframe for the app's pair tab (2026-11-21).

The same Dow engine the EAs use (env_recognition.dow_trend) on MT5's own MN1 / W1 / D1 / H4 / H1 bars:
  ↑  major trend up   and the provisional trend agrees
  ↓  major trend down and the provisional trend agrees
  →  no trend yet, or the provisional trend has already turned against the major one (turning)
The alerts window (demo) sends these once an hour; PAIR_ENV.bat (python -m mt5_ea.live.pair_env) sends them now. -> GAS eaPairEnv. GAS keeps them in Pairs Auto_* and copies a value into the
pair's own M1..H1 only when the automatic value changes, so a correction made in the app stays until the market moves.
Only reads prices; never orders."""
import logging

import pandas as pd

from mt5_ea.live import core  # noqa: F401  (puts research/ on sys.path)
from env_recognition import dow_trend  # noqa: E402

# app field <- MT5 timeframe, bars to read
TFS = (('M1', 'MN1', 300), ('W1', 'W1', 1300), ('D1', 'D1', 1500), ('H4', 'H4', 2500), ('H1', 'H1', 3000))
# Pairs tab names; symbols this account does not have are skipped
PAIRS = ('AUDCAD', 'AUDCHF', 'AUDNZD', 'AUDJPY', 'AUDUSD', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP',
         'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY',
         'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAUUSD', 'XAGUSD', 'XAUEUR', 'BTCUSD', 'BTCJPY', 'BTCEUR', 'BTCGBP',
         'US500', 'US30', 'US2000', 'JP225', 'UK100', 'EU50', 'OIL', 'BRENT', 'NATGAS')
ARROW = {'up': '↑', 'down': '↓'}


def direction(df, tf):
    """Arrow for the last closed bar of df (columns o, h, l, c). '' when there are too few bars."""
    df = df.reset_index(drop=True)
    if len(df) < 40:
        return ''
    R = dow_trend.run(df, tf, start=min(60, len(df) // 4))
    major = R['bars'][-1][0] if R['bars'] else None
    prov = R['prov_bars'][-1][0] if R.get('prov_bars') else None
    if major not in ARROW or (prov in ARROW and prov != major):
        return '→'
    return ARROW[major]


def rates(b, sym, tf, n):
    """Last n closed bars of one MT5 timeframe (the last bar is still forming)."""
    mt5 = b.mt5
    r = mt5.copy_rates_from_pos(b.name(sym), getattr(mt5, 'TIMEFRAME_' + tf), 0, n)
    if r is None or len(r) < 10:
        return None
    d = pd.DataFrame(r).rename(columns=dict(open='o', high='h', low='l', close='c'))
    d['t'] = pd.to_datetime(d.time, unit='s')
    return d[['t', 'o', 'h', 'l', 'c']].iloc[:-1]


class Stalled(RuntimeError):
    """MT5 did not answer one request in time (the stuck call cannot be cancelled, so the scan stops there)."""


def scan(b, pairs=PAIRS, log=None, timeout=None):
    """[{pair, M1, W1, D1, H4, H1}] for every pair this account has.
    log(text): progress line per pair. timeout: seconds one MT5 request may take (None = wait forever, as before);
    when MT5 does not answer, Stalled is raised with the rows done so far in .rows and the place in .where."""
    import concurrent.futures as cf
    import time
    pool = cf.ThreadPoolExecutor(1) if timeout else None

    def call(fn, *a):
        if not pool:
            return fn(*a)
        return pool.submit(fn, *a).result(timeout=timeout)

    out = []
    for p in pairs:
        t0 = time.time(); row = {'pair': p}; tf = 'symbol'
        try:
            call(b.name, p)
            for key, tf, n in TFS:
                d = call(rates, b, p, tf, n)
                row[key] = direction(d, key) if d is not None else ''
            if any(row[k] for k, _, _ in TFS):
                out.append(row)
            if log:
                log(f"  {p:7s} M1 {row['M1'] or '-'}  W1 {row['W1'] or '-'}  D1 {row['D1'] or '-'}  H4 {row['H4'] or '-'}  H1 {row['H1'] or '-'}   ({time.time() - t0:.1f}秒)")
        except cf.TimeoutError:
            ex = Stalled(f'{p} の {tf} で MT5 が {timeout} 秒たっても返事をしない'); ex.rows, ex.where = out, (p, tf)
            raise ex
        except Exception as ex:                         # symbol missing on this account, no history, ...
            logging.info('pair env %s: %s', p, ex)
            if log:
                log(f'  {p:7s} とばした（{str(ex)[:80]}）')
    return out


def main(argv=None):
    """PAIR_ENV.bat: read the arrows from MT5 (the demo terminal, read only) and send them to the app once.
    python -m mt5_ea.live.pair_env [--pairs EURUSD,USDJPY] [--timeout 60] [--no-send]"""
    import argparse
    import os
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument('--pairs', default=''); ap.add_argument('--timeout', type=float, default=60); ap.add_argument('--no-send', action='store_true')
    a = ap.parse_args(argv)
    from mt5_ea.live import gas
    from mt5_ea.live.broker import MT5Broker
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    path = os.getenv('EA_ALERT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or ''
    if path:
        os.environ['EA_MT5_PATH'] = path
    say = lambda x: print(x, flush=True)
    say('通貨ペアの向きを計算します（注文はしません）')
    t0 = time.time(); say(f'  MT5 につなぎます: {path or "（いつもの MT5）"}')
    b = MT5Broker(); say(f'  つながりました（{time.time() - t0:.0f}秒）')
    pairs = tuple(x.strip().upper() for x in a.pairs.split(',') if x.strip()) or PAIRS
    stalled = None
    try:
        rows = scan(b, pairs, log=say, timeout=a.timeout)
    except Stalled as ex:
        rows, stalled = ex.rows, ex
        say(f'\n止まりました: {ex}。ここまでの {len(rows)} ペアだけ送ります。')
    if a.no_send:
        say('（--no-send: 送りません）')
    elif rows:
        res = gas.call('eaPairEnv', {'pairs': rows}, timeout=90)
        if not res or res.get('success') is False:
            say('送れませんでした: ' + str((res or {}).get('error')))
            os._exit(1)
        say(f"\n{len(rows)} ペアをアプリに送りました（自動の向きが変わって書き換えた所: {res.get('changed', 0)}）")
    if stalled:
        os._exit(2)                                     # the stuck MT5 call cannot be cancelled: leave without waiting for it


if __name__ == '__main__':
    main()
