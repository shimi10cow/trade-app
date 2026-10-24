"""Same-risk check (month-block bootstrap) of a short list decided before looking: the EA families that travel
(Q quiet-breakout, J3, PB2) and the gold-like silver Q. Uses feat/all_trades_new.pkl from port_new.py (XM costs)."""
import pandas as pd, pfx
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl'); A = pd.read_pickle(f'{S}/feat/all_trades_new.pkl')
qk = sorted(k for k in A.key.unique() if k.startswith('Q@'))
G = {'Q 銀だけ': ['Q@XAGUSD'],
     'Q 新銘柄すべて（前半で選んだ設定）': qk,
     'Q 円クロス4つ': [k for k in qk if k.endswith('JPY')],
     'J3 円クロス4つ': ['J3@GBPJPY', 'J3@AUDJPY', 'J3@CADJPY', 'J3@CHFJPY'],
     'PB2 新銘柄（前半で選べたもの）': sorted(k for k in A.key.unique() if k.startswith('PB2@')),
     'C 銀＋CHFJPY': ['C@XAGUSD', 'C@CHFJPY'],
     'T US30': ['T@US30'],
     'Q すべて＋J3 円クロス': qk + ['J3@GBPJPY', 'J3@AUDJPY', 'J3@CADJPY', 'J3@CHFJPY']}
pfx.ev(T, pfx.BASE9T2, label='基準 BASE9T2(XM)')
for lab, ks in G.items():
    ks = [k for k in ks if k in set(A.key)]
    pfx.ev(T, pfx.BASE9T2, A[A.key.isin(ks)], label=f'+ {lab}({len(ks)})')
