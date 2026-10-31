"""DS (right shoulder) context study: H1 support / resistance at the right shoulder, trend lines, H4 trend stage."""
import sys, time, bisect
sys.path.insert(0, '/home/user/trade-app')
import numpy as np, pandas as pd
from mt5_ea.live.core import to_space
def load(sym):
    if sym in ('OIL', 'NGAS'):
        d = pd.read_csv(f'/home/user/trade-app/{sym}Cash#_M15_MT5.csv', usecols=[0, 1, 2, 3, 4], encoding='utf-8-sig', parse_dates=['time'])
        d = d[d.time >= '2016-10-27 01:15'].reset_index(drop=True); start = '2017-12-01'; conv = lambda x: np.round(np.log(x), 6)
    else:
        d = pd.read_csv(f'/home/user/trade-app/{sym}_m1_M5.csv.gz', usecols=[0, 1, 2, 3, 4], parse_dates=['time'])
        d = d.set_index('time').resample('15min', label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna().reset_index()
        start = '2005-01-01'; conv = lambda x: to_space(sym, x)
    return pd.DataFrame(dict(t=d.time, o=conv(d.open), h=conv(d.high), l=conv(d.low), c=conv(d.close))), start
from mt5_ea.live.core import Frames
from mt5_ea.live.eas import ds as DS
def pivots_known(Rk, times, t):
    """pivots (anchor time, kind, price) as known at time t (relocations applied), from a dow_trend run"""
    last = {}
    for e in Rk['pivot_events']:
        if times[e['available_idx']] > t: continue
        last[e['id']] = (e['idx'], e['kind'], e['price'])
    return sorted(last.values())
out = []
for sym in sys.argv[1:]:
    t0 = time.time(); m, start = load(sym); F = Frames(m, start); a = dict(stop='left', exit='tp2', side=None, ln=True)   # the JP225 type
    evs = DS.setups(F, 'H1'); EV = {e['t']: e for e in evs}
    EVT = sorted((e['te'], e['t_left']) for e in DS._events(F, 'H1')); TE = [x[0] for x in EVT]
    r = DS.run_variant(F, 'H1', a['stop'], a['exit'], events=evs)['trades']
    T1 = list(pd.to_datetime(F.h1.t)); C1 = F.C1; A1 = np.asarray(F.A1); T4 = list(pd.to_datetime(F.h4.t)); C4 = F.C4
    bars4 = [b[0] for b in F.R4['bars']]
    rows = []
    for _, x in r.iterrows():
        e = EV[x.setup_t]; s = int(x.side); t = pd.Timestamp(x.setup_t); sh = e['ref_sh']; tl = None
        # left shoulder time: the event whose setup this is (setup tag hours back from t)
        hrs = float(e['tag'].split('|')[4]); te = t - pd.Timedelta(hours=hrs)
        j = bisect.bisect_right(TE, te + pd.Timedelta('1h')) - 1                   # the H1 turn this setup came from (tag hours are rounded)
        tl = EVT[j][1] if j >= 0 and abs((TE[j] - te) / pd.Timedelta('1h')) <= 1 else None
        k1 = bisect.bisect_right(C1, t) - 1; atr = A1[k1]
        P1 = pivots_known(F.R1, C1, t)
        # 1) H1 S/R near the right shoulder: pivots before the left shoulder, last 30 days
        lv = [p for i, kd, p in P1 if tl is not None and T1[i] < tl and T1[i] >= tl - pd.Timedelta('30D')]
        sr = sum(abs(p - sh) <= 0.5 * atr for p in lv)
        # 2a) broken trend line retest: line through the last two counter-trend swing extremes before the left shoulder
        kd_c = 'hi' if s == 1 else 'lo'
        cc = [(T1[i], p) for i, kd, p in P1 if kd == kd_c and tl is not None and T1[i] < tl][-2:]
        tl_re = np.nan
        if len(cc) == 2 and (cc[1][1] - cc[0][1]) * s < 0:            # lower highs (buy) / higher lows (sell)
            slope = (cc[1][1] - cc[0][1]) / ((cc[1][0] - cc[0][0]) / pd.Timedelta('1h'))
            line = cc[1][1] + slope * ((t - cc[1][0]) / pd.Timedelta('1h')); tl_re = abs(sh - line) / atr
        # 2b) rising line from the left shoulder through a swing low between the left shoulder and the right shoulder
        kd_w = 'lo' if s == 1 else 'hi'
        ww = [(T1[i], p) for i, kd, p in P1 if kd == kd_w and tl is not None and tl < T1[i] < t - pd.Timedelta('2h')]
        tl_up = np.nan
        if ww and tl is not None:
            (tw, pw) = ww[-1]; dt = (tw - tl) / pd.Timedelta('1h')
            if dt > 0 and (pw - e['ref_H']) * s > 0:
                line = e['ref_H'] + (pw - e['ref_H']) / dt * ((t - tl) / pd.Timedelta('1h')); tl_up = abs(sh - line) / atr
        # 3) H4 trend at the left shoulder: direction vs the trade, and how many swings it had made
        k4 = bisect.bisect_right(C4, tl if tl is not None else t) - 1; d4 = bars4[k4]
        ks = k4
        while ks > 0 and bars4[ks - 1] == d4: ks -= 1
        P4 = pivots_known(F.R4, C4, tl if tl is not None else t)
        ext = 'lo' if d4 == 'down' else 'hi'
        waves = sum(1 for i, kd, p in P4 if kd == ext and ks <= i <= k4)
        rel = 'counter' if (d4 == 'down' and s == 1) or (d4 == 'up' and s == -1) else ('same' if d4 in ('up', 'down') else 'none')
        rows.append(dict(sym=sym, t=x.t, side=s, R=x.R, adopted=DS.adopted_filter(dict(tag=x.tag, side=s), a['side'], e['ln_h']),
                         ln_h=e['ln_h'], depth=float(e['tag'].split('|')[2]), sr=sr, tl_re=tl_re, tl_up=tl_up, h4=rel, h4_waves=waves, h4_bars=k4 - ks))
    out += rows; print(sym, len(rows), 'trades', f'{time.time() - t0:.0f}s', flush=True)
    pd.DataFrame(rows).to_pickle(f'/home/user/ds_work/oos_{sym}.pkl')
