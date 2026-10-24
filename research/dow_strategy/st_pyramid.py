"""Gold/BTC trend EA (S) with adding positions in the same direction (2026-10-22). Same settings as the picked S
(gold: H4 MA + H1 provisional Dow, buy only, stop M15 turn + 0.3 ATR, H1 trail from +1R; BTC: H4/H1 MA, +2R) but
one_per_side=False, so each new M15 turn while the trend holds opens another position (max open = MAXPOS)."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import st_trend as ST  # noqa: E402
X = ST.X
sym = sys.argv[1]; OUT = ST.B.HERE / 'results' / 'st2'
c4, c1, act = ('ma', 'prov', 1.0) if sym == 'XAUUSD' else ('ma', 'ma', 2.0)
ev = ST.events(c4, c1, 'buy')
for mx in (2, 3):
    cfg = dict(trig='dow', stop='m15turn', buf=0.3, exit='h1', act=act, win=1, one_per_side=False, max_side=mx)
    tr = X.run(ev, cfg); name = f'S_pyr_max{mx}'
    tr.to_csv(OUT / f'{name}.csv', index=False); print(name, len(tr), flush=True)
