"""NFP rules on the adopted trades of gold / USDJPY / EURUSD (2026-10-23):
  close_all  : a position still open at the release is closed at the last M15 close before 08:30 NY
  close_with : only positions in the direction of the week's trend are closed (the reaction tends to go against it, 2016-)
  skip{h}    : no new entries in the h hours before a release (h = 12, 24, 48)
Trade paths from feat/tp_eval.pkl (entry / risk / side in the trade table's units)."""
import numpy as np, pandas as pd, nfp_study as NS, combo_stable as CS
S = NS.S
D = pd.read_pickle(f'{S}/feat/tp_eval.pkl'); D = D[D.pair.isin(['XAUUSD', 'USDJPY', 'EURUSD'])].copy()
D['tt'] = pd.to_datetime(D.tt); D['et'] = pd.to_datetime(D.et)
ADOPT = CS.P['④ ③＋US30（T・Q）']
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv', 'USDJPY': f'{S}/ws_USDJPY/M15_broker.csv', 'XAUUSD': f'{S}/ws_XAUUSD/M15_broker.csv'}
fns = (lambda v: v, lambda v: v / 100, lambda v: np.log(np.maximum(v, 1e-12)))
NF = NS.NFP
out = []
for pair, g in D.groupby('pair'):
    m = pd.read_csv(M15[pair], parse_dates=['time']).set_index('time'); T = m.index; cl = m.close.to_numpy(float)
    for key, h in g.groupby('key'):
        i0 = np.clip(T.searchsorted(h.tt[:200]), 0, len(T) - 1)
        fn = min(fns, key=lambda f: np.nanmedian(np.abs(f(cl[i0]) / h.entry.to_numpy()[:200] - 1)))
        C = fn(cl); h = h.copy()
        k = NF.searchsorted(h.tt); rel = NF[np.minimum(k, len(NF) - 1)]
        across = (rel > h.tt) & (rel < h.et)
        j = np.clip(T.searchsorted(rel) - 1, 0, len(T) - 1)                    # last bar before the release
        px = C[j]; wk0 = np.clip(T.searchsorted(rel.normalize() - pd.to_timedelta(rel.dayofweek, unit='D')), 0, len(T) - 1)
        wkdir = np.sign(C[j] - C[wk0])
        Rclose = h.side * (px - h.entry) / h.risk - h.cR
        h['R_close_all'] = np.where(across, Rclose, h.R)
        h['R_close_with'] = np.where(across & (wkdir == h.side), Rclose, h.R)
        for hh in (12, 24, 48):
            pre = ((rel - h.tt) <= pd.Timedelta(f'{hh}h')) & (rel > h.tt)
            h[f'R_skip{hh}'] = np.where(pre, np.nan, h.R)
        h['across'] = across; h['with'] = across & (wkdir == h.side); out.append(h)
X = pd.concat(out); X['half'] = np.where(X.tt.dt.year <= 2015, 1, 2); A = X[X.key.isin(ADOPT)]
cols = ['R', 'R_close_all', 'R_close_with', 'R_skip12', 'R_skip24', 'R_skip48']
print('### 採用中（ゴールド・ドル円・ユーロドルの分）合計R 前半/後半')
print(A.groupby('half')[cols].sum().round(1).T.to_string())
print('\n発表をまたいだ回数', int(A.across.sum()), ' うち週のトレンドと同じ向き', int(A['with'].sum()))
print('\n### EA ごと（後半 2016-26）合計R'); print(A[A.half == 2].groupby('key')[cols].sum().round(1).to_string())
print('\n### EA ごと（前半 2005-15）合計R'); print(A[A.half == 1].groupby('key')[cols].sum().round(1).to_string())
X.to_pickle(f'{S}/feat/nfp_rules.pkl')
