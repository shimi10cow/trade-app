import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from env_recognition import lines, dow_trend  # noqa
from env_recognition.data import load  # noqa


def frame(closes):
    c = np.asarray(closes, float)
    return pd.DataFrame(dict(t=pd.date_range('2020', periods=len(c), freq='D'), o=c, h=c, l=c, c=c))


def asc_line(avail=5):
    # ascending line y = 1.00 + 0.01*i, built from lows at 0 and 4
    return [dict(action='create', key='L', type='two', kind='lo', available_idx=avail,
                 anchor_idx=0, end_idx=4, anchor_price=1.00, end_price=1.04)]


def res_with(pivots, n, trend='up'):
    return dict(pivot_events=pivots, bars=[(trend, 0.9)] * n)


def piv(pid, kind, idx, avail):
    return dict(action='confirm', id=pid, kind=kind, idx=idx, price=0, available_idx=avail)


def test_break_then_two_highs_retires():
    n = 30
    df = frame([1.0 + .01 * i for i in range(10)] + [1.0] * 20)   # breaks below at bar 10
    r = lines.run(df, 'D1', res_with([piv(1, 'hi', 12, 14), piv(2, 'lo', 15, 16), piv(3, 'hi', 18, 20)], n),
                  gen_events=asc_line())
    ln = r['lines'][0]
    assert ln['reason'] == 'break_2pivots' and ln['retired'] == 20


def test_high_before_break_not_counted():
    n = 30
    df = frame([1.0 + .01 * i for i in range(10)] + [1.0] * 20)
    # hi anchored at 9 (before break bar 10) confirmed at 12 -> not counted
    r = lines.run(df, 'D1', res_with([piv(1, 'hi', 9, 12), piv(2, 'hi', 14, 16)], n), gen_events=asc_line())
    assert r['lines'][0]['retired'] is None


def test_close_back_inside_resets():
    n = 30
    cl = [1.0 + .01 * i for i in range(10)] + [1.0, 1.0, 1.5, 1.0, 1.0] + [1.0] * 15
    df = frame(cl)   # break at 10, back inside at 12, break again at 13
    r = lines.run(df, 'D1', res_with([piv(1, 'hi', 11, 11), piv(2, 'hi', 16, 17), piv(3, 'hi', 20, 22)], n),
                  gen_events=asc_line())
    acts = [e['action'] for e in r['events']]
    assert 'reset' in acts
    assert r['lines'][0]['retired'] == 22        # pivot 1 belonged to the cancelled break


def test_impulse_line_retires_on_major_reversal_correction_survives():
    n = 20
    df = frame([1.0 + .01 * i for i in range(n)])
    gen = asc_line() + [dict(action='create', key='D', type='two', kind='hi', available_idx=5,
                             anchor_idx=0, end_idx=4, anchor_price=2.0, end_price=1.96)]
    bars = [('up', 0.9)] * 10 + [('down', 1.5)] * 10
    r = lines.run(df, 'D1', dict(pivot_events=[], bars=bars), gen_events=gen)
    by = {ln['key']: ln for ln in r['lines']}
    assert by['L']['reason'] == 'impulse_trend_reversal' and by['L']['retired'] == 10
    assert by['D']['retired'] is None            # was correction, now impulse


def test_lines_no_lookahead():
    df = load('H4')
    full = lines.run(df, 'H4', dow_trend.run(df, 'H4'))
    cut = len(df) // 2
    p = df.iloc[:cut].reset_index(drop=True)
    part = lines.run(p, 'H4', dow_trend.run(p, 'H4'))
    for k in (cut // 2, cut - 1):
        a = sorted((x['key'], round(x['value'], 8)) for x in lines.active_asof(part, k))
        b = sorted((x['key'], round(x['value'], 8)) for x in lines.active_asof(full, k))
        assert a == b
