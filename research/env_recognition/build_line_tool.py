"""Build the manual trendline drawing tool: python -m env_recognition.build_line_tool out.html"""
import json
import sys
from pathlib import Path
import pandas as pd
from .data import load
from .pivots import pivot_events, final_pivots
from . import dow_trend, lines as lmod
from .build_html import epoch_s

TEMPLATE = Path(__file__).with_name('line_tool_template.html')
TFSEC = {'W1': 604800, 'D1': 86400, 'H4': 14400, 'H1': 3600, 'M15': 900}
SHOW = {'W1': 615, 'D1': 800, 'H4': 1500, 'H1': 2000, 'M15': 3000}


def payload(tf):
    df = load(tf)
    n = len(df); s0 = max(0, n - SHOW[tf])
    t = epoch_s(df.t)
    r5 = lambda x: round(float(x), 5)
    sma = {p: df.c.rolling(p).mean() for p in (20, 75)}
    ev = pivot_events(df)
    known = {}
    for e in ev:
        known.setdefault(e['id'], e['available_idx'])
    # final position + time it first became known (replay shows a pivot only after it is known)
    piv = [[t[p['idx']], p['kind'], r5(p['price']), t[known[p['id']]]] for p in final_pivots(ev) if p['idx'] >= s0]
    res = dow_trend.run(df, tf)
    lr = lmod.run(df, tf, res, gen_events=None)
    sec = TFSEC[tf]
    # engine lines: geometry at bar-open times, created/retired as bar CLOSE times (replay gating)
    eng = [[t[x['anchor_idx']], r5(x['anchor_price']), t[x['end_idx']], r5(x['end_price']), x['kind'], x['tier'],
            t[x['created']] + sec, (t[x['retired']] + sec) if x['retired'] is not None else None, x['reason'] or '']
           for x in lr['lines'] if x['end_idx'] >= s0]
    return dict(eng=eng, c=[[t[i], r5(df.o[i]), r5(df.h[i]), r5(df.l[i]), r5(df.c[i])] for i in range(s0, n)],
                s20=[[t[i], r5(sma[20][i])] for i in range(s0, n) if pd.notna(sma[20][i])],
                s75=[[t[i], r5(sma[75][i])] for i in range(s0, n) if pd.notna(sma[75][i])],
                piv=piv)


def trend_changes(tf):
    """Major-trend timeline as [[bar close time, 'up'|'down'|None], ...] (only changes)."""
    df = load(tf)
    t = epoch_s(df.t)
    out, last = [], 'x'
    for i, (tr, _) in enumerate(dow_trend.run(df, tf)['bars']):
        if tr != last:
            out.append([t[i] + TFSEC[tf], tr]); last = tr
    return out


if __name__ == '__main__':
    data = {tf: payload(tf) for tf in ('W1', 'D1', 'H4', 'H1', 'M15')}
    data['ctx'] = {tf: trend_changes(tf) for tf in ('D1', 'H4')}
    html = TEMPLATE.read_text(encoding='utf-8').replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    Path(sys.argv[1]).write_text(html, encoding='utf-8')
    print(sys.argv[1], round(len(html) / 1e6, 2), 'MB')
