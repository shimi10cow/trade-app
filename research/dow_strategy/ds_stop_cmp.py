"""Right shoulder: stop above the LEFT shoulder vs above the RIGHT shoulder (user 2026-10-24), per instrument.
H1 version, pullback >= 4 ATR(H4). Mean R / PF / win rate by half, top-5 share, stop width (share of price) and the risk
at XM KIWAMI's minimum lot at today's price (JPY)."""
import pandas as pd, numpy as np
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/ds_eval.pkl'); A = A[(A.tf == 'H1') & (A.depth >= 4)]
PX = {'US30': 52000, 'US500': 7670, 'JP225': 62500, 'XAUUSD': 4135, 'XAGUSD': 56.9, 'USDJPY': 158.5, 'EURUSD': 1.116}
UNIT = {'EURUSD': 1000 * 158.5, 'USDJPY': 1000, 'XAUUSD': 158.5, 'XAGUSD': 50 * 158.5, 'US30': 0.1 * 158.5, 'US500': 0.1 * 158.5, 'JP225': 0.1}
RD = lambda s: '/home/user/trade-app/research/dow_strategy/results' if s == 'EURUSD' else f'{S}/ws_{s}/research/dow_strategy/results'
LOGP = {'XAUUSD', 'XAGUSD', 'US30', 'US500', 'JP225'}
def pf(r): return r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
rows = []
for sym in PX:
    for stop in ('left', 'shoulder'):
        d = pd.read_csv(f'{RD(sym)}/ds/DS_H1_{stop}_tp2.csv'); d = d[d.tag.str.split('|').str[2].astype(float) >= 4]
        w = d.risk if sym in LOGP else d.risk / d.entry
        jpy = (w * PX[sym] * UNIT[sym]).median()
        for ex in ('tp2', 'h1', 'neck'):
            for side in ('両方', '買い'):
                g = A[(A.sym == sym) & (A.stop == stop) & (A.ex == ex)]
                if side == '買い': g = g[g.side == 1]
                r1 = g[g.half == 1].R; r2 = g[g.half == 2].R
                rows.append(dict(sym=sym, side=side, ex=ex, stop={'left': '左肩', 'shoulder': '右肩'}[stop], n1=len(r1), m1=r1.mean(), PF1=pf(r1), n2=len(r2), m2=r2.mean(), PF2=pf(r2),
                                 win=(g.R > 0).mean(), top5=g.R.nlargest(5).sum() / g.R.sum() if g.R.sum() > 0 else np.nan,
                                 幅=f'{w.median():.2%}', 最小ロット円=round(jpy)))
D = pd.DataFrame(rows).round(2); D.to_csv(f'{S}/ds_stop_cmp.csv', index=False)
pd.set_option('display.width', 230)
for sym in PX:
    print(f'\n== {sym}'); print(D[D.sym == sym].drop(columns='sym').to_string(index=False))
