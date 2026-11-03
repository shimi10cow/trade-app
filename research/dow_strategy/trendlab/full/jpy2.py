import sys, pickle, bisect, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
X = pd.read_pickle('full/jpy.pkl')          # USDJPY trades with sdv (daily side strength)
DS = pd.read_pickle('regime/dow_states.pkl')['USDJPY']
F = pickle.load(open('live_frames_USDJPY.pkl', 'rb'))
h1 = F.h1.copy(); h1['t'] = pd.to_datetime(h1.t)
d1 = h1.set_index('t').resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna(); d1 = d1[d1.index.dayofweek < 5]
pc = d1.c.shift(); tr = np.maximum(d1.h - d1.l, np.maximum((d1.h - pc).abs(), (d1.l - pc).abs())); atr = tr.rolling(14).mean()
d1['vol'] = atr / atr.rolling(250, min_periods=100).median(); d1['end'] = d1.index + pd.Timedelta('1D')
d1['ret20'] = (d1.c - d1.c.shift(20)) / atr                     # 20-day move in ATR
C4 = list(F.C4); P4 = [b[0] for b in F.R4['prov_bars']]; M4 = [b[0] for b in F.R4['bars']]
SG = {'up': 1, 'down': -1}
def at(df, t, col): k = df.index.searchsorted(t, side='right') - 1; return df[col].iloc[k] if k >= 0 else np.nan
rows = []
for r in X.itertuples():
    t = pd.Timestamp(r.t); s = r.side
    k = DS.index.searchsorted(t, side='right') - 1; st = DS.iloc[k]
    kd = d1.end.searchsorted(t, side='right') - 1; k4 = bisect.bisect_right(C4, t) - 1
    rows.append(dict(WM=s * st.WM, WP=s * st.WP, DM=s * st.DM, DP=s * st.DP, W_in=bool(st.W_in), D_in=bool(st.D_in),
                     vol=d1.vol.iloc[kd], ret20=s * d1.ret20.iloc[kd], H4M=s * SG.get(M4[k4], 0), H4P=s * SG.get(P4[k4], 0)))
X = pd.concat([X.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
X.to_pickle('full/jpy2.pkl')
pd.set_option('display.width', 250)
for k in ('J2@USDJPY', 'C@USDJPY'):
    x = X[X.key == k].copy()
    bad = x.t.dt.year.isin([2008, 2010, 2011, 2012, 2018, 2020, 2021, 2022, 2025]) if k == 'J2@USDJPY' else x.t.dt.year.isin(range(2011, 2020))
    print(f'\n===== {k}  n{len(x)} {x.R.mean():+.3f}   （{"負けた年" if k[0]=="J" else "2011〜19"} n{bad.sum()} {x[bad].R.mean():+.2f} / その他 {x[~bad].R.mean():+.2f}）')
    def show(col, bins=None):
        g = x.groupby(pd.cut(x[col], bins) if bins else x[col], observed=True)
        print(f'  {col:6s}: ' + ' | '.join(f'{iv}: n{len(v)} {v.R.mean():+.2f} ({v[v.t<"2016"].R.mean():+.2f}/{v[v.t>="2016"].R.mean():+.2f}) 弱い時期の割合 {bad[v.index].mean():.0%}' for iv, v in g))
    for c in ('WM', 'WP', 'DM', 'DP', 'W_in', 'D_in', 'H4M', 'H4P'): show(c)
    show('vol', [0, 0.8, 1.0, 1.2, 1.5, 9]); show('ret20', [-99, -2, 0, 2, 4, 99]); show('sdv', [-99, 0, 4, 8, 99])
