"""Evaluate the zone counter-move EAs (zone_ea Z_*, zone_lt ZL_*) on all instruments, XM costs.
(1) per instrument: settings passing the first half (PF >= 1.15, n >= 40) -> how many stay PF > 1 in the second half
(2) by design choice (trigger, stop, exit, zone TF) pooled over instruments: halves
(3) MA context (ZL only): H1 / H4 SMA75 slope in the bounce direction, MA inside the zone"""
import glob, os, sys, numpy as np, pandas as pd, new_summary as N
S = N.S; pf = N.pf
OLD = {'EURUSD': ('/home/user/trade-app/research/dow_strategy/results/zone', 0.0), 'USDJPY': (None, 0.3e-4), 'EURJPY': (None, 0.8e-4),
       'GBPUSD': (None, 0.4e-4), 'XAUUSD': (None, 1.3e-4), 'BTCUSD': (None, 6.8e-4)}
SPLIT = dict(N.SPLIT, BTCUSD=((2017, 2021), (2022, 2026)))
def load(sym, f):
    if sym in N.COST: return N.load(sym, f.split('/results/')[1])
    d = pd.read_csv(f)
    if not len(d): return None
    extra = OLD[sym][1]; R = d.R - extra / d.risk
    (a0, a1), (b0, b1) = SPLIT.get(sym, ((2005, 2015), (2016, 2026)))
    x = pd.DataFrame(dict(tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), R=R, side=d.side, risk=d.risk)); y = x.tt.dt.year
    for c in ('ma1', 'ma4', 'conf', 'tag'):
        if c in d: x[c] = d[c]
    x = x[(y >= a0) & (y <= b1)].copy(); x['half'] = np.where(x.tt.dt.year <= a1, 1, 2); return x
rows = []; ALL = []
for sym in ['EURUSD', 'USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD'] + list(N.COST):
    d = OLD.get(sym, (None,))[0] or f'{S}/ws_{sym}/research/dow_strategy/results/zone'
    for f in sorted(glob.glob(f'{d}/Z*.csv')):
        if os.path.basename(f).startswith('Z5'): continue
        x = load(sym, f)
        if x is None or not len(x): continue
        for c in ('ma1', 'ma4', 'conf', 'tag'):
            if c not in x:
                dd = pd.read_csv(f)
                if c in dd: x[c] = dd[c].to_numpy()[-len(x):]
        cfg = os.path.basename(f)[:-4]; a = x[x.half == 1].R; b = x[x.half == 2].R
        rows.append(dict(sym=sym, cfg=cfg, n1=len(a), R1=a.sum(), PF1=pf(a), n2=len(b), R2=b.sum(), PF2=pf(b)))
        x['sym'] = sym; x['cfg'] = cfg; ALL.append(x)
D = pd.DataFrame(rows); A = pd.concat(ALL, ignore_index=True)
D.to_csv(f'{S}/feat/zone_eval.csv', index=False); A.to_pickle(f'{S}/feat/zone_trades.pkl')
print('### (1) 銘柄ごと：前半で合格した設定 → 後半')
for sym, g in D.groupby('sym', sort=False):
    sel = g[(g.PF1 >= 1.15) & (g.n1 >= 40)]; b = sel.sort_values('PF1', ascending=False).head(1)
    print(f'{sym}: {len(g)} 設定、合格 {len(sel)}、後半黒字 {(sel.PF2 > 1).sum()}、前後半PF相関 {np.corrcoef(g.PF1, g.PF2)[0,1]:+.2f}' +
          (f' | 前半最良 {b.cfg.iat[0]} {b.R1.iat[0]:+.0f}R PF{b.PF1.iat[0]:.2f}({b.n1.iat[0]}) → {b.R2.iat[0]:+.0f}R PF{b.PF2.iat[0]:.2f}({b.n2.iat[0]})' if len(b) else ''))
print('\n### (2) 作りの違い（全銘柄の平均R、前半／後半）')
A['family'] = A.cfg.str[:2]; p = A.cfg.str.split('_')
A['ztf'] = p.str[1]
A['trig'] = np.where(A.family == 'ZL', p.str[2], p.str[2])
A['stop'] = np.where(A.family == 'ZL', p.str[3], 'zone' + p.str[3].fillna(''))
A['exit'] = p.str[-1]
for c in ('ztf', 'trig', 'stop', 'exit'):
    print(f'-- {c}'); print(A.groupby([c, 'half']).R.agg(['count', 'mean']).unstack('half').round(3).to_string())
Z = A[A.family == 'ZL']
if len(Z):
    print('\n### (3) MA（ZL のみ、平均R 前半／後半）')
    for c in ('ma1', 'ma4', 'conf'):
        print(f'-- {c}'); print(Z.groupby([c, 'half']).R.agg(['count', 'mean']).unstack('half').round(3).to_string())
    print('-- tag（H4 トレンドに沿った跳ね返り with / 逆 against）'); print(Z.groupby([Z.tag.str[3:], 'half']).R.mean().unstack('half').round(3).to_string())
