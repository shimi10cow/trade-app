"""How well the ⭐ and the alerts notice the trader's areas (2026-11-23, user: "I only want to know price came into the area; whether
it runs is the EAs' job"). Two things per variant:
  catch  - of the trader's 「買いたい所 / 売りたい所」 marks (report chart analysis): was the ⭐ on within 48 h before it, did an alert
           come within 24 h of it (same side)
  noise  - over the last `days` days, FX 25 pairs: alerts per week, ⭐ episodes per week and the share of time a ⭐ is on
Variants: the line as now (any H4 close beyond ends it) / as an area (only an H4 close 0.5 ATR beyond ends it); the ⭐ zone 2.5 / 3.0 ATR;
the alert timing turn (touch the line, M15 Dow turn) / tl15 (within the zone, M15 trendline break). Read only, no orders.
  python -m mt5_ea.live.alert_study [--days 90]   -> TradeEA_data/reports/alert_study.csv and a summary"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from mt5_ea.live import alerts

VARIANTS = [('今の線・⭐2.5', 0.0, 2.5), ('エリア・⭐2.5', 0.5, 2.5), ('今の線・⭐3.0', 0.0, 3.0), ('エリア・⭐3.0', 0.5, 3.0)]


def profs_for(brk, timing):
    return [dict(p, id=p['id'] + timing + str(brk), timing=timing, timings=[timing], brk=brk) for p in alerts.PRESETS]


def marks_of(repmarks):
    from mt5_ea.live.trade_images import jmin_to_server
    out = {}
    for sym, v in (repmarks or {}).items():
        if not str(sym).startswith('PAIR|'):
            continue
        for l in v.get('lines') or []:
            if isinstance(l, dict) and l.get('type') in ('eb', 'es') and not l.get('del'):
                te = jmin_to_server(l.get('t1'))
                if te is not None:
                    out.setdefault(sym[5:], []).append((te, 1 if l['type'] == 'eb' else -1))
    return out


def study(b, pairs, days, marks, say=print):
    rows, noise = [], []
    for sym in sorted(set(pairs) | set(marks)):
        try:
            m = b.bars(sym, days + alerts.DAYS + 5)
            mk = alerts.Market(sym, m.reset_index(drop=True))
        except Exception as ex:
            say(f'  {sym:7s} とばした（{str(ex)[:60]}）'); continue
        end = pd.Timestamp(m.t.iat[-1]); since = end - pd.Timedelta(days=days)
        ms = marks.get(sym, [])
        for name, brk, zone in VARIANTS:
            pr = profs_for(brk, 'turn'); st = {'zone': zone}
            al = {t: alerts.evaluate(mk, profs_for(brk, t), min([since] + [x[0] - pd.Timedelta(days=3) for x in ms])) for t in ('turn', 'tl15')}
            for te, side in ms:                                    # catch
                lead = None
                for h in range(0, 49, 2):
                    i = int(np.searchsorted(mk.CL, np.datetime64(te - pd.Timedelta(hours=h)), side='right')) - 1
                    if i > 0 and any(x['side'] == side for x in alerts.armed(mk, pr, at=i, star=st)):
                        lead = h; break
                near = {t: any(a['side'] == side and abs((pd.Timestamp(a['t']) - te) / pd.Timedelta(hours=1)) <= 24 for a in al[t]) for t in al}
                rows.append(dict(variant=name, pair=sym, t=str(te)[:16], side=side, star=lead is not None, starLead=lead, turn=near['turn'], tl15=near['tl15']))
            # noise over the period: every 4 hours
            i0 = int(np.searchsorted(mk.CL, np.datetime64(since))); on = 0; eps = 0; prev = set()
            idx = range(max(i0, 1), len(mk.TM), 16)
            for i in idx:
                cur = {(x['side'], x['line']) for x in alerts.armed(mk, pr, at=i, star=st)}
                on += bool(cur); eps += len(cur - prev); prev = cur
            wk = days / 7
            noise.append(dict(variant=name, pair=sym, starOn=on / max(1, len(idx)), starPerWeek=eps / wk,
                              turnPerWeek=sum(1 for a in al['turn'] if pd.Timestamp(a['t']) >= since) / wk,
                              tl15PerWeek=sum(1 for a in al['tl15'] if pd.Timestamp(a['t']) >= since) / wk))
        say(f'  {sym:7s} 済み（印 {len(ms)}）')
    return pd.DataFrame(rows), pd.DataFrame(noise)


def summary(R, N):
    out = []
    for name, _, _ in VARIANTS:
        r = R[R.variant == name] if len(R) else R; n = N[N.variant == name]
        k = len(r)
        out.append({'形': name, '印': k,
                    '⭐ が付いていた': f"{r.star.sum()}/{k}" if k else '—', '通知 今の形': f"{r.turn.sum()}/{k}" if k else '—', '通知 新しい形': f"{r.tl15.sum()}/{k}" if k else '—',
                    '⭐ の時間（1 ペア平均）': f"{n.starOn.mean() * 100:.0f}%", '⭐ 週あたり（全ペア）': round(n.starPerWeek.sum(), 1),
                    '通知 今の形 週あたり': round(n.turnPerWeek.sum(), 1), '通知 新しい形 週あたり': round(n.tl15PerWeek.sum(), 1)})
    return pd.DataFrame(out)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=90); ap.add_argument('--pairs', default='')
    a = ap.parse_args(argv)
    from mt5_ea.live import gas
    from mt5_ea.live.broker import MT5Broker
    path = os.getenv('EA_ALERT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or ''
    if path:
        os.environ['EA_MT5_PATH'] = path
    say = lambda x: print(x, flush=True)
    try:
        rm = {str(r.get('ID')): {'lines': json.loads(r.get('Lines') or '[]')} for r in (gas.call('eaReportData', {}, timeout=120).get('repmarks') or [])}
    except Exception as ex:
        say(f'  印を読めませんでした（{ex}）'); rm = {}
    marks = marks_of(rm)
    pairs = [p.strip().upper() for p in a.pairs.split(',') if p.strip()] or list(alerts.PAIRS)
    say(f'⭐ と通知の比べ：印 {sum(len(v) for v in marks.values())} か所、うるささは直近 {a.days} 日・{len(pairs)} ペア（注文はしません、10 分ほど）')
    R, N = study(MT5Broker(), pairs, a.days, marks, say)
    out = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data') / 'reports'; out.mkdir(parents=True, exist_ok=True)
    R.to_csv(out / 'alert_study_marks.csv', index=False, encoding='utf-8-sig'); N.to_csv(out / 'alert_study_noise.csv', index=False, encoding='utf-8-sig')
    say('\n' + summary(R, N).to_string(index=False))
    say(f'\n保存: {out / "alert_study_marks.csv"}・{out / "alert_study_noise.csv"}')


if __name__ == '__main__':
    main()
