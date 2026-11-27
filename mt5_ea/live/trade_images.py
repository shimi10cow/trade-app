"""Chart images for discretionary trades from the MT5 import (2026-11-22, user: no more manual screenshots).

The alerts window (demo MT5, which has the bars) asks GAS once an hour for recorded MT5 trades without images (eaNeedImages),
draws for each: entry H4 + entry M15 (ChartImage / ChartImage2) and, when closed, exit H4 + exit M15 (決済チャート / 決済チャート2),
with the EA lines as they were at the entry (alerts.ea_chart_objects on the bars up to the entry) and sends them (eaEntryImages).
GAS fills only empty image fields (a hand-made image is never replaced). Read only: never orders. `python -m mt5_ea.live.trade_images`
runs it once by hand (--limit N, --dry: draw into TradeEA_data/trade_images without sending)."""
import base64
import logging
import os
from pathlib import Path

import pandas as pd

from mt5_ea.live import alerts, pair_env, tradechart

SERVER_TZ, JST = 'Europe/Athens', 'Asia/Tokyo'
APP2SYM = {'GOLD': 'XAUUSD', 'SILVER': 'XAGUSD', 'NGAS': 'NATGAS'}


def jst_to_server(d, t):
    s = f"{str(d).replace('/', '-')[:10]} {str(t or '00:00')[:5]}"
    x = pd.to_datetime(s, errors='coerce')
    return pd.NaT if pd.isna(x) else x.tz_localize(JST).tz_convert(SERVER_TZ).tz_localize(None)


def num(v):
    try:
        f = float(v)
        return f if f == f and f != 0 else None
    except Exception:
        return None


def jmin_to_server(v):
    """the report's times (Japan-time minutes) -> broker time"""
    try:
        return pd.Timestamp(int(v) * 60, unit='s').tz_localize(JST).tz_convert(SERVER_TZ).tz_localize(None)
    except Exception:
        return None


def report_lines(ls):
    """the trader's saved lines of the pair (report's chart analysis) -> draw_tf lines: 抵抗体 (EA bands he kept), his own lines,
    boxes and trendlines, and EA lines he moved (their moved place)"""
    out = []
    for l in ls:
        t1 = jmin_to_server(l.get('t1')); tf = l.get('tf') or 'H4'
        if t1 is None or l.get('p1') is None:
            continue
        ty, kind = l.get('type'), l.get('kind')
        if ty in ('h', 'x') or (ty == 'ea'):
            k = 'band' if kind == 'band' else (kind if ty == 'ea' else 'user')
            out.append(dict(type='h', kind=k, tf=tf, side=0, t1=t1, p1=float(l['p1']), t2=None, p2=None, note=l.get('note')))
        elif ty in ('t', 'b') and l.get('t2') is not None:
            t2 = jmin_to_server(l['t2'])
            if t2 is not None:
                out.append(dict(type=ty, kind='user', tf=tf, side=0, t1=t1, p1=float(l['p1']), t2=t2, p2=float(l['p2'])))
    return out


def images_for(b, t):
    """[(field, png bytes)] for one trade dict from GAS."""
    sym = APP2SYM.get(str(t['pair']).upper(), str(t['pair']).upper())
    et, xt = jst_to_server(t['entryDate'], t['entryTime']), (jst_to_server(t['exitDate'], t['exitTime']) if t.get('exitDate') else None)
    if pd.isna(et):
        return []
    now = pd.Timestamp.now(tz='UTC').tz_localize(None)
    days = int((now - et) / pd.Timedelta('1D')) + 410
    m = pair_env.bars_any(b, sym, days)[['t', 'o', 'h', 'l', 'c']]
    m['t'] = pd.to_datetime(m.t)
    try:                    # 砦 / 出入口 / trendlines: the EA's, as they were at the entry (its 抵抗体 are left out: those come from the report)
        lines = [l for l in alerts.ea_chart_objects(sym, m[m.t <= et].tail(400 * 96).reset_index(drop=True)) if l['kind'] != 'band']
    except Exception as ex:
        logging.info('trade images %s: no EA lines (%s)', t['id'], ex); lines = []
    lines += report_lines(t.get('lines') or [])
    try:
        digits = int(b.mt5.symbol_info(b.name(sym)).digits)
    except Exception:
        digits = 3 if sym.endswith('JPY') else 5
    side = 1 if str(t['direction']).lower().startswith('b') else -1
    ep, sl, tp, xp = num(t.get('entryPrice')), num(t.get('sl')), num(t.get('tp')), num(t.get('exitPrice'))
    R = None
    if ep and sl and xp:
        R = side * (xp - ep) / abs(ep - sl) if ep != sl else None
    m_cut = m[m.t <= (xt if xt is not None and not pd.isna(xt) else now) + pd.Timedelta(days=2)]
    deals = []
    for d in t.get('deals') or []:                     # DealTime 'yyyy-MM-dd HH:mm+09:00' (Japan) -> broker time
        x = pd.to_datetime(str(d.get('t', '')).replace('+09:00', ''), errors='coerce')
        if not pd.isna(x):
            deals.append(dict(io=d.get('io'), t=x.tz_localize(JST).tz_convert(SERVER_TZ).tz_localize(None), p=float(d.get('p') or 0), v=float(d.get('v') or 0)))
    out = []
    want = []
    if t.get('needEntry'):
        want += [('ChartImage', 'H4', 'entry'), ('ChartImage2', 'M15', 'entry')]
    if t.get('needExit') and xt is not None and not pd.isna(xt):
        want += [('決済チャート', 'H4', 'exit'), ('決済チャート2', 'M15', 'exit')]
    for field, tf, focus in want:
        rr = f'  {R:+.2f}R' if R is not None else ''
        title = f"{t['pair']} {'買い' if side > 0 else '売り'} · {'エントリー' if focus == 'entry' else '決済'} {t['entryDate'] if focus == 'entry' else t['exitDate']} {t['entryTime'] if focus == 'entry' else t['exitTime']}（{tf}）{rr}"
        png = tradechart.draw_tf(m_cut, tf, side, et, ep, sl, tp, exit_t=xt if focus == 'exit' or (xt is not None) else None, exit_px=xp, R=R, digits=digits,
                                 title=title, focus=focus, lines=lines, deals=deals)
        if png:
            out.append((field, png))
    return out


CHART_SPAN = {'D1': (400, 30, 600), 'H4': (90, 10, 1200), 'H1': (20, 4, 1500), 'M15': (4, 1, 3000)}   # days before entry, after exit, max bars


def chart_data(b, t):
    """2026-11-27 (user): the trade as a live chart in the app (trade_chart.html), to correct the trendlines / 抵抗帯 on it and keep them
    as data. {sym, dig, side, et, xt, ep, sl, tp, xp (Japan-time minutes like the report), D1/H4/H1/M15: [T, O, H, L, C], ea: the EA's
    lines at the entry, deals}. None when the bars are not there."""
    from mt5_ea.live.report import _tf_arrays, server_to_jst_min
    sym = APP2SYM.get(str(t['pair']).upper(), str(t['pair']).upper())
    et, xt = jst_to_server(t['entryDate'], t['entryTime']), (jst_to_server(t['exitDate'], t['exitTime']) if t.get('exitDate') else None)
    if pd.isna(et):
        return None
    xt = None if xt is None or pd.isna(xt) else xt
    now = pd.Timestamp.now(tz='UTC').tz_localize(None)
    m = pair_env.bars_any(b, sym, int((now - et) / pd.Timedelta('1D')) + 430)[['t', 'o', 'h', 'l', 'c']]
    m['t'] = pd.to_datetime(m.t); m = m.set_index('t').sort_index()
    if not len(m) or m.index.max() < et:
        return None
    try:
        dig = int(b.mt5.symbol_info(b.name(sym)).digits)
    except Exception:
        dig = 3 if sym.endswith('JPY') else 5
    end = xt if xt is not None else now
    out = dict(sym=sym, pair=t['pair'], dig=dig, side=1 if str(t['direction']).lower().startswith('b') else -1)
    for tf, rule in (('D1', '1D'), ('H4', '4h'), ('H1', '1h'), ('M15', None)):
        a, z, mx = CHART_SPAN[tf]
        x = m[(m.index >= et - pd.Timedelta(days=a)) & (m.index <= end + pd.Timedelta(days=z))]
        if rule:
            x = x.resample(rule, label='left', closed='left').agg({'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last'}).dropna()
        if len(x) > mx:                                   # a long trade: keep the entry side and the exit side
            ie = int(x.index.searchsorted(et)); keep = max(0, min(ie - mx // 3, len(x) - mx)); x = x.iloc[keep:keep + mx]
        out[tf] = _tf_arrays(x, dig)
    tt = server_to_jst_min([et] + ([xt] if xt is not None else []))
    out['et'] = int(tt[0]); out['xt'] = int(tt[1]) if xt is not None else None
    for k, f in (('ep', 'entryPrice'), ('sl', 'sl'), ('tp', 'tp'), ('xp', 'exitPrice')):
        out[k] = num(t.get(f))
    try:                                                    # the EA's lines as they were at the entry (report format)
        ls = [l for l in alerts.ea_chart_objects(sym, m[m.index <= et].reset_index().tail(400 * 96).reset_index(drop=True)) if l['kind'] != 'band']
        t1 = server_to_jst_min([x['t1'] for x in ls]) if ls else []
        t2 = server_to_jst_min([x['t2'] if x['t2'] is not None else x['t1'] for x in ls]) if ls else []
        out['ea'] = [dict(type=x['type'], kind=x['kind'], tf=x['tf'], side=x['side'], t=int(a), p=round(x['p1'], dig),
                          t2=(int(c) if x['type'] == 't' else None), p2=(round(x['p2'], dig) if x['type'] == 't' else None))
                     for x, a, c in zip(ls, t1, t2) if a > 0 and (x['type'] != 't' or c > 0)]
    except Exception as ex:
        logging.info('trade chart %s: no EA lines (%s)', t['id'], ex); out['ea'] = []
    deals = []
    for d in t.get('deals') or []:
        x = pd.to_datetime(str(d.get('t', '')).replace('+09:00', ''), errors='coerce')
        if not pd.isna(x):
            deals.append(dict(io=d.get('io'), t=int((x - pd.Timestamp('1970-01-01')) // pd.Timedelta(minutes=1)), p=float(d.get('p') or 0)))
    out['deals'] = deals
    return out


def run(b, gas, limit=5, dry=False, log=print):
    import json
    r = gas.call('eaNeedImages', {'limit': limit}, timeout=60)
    ts = (r or {}).get('trades') or []
    done = 0
    for t in ts:
        if t.get('needChart'):                              # 2026-11-27: the live chart data (its own step: a failure here keeps the images going)
            try:
                c = chart_data(b, t)
                if c is not None:
                    raw = json.dumps(c, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                    if dry:
                        d = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data') / 'trade_images'; d.mkdir(parents=True, exist_ok=True)
                        (d / f"{t['id']}_chart.json").write_bytes(raw)
                    else:
                        gas.call('eaTradeChart', {'entryId': t['id'], 'closed': bool(c.get('xt')), 'data64': base64.b64encode(raw).decode()}, timeout=180)
                    log(f"  チャート {t['pair']} {t['entryDate']}（{len(raw) // 1024} KB）")
            except Exception as ex:
                logging.warning('trade chart %s: %s', t.get('id'), ex)
        try:
            imgs = images_for(b, t) if (t.get('needEntry') or t.get('needExit')) else []
            if not imgs:
                continue
            if dry:
                d = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data') / 'trade_images'; d.mkdir(parents=True, exist_ok=True)
                for f, png in imgs:
                    (d / f"{t['id']}_{f}.png").write_bytes(png)
            else:
                gas.call('eaEntryImages', {'entryId': t['id'], 'images': [{'field': f, 'png': base64.b64encode(p).decode()} for f, p in imgs]}, timeout=180)
            done += 1
            log(f"  画像 {t['pair']} {t['entryDate']}：{len(imgs)} 枚")
        except Exception as ex:
            logging.warning('trade images %s: %s', t.get('id'), ex)
    return done


def main():
    import argparse
    from mt5_ea.live import gas
    from mt5_ea.live.broker import MT5Broker
    ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int, default=10); ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    path = os.getenv('EA_ALERT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or ''
    if path:
        os.environ['EA_MT5_PATH'] = path
    n = run(MT5Broker(), gas, a.limit, a.dry)
    print(f'{n} トレードの画像を作りました')


if __name__ == '__main__':
    main()
