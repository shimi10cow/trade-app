"""Gold right shoulder: stop above the left shoulder (adopted) vs above the right shoulder, buys only (2026-10-24).
Same-risk comparison and fixed 0.75 % within the adopted set (incl. US500 buy shoulder)."""
import numpy as np, pandas as pd, pfx, port_ds2 as P2, port_ds_us500 as PU
CS = P2.CS; S = CS.S
X = pd.concat([P2.X1, PU.U], ignore_index=True); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
base = X[X.key != 'DS@XAUUSD']; keys = list(X.key.unique())


def gold(stop, ex, buy):
    d = pd.read_csv(f'{S}/ws_XAUUSD/research/dow_strategy/results/ds/DS_H1_{stop}_{ex}.csv')
    d = d[d.tag.str.split('|').str[2].astype(float) >= 4]
    if buy: d = d[d.side == 1]
    return pd.DataFrame(dict(R=d.R - 1.3e-4 / d.risk, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), key='DS@XAUUSD', pair='XAUUSD'))


for lab, g in (('左肩・両方・2R（今の採用）', gold('left', 'tp2', False)), ('左肩・買い・2R', gold('left', 'tp2', True)),
               ('右肩・買い・H1トレール', gold('shoulder', 'h1', True)), ('右肩・買い・2R', gold('shoulder', 'tp2', True)),
               ('右肩・両方・H1トレール', gold('shoulder', 'h1', False))):
    Y = pd.concat([base, g], ignore_index=True)
    pfx.ev(Y, keys, label=f'ゴールド右肩 {lab}（{len(g)}回）')
    c, dd, y, n = CS.fixed(Y, 0.0075); print(f'    0.75%固定 年利 {c:.1%} 最大DD {dd:.1%}')
