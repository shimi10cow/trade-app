"""Does the 'time axis' of the correction matter, especially after a long H4 trend? (2026-10-22)"""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SPLIT = {'BTCUSD': ((2017, 2021), (2022, 2026))}; COST = {'XAUUSD': 2.5, 'BTCUSD': 8.0}
SYMS = ('EURUSD', 'USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD')
ALL = []
for sym in SYMS:
    D = pd.read_csv(f'{S}/feat/wave_{sym}.csv'); h1, h2 = SPLIT.get(sym, ((2005, 2015), (2016, 2026)))
    D = D[D.year >= h1[0]].copy(); D['R'] = D.R - (COST.get(sym, 1.2) - 1.2) * 1e-4 / D.risk
    D['half'] = np.where(D.year <= h1[1], 1, 2); D['sym'] = sym; ALL.append(D)
A = pd.concat(ALL, ignore_index=True)
A['ext'] = np.where(A.h4_major_push >= 3, 'H4が3回以上更新', np.where(A.h4_major_push >= 0, 'H4が0〜2回', 'H4と逆向き'))
A['tb'] = pd.cut(A.t_ratio, [0, 0.3, 0.7, 1.5, 1e9], labels=['短い(<0.3)', '0.3-0.7', '0.7-1.5', '長い(>1.5)'])
print('調整にかけた時間（推進の何倍か）別の平均R：全銘柄・全EA、前半/後半')
g = A.groupby(['ext', 'tb', 'half'], observed=True).R.agg(['mean', 'size']).unstack('half')
print(g.round(2).to_string())
print('\n銘柄ごと（H4が3回以上更新している時だけ）')
e = A[A.ext == 'H4が3回以上更新']
print(e.groupby(['sym', 'tb', 'half'], observed=True).R.mean().unstack('half').round(2).to_string())
A.to_pickle(f'{S}/feat/wave_all.pkl')
