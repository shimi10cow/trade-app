"""New entry idea (user 2026-10-19): instead of the M15 stochastic, enter on an M15 Dow reversal,
optionally only after an M15 trendline (against the trade) was broken in the preceding leg.

Direction filter : H1 Dow major trend (and optionally H1 SMA20/75 side, like the existing EA regime)
Entry            : open of the bar after the M15 reversal bar
Initial stop     : the new M15 (provisional or major) protected swing -/+ 1 pip, at least 10 pips
Exit             : same idea as the existing EA - stop; at +2R (or 240h) start trailing to the latest
                   confirmed M15 Dow pivot (tighten only)
Max 2 positions, cost 1.2 pip. Only bars closed before the entry are used.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ma_ea_zones_lines as M  # noqa: E402

PIP = 1e-4
m15 = M.env.tf['M15']
df = m15['df']
o, h, l, c = (df[z].to_numpy(float) for z in 'ohlc')
T = pd.to_datetime(df.t)
h1 = M.frames['H1'].reset_index(drop=True)
s20, s75 = h1.c.rolling(20).mean(), h1.c.rolling(75).mean()
piv_ev = m15['res']['pivot_events']
brk = [x for x in m15['lines']['events'] if x['action'] == 'break']
ldir = {ln['key']: ln['direction'] for ln in m15['lines']['lines']}


def signals(kind):
    if kind == 'major':
        ev = [e for e in m15['res']['events'] if e['action'] == 'REVERSAL']
        bars = m15['res']['bars']
    else:
        ev = [e for e in m15['res']['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
        bars = m15['res']['prov_bars']
    out = []
    for e in ev:
        k = e['idx']
        if k + 1 < len(df):
            out.append(dict(k=k, d=e['to'], stop=bars[k][1], leg0=e.get('broken_anchor', e.get('prot_anchor') or k - 96)))
    return out


def run(kind='prov', need_line=False, need_ma=False, need_h4=False, start='2025-02-10'):
    sig = signals(kind)
    # latest confirmed M15 pivot per kind as of each bar (for trailing)
    conf = sorted(((e['available_idx'], e['kind'], e['price']) for e in piv_ev), key=lambda x: x[0])
    trades, open_pos, ci = [], [], 0
    last_piv = {'hi': None, 'lo': None}
    sig_by_k = {}
    for s_ in sig:
        sig_by_k.setdefault(s_['k'], []).append(s_)
    for i in range(len(df)):
        # exits for positions opened before this bar
        keep = []
        for p in open_pos:
            hit = (l[i] <= p['sl']) if p['side'] == 1 else (h[i] >= p['sl'])
            if hit:
                p['R'] = (p['sl'] - p['entry']) * p['side'] / p['risk']; p['exit_t'] = T[i]; trades.append(p); continue
            if not p['trail']:
                fav = (h[i] - p['entry']) if p['side'] == 1 else (p['entry'] - l[i])
                if fav >= 2 * p['risk'] or (T[i] - p['t']).total_seconds() >= 240 * 3600:
                    p['trail'] = True
            if p['trail']:
                pv = last_piv['lo' if p['side'] == 1 else 'hi']
                if pv is not None:
                    p['sl'] = max(p['sl'], pv) if p['side'] == 1 else min(p['sl'], pv)
            keep.append(p)
        open_pos = keep
        while ci < len(conf) and conf[ci][0] <= i:            # pivots confirmed at this bar close
            last_piv[conf[ci][1]] = conf[ci][2]; ci += 1
        for s_ in sig_by_k.get(i, []):
            if T[i] < pd.Timestamp(start) or len(open_pos) >= 2:
                continue
            d = s_['d']; side = 1 if d == 'up' else -1
            st = M.state(T[i])
            if st['H1']['trend'] != d:
                continue
            if need_h4 and st['H4']['trend'] != d:
                continue
            if need_ma:
                j = M.env.last_closed('H1', T[i] + pd.Timedelta(minutes=15))
                if not side * (s20[j] - s75[j]) > 0:
                    continue
            if need_line and not any(x['action'] == 'break' and s_['leg0'] <= x['idx'] <= i and ldir.get(x['key']) != d for x in brk):
                continue
            entry = o[i + 1]
            sl = s_['stop'] - side * PIP
            if side * (entry - sl) < 10 * PIP:
                sl = entry - side * 10 * PIP
            risk = side * (entry - sl)
            corr = any(x['cls'] == 'correction' and x['broken'] for x in st['H4']['lines'])
            open_pos.append(dict(t=T[i + 1], side=side, entry=entry, sl=sl, risk=risk, trail=False, corr=corr))
    for p in open_pos:
        p['R'] = (c[-1] - p['entry']) * p['side'] / p['risk']; p['exit_t'] = T[len(df) - 1]; trades.append(p)
    return pd.DataFrame(trades)


if __name__ == '__main__':
    rows = {}
    for name, kw in {
        '仮転換＋H1ダウ': dict(kind='prov'),
        '仮転換＋H1ダウ＋M15ラインブレイク後': dict(kind='prov', need_line=True),
        '仮転換＋H1ダウ＋H1 20/75': dict(kind='prov', need_ma=True),
        '仮転換＋H1ダウ＋H1 20/75＋M15ラインブレイク後': dict(kind='prov', need_ma=True, need_line=True),
        '主要転換＋H1ダウ': dict(kind='major'),
        '主要転換＋H1ダウ＋M15ラインブレイク後': dict(kind='major', need_line=True),
        '主要転換＋H1ダウ＋H1 20/75＋M15ラインブレイク後': dict(kind='major', need_ma=True, need_line=True),
    }.items():
        tr = run(**kw)
        rows[name] = M.metrics(tr)
        rows[name + '｜H4調整ラインブレイク中'] = M.metrics(tr[tr['corr']]) if len(tr) else {}
        print(name, rows[name], '｜ライン', rows[name + '｜H4調整ラインブレイク中'], flush=True)
    out = Path(__file__).with_name('results'); out.mkdir(exist_ok=True)
    pd.DataFrame(rows).T.to_csv(out / 'dow_entry_m15_2025_2026.csv')
