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


def scan(b, pairs=PAIRS):
    """[{pair, M1, W1, D1, H4, H1}] for every pair this account has."""
    out = []
    for p in pairs:
        try:
            row = {'pair': p}
            for key, tf, n in TFS:
                d = rates(b, p, tf, n)
                row[key] = direction(d, key) if d is not None else ''
            if any(row[k] for k, _, _ in TFS):
                out.append(row)
        except Exception as ex:                         # symbol missing on this account, no history, ...
            logging.info('pair env %s: %s', p, ex)
    return out


def main():
    """PAIR_ENV.bat: read the arrows from MT5 (the demo terminal, read only) and send them to the app once."""
    import os
    from mt5_ea.live import gas
    from mt5_ea.live.broker import MT5Broker
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    path = os.getenv('EA_ALERT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or ''
    if path:
        os.environ['EA_MT5_PATH'] = path
    print('通貨ペアの向きを計算します（注文はしません）', flush=True)
    rows = scan(MT5Broker())
    for r in rows:
        print(f"  {r['pair']:7s} M1 {r['M1'] or '-'}  W1 {r['W1'] or '-'}  D1 {r['D1'] or '-'}  H4 {r['H4'] or '-'}  H1 {r['H1'] or '-'}", flush=True)
    res = gas.call('eaPairEnv', {'pairs': rows}, timeout=90)
    if not res or res.get('success') is False:
        raise SystemExit('送れませんでした: ' + str((res or {}).get('error')))
    print(f"\n{len(rows)} ペアをアプリに送りました（自動の向きが変わって書き換えた所: {res.get('changed', 0)}）", flush=True)


if __name__ == '__main__':
    main()
