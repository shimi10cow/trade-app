"""Does the EURUSD zone bounce (against the H4 trend, price 0-2 ATR past the H4 SMA75; H4 zone, M5 turn, stop beyond the
zone) add anything to combo ④? Same-risk bootstrap."""
import numpy as np, pandas as pd, pfx, combo_stable as CS
S = CS.S
X = pd.read_pickle(f'{S}/feat/zone_exhaust_EURUSD.pkl')
keys4 = CS.P['④ ③＋US30（T・Q）']
for cfg in ('ZL_H4_m5_zone_be2', 'ZL_H4_m5_zone_tp3'):
    d = pd.read_csv(f'results/zone/{cfg}.csv'); d['t'] = pd.to_datetime(d.t); d['exit_t'] = pd.to_datetime(d.exit_t)
    x = X[X.cfg == cfg].reset_index(drop=True); m = x.against & (x.dev4 > 0) & (x.dev4 <= 2)
    z = pd.DataFrame(dict(R=d.R[m.to_numpy()], tt=d.t[m.to_numpy()], et=d.exit_t[m.to_numpy()])); z['key'] = 'ZB@EURUSD'; z['pair'] = 'EURUSD'
    print(cfg, len(z), '回', f"前半 {z[z.tt.dt.year<=2015].R.sum():+.1f}R 後半 {z[z.tt.dt.year>=2016].R.sum():+.1f}R", flush=True)
    base = CS.mk(keys4); base['tt'] = pd.to_datetime(base.tt); base['et'] = pd.to_datetime(base.et)
    pfx.ev(base, keys4, label='④ 基準')
    pfx.ev(base, keys4, z, label=f'④＋{cfg}')
