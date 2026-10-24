"""Return move with a SHALLOW pullback (user 2026-10-21): price does not have to come all the way back to the broken level.
Same as retest EA A (N1: H4 turns, H1 MA, daily side, not stretched), but the 'touch' is the first M15 bar where the
pullback has retraced >= q of the move from the level L to the best price since the turn (q=1.0 ~ back to the level).
Entry on the next M15 provisional turn in the trade direction. Each trade is tagged 'shallow' if, at entry, price had NOT
yet come back within tol x ATR of L (= a trade the original A would not have taken at that point).
Reports by q, shallow vs full, and by JST entry hour."""
import os as _os; _ENTRY_BAR = _os.environ.get('EA_ENTRY_BAR') == '1'   # 1 = also check the stop on the entry bar (2026-10-24 fix, §93/§106)
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import retest_ea as RT  # noqa: E402
B = RT.B; M15T = RT.M15T; EC = RT.EC; TF_LEN = RT.TF_LEN
N1 = [c for c in RT.CFGS if c['name'].startswith('N1')][0]
TURN = {}
for e in B.R15['prov_events']:
    if e['action'] in ('REVERSAL', 'PROV_START'): TURN.setdefault(e['to'], []).append(e['idx'])
for d in TURN: TURN[d].sort()
def entries_for(q, cfg=N1):
    ent = {}
    for tf in cfg['tfs']:
        df, R, C, A = RT.FR[tf]
        for t, d, L, _ in RT.events(tf, cfg['kinds']):
            s = 1 if d == 'up' else -1; k = bisect.bisect_right(C, t) - 1; band = cfg['tol'] * A[k]
            i0 = M15T.searchsorted(t); i1 = M15T.searchsorted(t + pd.Timedelta(hours=cfg['win']))
            best = None; touch = None; lvl_touch = None
            for i in range(i0, min(i1, len(M15T))):
                if s * (B.c[i] - L) < -band: break
                best = (B.h[i] if best is None else max(best, B.h[i])) if s == 1 else (B.l[i] if best is None else min(best, B.l[i]))
                leg = s * (best - L)
                if lvl_touch is None and ((B.l[i] <= L + band) if s == 1 else (B.h[i] >= L - band)): lvl_touch = i
                if touch is None and leg > 0:
                    depth = s * (best - (B.l[i] if s == 1 else B.h[i])) / leg
                    if depth >= q or lvl_touch is not None: touch = i
                if touch is not None: break
            if touch is None: continue
            lst = TURN.get(d, []); j = bisect.bisect_left(lst, touch)
            if j < len(lst) and lst[j] < i1 + 96:
                kk = lst[j]
                # was the level reached (within band) by the entry bar?
                seg = B.l[i0:kk + 1] if s == 1 else B.h[i0:kk + 1]
                reached = (seg.min() <= L + band) if s == 1 else (seg.max() >= L - band)
                ent.setdefault(kk, []).append((d, L, tf, not reached))
    return ent
def simulate(ent, cfg=N1):
    trades, pos = [], []; n = len(M15T)
    for i in range(n):
        keep = []
        for p in pos:
            if p['k'] > i or (p['k'] == i and not _ENTRY_BAR): keep.append(p); continue
            s = p['side']
            if (B.l[i] <= p['sl']) if s == 1 else (B.h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = M15T[i]; trades.append(p); continue
            if not p['trail'] and s * ((B.h[i] if s == 1 else B.l[i]) - p['entry']) >= p['risk']: p['trail'] = True
            if p['trail']:
                j = bisect.bisect_right(B.H1PT, M15T[i] + TF_LEN['M15']) - 1
                while j >= 0 and B.H1P[j][1] != ('lo' if s == 1 else 'hi'): j -= 1
                if j >= 0:
                    v = B.H1P[j][2] - s * B.PIP
                    if (v < B.c[i]) if s == 1 else (v > B.c[i]): p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in ent or i + 1 >= n or M15T[i] < B.START: continue
        k1 = bisect.bisect_right(B.C1, M15T[i] + TF_LEN['M15']) - 1
        for d, L, tf, shallow in ent[i]:
            s = 1 if d == 'up' else -1
            if any(p['side'] == s for p in pos): continue
            if cfg.get('ma') and not (s * (B.h1.c.iloc[k1] - RT.S75[k1]) > 0 and s * (RT.S20[k1] - RT.S75[k1]) > 0): continue
            if not EC.env_ok(cfg, M15T[i] + TF_LEN['M15'], s): continue
            swing = B.R15['prov_bars'][i][1]
            if swing is None: continue
            entry = B.o[i + 1]; sl = swing - s * cfg['buf'] * B.A1[k1]
            if s * (entry - sl) < 10 * B.PIP: sl = entry - s * 10 * B.PIP
            pos.append(dict(k=i + 1, t=M15T[i + 1], side=s, entry=entry, sl=sl, risk=s * (entry - sl), trail=False, shallow=shallow))
    for p in pos: p['exit'] = B.c[-1]; p['exit_t'] = M15T[n - 1]; trades.append(p)
    tr = pd.DataFrame(trades); tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - B.COST / tr.risk
    return tr[tr.t.dt.year >= 2005]
def pf(r): w = r > 0; return r[w].sum() / max(1e-9, -r[~w].sum())
def line(lab, tr):
    y = tr.t.dt.year; r = tr.R
    print(f'{lab:26s} n={len(r):4d} {r.sum():+6.1f}R PF{pf(r):.2f} 勝率{(r > 0).mean():.0%} | 前半 {r[y <= 2015].sum():+.1f}R PF{pf(r[y <= 2015]):.2f} | 後半 {r[y >= 2016].sum():+.1f}R PF{pf(r[y >= 2016]):.2f}', flush=True)
if __name__ == '__main__':
    out = B.HERE / 'results' / 'retest_depth'; out.mkdir(exist_ok=True)
    for q in (1.01, 0.7, 0.5, 0.3):
        tr = simulate(entries_for(q)); tr.to_csv(out / f'q{q}.csv', index=False)
        line(f'戻り {"水平線まで" if q > 1 else f"{int(q * 100)}%以上"}', tr)
        if q < 1:
            line('   うち浅い戻り（線まで来ていない）', tr[tr.shallow]); line('   うち線まで戻った', tr[~tr.shallow])
            jst = pd.DatetimeIndex(tr.t).tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').tz_convert('Asia/Tokyo').hour
            g = tr.assign(b=(np.asarray(jst) // 6) * 6).groupby('b').R.agg(['size', 'sum', pf]).round(2)
            print('   日本時間(6時間ごと):', g.to_dict('index'))
