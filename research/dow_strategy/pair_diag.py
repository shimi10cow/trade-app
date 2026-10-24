"""Why does USDJPY earn less than EURUSD? (2026-10-21)
Part 1 market character (H4, 2005-2026): ATR in pips, ER200, share of time with an H4 major trend, how often an H4 trend
makes another breakout (continuation) before reversing, H4 trend leg length.
Part 2 per EA and pair: MFE reach (+1/+2/+3R), quick losers (MFE<0.3R), stop in ATR(H1) units, cost / risk, hold time.
Usage: python pair_diag.py  (reads both workspaces' caches)"""
import sys, pickle
from pathlib import Path
import numpy as np, pandas as pd
S = Path('/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad')
PAIRS = {'EUR': (S / 'dowruns_2005-01-01.pkl', S / 'EURUSD_M15_long_broker.csv', Path(__file__).parent / 'results'),
         'JPY': (S / 'jpy/cache/dowruns_2005-01-01.pkl', S / 'jpy/USDJPY_M15_long_broker.csv', Path(__file__).parent / 'results/usdjpy')}
F = {'R': 'regime2_R2c.csv', 'T': 'regime2_T1t.csv', 'L': 'tl_N2.csv', 'A': 'retest_N1.csv', 'C': 'step2/cl15_md4tri.csv'}
def atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().to_numpy()
print('== 相場の性格（H4、2005〜2026）')
MK = {}
for p, (pk, m15f, res) in PAIRS.items():
    R4, R1, R15 = pickle.load(open(pk, 'rb'))
    m = pd.read_csv(m15f, parse_dates=['time']); m = m[m.time >= '2004-12-01'].reset_index(drop=True)
    h4 = m.set_index('time').resample('4h').agg(dict(open='first', high='max', low='min', close='last')).dropna()
    h4 = h4[h4.index >= '2004-12-01']
    a = atr(h4.high.to_numpy(), h4.low.to_numpy(), h4.close.to_numpy())
    c = pd.Series(h4.close.to_numpy()); er = (c.diff(200).abs() / c.diff().abs().rolling(200).sum())
    bars = [b[0] for b in R4['bars']]
    tr_share = np.mean([b in ('up', 'down') for b in bars])
    ev = [e for e in R4['events'] if e.get('machine') == 'major' and e['action'] in ('BREAKOUT', 'REVERSAL')]
    # continuation: after each breakout or reversal, is the next event a BREAKOUT (trend continues) or a REVERSAL?
    nxt = [ev[i + 1]['action'] for i in range(len(ev) - 1)]
    cont = np.mean([x == 'BREAKOUT' for x in nxt])
    rev_idx = [e['idx'] for e in ev if e['action'] == 'REVERSAL']; legs = np.diff(rev_idx)
    # pullback depth inside H4 trends: retrace of each H4 swing vs previous swing (in ATR)
    print(f'  {p}: H4 ATR 中央 {np.nanmedian(a) / 1e-4:.0f}pips / ER200 中央 {er.median():.3f} / H4 トレンドが出ている時間 {tr_share:.0%} / '
          f'更新→次も更新（続く） {cont:.0%} / H4 転換から次の転換まで 中央 {np.median(legs):.0f}本')
print('\n== EAごとのトレードの中身')
print('| EA | 通貨 | 回数 | 勝率 | +1R到達 | +2R | +3R | すぐ負け(含み益<0.3R) | +1Rから負け | 損切り(H1 ATR倍) | コスト/損切り | 保有時間 中央 |')
for c_, f in F.items():
    for p, (pk, m15f, res) in PAIRS.items():
        m = pd.read_csv(m15f, parse_dates=['time']); T = m.time.to_numpy(); H = m.high.to_numpy(); L = m.low.to_numpy()
        h1 = m.set_index('time').resample('1h').agg(dict(high='max', low='min', close='last')).dropna(); A1 = atr(h1.high.to_numpy(), h1.low.to_numpy(), h1.close.to_numpy()); T1 = h1.index.to_numpy()
        d = pd.read_csv(res / f)
        if 'Rc' in d:
            t0 = pd.to_datetime(d.time) + pd.Timedelta(minutes=15); xt = pd.to_datetime(d.ExitTime); R = d.Rc
        else:
            t0 = pd.to_datetime(d.t); xt = pd.to_datetime(d.exit_t); R = d.R
        keep = t0.dt.year >= 2005; d = d[keep]; t0 = t0[keep]; xt = xt[keep]; R = R[keep]
        mfe = []; ra = []
        for x, a_, b_ in zip(d.itertuples(), t0, xt):
            i0 = T.searchsorted(np.datetime64(a_)); ie = max(i0 + 1, T.searchsorted(np.datetime64(b_)))
            mfe.append(x.side * ((H[i0:ie].max() if x.side == 1 else L[i0:ie].min()) - x.entry) / x.risk)
            k = T1.searchsorted(np.datetime64(a_)) - 1; ra.append(x.risk / A1[max(k, 0)])
        mfe = np.array(mfe); R = R.to_numpy(); w = R > 0
        hold = ((xt - t0).dt.total_seconds() / 3600).median()
        print(f'| {c_} | {p} | {len(R)} | {w.mean():.0%} | {np.mean(mfe >= 1):.0%} | {np.mean(mfe >= 2):.0%} | {np.mean(mfe >= 3):.0%} | {np.mean((mfe < 0.3) & ~w):.0%} | '
              f'{np.mean((mfe >= 1) & ~w):.0%} | {np.nanmedian(ra):.1f} | {np.median(1.2e-4 / d.risk.to_numpy()):.0%} | {hold:.0f}h |')
