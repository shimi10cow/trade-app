"""Check 5 (2026-10-24): are the long-adopted EAs robust to their neighbouring settings? For each family of saved
setting variants: number of variants, share with both halves positive, median PF by half, and where the adopted setting
ranks (second-half R percentile among the variants). Costs: the saved R (FX 1.2 pip; gold / silver / indices / BTC
re-costed by new_summary.load where available)."""
import glob, os, numpy as np, pandas as pd, new_summary as N
S = N.S; RES = '/home/user/trade-app/research/dow_strategy/results'
WS = lambda s: f'{S}/ws_{s}/research/dow_strategy/results'
FAM = [('R@EURUSD', 'EURUSD', RES, 'regime2_R*.csv', 'regime2_R2c.csv'),
       ('T2@EURUSD', 'EURUSD', RES, 'regime2_T*.csv', 'regime2_T1t_axis.csv'),
       ('L@EURUSD', 'EURUSD', RES, 'tl_*.csv', 'tl_N2.csv'),
       ('A@EURUSD', 'EURUSD', RES, 'retest_*.csv', 'retest_N1.csv'),
       ('C@EURUSD', 'EURUSD', RES, 'step2/cl15_*.csv', 'step2/cl15_md4tri.csv'),
       ('C@USDJPY', 'USDJPY', RES + '/usdjpy', 'step2/cl15_*.csv', 'step2/cl15_md4tri.csv'),
       ('J2@USDJPY', 'USDJPY', RES + '/usdjpy', 'turn/jt2_*.csv', 'turn/jt2_h1major+hour0_10.csv'),
       ('L2@XAUUSD', 'XAUUSD', WS('XAUUSD'), 'tl_*.csv', 'tl_N2_room1.csv'),
       ('S@XAUUSD', 'XAUUSD', WS('XAUUSD'), 'st2/S_*.csv', 'st2/S_ma_prov_buy_mt3_h1a1.csv'),
       ('Q@XAUUSD', 'XAUUSD', WS('XAUUSD'), 'q/Q_*.csv', None),
       ('Q@XAGUSD', 'XAGUSD', WS('XAGUSD'), 'q/Q_*.csv', 'q/Q_0.8_24_any_dow_ref_h4.csv'),
       ('T@US30', 'US30', WS('US30'), 'regime2_T*.csv', 'regime2_T1t.csv'),
       ('Q@US30', 'US30', WS('US30'), 'q/Q_*.csv', 'q/Q_1.0_24_ma_dow_ref_h1.csv'),
       ('M@US500', 'US500', WS('US500'), 'rsi2/M_*.csv', 'rsi2/M_200_10_ma5_st.csv'),
       ('M@US30', 'US30', WS('US30'), 'rsi2/M_*.csv', 'rsi2/M_200_10_ma5_st.csv'),
       ('S@BTCUSD', 'BTCUSD', WS('BTCUSD'), 'st2/S_*buy*.csv', 'st2/S_ma_ma_buy_mt3_h1a2.csv')]


def load(sym, d, f):
    rel = os.path.relpath(f, d)
    if sym in N.COST and not d.startswith(RES): return N.load(sym, rel)
    x = pd.read_csv(f)
    if not len(x) or ('R' not in x and 'Rc' not in x): return None
    if 'Rc' in x: x = pd.DataFrame(dict(tt=pd.to_datetime(x.time), R=x.Rc))
    else: x = pd.DataFrame(dict(tt=pd.to_datetime(x.t), R=x.R))
    if sym == 'XAUUSD': x['R'] = x.R - 1.3e-4 / pd.read_csv(f).risk.to_numpy()
    x = x[x.tt.dt.year >= 2005].copy(); x['half'] = np.where(x.tt.dt.year <= 2015, 1, 2); return x


rows = []
for key, sym, d, pat, adopt in FAM:
    res = []
    for f in sorted(glob.glob(f'{d}/{pat}')):
        try: x = load(sym, d, f)
        except Exception: x = None
        if x is None or len(x) < 30: continue
        a, b = x[x.half == 1].R, x[x.half == 2].R
        if len(a) < 10 or len(b) < 10: continue
        res.append(dict(f=os.path.relpath(f, d), R1=a.sum(), R2=b.sum(), PF1=N.pf(a), PF2=N.pf(b)))
    R = pd.DataFrame(res)
    if not len(R): print(key, 'no variants'); continue
    ad = R[R.f == adopt] if adopt else R.sort_values('PF1', ascending=False).head(1)
    rank = (R.R2 < ad.R2.iat[0]).mean() if len(ad) else np.nan
    rows.append(dict(EA=key, 設定数=len(R), 前後半とも黒字=f'{((R.R1 > 0) & (R.R2 > 0)).mean():.0%}', PF中央_前半=round(R.PF1.median(), 2), PF中央_後半=round(R.PF2.median(), 2),
                     採用の後半R=round(ad.R2.iat[0], 1) if len(ad) else np.nan, 採用の順位=f'上位{1 - rank:.0%}' if np.isfinite(rank) else '', 後半の中央R=round(R.R2.median(), 1)))
pd.set_option('display.width', 220)
print(pd.DataFrame(rows).to_string(index=False))
