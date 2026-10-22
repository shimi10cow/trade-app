"""Final combos with the new instruments (XM costs, same-risk bootstrap): gold S/Q half, + silver Q, + US30 T."""
import pandas as pd, pfx
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl'); A = pd.read_pickle(f'{S}/feat/all_trades_new.pkl')
Q = pd.read_pickle(f'{S}/feat/q_best.pkl'); Qg = Q[Q.pair == 'XAUUSD'].copy(); Qg['key'] = 'Q@XAUUSD'
B = T[T.key.isin(pfx.BASE9T2)].copy(); B.loc[B.key == 'S@XAUUSD', 'R'] *= 0.5
g = Qg.copy(); g['R'] *= 0.5
def X(*ks): return pd.concat([g] + [A[A.key == k] for k in ks], ignore_index=True)
qk = sorted(k for k in A.key.unique() if k.startswith('Q@'))
pfx.ev(T, pfx.BASE9T2, label='① 基準 BASE9T2(XM)')
pfx.ev(B, pfx.BASE9T2, X(), label='② ゴールド S/Q 半分ずつ')
pfx.ev(B, pfx.BASE9T2, X('Q@XAGUSD'), label='③ ②＋銀 Q')
pfx.ev(B, pfx.BASE9T2, X('Q@XAGUSD', 'T@US30'), label='④ ③＋US30 T')
pfx.ev(B, pfx.BASE9T2, X(*qk, 'T@US30'), label='⑤ ②＋新銘柄 Q すべて＋US30 T')
