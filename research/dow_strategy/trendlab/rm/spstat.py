import pandas as pd, numpy as np
S = ('EURUSD', 'USDJPY', 'XAUUSD')
def stats(x, col, tcol):
    x = x.dropna(subset=[col]).copy(); x['tt'] = pd.to_datetime(x[tcol]); x = x.sort_values('tt'); r = x[col].to_numpy()
    if len(r) < 3: return None
    eq = np.cumsum(r); pk = np.maximum.accumulate(np.r_[0, eq])[1:]; dd = pk - eq
    e = p_ = 1.0; m = 0.0
    for v in r: e *= 1 + 0.01 * v; p_ = max(p_, e); m = min(m, e / p_ - 1)
    ls = mx = 0
    for v in r: ls = ls + 1 if v < 0 else 0; mx = max(mx, ls)
    pk_t = x.tt.iat[0]; lw = pd.Timedelta(0)
    for k in range(len(r)):
        if dd[k] == 0: pk_t = x.tt.iat[k]
        else: lw = max(lw, x.tt.iat[k] - pk_t)
    yr = x.groupby(x.tt.dt.year)[col].sum(); s = np.sort(r)[::-1]; w = r[r > 0]; lo = r[r <= 0]
    return dict(回数=len(r), 年=round(len(r) / 22, 1), 勝率=f'{(r > 0).mean():.0%}', 平均=round(r.mean(), 2), 合計=round(r.sum(), 1),
                t=round(r.mean() / (r.std(ddof=1) / np.sqrt(len(r))), 2), 前半=round(x[x.tt < '2016'][col].sum(), 1), 後半=round(x[x.tt >= '2016'][col].sum(), 1),
                勝ち=round(w.mean(), 2), 負け=round(lo.mean(), 2), PF=round(w.sum() / -lo.sum(), 2) if lo.sum() < 0 else np.inf,
                上位5=f'{s[:5].sum() / r.sum():.0%}' if r.sum() > 0 else '-', 最大DD_R=round(dd.max(), 1), DD_1pct=f'{m:.1%}', 最大連敗=mx,
                水面下_日=lw.days, 最悪年=f'{yr.idxmin()} {yr.min():+.1f}', マイナス年=f'{(yr < 0).sum()}/{len(yr)}')
pd.set_option('display.width', 300)
for st in ('LO', 'LO5'):
    r = pd.concat([pd.read_pickle(f'sp_{s}_{st}.pkl') for s in S])
    r['first_t'] = r[['ST_t', 'D_t']].min(axis=1)
    rows = []
    for col, tcol, lab in (('D', 'D_t', 'D 全部ダウで入る'), ('ST', 'ST_t', 'ST 全部ストキャス'), ('SP', 'first_t', 'SP 半分ずつ'), ('SPX', 'first_t', 'SPX 半分ずつ＋撤退')):
        z = stats(r, col, tcol)
        if z: rows.append(dict(損切り=st, 形=lab, 銘柄='3通貨', **z))
        for s in S:
            z = stats(r[r.sym == s], col, tcol)
            if z: rows.append(dict(損切り=st, 形=lab, 銘柄=s, **z))
    print(pd.DataFrame(rows).to_string(index=False)); print()
    b = r[r.hasD & r.hasST]; print(st, 'D と ST が両方ある形', len(b), 'ST だけ', (r.hasST & ~r.hasD).sum(), 'D だけ', (r.hasD & ~r.hasST).sum(),
          '| ST だけの形の ST %+.2f STX %+.2f' % (r[r.hasST & ~r.hasD].ST.mean(), r[r.hasST & ~r.hasD].STX.mean()))
