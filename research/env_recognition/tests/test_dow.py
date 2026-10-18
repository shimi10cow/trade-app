import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from env_recognition.pivots import pivot_events, final_pivots, indicators  # noqa
from env_recognition import dow_trend  # noqa
from env_recognition.data import load  # noqa


def bars_from_path(path, w=0.0002):
    """Build OHLC whose closes follow `path`; wick = small fixed width."""
    p = np.asarray(path, float)
    o = np.r_[p[0], p[:-1]]
    return pd.DataFrame(dict(t=pd.date_range('2020', periods=len(p), freq='D'), o=o,
                             h=np.maximum(o, p) + w, l=np.minimum(o, p) - w, c=p))


def zigzag(points, step=10):
    out = []
    for a, b in zip(points, points[1:]):
        out += list(np.linspace(a, b, step, endpoint=False))
    return out + [points[-1]]


@pytest.mark.parametrize('tf', ['W1', 'D1', 'H4', 'H1', 'M15'])
def test_parity_with_frozen_detector(tf):
    pytest.importorskip('numba')
    sys.path.insert(0, str(ROOT / 'dow_frozen_v1'))
    import dow_final_engine as fz
    df = load(tf)
    _, th = indicators(df, tf)
    h, l, c = (df[z].to_numpy(float) for z in 'hlc')
    ref = fz.detect(h, l, c, th, 60, len(df) - 1)
    mine = final_pivots(pivot_events(df, tf))
    assert [(int(a), 'hi' if k == 1 else 'lo') for a, k, _ in ref] == [(p['idx'], p['kind']) for p in mine]


@pytest.mark.parametrize('tf', ['W1', 'D1', 'H4', 'H1'])
def test_no_lookahead(tf):
    df = load(tf)
    full = dow_trend.run(df, tf)
    for cut in (len(df) // 3, len(df) // 2, len(df) - 50):
        part = dow_trend.run(df.iloc[:cut].reset_index(drop=True), tf)
        assert part['bars'] == full['bars'][:cut]
        assert part['events'] == [e for e in full['events'] if e['idx'] < cut]
        assert part['prov_bars'] == full['prov_bars'][:cut]
        assert part['prov_events'] == [e for e in full['prov_events'] if e['idx'] < cut]
        assert part['w_events'] == [e for e in full['w_events'] if e['idx'] < cut]


def _run_synth(points, step=10):
    df = bars_from_path(zigzag(points, step))
    th = np.full(len(df), 0.01)  # fixed threshold for hand-made scenarios
    ev = pivot_events(df, 'D1', start=0, th=th)
    return df, dow_trend.run(df, 'D1', start=0, events=ev)


def acts(res, name):
    return [e for e in res['events'] if e['action'] == name]


def test_uptrend_protected_low_trails_and_reverses():
    # 1.00 -> up 1.05 -> 1.03 -> 1.08 (break) -> 1.06 -> 1.10 (break) -> 1.05 (below prot 1.06)
    df, r = _run_synth([1.00, 1.05, 1.03, 1.08, 1.06, 1.10, 1.04])
    prot = [round(e['price'], 2) for e in r['events'] if e['action'].endswith('protect') or e['action'].startswith('init')]
    assert acts(r, 'init_up')
    assert 1.06 in [round(p, 2) for p in prot]
    rev = acts(r, 'REVERSAL')
    assert len(rev) == 1 and rev[0]['frm'] == 'up'
    assert round(rev[0]['broken_price'], 2) == 1.06
    # new protected high = latest swing high before the break (here the top 1.10)
    rp = acts(r, 'reversal_protect')[0]
    assert round(rp['price'], 2) == 1.10


def test_lower_high_does_not_move_protected_low():
    # after a break, a lower high then higher low: no new breakout -> protected stays
    df, r = _run_synth([1.00, 1.05, 1.03, 1.08, 1.06, 1.07, 1.065, 1.075])
    bp = [round(e['price'], 3) for e in acts(r, 'breakout_protect')]
    assert 1.065 not in bp
    assert not acts(r, 'REVERSAL')


def test_mirror_downtrend():
    df, r = _run_synth([1.10, 1.05, 1.07, 1.02, 1.04, 0.99, 1.05])
    rev = acts(r, 'REVERSAL')
    assert len(rev) == 1 and rev[0]['frm'] == 'down'
    assert round(rev[0]['broken_price'], 2) == 1.04


def test_reversal_does_not_immediately_breakout_on_stale_pivot():
    # up epoch with an intermediate low ABOVE protected, then a reversal through protected
    df, r = _run_synth([1.00, 1.05, 1.03, 1.08, 1.065, 1.075, 1.06, 1.02, 1.04, 1.00])
    rev = acts(r, 'REVERSAL')[0]
    nxt = [e for e in r['events'] if e['idx'] in (rev['idx'], rev['idx'] + 1) and e['action'] == 'BREAKOUT']
    assert not nxt


def test_reversal_protect_is_latest_lower_high_not_top():
    # user case 2026-03: top 1.10, lower high 1.09, then break of protected 1.06 -> 戻り高値 = 1.09
    df, r = _run_synth([1.00, 1.05, 1.03, 1.08, 1.06, 1.10, 1.07, 1.09, 1.05])
    rp = acts(r, 'reversal_protect')[0]
    assert round(rp['price'], 2) == 1.09


def test_provisional_up_inside_major_down():
    # major down with 戻り高値 far above; inner higher lows/highs -> provisional up, major unchanged
    df, r = _run_synth([1.20, 1.10, 1.15, 1.00, 1.04, 1.02, 1.06, 1.03, 1.08, 1.05, 1.10])
    ps = [e for e in r['prov_events'] if e['action'] == 'PROV_START']
    assert ps and ps[0]['to'] == 'up'
    assert round(ps[0]['l2'], 2) == 1.03
    assert r['bars'][-1][0] == 'down'          # major still down
    assert r['prov_bars'][-1][0] == 'up'


def test_w_top_in_major_up():
    # up trend, A=1.10, B=1.07, C=1.095 (no close above A), then close below B
    df, r = _run_synth([1.00, 1.05, 1.03, 1.10, 1.07, 1.095, 1.06])
    w = r['w_events']
    assert len(w) == 1 and w[0]['action'] == 'W_TOP'
    assert round(w[0]['b'], 2) == 1.07


def test_prov_and_w_no_lookahead():
    df = load('H4')
    full = dow_trend.run(df, 'H4')
    cut = len(df) // 2
    part = dow_trend.run(df.iloc[:cut].reset_index(drop=True), 'H4')
    assert part['prov_bars'] == full['prov_bars'][:cut]
    assert part['w_events'] == [e for e in full['w_events'] if e['idx'] < cut]


def test_zone_geometry_and_expiry():
    from env_recognition import zones
    df, r = _run_synth([1.00, 1.05, 1.03, 1.08, 1.06, 1.10, 1.04, 1.07, 1.12])
    zs = zones.build(df, r)
    z = [z for z in zs if '押し安値' in z['sources']][0]
    assert z['kind'] == 'lo' and z['bottom'] <= z['top']
    assert abs(z['bottom'] - r['pivots'][[k for k, p in r['pivots'].items()
               if p['idx'] == z['anchor']][0]]['price']) < 1e-9      # outer edge = wick
    assert z['expiry'] is not None and z['expiry'] > z['activation']
    j = z['expiry']
    assert min(df.o[j], df.c[j]) > z['top']                          # whole body above


def test_zones_no_lookahead():
    from env_recognition import zones
    df = load('H4')
    full = zones.build(df, dow_trend.run(df, 'H4'))
    cut = len(df) // 2
    part_df = df.iloc[:cut].reset_index(drop=True)
    part = zones.build(part_df, dow_trend.run(part_df, 'H4'))
    strip = lambda z: {k: v for k, v in z.items() if k != 'expiry'}
    want = [z for z in full if z['activation'] < cut]
    assert [strip(z) for z in part] == [strip(z) for z in want]
    for a, b in zip(part, want):
        assert a['expiry'] == (b['expiry'] if b['expiry'] is not None and b['expiry'] < cut else None)
