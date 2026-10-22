"""'First pullback right after a sharp move is dangerous' (user, 2026-10-22). Post-hoc on trade lists.
spike = largest 12-bar move in the trade's direction within the 36 H1 bars before entry, in ATR(H1) units.
Compares results by spike bucket, and two fixes for spiky entries: skip, or take profit at +1R / +1.5R (if the trade's
max favourable excursion reached it before exit). Usage: python spike_check.py <pair_tag> <trades.csv>... (run in the pair's workspace)"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load
from env_recognition.ea_api import TF_LEN
from env_recognition.pivots import atr
h1 = load('H1', 'long').reset_index(drop=True)
C1 = (pd.to_datetime(h1.t) + TF_LEN['H1']).to_numpy(); c = h1.c.to_numpy(); A = np.asarray(atr(h1))
mv = (h1.c - h1.c.shift(12)).to_numpy() / A
M5 = pd.read_csv(__import__('os').environ['EA_M15_CACHE']); MT = pd.to_datetime(M5.time).to_numpy(); MH = M5.high.to_numpy(); ML = M5.low.to_numpy()
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
tag = sys.argv[1]
for f in sys.argv[2:]:
    d = pd.read_csv(f)
    if 'Rc' in d:
        t, R, xt = pd.to_datetime(d.time), d.Rc, pd.to_datetime(d.ExitTime)
    else:
        t, R, xt = pd.to_datetime(d.t), d.R, pd.to_datetime(d.exit_t)
    keep = t.dt.year >= 2005; d, t, R, xt = d[keep], t[keep], R[keep].to_numpy(), xt[keep]
    sp, mfe = [], []
    for ti, s, e, rk, x in zip(t, d.side, d.entry, d.risk, xt):
        i = np.searchsorted(C1, np.datetime64(ti), 'right') - 1
        sp.append(np.nanmax(s * mv[max(0, i - 36):i + 1]))
        a = MT.searchsorted(np.datetime64(ti)); b = max(a + 1, MT.searchsorted(np.datetime64(x)))
        mfe.append((MH[a:b].max() - e if s == 1 else e - ML[a:b].min()) / rk)
    sp, mfe = np.array(sp), np.array(mfe); y = t.dt.year.to_numpy(); h = np.where(y <= 2015, 0, 1)
    name = Path(f).stem
    out = [f'## {tag} {name}  全体 {len(R)}回 前半{R[h==0].sum():+.1f}R 後半{R[h==1].sum():+.1f}R']
    for lo, hi in ((-99, 4), (4, 6), (6, 8), (8, 99)):
        m = (sp >= lo) & (sp < hi)
        out.append(f'  急な動き {lo}〜{hi}ATR: {m.sum():4d}回 平均 前半{R[m&(h==0)].mean():+.2f}R 後半{R[m&(h==1)].mean():+.2f}R')
    for X in (6, 8):
        m = sp >= X
        for lab, alt in (('入らない', np.where(m, 0, R)), ('+1Rで利確', np.where(m & (mfe >= 1), 1 - 0.0, R)), ('+1.5Rで利確', np.where(m & (mfe >= 1.5), 1.5, R))):
            out.append(f'  {X}ATR以上なら{lab}: 前半 {alt[h==0].sum():+6.1f}R PF{pf(alt[h==0]):.2f} | 後半 {alt[h==1].sum():+6.1f}R PF{pf(alt[h==1]):.2f}')
    print('\n'.join(out), flush=True)
