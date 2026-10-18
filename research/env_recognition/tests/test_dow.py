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


@pytest.mark.parametrize('tf', ['D1', 'H4'])
def test_no_lookahead(tf):
    df = load(tf)
    full = dow_trend.run(df, tf)
    for cut in (len(df) // 3, len(df) // 2, len(df) - 50):
        part = dow_trend.run(df.iloc[:cut].reset_index(drop=True), tf)
        assert part['bars'] == full['bars'][:cut]
        assert part['events'] == [e for e in full['events'] if e['idx'] < cut]


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
    # new protected high = raw top of the up epoch
    rp = acts(r, 'reversal_protect')[0]
    assert abs(rp['price'] - df.h.max()) < 1e-9


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
