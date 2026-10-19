"""Entry viewer for the MA EA + Dow filter trades (62 trades, 2025-02..2026-10).

python dow_strategy/build_trade_viewer.py out.html   (needs EA_M15_CACHE=<M15 csv>)
Reuses env_recognition chart payloads (Dow pivots, protected swings, provisional trend, W, zones,
trendlines, SMA) over the full available range and adds the trades.
"""
import json
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'dow_strategy'))
from env_recognition import build_html as B  # noqa: E402
import ma_ea_zones_lines as M  # noqa: E402

TEMPLATE = Path(__file__).with_name('trade_viewer_template.html')


def trades():
    A = M.E.run_pair('EURUSD', M.E.Config(extra_filter=M.M_filter if hasattr(M, 'M_filter') else M.dow_ok))
    out = []
    for n, x in enumerate(A.sort_values('time').itertuples(), 1):
        st = M.state(x.time)
        corr = any(l['cls'] == 'correction' and l['broken'] for l in st['H4']['lines'])
        sec = lambda ts: int((pd.Timestamp(ts) - pd.Timestamp('1970-01-01')) // pd.Timedelta(seconds=1))
        out.append(dict(n=n, t=sec(x.time), side=int(x.side), p=int(x.point), entry=round(x.entry, 5),
                        sl=round(x.initial_sl, 5), xt=sec(x.ExitTime), xp=round(float(x.exit), 5),
                        R=round(float(x.R - M.COST / x.risk), 2), risk=round(x.risk / 1e-4, 1), corr=corr,
                        trail=x.trail_reason or '', h1=st['H1']['trend'], h4=st['H4']['trend'], d1=st['D1']['trend']))
    return out


if __name__ == '__main__':
    B.SHOW = {k: 10 ** 6 for k in B.SHOW}          # whole available range
    data = {tf: B.tf_payload(tf) for tf in ('W1', 'D1', 'H4', 'H1', 'M15')}
    data['trades'] = trades()
    html = TEMPLATE.read_text(encoding='utf-8').replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    Path(sys.argv[1]).write_text(html, encoding='utf-8')
    print(sys.argv[1], round(len(html) / 1e6, 2), 'MB', len(data['trades']), 'trades')
