"""EA #2, round 2: add the user's own entry evidence (2026-10-19 voice notes):
  - a correction trendline (against the trade) broke just before the entry  (M15 or H1)
  - H1 SMA20 vs SMA75 in the trade direction and price on the right side of SMA75 (75 acting as support)
Reuses dow_turn_ea (same periods, stop, exit, model-trade recall). Usage: EA_M15_CACHE=<csv> python dow_strategy/dow_turn_ea2.py
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402  (runs the shared prep)
from env_recognition import lines  # noqa: E402

print('lines...', flush=True)
L15 = lines.run(B.m15, 'M15', B.R15); L1 = lines.run(B.h1, 'H1', B.R1)
print('lines done', flush=True)


def breaks(L):
    dirs = {x['key']: x['direction'] for x in L['lines']}
    return sorted((e['idx'], dirs.get(e['key'])) for e in L['events'] if e['action'] == 'break')


BR15, BR1 = breaks(L15), breaks(L1)
I15 = np.array([b[0] for b in BR15]); I1 = np.array([b[0] for b in BR1])
s20 = B.h1.c.rolling(20).mean().to_numpy(); s75 = B.h1.c.rolling(75).mean().to_numpy(); hc = B.h1.c.to_numpy()


def tl15(i, d, k1, k4, look=96):
    a, b = np.searchsorted(I15, i - look), np.searchsorted(I15, i, side='right')
    return any(BR15[j][1] not in (None, d) for j in range(a, b))


def tl1(i, d, k1, k4, look=24):
    a, b = np.searchsorted(I1, k1 - look), np.searchsorted(I1, k1, side='right')
    return any(BR1[j][1] not in (None, d) for j in range(a, b))


def ma(i, d, k1, k4):
    s = 1 if d == 'up' else -1
    return s * (s20[k1] - s75[k1]) > 0 and s * (hc[k1] - s75[k1]) > 0


F = {'MA': ma, 'M15線': tl15, 'H1線': tl1}
SPEC = {  # filter spec: list of required names; ('any', a, b) = either
    'C0 仮転換（基準）': ('prov', False, []),
    'C1 ＋MA': ('prov', False, ['MA']),
    'C2 ＋M15調整ライン抜け': ('prov', False, ['M15線']),
    'C3 ＋H1調整ライン抜け': ('prov', False, ['H1線']),
    'C4 ＋MA＋M15ライン': ('prov', False, ['MA', 'M15線']),
    'C5 ＋MA＋(M15かH1ライン)': ('prov', False, ['MA', ('any', 'M15線', 'H1線')]),
    'B4 主要転換＋MA＋M15ライン': ('major', False, ['MA', 'M15線']),
    'A5 仮転換＋H1調整＋MA＋(M15かH1ライン)': ('prov', True, ['MA', ('any', 'M15線', 'H1線')]),
}


def check(req, *a):
    return all((F[r[1]](*a) or F[r[2]](*a)) if isinstance(r, tuple) else F[r](*a) for r in req)


def run2(name):
    trig, h1c, req = SPEC[name]
    flt = (lambda *a: check(req, *a)) if req else None
    return B.run((name, trig, h1c, 1.0, 1.0, flt))


if __name__ == '__main__':
    with Pool(4) as pool:
        for name, tr in pool.imap(run2, list(SPEC)):
            y = tr.t.dt.year
            tr.to_csv(B.HERE / 'results' / f"dow_turn2_{name.split()[0]}.csv", index=False)
            print(f"{name}\n   開発2020-24 {B.stats(tr.R[(y >= 2020) & (y <= 2024)].to_numpy())}"
                  f"\n   確認2025    {B.stats(tr.R[y == 2025].to_numpy())}\n   2026        {B.stats(tr.R[y == 2026].to_numpy())}"
                  f"\n   SL中央値{tr.risk.median() / B.PIP:.0f}pips  {B.recall(tr)}", flush=True)
