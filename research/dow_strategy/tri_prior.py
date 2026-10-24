"""User (2026-10-20): a triangle/wedge is worth it after a clear trend move (+ some correction); if the part before the
contraction is a messy range, the contraction is just part of the range. Check on judged triangles and on all
automatic v2 triangles: prior move = net move over the 2x triangle length before the triangle (ATR) and its
efficiency (net / path). Usage: python tri_prior.py <trijudge dump dir>"""
import sys, json, glob
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import triangles as TR  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
pd.set_option('display.width', 200)
J = {}
for f in glob.glob(sys.argv[1] + '/*.json'):
    j = json.load(open(f)); J[(j['tf'], j['created'], j['shape'])] = j.get('v')
sec = lambda t: int((t - pd.Timestamp('1970-01-01')) // pd.Timedelta(seconds=1))
BLK = [2004, 2009, 2014, 2019, 2024, 2026]; LAB = ['05-09', '10-14', '15-19', '20-24', '25-26']
for tf in ('H4', 'M15', 'H1'):
    df, R = TR.FR[tf]; C = df.c.to_numpy(float); A = atr(df); T = pd.to_datetime(df.t)
    tri = TR.detect2(tf); out = TR.outcome(tf, tri).set_index('created')
    rows = []
    for x in tri:
        s0 = min(x['ih1'], x['il1']); n = max(10, 2 * x['len']); a = max(0, s0 - n)
        net = (C[s0] - C[a]) / A[s0]; path = np.abs(np.diff(C[a:s0 + 1])).sum() / A[s0]
        r = dict(tf=tf, year=T[x['created']].year, shape=x['shape'], prior=abs(net), prior_er=abs(net) / max(1e-9, path),
                 v=J.get((tf, sec(T[x['created']]), x['shape'])))
        if x['created'] in out.index:
            o = out.loc[x['created']]
            o = o.iloc[0] if isinstance(o, pd.DataFrame) else o
            r.update(f30=o.f30, with_higher=o.with_higher, with_prior=o.with_prior)
        rows.append(r)
    d = pd.DataFrame(rows)
    j = d[d.v.notna()].copy(); j['ok'] = j.v == 'ok'
    print(f'== {tf}: 判定 {len(j)}（○{int(j.ok.sum())}）')
    if len(j):
        print(j.groupby('ok')[['prior', 'prior_er']].median().round(2).to_string())
        j['q'] = pd.qcut(j.prior_er, 3, labels=['前がぐちゃぐちゃ', '中', '前がトレンド'], duplicates='drop')
        print(j.groupby('q', observed=True).ok.agg(['mean', 'size']).round(2).to_string())
    # all automatic triangles 2005-2026: outcome by prior efficiency (break with the prior move / higher TF)
    a = d[d.f30.notna() & (d.year >= 2005)].copy()
    a['q'] = pd.qcut(a.prior_er, 3, labels=['前がぐちゃぐちゃ', '中', '前がトレンド'])
    a['blk'] = pd.cut(a.year, BLK, labels=LAB)
    for nm, m in (('全部', a.f30 == a.f30), ('前の流れの向きに抜け', a.with_prior == True), ('前の流れ＆上位足の向き', (a.with_prior == True) & (a.with_higher == True))):
        x = a[m]
        for q in ('前がぐちゃぐちゃ', '前がトレンド'):
            y = x[x.q == q]; g = y.groupby('blk', observed=True).f30.mean()
            print(f'  {nm:12s} {q:8s} n={len(y):5d} 30本後{y.f30.mean():+.2f} | ' + ' '.join(f'{b}:{v:+.2f}' for b, v in g.items()))
