"""Data-side search for 'bad places' of the adopted/candidate EAs (2026-10-22).
For each EA and each entry feature, split trades by the feature's FIRST-HALF tertiles (numeric) or by value (flags,
side, Tokyo/London/NY session). A bucket counts as bad only if its mean R is negative in BOTH halves and removing it
raises total R in BOTH halves. Few features, fixed buckets, so the scan stays small."""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SPLIT = {'BTCUSD': ((2017, 2021), (2022, 2026))}; COST = {'XAUUSD': 2.5, 'BTCUSD': 8.0}
TARGET = [('EURUSD', 'R'), ('EURUSD', 'T'), ('EURUSD', 'L'), ('EURUSD', 'A'), ('EURUSD', 'C'), ('USDJPY', 'C'), ('USDJPY', 'J2'),
          ('XAUUSD', 'L'), ('XAUUSD', 'S'), ('BTCUSD', 'S'), ('GBPUSD', 'J3')]
NUM = ['h4_d75', 'h4_push', 'room_h4', 'rs']; FLAG = ['h4_prov_against', 'h1_prov_against', 'h1_major_against', 'm15_prov_against', 'side', 'sess']
NAMES = {'h4_d75': 'H4 SMA75からの距離', 'h4_push': 'H4の押し回数', 'room_h4': 'H4の抵抗までの余裕', 'rs': 'H4のレンジ度', 'h4_prov_against': 'H4仮ダウ逆',
         'h1_prov_against': 'H1仮ダウ逆', 'h1_major_against': 'H1本ダウ逆', 'm15_prov_against': 'M15仮ダウ逆', 'side': '売買', 'sess': '時間帯(日本時間)'}
def sess(t):
    h = (t.dt.hour + 7) % 24  # broker (≈UTC+2) -> JST
    return np.select([h.between(7, 14), h.between(15, 20)], ['東京7-14', '欧州15-20'], 'NY21-6')
found = []
for sym, ea in TARGET:
    D = pd.read_csv(f'{S}/feat/{sym}.csv', parse_dates=['t']); h1, h2 = SPLIT.get(sym, ((2005, 2015), (2016, 2026)))
    g = D[(D.ea == ea) & (D.year >= h1[0])].copy(); g['R'] = g.R - (COST.get(sym, 1.2) - 1.2) * 1e-4 / g.risk
    g['sess'] = sess(g.t); f = (g.year <= h1[1]).to_numpy(); A0, B0 = g[f].R.sum(), g[~f].R.sum()
    for c in NUM + FLAG:
        if c in NUM:
            x = g[c].astype(float); q = np.nanquantile(x[f], [1 / 3, 2 / 3])
            b = pd.Series(np.select([x <= q[0], x <= q[1]], ['低', '中'], '高'), index=g.index).where(x.notna(), 'なし')
        else:
            b = g[c].astype(str)
        for v in b.unique():
            m = (b == v).to_numpy()
            if m[f].sum() < 15 or m[~f].sum() < 15: continue
            ra, rb = g[f & m].R, g[~f & m].R
            if ra.mean() < 0 and rb.mean() < 0:
                found.append(dict(sym=sym, ea=ea, feat=NAMES[c], bucket=v, n1=int(m[f].sum()), n2=int(m[~f].sum()),
                                  mean1=ra.mean(), mean2=rb.mean(), base1=A0, base2=B0, new1=A0 - ra.sum(), new2=B0 - rb.sum(), cut=m.mean()))
F = pd.DataFrame(found); F.to_csv(f'{S}/feat/loser_scan.csv', index=False)
print(f'見つかった「前後半とも平均がマイナスの場面」: {len(F)} 件（調べた組み合わせ 約{len(TARGET) * 30}）')
pd.set_option('display.width', 220)
print(F.round(2).to_string(index=False))
