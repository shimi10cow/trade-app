"""Build interactive review chart: python -m env_recognition.build_html out.html

Everything is computed on the full series (warm-up for pivots/state), then only the most recent
SHOW[tf] bars are embedded to keep the page light.
"""
import json
import sys
from pathlib import Path
import pandas as pd
from .data import load
from .pivots import final_pivots
from . import dow_trend, zones

TEMPLATE = Path(__file__).with_name('chart_template.html')
SHOW = {'W1': 400, 'D1': 500, 'H4': 600, 'H1': 800, 'M15': 1000}


def epoch_s(ts):
    """Unit-safe epoch seconds (datetime64 may be ns, us or s)."""
    return ((pd.to_datetime(ts) - pd.Timestamp('1970-01-01')) // pd.Timedelta(seconds=1)).astype('int64').tolist()


def tf_payload(tf):
    df = load(tf)
    res = dow_trend.run(df, tf)
    zs = zones.build(df, res)
    n = len(df)
    s0 = max(0, n - SHOW[tf])
    t = epoch_s(df.t)
    r5 = lambda x: round(float(x), 5)
    keep = lambda i: i >= s0
    candles = [[t[i], r5(df.o[i]), r5(df.h[i]), r5(df.l[i]), r5(df.c[i])] for i in range(s0, n)]
    sma = {}
    for p in (20, 75):
        m = df.c.rolling(p).mean()
        sma[p] = [[t[i], r5(m[i])] for i in range(s0, n) if pd.notna(m[i])]
    prot = [[t[i], None if tr is None else r5(p), tr] for i, (tr, p) in enumerate(res['bars']) if keep(i)]
    pprot = [[t[i], None if tr is None else r5(p), tr] for i, (tr, p) in enumerate(res['prov_bars']) if keep(i)]
    known = {}
    for e in res['pivot_events']:
        known.setdefault(e['id'], e['available_idx'])
    piv = [[t[p['idx']], p['kind'], r5(p['price']), p['label'], t[known[p['id']]]]
           for p in dow_trend.label_counts(final_pivots(res['pivot_events'])) if keep(p['idx'])]
    ev = []
    for e in res['events']:
        if not keep(e['idx']):
            continue
        a = e['action']
        if a == 'REVERSAL':
            ev.append([t[e['idx']], 'rev', e['to'], r5(e['broken_price']), t[e['broken_anchor']]])
        elif a == 'BREAKOUT':
            ev.append([t[e['idx']], 'bo', e['trend'], r5(e['ref_price']), t[e['ref_anchor']]])
        elif a in ('breakout_protect', 'late_protect', 'reversal_protect', 'reversal_protect_raw', 'init_up', 'init_down'):
            ev.append([t[e['idx']], a, e['trend'], r5(e['price']), t[e['anchor']]])
    pev = [[t[e['idx']], e['to'], r5(e.get('broken_price') or (e.get('h2') if e['to'] == 'up' else e.get('l2')))]
           for e in res['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and keep(e['idx'])]
    wev = [[t[e['idx']], e['action'], r5(e['a']), r5(e['b']), r5(e['c']), t[e['b_anchor']]]
           for e in res['w_events'] if keep(e['idx'])]
    # zones: any zone still alive inside the shown window
    zout = [[t[z['anchor']], t[z['activation']], t[z['expiry']] if z['expiry'] is not None else None,
             r5(z['bottom']), r5(z['top']), '・'.join(z['sources'])]
            for z in zs if z['expiry'] is None or z['expiry'] >= s0]
    return dict(candles=candles, sma20=sma[20], sma75=sma[75], prot=prot, pprot=pprot, piv=piv,
                ev=ev, pev=pev, wev=wev, zones=zout)


def main(out):
    data = {tf: tf_payload(tf) for tf in ('W1', 'D1', 'H4', 'H1', 'M15')}
    html = TEMPLATE.read_text(encoding='utf-8').replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    Path(out).write_text(html, encoding='utf-8')
    print(out, round(len(html) / 1e6, 2), 'MB')


if __name__ == '__main__':
    main(sys.argv[1])
