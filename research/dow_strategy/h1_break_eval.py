"""Evaluate the H1 break block (h1_break_block.py) on all EA trades per instrument: trades entered in the old direction while
blocked (break -> until the old extreme is regained, max 72h). Blocking helps if the blocked trades lose in both halves."""
import glob, numpy as np, pandas as pd, new_summary as N
S = N.S
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl')[['key', 'pair', 'tt', 'side', 'R', 'half']]
Q = pd.read_pickle(f'{S}/feat/q_best.pkl'); Q = Q[Q.pair.isin(['XAUUSD', 'USDJPY'])].assign(key=lambda d: 'Q@' + d.pair, half=lambda d: np.where(d.tt.dt.year <= 2015, 1, 2))
rows = [T, Q[['key', 'pair', 'tt', 'side', 'R', 'half']]]
for sym in ('XAGUSD', 'US30', 'US500', 'JP225', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY', 'OIL'):
    for ea, f in N.CORE:
        x = N.load(sym, f)
        if x is not None: rows.append(x.assign(key=f'{ea}@{sym}', pair=sym)[['key', 'pair', 'tt', 'side', 'R', 'half']])
    for ea, f in (('Q', 'q/Q_0.8_24_any_dow_ref_h4.csv'), ('Q', 'q/Q_1.0_24_ma_dow_ref_h1.csv')):
        x = N.load(sym, f) if sym in ('XAGUSD', 'US30') else None
        if x is not None and ((sym == 'XAGUSD') == ('0.8_24_any' in f)): rows.append(x.assign(key=f'Q@{sym}', pair=sym)[['key', 'pair', 'tt', 'side', 'R', 'half']])
X = pd.concat(rows, ignore_index=True); X['tt'] = pd.to_datetime(X.tt)
ADOPT = {'R@EURUSD', 'T2@EURUSD', 'L@EURUSD', 'A@EURUSD', 'C@EURUSD', 'C@USDJPY', 'J2@USDJPY', 'L2@XAUUSD', 'S@XAUUSD', 'Q@XAUUSD', 'Q@XAGUSD', 'T@US30', 'Q@US30', 'L@JP225'}
out = []
for f in sorted(glob.glob(f'{S}/feat/h1blk_*.pkl')):
    sym = f.split('h1blk_')[1][:-4]; D = pd.read_pickle(f); g = X[X.pair == sym]
    if not len(g): continue
    if 'outer_ok' not in D: continue
    D = D[D['mode'] == 'redraw'].copy()
    rg = ((D.until - D.t) < pd.Timedelta('71h'))
    print(sym, '元の高安を72h以内に更新：', {k: f'{v:.0%}' for k, v in rg.groupby(D.outer_ok.map({True: '内側だけ', False: '外側も'}).fillna('1本')).mean().items()}, D.outer_ok.map({True: '内側だけ', False: '外側も'}).fillna('1本').value_counts().to_dict())
    D['mode'] = D.outer_ok.map({True: '内側だけ割れ', False: '外側も割れ'}).fillna('線が1本')
    for mode, b in D.groupby('mode'):
        blk = np.zeros(len(g), bool)
        for sd in (1, -1):
            bb = b[b.side == sd].sort_values('t'); m = (g.side == sd).to_numpy(); tt = g.tt.to_numpy()[m]
            j = np.searchsorted(bb.t.to_numpy(), tt, 'right') - 1
            ok = (j >= 0) & (tt < bb.until.to_numpy()[np.maximum(j, 0)])
            blk[np.nonzero(m)[0][ok]] = True
        for grp, msk in (('全EA', np.ones(len(g), bool)), ('採用', g.key.isin(ADOPT).to_numpy())):
            if not msk.any(): continue
            for h in (1, 2):
                mm = msk & (g.half == h).to_numpy()
                out.append(dict(sym=sym, mode=mode, grp=grp, half=h, n=int((blk & mm).sum()), R=g.R[blk & mm].sum(), mean=g.R[blk & mm].mean(), rest=g.R[~blk & mm].mean()))
R = pd.DataFrame(out)
pd.set_option('display.width', 220)
t = R.pivot_table(index=['grp', 'mode', 'sym'], columns='half', values=['n', 'R', 'mean', 'rest']).round(2)
print(t.to_string())
w = R.pivot_table(index=['grp', 'mode', 'sym'], columns='half', values='R')
print('\n止めたトレードが前後半ともマイナス（＝止めると得）:'); print(w[(w[1] < 0) & (w[2] < 0)].round(1).to_string())
R.to_pickle(f'{S}/feat/h1blk_eval.pkl')
