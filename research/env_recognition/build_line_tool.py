"""Build the manual trendline drawing tool: python -m env_recognition.build_line_tool out.html"""
import json
import sys
from pathlib import Path
import pandas as pd
from .data import load
from .pivots import pivot_events, final_pivots
from .build_html import epoch_s

TEMPLATE = Path(__file__).with_name('line_tool_template.html')
SHOW = {'W1': 615, 'D1': 800, 'H4': 1500, 'H1': 2000, 'M15': 3000}


def payload(tf):
    df = load(tf)
    n = len(df); s0 = max(0, n - SHOW[tf])
    t = epoch_s(df.t)
    r5 = lambda x: round(float(x), 5)
    sma = {p: df.c.rolling(p).mean() for p in (20, 75)}
    piv = [[t[p['idx']], p['kind'], r5(p['price'])] for p in final_pivots(pivot_events(df)) if p['idx'] >= s0]
    return dict(c=[[t[i], r5(df.o[i]), r5(df.h[i]), r5(df.l[i]), r5(df.c[i])] for i in range(s0, n)],
                s20=[[t[i], r5(sma[20][i])] for i in range(s0, n) if pd.notna(sma[20][i])],
                s75=[[t[i], r5(sma[75][i])] for i in range(s0, n) if pd.notna(sma[75][i])],
                piv=piv)


if __name__ == '__main__':
    data = {tf: payload(tf) for tf in ('W1', 'D1', 'H4', 'H1', 'M15')}
    html = TEMPLATE.read_text(encoding='utf-8').replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    Path(sys.argv[1]).write_text(html, encoding='utf-8')
    print(sys.argv[1], round(len(html) / 1e6, 2), 'MB')
