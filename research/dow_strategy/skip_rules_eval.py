"""Feedback-derived skip rules on every EA x instrument (2026-10-22). Uses entry_features.py output.
Rules (fixed from the user's notes before looking at results): ext5 = H4 close >= 5 ATR(H4) beyond H4 SMA75 in the trade
direction; h1 = H1 provisional Dow against; m15 = M15 provisional Dow against; h4 = H4 provisional Dow against;
range = H4 range score >= 0.75 (not applied to R, which trades ranges).
For each EA: total R / PF in each half with and without the rule. Costs: gold 0.025%, BTC 0.08% (files carry 1.2 pip)."""
import sys, numpy as np, pandas as pd
S = sys.argv[1]
SPLIT = {'BTCUSD': ((2017, 2021), (2022, 2026))}
COST = {'XAUUSD': 2.5, 'BTCUSD': 8.0}
RULES = {'ext5': lambda d: d.h4_d75 >= 5, 'h1': lambda d: d.h1_prov_against == 1, 'm15': lambda d: d.m15_prov_against == 1,
         'h4': lambda d: d.h4_prov_against == 1, 'range': lambda d: (d.rs >= 0.75) & (d.ea != 'R')}
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
out = []
for sym in ('EURUSD', 'USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD'):
    D = pd.read_csv(f'{S}/feat/{sym}.csv', parse_dates=['t']); h1, h2 = SPLIT.get(sym, ((2005, 2015), (2016, 2026)))
    D = D[D.year >= h1[0]].copy(); D['R'] = D.R - (COST.get(sym, 1.2) - 1.2) * 1e-4 / D.risk
    D['half'] = np.where(D.year <= h1[1], 1, 2)
    for ea, g in D.groupby('ea'):
        base = {h: g[g.half == h].R for h in (1, 2)}
        row = dict(sym=sym, ea=ea, n=len(g), a=base[1].sum(), pa=pf(base[1]), b=base[2].sum(), pb=pf(base[2]))
        for k, f in RULES.items():
            m = f(g).to_numpy()
            for h in (1, 2):
                keep = g[(g.half == h).to_numpy() & ~m].R
                row[f'{k}_{h}'] = keep.sum() - base[h].sum(); row[f'{k}_pf{h}'] = pf(keep)
            row[f'{k}_cut'] = m.mean()
        out.append(row)
T = pd.DataFrame(out); T.to_csv(f'{S}/feat/skip_rules_eval.csv', index=False)
pd.set_option('display.width', 250)
print('合計Rの変化（前半/後半）と、条件で外れるトレードの割合。プラス＝外した方が良い')
for k in RULES:
    T[k] = [f"{a:+.0f}/{b:+.0f} ({c:.0%})" for a, b, c in zip(T[f'{k}_1'], T[f'{k}_2'], T[f'{k}_cut'])]
print(T[['sym', 'ea', 'n', 'a', 'b'] + list(RULES)].round(1).to_string(index=False))
print('\n前後半とも合計Rが増えたEAの数 / 全体')
for k in RULES:
    ok = ((T[f'{k}_1'] > 0) & (T[f'{k}_2'] > 0)).sum(); bad = ((T[f'{k}_1'] < 0) & (T[f'{k}_2'] < 0)).sum()
    print(f'{k}: 両方プラス {ok} / 両方マイナス {bad} / 全 {len(T)}  合計Rの変化 前半 {T[k + "_1"].sum():+.0f} 後半 {T[k + "_2"].sum():+.0f}')
