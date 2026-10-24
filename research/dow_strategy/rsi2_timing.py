"""RSI(2) entry timing (user, 2026-10-24: the research enters at the D1 close, which live cannot hit exactly - can the entry be
done better?). Adopted rule M_200_10_ma5_st: close > SMA200 and RSI(2) < 10 -> buy; exit at a close above SMA5; stop 2.5 ATR.
Variants (all with the same stop width 2.5 x ATR(D1, 14) and R = move / that width - 2 x cost / width):
  close   : research (signal and fill at the D1 close)
  preN    : signal from the price N minutes before the session's last bar closes (today's close replaced by that price in
            RSI / SMA), fill at that price; exits judged the same way at N minutes before the close
  open    : signal at the close, fill at the next day's open
  limK    : signal at the close, buy limit K x ATR below the close during the next day (filled at the limit, else no trade)
Halves: 2017-21 / 2022-26 (index split). Run from the scratchpad workspaces' M15 (log prices)."""
import numpy as np, pandas as pd

S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
COST = 1.2e-4


def rsi_last(cl):
    d = np.diff(cl); up = pd.Series(np.clip(d, 0, None)).ewm(alpha=0.5).mean().iat[-1]; dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=0.5).mean().iat[-1]
    return 100 - 100 / (1 + up / dn) if dn > 0 else 100.0


def daily(sym, pre):
    m = pd.read_csv(f'{S}/ws_{sym}/M15_broker.csv', parse_dates=['time'])
    m = m[m.time >= '2016-01-01']; m['d'] = m.time.dt.normalize()
    g = m.groupby('d')
    D = pd.DataFrame(dict(o=g.open.first(), h=g.high.max(), l=g.low.min(), c=g.close.last()))
    D = D[D.index.dayofweek < 5]
    for n in pre:          # price at the close of the bar ending n minutes before the last bar's close
        def px(x, n=n):
            cut = x.time.max() + pd.Timedelta(minutes=15) - pd.Timedelta(minutes=n)
            y = x[x.time + pd.Timedelta(minutes=15) <= cut]
            return y.close.iat[-1] if len(y) else np.nan
        D[f'p{n}'] = g.apply(px).reindex(D.index)
    pc = D.c.shift(); D['atr'] = np.maximum(D.h - D.l, np.maximum((D.h - pc).abs(), (D.l - pc).abs())).rolling(14).mean()
    return D


def simulate(D, mode, k=0.0):
    c = D.c.to_numpy(); n = len(D); out = []
    pcol = mode[3:] if mode.startswith('pre') else None
    p = D[f'p{pcol}'].to_numpy() if pcol else c
    atr = D.atr.to_numpy()

    def ind(i, last):                           # RSI / SMA200 / SMA5 with today's close replaced by `last`
        cl = np.r_[c[max(0, i - 60):i], last]
        s200 = (c[i - 199:i].sum() + last) / 200 if i >= 199 else np.nan
        s5 = (c[i - 4:i].sum() + last) / 5
        return rsi_last(cl), s200, s5
    i = 220
    while i < n - 1:
        last = p[i]
        if not np.isfinite(last) or not np.isfinite(atr[i - 1]):
            i += 1; continue
        r2, s200, _ = ind(i, last)
        if not (last > s200 and r2 < 10):
            i += 1; continue
        risk = 2.5 * (atr[i] if mode in ('close', 'open') or mode.startswith('lim') else atr[i - 1])
        if mode == 'close' or mode.startswith('pre'):
            en, j0 = last, i + 1
        elif mode == 'open':
            en, j0 = D.o.iat[i + 1], i + 1
        else:                                   # limit next day
            lim = c[i] - k * atr[i]
            if D.l.iat[i + 1] > lim:
                i += 1; continue
            en = min(lim, D.o.iat[i + 1]); j0 = i + 1
        stp = en - risk; xp = None; j = j0
        for j in range(j0, min(i + 30, n)):
            if D.l.iat[j] <= stp and not (mode.startswith('lim') and j == j0 and D.o.iat[j] > en and False):
                xp = min(stp, D.o.iat[j]) if j > j0 or mode != 'open' else min(stp, D.o.iat[j]); break
            lastj = p[j] if pcol else c[j]
            if lastj > ind(j, lastj)[2]:
                xp = lastj; break
        if xp is None: xp = c[j]
        out.append(dict(t=D.index[i], R=(xp - en) / risk - 2 * COST / risk))
        i = j + 1
    return pd.DataFrame(out)


if __name__ == '__main__':
    rows = []
    for sym in ('US30', 'US500'):
        D = daily(sym, (30, 60))
        for mode, k in (('close', 0), ('pre30', 0), ('pre60', 0), ('open', 0), ('lim', 0.2), ('lim', 0.5)):
            t = simulate(D, mode, k); t = t[t.t >= '2017-01-01']; h = np.where(t.t.dt.year <= 2021, 1, 2)
            for half in (1, 2):
                r = t.R[h == half]; w = r > 0
                rows.append(dict(sym=sym, mode=mode + (f'{k}' if mode == 'lim' else ''), half=half, n=len(r), sumR=round(r.sum(), 1), avgR=round(r.mean(), 3),
                                 PF=round(r[w].sum() / max(1e-9, -r[~w].sum()), 2), win=round(w.mean(), 2)))
    R = pd.DataFrame(rows)
    pd.set_option('display.width', 200)
    print(R.pivot_table(index=['sym', 'mode'], columns='half', values=['n', 'sumR', 'avgR', 'PF']).to_string())
