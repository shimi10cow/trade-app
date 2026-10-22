"""Double tops/bottoms the user rejected (EURUSD H4, 2006/2013/2019) vs the ones kept: shape features; and whether
A (retest EA) trades taken from such W necks do worse over 2005-2026."""
import json, glob, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
C = {}; W = {}
for f in sorted(glob.glob(f'{S}/stage_viewer/data/[12][0-9][0-9][0-9].json')):
    d = json.load(open(f))['H4']
    for c in d['candles']: C[c[0]] = c[1:5]
    for w in d['wev']: W[(w[0], w[5])] = w
t = np.array(sorted(C)); a = np.array([C[x] for x in t]); b = pd.DataFrame(a, columns=['o', 'h', 'l', 'c'], index=t)
pc = b.c.shift(); b['atr'] = np.maximum(b.h - b.l, np.maximum((b.h - pc).abs(), (b.l - pc).abs())).rolling(14).mean().bfill()
cl = b.c.values; T = b.index.values
def feat(w):
    te, act, A, B, Cc, ba = w; i = np.searchsorted(T, te); ib = np.searchsorted(T, ba); at = b.atr.values[i]
    er = lambda k, n: abs(cl[k] - cl[max(0, k - n)]) / max(1e-9, np.abs(np.diff(cl[max(0, k - n):k + 1])).sum())
    return dict(t=te, ba=ba, kind=act, depth=abs(A - B) / at, diff=abs(A - Cc) / at, span=i - ib, er_before=er(ib, 40), er_wide=er(i, 80))
F = pd.DataFrame([feat(w) for w in W.values()]); F['year'] = pd.to_datetime(F.t, unit='s').dt.year
J = pd.read_pickle(f'{S}/zj_eur3.pkl'); Jw = J[J.lab.str.contains('ダブル')]
ng = set(zip(Jw[Jw.v == 'ng'].anchor, Jw[Jw.v == 'ng'].act))
# zone ids are (B anchor, activation bar open time); W event t is the activation bar time
F['ng'] = [(r.ba, r.t) in ng for r in F.itertuples()]
yrs = F.year.isin([2006, 2013, 2019]); X = F[yrs]
print(f'2006/2013/2019 の H4 の W：{len(X)} 個、うち × {X.ng.sum()} 個（照合できたもの）／× の総数 {len(ng)}')
print(X.groupby('ng')[['depth', 'diff', 'span', 'er_before', 'er_wide']].median().round(2).to_string())
F.to_pickle(f'{S}/w_feat_eur.pkl')
# A trades from W necks: same side, within 72h after the W event, entry within 1 ATR of B
A = pd.read_csv('../results/retest_N1.csv', parse_dates=['t']); A = A[A.src == 'H4']
rows = []
for x in A.itertuples():
    tt = x.t.value // 10**9; c = F[(F.t <= tt) & (F.t >= tt - 72 * 3600)]
    for r in c.itertuples():
        w = W[(r.t, r.ba)]; s = 1 if w[1] == 'W_BOTTOM' else -1; at = b.atr.values[np.searchsorted(T, r.t)]
        if s == x.side and abs(x.entry - w[3]) <= at: rows.append(dict(tt=x.t, R=x.R, **{k: getattr(r, k) for k in ('depth', 'diff', 'span', 'er_before', 'er_wide', 'ng')})); break
M = pd.DataFrame(rows); M['half'] = np.where(M.tt.dt.year <= 2015, 1, 2)
print(f'\nA（H4）のうち W のネックからのトレード：{len(M)} 回（A の H4 全体 {len(A)} 回）、平均R 前半 {M[M.half==1].R.mean():+.2f}／後半 {M[M.half==2].R.mean():+.2f}')
for f in ('span', 'depth', 'diff', 'er_before', 'er_wide'):
    q = M[f].quantile([.33, .67]).to_numpy(); M['b'] = np.searchsorted(q, M[f])
    g = M.groupby(['b', 'half']).R.agg(['mean', 'size']).unstack('half')
    print(f'{f:10s} ' + ' | '.join(f"{['小','中','大'][k]}: {g.loc[k,('mean',1)]:+.2f}/{g.loc[k,('mean',2)]:+.2f}（{int(g.loc[k,('size',1)])}/{int(g.loc[k,('size',2)])}）" for k in g.index))
