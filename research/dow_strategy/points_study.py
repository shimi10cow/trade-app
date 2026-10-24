"""The user's 'want to enter' points (missed, kind=point): where are they, did an EA take them, what happens after
(forward move in ATR(H1)), and what structure is around them (H4/H1 trend + provisional, H1 SMA75 side, the latest
M15/H1 turn, distance from the last H1 swing)."""
import sys, json, glob, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import user_marks_study as U  # noqa: E402
B = U.B
FB = Path(sys.argv[1]); PF = Path(sys.argv[2])
M = [json.load(open(f)) for f in glob.glob(str(FB / 'missed' / '*.json'))]; M = [m.get('data', m) for m in M]
P = pd.DataFrame([m for m in M if m.get('kind') == 'point']); P['time'] = pd.to_datetime(P.t, unit='s')
A = pd.DataFrame(json.load(open(PF))['tr'], columns=['y', 'src', 'R', 'mfe', 't', 'side', 'n']); A['time'] = pd.to_datetime(A.t, unit='s')
T15 = B.T15; H, L, C = B.h, B.l, B.c; C1 = B.C1; A1 = U.A1
# provisional / major turn events on M15 and H1 (time available)
def evtimes(R, CL, machine):
    out = {'up': [], 'down': []}
    src = R['prov_events'] if machine == 'prov' else [e for e in R['events'] if e.get('machine') == 'major']
    for e in src:
        if e['action'] in ('REVERSAL', 'PROV_START') if machine == 'prov' else e['action'] == 'REVERSAL':
            out[e['to']].append(CL[e['idx']])
    return {k: sorted(v) for k, v in out.items()}
CL15 = list(T15 + pd.Timedelta(minutes=15))
E15p = evtimes(B.R15, CL15, 'prov'); E1p = evtimes(B.R1, C1, 'prov'); E1m = evtimes(B.R1, C1, 'major')
def since(E, t, d):
    v = E[d]; k = bisect.bisect_right(v, t) - 1
    return (t - v[k]).total_seconds() / 3600 if k >= 0 else np.nan
rows = []
for p in P.itertuples():
    t = p.time + pd.Timedelta(hours=1 if p.tf == 'H1' else 4 if p.tf == 'H4' else 0.25)   # the user clicks a bar; use its close
    s = p.side; d = 'up' if s == 1 else 'down'
    f = U.feats(t, s)
    i = T15.searchsorted(t); k1 = bisect.bisect_right(C1, t) - 1; a = A1[k1]
    fw = {}
    for hrs in (24, 72):
        j = min(i + hrs * 4, len(C) - 1)
        fw[f'up{hrs}'] = s * ((H[i:j].max() if s == 1 else L[i:j].min()) - p.p) / a
        fw[f'dn{hrs}'] = -s * ((L[i:j].min() if s == 1 else H[i:j].max()) - p.p) / a
    near = A[(A.side == s) & ((A.time - p.time).abs() <= pd.Timedelta(hours=12))]
    rows.append(dict(time=p.time, side=s, tf=p.tf, ea=','.join(sorted(set(near.src))) or '-', **f, **fw,
                     m15prov_h=since(E15p, t, d), h1prov_h=since(E1p, t, d), h1maj_h=since(E1m, t, d)))
D = pd.DataFrame(rows).sort_values('time')
D.to_csv(B.HERE / 'results' / 'user_points.csv', index=False)
print(f'入りたい点 {len(D)}件  買い{(D.side == 1).sum()} 売り{(D.side == -1).sum()} / 付けた足', D.tf.value_counts().to_dict())
print('年', D.time.dt.year.value_counts().sort_index().to_dict())
print(f"EAが前後12時間に同じ向きで入っていた: {(D.ea != '-').mean():.0%}", D.ea.value_counts().to_dict())
print('\n== その後の値動き（H1 ATR 単位、入りたい点の価格から）')
for h in (24, 72):
    print(f'  {h}時間: 順方向の最大 中央{D[f"up{h}"].median():.1f} / 逆方向の最大 中央{D[f"dn{h}"].median():.1f} / 順>逆2倍 {(D[f"up{h}"] > 2 * D[f"dn{h}"]).mean():.0%}')
print('\n== 環境（割合／中央値）')
print(f"  H4 本トレンド順 {D.h4.mean():.0%} / H4 仮順 {D.h4p.mean():.0%} / H1 本順 {D.h1.mean():.0%} / H1 仮順 {D.h1p.mean():.0%}")
print(f"  H1 SMA75 の有利側 {(D.h1ma75 > 0).mean():.0%}（中央 {D.h1ma75.median():+.1f}ATR） / H1 SMA200 有利側 {(D.h1ma200 > 0).mean():.0%} / H4 SMA75 からの距離 中央 {D.d75.median():+.1f} / レンジ度 中央 {D.rs.median():.2f} / H4 三角の最中 {D.tri4.mean():.0%}")
print(f"  直前の M15 仮転換（同じ向き）からの時間 中央 {D.m15prov_h.median():.1f}h（4h以内 {(D.m15prov_h <= 4).mean():.0%}）")
print(f"  直前の H1 仮転換から 中央 {D.h1prov_h.median():.0f}h / H1 本転換から 中央 {D.h1maj_h.median():.0f}h（24h以内 {(D.h1maj_h <= 24).mean():.0%}）")
print('\n== H4/H1 の組み合わせ')
D['combo'] = np.where(D.h4, 'H4順', 'H4逆') + '・' + np.where(D.h1, 'H1順', 'H1逆') + '/仮' + np.where(D.h1p, '順', '逆')
print(D.groupby('combo').agg(n=('side', 'size'), 順72h=('up72', 'median'), 逆72h=('dn72', 'median')).round(1).to_string())
