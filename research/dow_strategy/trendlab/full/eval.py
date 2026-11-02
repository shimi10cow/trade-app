"""Whole-portfolio review, evaluation (2026-11). Reads full/t_*.pkl.

1 filters from P on every EA: daily side, H1 MA75 slope on the side, no level bounce, MA20 distance > -0.9, impulse <= 6,
  H4 opening < 2.5, H4 slope < 0.35. A filter is 'adopted' for an EA only if the kept trades' average R is higher in BOTH halves,
  the total R loses at most 15%, and the EA's own max DD (R) does not get worse.
2 exit 'h1a1' (P's exit) per EA: adopted if the average R is higher in both halves and the top-5 share does not rise by > 15 pt.
3 P on US500 / JP225 / US30 / XAGUSD / BTCUSD: both halves, PF, top-5 share, effect on the whole.
Portfolio: 1% risk, half at DD 10%, calendar x1.5 (live sizing), gold S / Q weight 0.5, R@EURUSD off.
"""
import sys, glob, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app')
from mt5_ea.live.sizing import calendar_mult
TL = '/home/user/trendlab'
SPLIT = {'EURUSD': '2016', 'USDJPY': '2016', 'XAUUSD': '2016', 'XAGUSD': '2016', 'US30': '2020-07', 'US500': '2021-10', 'JP225': '2021-10', 'BTCUSD': '2022'}
HALF = {'S@XAUUSD': 0.5, 'Q@XAUUSD': 0.5}
D = pd.concat([pd.read_pickle(f) for f in glob.glob(f'{TL}/full/t_*.pkl')], ignore_index=True)
D['half'] = [1 if t < pd.Timestamp(SPLIT[s]) else 2 for s, t in zip(D.sym, D.t)]
days = {}
for s in D.sym.unique():
    mm = pd.read_pickle(f'{TL}/stoch/m15_{s}.pkl'); dd = pd.DatetimeIndex(mm.time.dt.normalize().unique())
    days[s] = pd.Series(1, index=dd).groupby([dd.year, dd.month]).cumsum()
def tdm(s, t):
    d = pd.Timestamp(t).normalize(); ser = days[s]; i = ser.index.searchsorted(d, side='right') - 1
    return int(ser.iloc[i]) if i >= 0 and ser.index[i].month == d.month and ser.index[i].year == d.year else 1
D['mult'] = [calendar_mult(s, sd, t, tdm(s, t)) for s, sd, t in zip(D.sym, D.side, D.t)]
D['w'] = D.key.map(HALF).fillna(1.0)
FILT = {'日足の向き': lambda x: x.dside == 1, 'H1MA75傾き': lambda x: x.h1sl > 0, '水平帯の反発なし': lambda x: x.band == 0,
        'MA20距離>-0.9': lambda x: x.m20d > -0.9, '伸び<=6ATR': lambda x: x.imp <= 6, 'H4開き<2.5': lambda x: x.op < 2.5, 'H4傾き<0.35': lambda x: x.sl4 < 0.35}


def ddR(r):
    e = np.cumsum(r); return (e - np.maximum.accumulate(np.r_[0, e])[1:]).min() if len(e) else 0.0


def port(X, risk=0.01, half=True, rcol='R', ecol='exit_t'):
    X = X.sort_values(ecol); eq = pk = 1.0; mdd = 0.0
    for r, k, w in zip(X[rcol], X.mult, X.w):
        eq *= 1 + risk * k * w * (0.5 if (half and eq < 0.9 * pk) else 1.0) * r; pk = max(pk, eq); mdd = min(mdd, eq / pk - 1)
    yrs = (pd.to_datetime(X[ecol]).max() - X.t.min()).days / 365.25; return eq ** (1 / yrs) - 1, mdd


live = sorted(k for k in D.key.unique() if not (k.startswith('P@') and k.split('@')[1] not in ('XAUUSD', 'EURUSD', 'USDJPY')))
base = D[D.key.isin(live) & (D.key != 'R@EURUSD')].copy()
c0, d0 = port(base); print(f'今の構成（R オフ）: {base.key.nunique()} 本 年利 {c0:+.1%} 最大DD {d0:.1%}\n')

# ---------- 1 filters
print('== 1. P の条件をほかの EA に（前半・後半とも平均 R が上がり、合計の減り 15% 以内、EA の DD が悪化しないものだけ）')
chosen = {}
rows = []
for k, g in base.groupby('key'):
    if k.startswith('P@'): continue
    b1, b2 = g[g.half == 1].R.mean(), g[g.half == 2].R.mean(); tot = g.R.sum(); dd = ddR(g.sort_values('t').R.to_numpy())
    for fn, f in FILT.items():
        m = f(g).fillna(False).to_numpy(); kp = g[m]
        if len(kp) < 20 or m.all(): continue
        a1, a2 = kp[kp.half == 1].R.mean(), kp[kp.half == 2].R.mean(); kt = kp.R.sum(); kd = ddR(kp.sort_values('t').R.to_numpy())
        ok = (a1 > b1 + 0.02) and (a2 > b2 + 0.02) and kt >= 0.85 * tot and kd >= dd
        rows.append(dict(EA=k, 条件=fn, 残り=f'{len(kp)}/{len(g)}', 前半=f'{b1:+.2f}→{a1:+.2f}', 後半=f'{b2:+.2f}→{a2:+.2f}', 合計=f'{tot:+.0f}→{kt:+.0f}', DD=f'{dd:.0f}→{kd:.0f}', 採用='◯' if ok else ''))
        if ok and (k not in chosen or kt > chosen[k][1]): chosen[k] = (fn, kt)
R1 = pd.DataFrame(rows); print(R1[R1.採用 == '◯'].to_string(index=False) if (R1.採用 == '◯').any() else '採用なし')
F1 = base.copy()
for k, (fn, _) in chosen.items():
    F1 = F1[~((F1.key == k) & ~FILT[fn](F1).fillna(False))]
c1, d1 = port(F1); print(f'→ 全体: 年利 {c0:+.1%}→{c1:+.1%}  最大DD {d0:.1%}→{d1:.1%}  回数 {len(base)}→{len(F1)}\n')

# ---------- 2 exits
print('== 2. 決済を「+1R から H1 の山谷で追う」に（前半・後半とも平均 R が上がり、上位 5 回の割合が 15pt 以上増えないものだけ）')
rows = []; ex_ok = []
for k, g in F1.groupby('key'):
    if k.startswith('P@') or g.R_h1.isna().all(): continue
    g = g.dropna(subset=['R_h1'])
    top = lambda r: np.sort(r)[::-1][:5].sum() / r.sum() if r.sum() > 0 else np.nan
    b1, b2, a1, a2 = g[g.half == 1].R.mean(), g[g.half == 2].R.mean(), g[g.half == 1].R_h1.mean(), g[g.half == 2].R_h1.mean()
    t0_, t1_ = top(g.R.to_numpy()), top(g.R_h1.to_numpy())
    ok = a1 > b1 + 0.02 and a2 > b2 + 0.02 and np.isfinite(t1_) and t1_ <= t0_ + 0.15
    rows.append(dict(EA=k, 前半=f'{b1:+.2f}→{a1:+.2f}', 後半=f'{b2:+.2f}→{a2:+.2f}', 合計=f'{g.R.sum():+.0f}→{g.R_h1.sum():+.0f}',
                     DD=f'{ddR(g.sort_values("t").R.to_numpy()):.0f}→{ddR(g.sort_values("t").R_h1.to_numpy()):.0f}', 上位5=f'{t0_:.0%}→{t1_:.0%}', 採用='◯' if ok else ''))
    if ok: ex_ok.append(k)
print(pd.DataFrame(rows).to_string(index=False))
F2 = F1.copy(); m = F2.key.isin(ex_ok) & F2.R_h1.notna()
F2.loc[m, 'R'] = F2.loc[m, 'R_h1']; F2.loc[m, 'exit_t'] = F2.loc[m, 'exit_h1']
c2, d2 = port(F2); print(f'→ 全体（1 の後に）: 年利 {c1:+.1%}→{c2:+.1%}  最大DD {d1:.1%}→{d2:.1%}\n')

# ---------- 3 P elsewhere
print('== 3. P をほかの銘柄に')
rows = []; p_ok = []
for k, g in D[D.key.str.startswith('P@') & ~D.key.isin(live)].groupby('key'):
    r = g.R.to_numpy(); yrs = (g.exit_t.max() - g.t.min()).days / 365.25
    a1, a2 = g[g.half == 1].R.mean(), g[g.half == 2].R.mean(); top = np.sort(r)[::-1][:5].sum() / r.sum() if r.sum() > 0 else np.nan
    ok = a1 > 0.1 and a2 > 0.1 and r[r > 0].sum() / -r[r < 0].sum() > 1.3 and len(r) >= 30
    rows.append(dict(EA=k, 回数=len(r), 年=round(len(r) / yrs, 1), 前半=round(a1, 2), 後半=round(a2, 2), 合計=round(r.sum(), 1), PF=round(r[r > 0].sum() / -r[r < 0].sum(), 2),
                     勝率=f'{(r > 0).mean():.0%}', 上位5=f'{top:.0%}', DD=round(ddR(g.sort_values("t").R.to_numpy()), 1), 採用='◯' if ok else ''))
    if ok: p_ok.append(k)
print(pd.DataFrame(rows).to_string(index=False))
F3 = pd.concat([F2, D[D.key.isin(p_ok)]], ignore_index=True)
c3, d3 = port(F3); print(f'→ 全体（1・2 の後に）: 年利 {c2:+.1%}→{c3:+.1%}  最大DD {d2:.1%}→{d3:.1%}\n')

print('== まとめ（1%・半分あり / 0.75% / 1.5% / 1% 半分なし）')
for lab, X in (('今', base), ('1 条件', F1), ('1+2 決済', F2), ('1+2+3 P 追加', F3)):
    s = [port(X, r, h) for r, h in ((0.01, True), (0.0075, True), (0.015, True), (0.01, False))]
    print(f'{lab:12s} 回数 {len(X)}  ' + '  '.join(f'{a:+.0%}/{b:.1%}' for a, b in s))
pd.to_pickle(dict(chosen=chosen, ex_ok=ex_ok, p_ok=p_ok), f'{TL}/full/choice.pkl')

print('\n== 1b. 候補を 1 つずつ全体に入れた時（1% と 1.5%、半分あり）')
rows = []
for _, x in R1[R1.採用 == '◯'].iterrows():
    k, fn = x.EA, x.条件; Y = base[~((base.key == k) & ~FILT[fn](base).fillna(False))]
    a = port(Y); b = port(Y, 0.015)
    rows.append(dict(EA=k, 条件=fn, 年利1=f'{a[0] - c0:+.1%}', DD1=f'{a[1] - d0:+.1%}', 比1=round(a[0] / -a[1] - c0 / -d0, 2),
                     年利15=f'{b[0] - port(base, 0.015)[0]:+.1%}', DD15=f'{b[1] - port(base, 0.015)[1]:+.1%}'))
print(pd.DataFrame(rows).to_string(index=False))
