"""Tag every long-validation trade with the environment at entry, then break results down.

Features (all known at the close of the signal M15 bar = t + 15 min, causal):
  h4corr    a live H4 correction line (against the H4 trend) is broken
  h4/d1/h1  that TF's major Dow trend agrees with the trade
  h4_stage  H4 trend stage: number of BREAKOUTs (HH for up / LL for down) since the last REVERSAL
            0 = trend start (before the first update), 1, 2, 3+ = mid / late
  h1_stage  same on H1
  h4_dist   distance entry - H4 protected level, in H4 ATR (how far price has run from the protected swing)
Usage: python dow_strategy/long_features.py [config numbers...]   (needs results/long_trades_{i}.csv)
"""
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import EnvRecognizer, TF_LEN  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402

OUT = Path(__file__).with_name('results')
PERIODS = (('全期間', 2003, 2026), ('2003-2014', 2003, 2014), ('2015-2024', 2015, 2024), ('2025-2026', 2025, 2026))


def stage_arrays(res, n):
    """Per bar: BREAKOUT count since the last REVERSAL of the major machine (events idx <= k)."""
    stage = np.full(n, -1)
    ev = sorted((e['idx'], e['action']) for e in res['events']
                if e.get('machine') == 'major' and (e['action'] in ('REVERSAL', 'BREAKOUT') or e['action'].startswith('init_')))
    cnt, j = -1, 0
    for k in range(n):
        while j < len(ev) and ev[j][0] <= k:
            cnt = cnt + 1 if ev[j][1] == 'BREAKOUT' and cnt >= 0 else 0
            j += 1
        stage[k] = cnt
    return stage


def stats(r):
    if not len(r):
        return dict(n=0)
    w = r > 0
    eq = np.cumsum(r)
    return dict(n=len(r), win=round(w.mean(), 3), sumR=round(r.sum(), 1), avgR=round(r.mean(), 3),
                PF=round(r[w].sum() / max(1e-9, -r[~w].sum()), 2),
                maxDD=round((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(), 1))


def main(pick):
    t0 = time.time()
    frames = {tf: load(tf, 'long') for tf in ('D1', 'H4')}
    env = EnvRecognizer(frames)
    h4 = env.tf['H4']
    h4_stage = stage_arrays(h4['res'], len(h4['df']))
    h4_atr = atr(h4['df'])
    h1 = load('H1', 'long').reset_index(drop=True)
    h1_res = dow_trend.run(h1, 'H1')
    h1_trend = [b[0] for b in h1_res['bars']]
    h1_stage = stage_arrays(h1_res, len(h1))
    h1_close = list(pd.to_datetime(h1.t) + TF_LEN['H1'])
    import bisect
    print(f'prep {time.time() - t0:.0f}s', flush=True)

    for i in pick:
        tr = pd.read_csv(OUT / f'long_trades_{i}.csv', parse_dates=['time'])
        rows = []
        for t, side, entry in zip(tr.time, tr.side, tr.entry):
            ts = t + pd.Timedelta(minutes=15)
            d = 'up' if side == 1 else 'down'
            s = env.state_at(ts)
            k4 = env.last_closed('H4', ts)
            k1 = bisect.bisect_right(h1_close, ts) - 1
            H4, D1 = s['H4'], s['D1']
            rows.append(dict(
                h4=H4 is not None and H4['trend'] == d,
                d1=D1 is not None and D1['trend'] == d,
                h1=k1 >= 0 and h1_trend[k1] == d,
                h4corr=H4 is not None and any(l['cls'] == 'correction' and l['broken'] for l in H4['lines']),
                h4_stage=int(h4_stage[k4]) if H4 is not None and H4['trend'] == d else -1,
                h1_stage=int(h1_stage[k1]) if k1 >= 0 and h1_trend[k1] == d else -1,
                h4_dist=(side * (entry - H4['protected']) / h4_atr[k4]) if H4 and H4['trend'] == d and H4['protected'] else np.nan,
            ))
        F = pd.concat([tr, pd.DataFrame(rows)], axis=1)
        F.to_csv(OUT / f'long_features_{i}.csv', index=False)
        y = F.time.dt.year
        groups = {'全体': F.index == F.index}
        for c in ('h4', 'd1', 'h1', 'h4corr'):
            groups[f'{c}=あり'] = F[c].to_numpy(bool)
            groups[f'{c}=なし'] = ~F[c].to_numpy(bool)
        groups['H4一致＋調整ラインブレイク中'] = (F.h4 & F.h4corr).to_numpy()
        groups['H4一致＋調整ライン未ブレイク'] = (F.h4 & ~F.h4corr).to_numpy()
        for st, lab in ((0, '0 転換直後'), (1, '1 更新1回'), (2, '2 更新2回')):
            groups[f'H4段階{lab}'] = (F.h4_stage == st).to_numpy()
            groups[f'H1段階{lab}'] = (F.h1_stage == st).to_numpy()
        groups['H4段階3+ 更新3回以上'] = (F.h4_stage >= 3).to_numpy()
        groups['H1段階3+ 更新3回以上'] = (F.h1_stage >= 3).to_numpy()
        for a, b in ((0, 1), (1, 2), (2, 4), (4, 99)):
            groups[f'H4押安からの距離 {a}-{b}ATR'] = ((F.h4_dist >= a) & (F.h4_dist < b)).to_numpy()
        table = {}
        for g, m in groups.items():
            for lab, a, b in PERIODS:
                sel = m & (y >= a).to_numpy() & (y <= b).to_numpy()
                st = stats(F.Rc[sel].to_numpy())
                table[(g, lab)] = f"{st['n']} / {st.get('sumR', 0):+.1f} / {st.get('PF', 0):.2f}" if st['n'] else '0'
        T = pd.Series(table).unstack()[[p[0] for p in PERIODS]].reindex(list(groups))
        T.to_csv(OUT / f'long_breakdown_{i}.csv')
        print(f'\n[{i}]  n / 合計R / PF', flush=True)
        print(T.to_string(), flush=True)


if __name__ == '__main__':
    main([int(x) for x in sys.argv[1:]] or [1, 4])
