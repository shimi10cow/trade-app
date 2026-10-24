"""Portfolio with the ensembles (feat/ens.pkl) on top of combo ③/④ (combo_stable.py). Same-risk bootstrap."""
import pandas as pd, pfx, combo_stable as CS
S = CS.S; E = pd.read_pickle(f'{S}/feat/ens.pkl')[['R', 'tt', 'et', 'key', 'pair', 'half']]
POOL = pd.concat([CS.POOL, E[CS.cols]], ignore_index=True); CS.POOL = POOL
B = pfx.BASE9T2 + ['Q@XAUUSD']
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
rule = [k for k, g in E.groupby('key') if pf(g[g.half == 1].R) >= 1.2]   # first-half-only rule
P = {'③ 基準（今の9本＋金Q半分＋銀Q）': B + ['Q@XAGUSD'],
     '③e 銀Qを全設定の平均に': B + ['Qe@XAGUSD'],
     '④ ③＋US30 T・Q': B + ['Q@XAGUSD', 'T@US30', 'Q@US30'],
     '④e ③e＋US30 RT平均': B + ['Qe@XAGUSD', 'RTe@US30'],
     '⑧ ④e＋AUDJPY Q平均・CADJPY PB2平均': B + ['Qe@XAGUSD', 'RTe@US30', 'Qe@AUDJPY', 'PB2e@CADJPY'],
     '⑨ ⑧＋GBPJPY L平均・AUDJPY A平均・CHFJPY C・銀S平均': B + ['Qe@XAGUSD', 'RTe@US30', 'Qe@AUDJPY', 'PB2e@CADJPY', 'Le@GBPJPY', 'Ae@AUDJPY', 'C@CHFJPY', 'Se@XAGUSD'],
     f'参考 前半PF1.2以上の平均を全部（{len(rule)}本、後半を見ずに決めた）': B + ['Q@XAGUSD'] + rule}
for lab, keys in P.items():
    X = CS.mk(keys); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
    print(f'\n### {lab}（{len(keys)}本）', flush=True)
    pfx.ev(X, keys, label='  ')
    c, dd, y, n = CS.fixed(X)
    print(f'  1回0.5%固定：年利 {c:.1%}  最大DD {dd:.1%}  最悪年 {y.min():.1%}  年 {n:.0f} 回', flush=True)
