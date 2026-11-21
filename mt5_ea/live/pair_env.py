"""Trend direction per pair and timeframe for the app's pair tab (2026-11-21, history limit 2026-11-22).

The same Dow engine the EAs use (env_recognition.dow_trend) on D1 / H4 / H1 made from the last 400 days of M15 bars:
  ↑  major trend up   and the provisional trend agrees
  ↓  major trend down and the provisional trend agrees
  →  no trend yet, or the provisional trend has already turned against the major one (turning)
2026-11-22: MT5 builds every timeframe from M1 history, so asking for 300 monthly / 1300 weekly bars made the terminal
download ~25 years of M1 per symbol (about 2 GB for 11 pairs, the PC's disk filled up). Now only the same 400 days of M15
the alerts window already reads (D1 over 1 year gave the same arrow as the long history in 38 of 38 checks on EURUSD).
2026-11-22: W1 too, from W1 bars of the last 3 years only (2.5 years already gave the long-history arrow in 139 of 139
EURUSD checks). M1 (monthly) stays the trader's own input: 10 years of history matched only 91 of 139 (needs 15+ years,
~7-8 GB of M1 history for 42 symbols). 2026-11-22: every pair the app has (Pairs sheet).
PAIR_ENV.bat (python -m mt5_ea.live.pair_env) sends them -> GAS eaPairEnv. Only reads prices; never orders."""
import logging

import pandas as pd

from mt5_ea.live import core  # noqa: F401  (puts research/ on sys.path)
from mt5_ea.live.core import resample

TF_LEN = {'D1': '1D', 'H4': '4h', 'H1': '1h'}
from env_recognition import dow_trend  # noqa: E402

DAYS = 400                              # never read older bars than this (the alerts window reads the same)
TFS = ('D1', 'H4', 'H1')
ALL_TFS = ('M1', 'W1', 'D1', 'H4', 'H1')
PAIRS = ('AUDCAD', 'AUDCHF', 'AUDNZD', 'AUDJPY', 'AUDUSD', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP',
         'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY',
         'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY')
ARROW = {'up': '↑', 'down': '↓'}
# app name -> names to try on the broker (the broker map in broker.py knows most; these are the extra ones)
ALIAS = {'NATGAS': ('NGAS',), 'XAUEUR': ('XAUEUR', 'GOLDEUR'), 'UK100': ('UK100',), 'EU50': ('EU50', 'EUSTX50'), 'BRENT': ('BRENT', 'UKOIL'),
         'US2000': ('US2000', 'US2000Cash')}


def app_pairs(gas):
    """The pairs the app has now (Pairs sheet), from GAS; PAIRS when GAS cannot be reached."""
    try:
        r = gas.call('eaPairEnv', {'pairs': []}, timeout=60)
        xs = [str(x).strip().upper() for x in (r or {}).get('names') or [] if str(x).strip()]
        return tuple(xs) or PAIRS
    except Exception as ex:
        logging.warning('pair env: pair list from GAS: %s', ex)
        return PAIRS


def bars_any(b, p, days):
    """M15 bars under the app's name, or the first broker name in ALIAS that works."""
    err = None
    for n in ALIAS.get(p, (p,)):
        try:
            return b.bars(n, days)
        except Exception as ex:
            err = ex
    raise err


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


def arrows(m15):
    """{'D1','H4','H1'} arrows from closed M15 bars (t, o, h, l, c); a frame bar still forming is left out."""
    m = m15[['t', 'o', 'h', 'l', 'c']].copy(); m['t'] = pd.to_datetime(m.t)
    end = m.t.iat[-1] + pd.Timedelta(minutes=15); out = {}
    for tf in TFS:
        x = resample(m, tf)
        x = x[x.t + pd.Timedelta(TF_LEN[tf]) <= end]        # closed frame bars only (Friday's D1 counts on the weekend)
        out[tf] = direction(x, tf)
    return out


class Stalled(RuntimeError):
    """MT5 did not answer one request in time (the stuck call cannot be cancelled, so the scan stops there)."""


W1_DAYS = 3 * 365 + 7                   # weekly: never older than 3 years


def weekly_bars(b, p, now=None):
    """Closed W1 bars of the last 3 years (copy_rates_range with a start date: never a count, which pulled decades of M1)."""
    mt5 = b.mt5; err = None
    to = pd.Timestamp(now) if now is not None else pd.Timestamp.utcnow().tz_localize(None) + pd.Timedelta(days=1)
    for n in ALIAS.get(p, (p,)):
        try:
            r = mt5.copy_rates_range(b.name(n), mt5.TIMEFRAME_W1, (to - pd.Timedelta(days=W1_DAYS)).to_pydatetime(), to.to_pydatetime())
            if r is None or len(r) < 10:
                raise RuntimeError(f'{n}: no W1 history ({mt5.last_error()})')
            d = pd.DataFrame(r).rename(columns=dict(open='o', high='h', low='l', close='c'))
            d['t'] = pd.to_datetime(d.time, unit='s')
            return d[['t', 'o', 'h', 'l', 'c']]
        except Exception as ex:
            err = ex
    raise err


def weekly_arrow(w1, m15_end):
    """W1 arrow from closed weeks: a week counts once its bars are over (the Friday close counts on the weekend)."""
    w = w1[pd.to_datetime(w1.t) + pd.Timedelta(days=7) <= pd.Timestamp(m15_end) + pd.Timedelta(days=2)]
    return direction(w, 'W1')


def scan(b, pairs=PAIRS, log=None, timeout=None):
    """[{pair, W1, D1, H4, H1}] for every pair this account has.
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
        t0 = time.time(); row = {'pair': p}; tf = 'M15'
        try:
            m15 = call(bars_any, b, p, DAYS)
            row.update(arrows(m15))
            tf = 'W1'
            try:
                row['W1'] = weekly_arrow(call(weekly_bars, b, p), pd.to_datetime(m15.t).iat[-1] + pd.Timedelta(minutes=15))
            except cf.TimeoutError:
                raise
            except Exception as ex:                     # no weekly history: D1/H4/H1 still go
                row['W1'] = ''; logging.info('pair env %s W1: %s', p, ex)
            if any(row[k] for k in TFS + ('W1',)):
                out.append(row)
            if log:
                log(f"  {p:7s} W1 {row['W1'] or '-'}  D1 {row['D1'] or '-'}  H4 {row['H4'] or '-'}  H1 {row['H1'] or '-'}   ({time.time() - t0:.1f}秒)")
        except cf.TimeoutError:
            ex = Stalled(f'{p} の {tf} で MT5 が {timeout} 秒たっても返事をしない'); ex.rows, ex.where = out, (p, tf)
            raise ex
        except Exception as ex:                         # symbol missing on this account, no history, ...
            logging.info('pair env %s: %s', p, ex)
            if log:
                log(f'  {p:7s} とばした（{str(ex)[:80]}）')
    if pool:
        pool.shutdown(wait=False)
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
    pairs = tuple(x.strip().upper() for x in a.pairs.split(',') if x.strip()) or app_pairs(gas)
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
