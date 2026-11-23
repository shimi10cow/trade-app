"""Study of the alert timings before turning one on (2026-11-22, user: "test first how often it rings and how far it runs").
For every FX pair over the last N days (the M15 history MT5 already keeps): the alerts of the presets (methods 1 / 2 / 6 / 7) with
  turn = the current one (back within 0.3 ATR(H4) of the H4 line, then the M15 Dow turn)
  tl15 = the new one   (within 2.5 ATR(H4) of the line after leaving it, on the M15 trendline break)
and what came after each: stop = the M15 swing of the last 4 hours (+0.1 ATR(H1)), then within 5 days: did +1R / +2R / +3R come before
the stop, and the largest R before the stop. Read only, no orders.
  python -m mt5_ea.live.alert_study [--days 540] [--pairs EURUSD,AUDJPY]   -> TradeEA_data/reports/alert_study.csv and a summary."""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from mt5_ea.live import alerts


def outcome(mk, a, k):
    """a: an alert of evaluate (t, price, side); k: price factor. -> dict(r1, r2, r3, maxR, stop) on the M15 bars after it"""
    s = a['side']; te = np.datetime64(pd.Timestamp(a['t'])); i = int(np.searchsorted(mk.CL, te, side='right')) - 1
    if i < 20:
        return None
    en = mk.MC[i]; lo, hi = mk.ML[i - 15:i + 1].min(), mk.MH[i - 15:i + 1].max()
    a1 = float(np.nanmean(mk.MH[i - 15:i + 1] - mk.ML[i - 15:i + 1])) * 2          # ~ ATR(H1)
    sl = (lo - 0.1 * a1) if s > 0 else (hi + 0.1 * a1); risk = s * (en - sl)
    if not risk > 0:
        return None
    best, stop = 0.0, False
    for j in range(i + 1, min(i + 1 + 5 * 96, len(mk.MC))):
        adv = s * ((mk.MH[j] if s > 0 else mk.ML[j]) - en) / risk; bad = s * ((mk.ML[j] if s > 0 else mk.MH[j]) - en) / risk
        if bad <= -1:
            stop = True; break
        best = max(best, adv)
    return dict(r1=best >= 1, r2=best >= 2, r3=best >= 3, maxR=round(best, 2), stop=stop, riskATR=round(risk / (a['atr'] / k), 2) if a.get('atr') else None)


def study(b, pairs, days, say=print):
    rows = []
    T = {'turn': [dict(p, timing='turn', timings=['turn']) for p in alerts.PRESETS],
         'tl15': [dict(p, id=p['id'] + 'z', timing='tl15', timings=['tl15']) for p in alerts.PRESETS]}
    for sym in pairs:
        try:
            m = b.bars(sym, days + alerts.DAYS)
            mk = alerts.Market(sym, m.reset_index(drop=True))
        except Exception as ex:
            say(f'  {sym:7s} とばした（{str(ex)[:60]}）'); continue
        since = pd.Timestamp(m.t.iat[-1]) - pd.Timedelta(days=days)
        n = {}
        for name, profs in T.items():
            for a in alerts.evaluate(mk, profs, since):
                o = outcome(mk, a, mk.k)
                if o:
                    rows.append(dict(pair=sym, timing=name, t=str(a['t'])[:16], side=a['side'], method=a.get('method'), kind=a.get('kind'), **o))
                    n[name] = n.get(name, 0) + 1
        say(f"  {sym:7s} 今の形 {n.get('turn', 0)} 回 · 新しい形 {n.get('tl15', 0)} 回")
    return pd.DataFrame(rows)


def summary(df, days, npairs):
    out = []
    for name, g in df.groupby('timing'):
        out.append(dict(形={'turn': '今の形（線に触って M15 転換）', 'tl15': '新しい形（2.5ATR 以内で M15 TL 抜け）'}[name], 回数=len(g),
                        週あたり_全ペア=round(len(g) / (days / 7), 1), **{'+1R 先に': f"{g.r1.mean() * 100:.0f}%", '+2R 先に': f"{g.r2.mean() * 100:.0f}%",
                        '+3R 先に': f"{g.r3.mean() * 100:.0f}%", '損切りまでの最大R（中央）': g.maxR.median()}))
    return pd.DataFrame(out)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=540); ap.add_argument('--pairs', default='')
    a = ap.parse_args(argv)
    from mt5_ea.live.broker import MT5Broker
    path = os.getenv('EA_ALERT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or ''
    if path:
        os.environ['EA_MT5_PATH'] = path
    say = lambda x: print(x, flush=True)
    pairs = [p.strip().upper() for p in a.pairs.split(',') if p.strip()] or list(alerts.PAIRS)
    say(f'通知の形の比べ：直近 {a.days} 日、{len(pairs)} ペア（注文はしません、数分かかります）')
    df = study(MT5Broker(), pairs, a.days, say)
    out = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data') / 'reports'; out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / 'alert_study.csv', index=False, encoding='utf-8-sig')
    if len(df):
        say('\n' + summary(df, a.days, len(pairs)).to_string(index=False))
        say('\n新しい形の手法ごと：'); say(df[df.timing == 'tl15'].groupby('method').agg(回数=('r1', 'size'), r1=('r1', 'mean'), r2=('r2', 'mean'), maxR=('maxR', 'median')).round(2).to_string())
    say(f'\n保存: {out / "alert_study.csv"}')


if __name__ == '__main__':
    main()
