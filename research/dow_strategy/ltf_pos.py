"""Where is the entry on the daily / weekly chart? (user, 2026-10-23: how much does the weekly / daily position — Dow,
horizontal levels — affect the results). Everything from completed daily / weekly bars before the entry (causal),
and aligned with the trade side (for a sell, 'high' means near the lows, 'up' means a down trend):
  w52  : position in the 52-week high-low range (0 = at the far end against the trade, 1 = at the end in its favour)
  wdow : weekly Dow (fractal swings 2+2): 順 = last two swing highs and lows both moving with the trade, 逆 = against, 混在
  ddow : the same on daily bars (swings 3+3)
  wma  : weekly close above / below SMA20 of weekly closes, with / against the trade
  room : distance from the price to the nearest earlier weekly swing high above (for a buy) in weekly ATR(14);
         none = no earlier swing that far out (new highs)
Prints mean R by bucket and half: adopted EAs pooled, then per instrument."""
import numpy as np, pandas as pd
import trade_pool as TP
S = TP.S
SRC = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'}
X = TP.load_all()


def swings(b, k):
    hs, ls = [], []
    H, L = b.high.to_numpy(), b.low.to_numpy(); t = b.index
    for i in range(k, len(b) - k):
        if H[i] == H[i - k:i + k + 1].max(): hs.append((t[i + k], H[i]))       # known when the k-th bar after closes
        if L[i] == L[i - k:i + k + 1].min(): ls.append((t[i + k], L[i]))
    return hs, ls


def dow(hs, ls, tt):
    h = [p for tk, p in hs if tk < tt][-2:]; l = [p for tk, p in ls if tk < tt][-2:]
    if len(h) < 2 or len(l) < 2: return 0
    return 1 if (h[1] > h[0] and l[1] > l[0]) else (-1 if (h[1] < h[0] and l[1] < l[0]) else 0)


rows = []
for sym, g in X.groupby('pair'):
    f = SRC.get(sym, f'{S}/ws_{sym}/M15_broker.csv')
    m = pd.read_csv(f, parse_dates=['time']).set_index('time')
    agg = dict(open='first', high='max', low='min', close='last')
    W = m.resample('W-FRI', label='right', closed='right').agg(agg).dropna()
    W.index = W.index + pd.Timedelta('1D')                       # a week is complete after Friday
    D = m.resample('1D').agg(agg).dropna(); D.index = D.index + pd.Timedelta('1D')
    tr = np.maximum(W.high - W.low, np.maximum((W.high - W.close.shift()).abs(), (W.low - W.close.shift()).abs()))
    W['atr'] = tr.rolling(14).mean(); W['ma'] = W.close.rolling(20).mean()
    W['hi52'] = W.high.rolling(52).max(); W['lo52'] = W.low.rolling(52).min()
    wh, wl = swings(W, 2); dh, dl = swings(D, 3)
    px = m.close
    for x in g.itertuples():
        k = W.index.searchsorted(x.tt, 'right') - 1
        if k < 52: continue
        w = W.iloc[k]; p = px.iloc[max(px.index.searchsorted(x.tt) - 1, 0)]; s = x.side
        pos = (p - w.lo52) / (w.hi52 - w.lo52) if w.hi52 > w.lo52 else 0.5
        lv = [q for tk, q in (wh if s == 1 else wl) if tk < x.tt and (q - p) * s > 0]
        room = min(abs(q - p) for q in lv) / w.atr if lv else np.inf
        rows.append(dict(key=x.key, pair=sym, adopt=x.adopt, half=x.half, R=x.R,
                         w52=pos if s == 1 else 1 - pos, wdow=dow(wh, wl, x.tt) * s, ddow=dow(dh, dl, x.tt) * s,
                         wma=np.sign(w.close - w.ma) * s, room=room))
F = pd.DataFrame(rows)
F.to_pickle(f'{S}/feat/ltf_pos.pkl')
lab = {-1: '逆', 0: '混在', 1: '順'}
F['w52b'] = pd.cut(F.w52, [-1, .33, .67, 2], labels=['不利な端(安値圏で買い)', '中ほど', '有利な端(高値圏で買い)'])
F['wdowb'] = F.wdow.map(lab); F['ddowb'] = F.ddow.map(lab); F['wmab'] = F.wma.map({-1: '逆', 0: '逆', 1: '順'})
F['roomb'] = pd.cut(F.room, [-1, 0.5, 1.5, 4, np.inf], labels=['0.5未満', '0.5-1.5', '1.5-4', '4超/なし'])
pd.set_option('display.width', 220)
for col in ('w52b', 'wdowb', 'ddowb', 'wmab', 'roomb'):
    for nm, sub in (('採用EA計', F[F.adopt]), ('全EA計', F)):
        t = sub.groupby([col, 'half'], observed=True).R.agg(['size', 'mean', 'sum']).unstack('half').round(2)
        print(f'\n== {col} / {nm}'); print(t.to_string())
    t = F[F.adopt].groupby(['pair', col, 'half'], observed=True).R.agg(['size', 'mean']).unstack('half').round(2)
    print(f'-- {col} 銘柄別（採用EA）'); print(t.to_string())
