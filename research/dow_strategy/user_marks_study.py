"""Compare the user's wanted entry points (missed/kind=point) with the EA trades (skip vs not) in the same years:
did an EA enter near the point, and how do the H1/H4 states and positions differ?"""
import sys, json, glob, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_ctx as EC  # noqa: E402
import dow_turn_ea as B  # noqa: E402
FB = Path(sys.argv[1]) if __name__ == "__main__" else None; PF = Path(sys.argv[2]) if __name__ == "__main__" else None
C1 = list(B.C1); C4 = list(B.C4); h1c = B.h1.c.to_numpy(float); s75 = B.h1.c.rolling(75).mean().to_numpy(); s200 = B.h1.c.rolling(200).mean().to_numpy()
from env_recognition.pivots import atr
A1 = atr(B.h1)
def feats(t, s):
    t = pd.Timestamp(t); k1 = bisect.bisect_right(C1, t) - 1; k4 = bisect.bisect_right(C4, t) - 1; dd = 'up' if s == 1 else 'down'
    c = EC.ctx_at(t, s)
    return dict(h1=B.R1['bars'][k1][0] == dd, h1p=B.R1['prov_bars'][k1][0] == dd, h4=B.R4['bars'][k4][0] == dd, h4p=B.R4['prov_bars'][k4][0] == dd,
                h1ma75=s * (h1c[k1] - s75[k1]) / A1[k1], h1ma200=s * (h1c[k1] - s200[k1]) / A1[k1], d75=c['d75'], sh=c['sh'], rs=c['rs'], tri4=EC.tri_active(t, 'H4'))
if __name__ == '__main__':
    M = [json.load(open(f)) for f in glob.glob(str(FB / 'missed' / '*.json'))]; M = [m.get('data', m) for m in M]
    P = pd.DataFrame([m for m in M if m.get('kind') == 'point']); P['time'] = pd.to_datetime(P.t, unit='s')
    A = pd.DataFrame(json.load(open(PF))['tr'], columns=['y', 'src', 'R', 'mfe', 't', 'side', 'n']); A['time'] = pd.to_datetime(A.t, unit='s')
    fb = {}
    for f in glob.glob(str(FB / 'feedback' / '*.json')):
        d = json.load(open(f)); d = d.get('data', d); fb[Path(f).stem] = d
    A['tag'] = [(fb.get(f't{t}_{s}_{c}') or {}).get('entry') for t, s, c in zip(A.t, A.side, A.src)]
    print('== 入りたい点 と EAのエントリー（同じ向き、前後12時間）')
    for p in P.sort_values('t').itertuples():
        near = A[(A.side == p.side) & ((A.time - p.time).abs() <= pd.Timedelta(hours=12))]
        f = feats(p.time, p.side)
        print(f"{p.time:%Y-%m-%d %H:%M} {'買' if p.side == 1 else '売'} EA: {','.join(f'{r.src}({(r.time - p.time).total_seconds() / 3600:+.0f}h,{r.R:+.1f})' for r in near.itertuples()) or 'なし':28s}"
              f" H4{'順' if f['h4'] else '逆'}/仮{'順' if f['h4p'] else '逆'} H1{'順' if f['h1'] else '逆'}/仮{'順' if f['h1p'] else '逆'} H1MA75から{f['h1ma75']:+.1f}ATR H4SMA75から{f['d75']:+.1f}")
    yrs = sorted(set(P.time.dt.year) & {2006, 2007})
    a = A[A.y.isin(yrs)].copy()
    rows = [dict(grp=('いらない' if r.tag == 'skip' else '良い' if r.tag == 'good' else '未チェック'), R=r.R, **feats(r.time, r.side)) for r in a.itertuples()]
    rows += [dict(grp='入りたい点', R=np.nan, **feats(p.time, p.side)) for p in P[P.time.dt.year.isin(yrs)].itertuples()]
    D = pd.DataFrame(rows)
    print('\n== 2006-2007 グループ別（平均）')
    print(D.groupby('grp').agg(n=('h1', 'size'), R合計=('R', 'sum'), H4順=('h4', 'mean'), H4仮順=('h4p', 'mean'), H1順=('h1', 'mean'), H1仮順=('h1p', 'mean'),
                               H1MA75=('h1ma75', 'median'), H1MA200=('h1ma200', 'median'), H4SMA75=('d75', 'median'), レンジ度=('rs', 'median')).round(2).to_string())
