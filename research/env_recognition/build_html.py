"""Build interactive review chart: python -m env_recognition.build_html out.html"""
import json
import sys
from pathlib import Path
from .data import load
from .pivots import final_pivots
from . import dow_trend

TEMPLATE = Path(__file__).with_name('chart_template.html')


def tf_payload(tf):
    df = load(tf)
    res = dow_trend.run(df, tf)
    t = (df.t.astype('int64') // 10**9).tolist()
    r5 = lambda x: round(float(x), 5)
    candles = [[t[i], r5(df.o[i]), r5(df.h[i]), r5(df.l[i]), r5(df.c[i])] for i in range(len(df))]
    prot = [[t[i], None if tr is None else r5(p), tr] for i, (tr, p) in enumerate(res['bars'])]
    pprot = [[t[i], None if tr is None else r5(p), tr] for i, (tr, p) in enumerate(res['prov_bars'])]
    pev = []
    for e in res['prov_events']:
        if e['action'] in ('REVERSAL', 'PROV_START'):
            pev.append([t[e['idx']], e['to'], r5(e.get('broken_price') or (e.get('h2') if e['to'] == 'up' else e.get('l2')))])
    wev = [[t[e['idx']], e['action'], r5(e['a']), r5(e['b']), r5(e['c']), t[e['b_anchor']]] for e in res['w_events']]
    known = {}
    for e in res['pivot_events']:
        known.setdefault(e['id'], e['available_idx'])
    piv = [[t[p['idx']], p['kind'], r5(p['price']), p['label'], t[known[p['id']]]]
           for p in dow_trend.label_counts(final_pivots(res['pivot_events']))]
    ev = []
    for e in res['events']:
        a = e['action']
        if a == 'REVERSAL':
            ev.append([t[e['idx']], 'rev', e['to'], r5(e['broken_price']), t[e['broken_anchor']]])
        elif a == 'BREAKOUT':
            ev.append([t[e['idx']], 'bo', e['trend'], r5(e['ref_price']), t[e['ref_anchor']]])
        elif a in ('breakout_protect', 'late_protect', 'reversal_protect', 'reversal_protect_raw', 'init_up', 'init_down'):
            ev.append([t[e['idx']], a, e['trend'], r5(e['price']), t[e['anchor']]])
    return dict(candles=candles, prot=prot, piv=piv, ev=ev, pprot=pprot, pev=pev, wev=wev)


def main(out):
    data = {tf: tf_payload(tf) for tf in ('W1', 'D1', 'H4', 'H1', 'M15')}
    html = TEMPLATE.read_text(encoding='utf-8').replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    Path(out).write_text(html, encoding='utf-8')
    print(out, round(len(html) / 1e6, 2), 'MB')


if __name__ == '__main__':
    main(sys.argv[1])
