"""EA-T late-trend exit test (post-hoc on the trade list, 2026-10-21).
If at entry the trade is 'late' (H4 close beyond H4 SMA75 by >= x ATR(H4), or pull number >= n), exit at the first H1 close
beyond H1 SMA75 against the trade, when that comes before the original exit. Otherwise keep the original exit.
Usage: python dow_strategy/t_late_exit.py <trades.csv> [cost_pips]"""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load
from env_recognition.ea_api import TF_LEN
from env_recognition.pivots import atr
tr = pd.read_csv(sys.argv[1], parse_dates=['time', 'ExitTime']); cost = float(sys.argv[2]) if len(sys.argv) > 2 else 1.2
tr = tr[tr.time.dt.year >= 2005].reset_index(drop=True)
h1 = load('H1', 'long').reset_index(drop=True); h4 = load('H4', 'long').reset_index(drop=True)
C1 = (pd.to_datetime(h1.t) + TF_LEN['H1']).to_numpy(); c1 = h1.c.to_numpy(); m75 = h1.c.rolling(75).mean().to_numpy()
C4 = (pd.to_datetime(h4.t) + TF_LEN['H4']).to_numpy(); c4 = h4.c.to_numpy(); A4 = np.asarray(atr(h4)); m4 = h4.c.rolling(75).mean().to_numpy()
rows = []
for x in tr.itertuples():
    s = x.side; te = np.datetime64(x.time + pd.Timedelta(minutes=15))
    k4 = np.searchsorted(C4, te, 'right') - 1; late = s * (c4[k4] - m4[k4]) / A4[k4]
    i0 = np.searchsorted(C1, te, 'right'); i1 = np.searchsorted(C1, np.datetime64(x.ExitTime), 'right')
    alt = None
    for i in range(i0, min(i1, len(c1))):
        if s * (c1[i] - m75[i]) < 0:
            alt = (c1[i] - x.entry) * s / x.risk - cost * 1e-4 / x.risk; break
    rows.append(dict(late=late, Rc=x.Rc, alt=x.Rc if alt is None else alt, year=x.time.year))
D = pd.DataFrame(rows)
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r < 0].sum())
print('元', f"前半 {D[D.year<=2015].Rc.sum():+.1f}R 後半 {D[D.year>=2016].Rc.sum():+.1f}R")
for x in (0, 1, 2, 3, 4, 99):
    r = np.where(D.late >= x, D.alt, D.Rc); a = r[D.year <= 2015]; b = r[D.year >= 2016]
    print(f'H4 SMA75から{x}ATR以上なら H1 SMA75割れで決済: 前半 {a.sum():+6.1f}R PF{pf(a):.2f} | 後半 {b.sum():+6.1f}R PF{pf(b):.2f} | 対象 {(D.late>=x).mean():.0%}')
