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


def trades_of(manual, keep_days, now):
    """2026-11-23 (user: "look at other weeks too"): the trader's own trades recorded in the app (real and missed) are places he
    wanted to enter as well -> {sym: [(broker time, side, 'real' / 'missed')]}, the last keep_days days"""
    from mt5_ea.live.trade_images import APP2SYM, jst_to_server
    out = {}
    for r in manual or []:
        te = jst_to_server(r.get('EntryDate'), r.get('EntryTime'))
        if te is None or pd.isna(te) or te < now - pd.Timedelta(days=keep_days):
            continue
        p = str(r.get('PairName（元）') or r.get('PairName') or '').upper().strip()
        side = 1 if str(r.get('Direction') or '').lower().startswith('b') else -1
        out.setdefault(APP2SYM.get(p, p), []).append((te, side, 'missed' if '見逃し' in str(r.get('ステータス') or '') else 'real'))
    return out


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
                    out.setdefault(sym[5:], []).append((te, 1 if l['type'] == 'eb' else -1, 'mark'))
    return out


def study(b, pairs, days, marks, say=print):
    rows, noise = [], []
    from mt5_ea.live import pair_env
    now = pd.Timestamp.now(tz='UTC').tz_localize(None)
    for sym in sorted(set(pairs) | set(marks)):
        ms = marks.get(sym, [])
        back = max([days] + [int((now - x[0]) / pd.Timedelta(days=1)) + 3 for x in ms])
        try:
            m = pair_env.bars_any(b, sym, back + alerts.DAYS + 5)
            mk = alerts.Market(sym, m.reset_index(drop=True))
        except Exception as ex:
            say(f'  {sym:7s} とばした（{str(ex)[:60]}）'); continue
        end = pd.Timestamp(m.t.iat[-1]); since = end - pd.Timedelta(days=days)
        ms = [x for x in ms if x[0] >= pd.Timestamp(m.t.iat[0]) + pd.Timedelta(days=alerts.DAYS)]   # enough history before it
        for name, brk, zone in VARIANTS:
            pr = profs_for(brk, 'turn'); st = {'zone': zone}
            al = {t: alerts.evaluate(mk, profs_for(brk, t), min([since] + [x[0] - pd.Timedelta(days=3) for x in ms])) for t in ('turn', 'tl15')}
            for te, side, src in ms:                               # catch
                lead = None
                for h in range(0, 49, 2):
                    i = int(np.searchsorted(mk.CL, np.datetime64(te - pd.Timedelta(hours=h)), side='right')) - 1
                    if i > 0 and any(x['side'] == side for x in alerts.armed(mk, pr, at=i, star=st)):
                        lead = h; break
                near = {t: any(a['side'] == side and abs((pd.Timestamp(a['t']) - te) / pd.Timedelta(hours=1)) <= 24 for a in al[t]) for t in al}
                rows.append(dict(variant=name, src=src, pair=sym, t=str(te)[:16], side=side, star=lead is not None, starLead=lead, turn=near['turn'], tl15=near['tl15']))
            # noise over the period: every 4 hours
            i0 = int(np.searchsorted(mk.CL, np.datetime64(since))); on = 0; eps = 0; prev = set()
            idx = range(max(i0, 1), len(mk.TM), 16)
            for i in idx:
                cur = {(x['side'], x['line']) for x in alerts.armed(mk, pr, at=i, star=st)}
                on += bool(cur); eps += len(cur - prev); prev = cur
            wk = days / 7
            if sym not in pairs:
                continue
            noise.append(dict(variant=name, pair=sym, starOn=on / max(1, len(idx)), starPerWeek=eps / wk,
                              turnPerWeek=sum(1 for a in al['turn'] if pd.Timestamp(a['t']) >= since) / wk,
                              tl15PerWeek=sum(1 for a in al['tl15'] if pd.Timestamp(a['t']) >= since) / wk))
        say(f'  {sym:7s} 済み（印 {len(ms)}）')
    return pd.DataFrame(rows), pd.DataFrame(noise)


def summary(R, N, src=None):
    out = []
    for name, _, _ in VARIANTS:
        r = R[(R.variant == name) & ((R.src == src) if src else True)] if len(R) else R; n = N[N.variant == name]
        k = len(r)
        out.append({'形': name, '印': k,
                    '⭐ が付いていた': f"{r.star.sum()}/{k}" if k else '—', '通知 今の形': f"{r.turn.sum()}/{k}" if k else '—', '通知 新しい形': f"{r.tl15.sum()}/{k}" if k else '—',
                    '⭐ の時間（1 ペア平均）': f"{n.starOn.mean() * 100:.0f}%", '⭐ 週あたり（全ペア）': round(n.starPerWeek.sum(), 1),
                    '通知 今の形 週あたり': round(n.turnPerWeek.sum(), 1), '通知 新しい形 週あたり': round(n.tl15PerWeek.sum(), 1)})
    return pd.DataFrame(out)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=90); ap.add_argument('--pairs', default='')
    ap.add_argument('--trade-days', type=int, default=365)
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
    try:
        man = gas.call('eaReportData', {}, timeout=120).get('manual') or []
    except Exception:
        man = []
    for k, v in trades_of(man, a.trade_days, pd.Timestamp.now(tz='UTC').tz_localize(None)).items():
        marks.setdefault(k, []).extend(v)
    pairs = [p.strip().upper() for p in a.pairs.split(',') if p.strip()] or list(alerts.PAIRS)
    cnt = lambda s_: sum(1 for v in marks.values() for x in v if x[2] == s_)
    say(f"⭐ と通知の比べ：今週の印 {cnt('mark')}・実トレード {cnt('real')}・見逃し {cnt('missed')}（直近 {a.trade_days} 日）、"
        f"うるささは直近 {a.days} 日・{len(pairs)} ペア（注文はしません、10〜20 分）")
    R, N = study(MT5Broker(), pairs, a.days, marks, say)
    out = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data') / 'reports'; out.mkdir(parents=True, exist_ok=True)
    R.to_csv(out / 'alert_study_marks.csv', index=False, encoding='utf-8-sig'); N.to_csv(out / 'alert_study_noise.csv', index=False, encoding='utf-8-sig')
    say('\n== 全部 ==\n' + summary(R, N).to_string(index=False))
    for s_, nm in (('mark', '今週の印'), ('real', '実トレード'), ('missed', '見逃し')):
        if len(R) and (R.src == s_).any():
            say(f'\n== {nm} ==\n' + summary(R, N, s_).iloc[:, :5].to_string(index=False))
    say(f'\n保存: {out / "alert_study_marks.csv"}・{out / "alert_study_noise.csv"}')


if __name__ == '__main__':
    main()
