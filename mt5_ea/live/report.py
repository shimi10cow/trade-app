"""One-click EA report (2026-11-21): every EA trade with its result, compared with the backtest of the same period, in one HTML page.

Usage (desktop, double-click 成績レポート.bat):  python -m mt5_ea.live.report [--days N] [--no-bt] [--out DIR] [--no-open]
  1. reads the EA trades / daily balance / config from GAS (eaReportData, read only; EA_GAS_URL / EA_GAS_KEY as the live EA)
  2. reads M15 bars from MT5 (EA_MT5_PATH or the default terminal; read only, no orders) and re-runs the live EA code over the
     same period -> which trades the backtest makes, matched one by one with the live trades
  3. writes TradeEA_data/reports/report_YYYYMMDD_HHMM.html (charts of every trade on D1 / H4 / H1 / M15) and opens it
Offline test: --data trades.json --bars-dir DIR (CSV per symbol: t,o,h,l,c in broker time) instead of GAS / MT5.
"""
import argparse
import json
import logging
import math
import os
import re
import sys
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd

from mt5_ea.live.core import from_space, to_space
from mt5_ea.live.registry import ADOPTED, BY_KEY

ROOT = Path(__file__).resolve().parents[2]
SERVER_TZ, JST = 'Europe/Athens', 'Asia/Tokyo'
log = logging.getLogger('report')


# ---------------------------------------------------------------- reference numbers from the app (one source: ea_live.js / EA_Live.gs)
def app_refs():
    js = (ROOT / 'ea_live.js').read_text(encoding='utf-8')
    gs = (ROOT / 'gas' / 'EA_Live.gs').read_text(encoding='utf-8')
    fam, code = {}, {}
    for m in re.finditer(r"\{id: '([A-Z0-9]+)', title: '([^']*)', code: '([^']*)', desc: '[^']*', keys: \[(.*?)\]\}", js):
        fid, title, cd = m.group(1), m.group(2), m.group(3)
        code[fid] = dict(code='D@' if fid == 'D' else cd, title=title)
        for k in re.findall(r"\['([^']+)'", m.group(4)):
            fam[k] = fid
    bt = json.loads(re.search(r'const BT = (\{.*?\});', js, re.S).group(1))
    exp = json.loads(re.search(r'const EAL_EXP_ = (\{.*?\});', gs, re.S).group(1))
    fam_bt = json.loads(re.search(r'const FAM_BT = (\{.*?\});', js, re.S).group(1))
    mk = re.search(r'const MC_KEYS = (\[.*?\]);', js, re.S); mm = re.search(r'const MC_MONTHS = (\[.*?\]);\n', js, re.S)
    return dict(fam=fam, fams=code, bt=bt, exp=exp, fam_bt=fam_bt, mc_keys=json.loads(mk.group(1)) if mk else [], mc_months=json.loads(mm.group(1)) if mm else [])


# ---------------------------------------------------------------- data sources
def load_gas(path=None):
    if path:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    from mt5_ea.live import gas
    r = gas.call('eaReportData', {}, timeout=120)
    if not r or r.get('success') is False:
        raise RuntimeError(f'GAS: {r and r.get("error")}  (EA_Live.gs を貼り直して新しいデプロイにしたか確認)')
    return r


class CsvBars:
    def __init__(self, d):
        self.d = Path(d)

    def bars(self, sym, days):
        m = pd.read_csv(self.d / f'{sym}.csv', parse_dates=['t'])
        return m[m.t >= m.t.iat[-1] - pd.Timedelta(days=days)].reset_index(drop=True)

    def weekly(self, sym):
        return None


def jst_to_server(s):
    """'2026-11-20 10:15+09:00' -> naive broker time."""
    t = pd.to_datetime(str(s).replace('+09:00', ''), errors='coerce')
    if pd.isna(t):
        return pd.NaT
    return t.tz_localize(JST).tz_convert(SERVER_TZ).tz_localize(None)


def server_to_jst_min(ts):
    """naive broker times -> minutes since 1970 in Japan time (what the page shows). The repeated hour when summer time ends is read
    as summer time (same as runner.to_jst); anything that still cannot be converted becomes -1 and is dropped by the caller (2026-11-21)."""
    idx = pd.DatetimeIndex(ts)
    t = idx.tz_localize(SERVER_TZ, ambiguous=np.ones(len(idx), dtype=bool), nonexistent='shift_forward').tz_convert(JST).tz_localize(None)
    out = np.full(len(t), -1, dtype='int64')
    ok = ~pd.isna(t)
    out[ok] = ((t[ok] - pd.Timestamp('1970-01-01')) // pd.Timedelta(minutes=1)).to_numpy().astype('int64')
    return out


# ---------------------------------------------------------------- live trades
def live_trades(data, refs):
    T = pd.DataFrame(data.get('trades') or [])
    if not len(T):
        return T
    T = T[~T.EA.astype(str).str.startswith('RES:')].copy()
    for c in ('EntryPrice', 'SLPrice', 'TPPrice', 'ExitPrice', 'Profit', 'R', 'Lot', 'RiskJPY', 'Slip', 'Spread'):
        T[c] = pd.to_numeric(T.get(c), errors='coerce')
    T['excluded'] = T.get('Excluded', pd.Series('', index=T.index)).fillna('').astype(str).str.strip().str.lower().replace({'nan': '', 'none': ''}) != ''
    T['sig_srv'] = [jst_to_server(x) for x in T.SignalTime]
    T['sim_t'] = T.sig_srv + pd.Timedelta(minutes=15)          # the backtest's trade time = close of the signal bar
    T['entry_srv'] = [jst_to_server(x) for x in T.EntryTime]
    T['exit_srv'] = [jst_to_server(x) for x in T.ExitTime]
    T['fam'] = T.EA.map(refs['fam']).fillna('OLD')
    T['side'] = np.where(T.Direction.astype(str).str.upper() == 'BUY', 1, -1)
    return T.sort_values('entry_srv').reset_index(drop=True)


# ---------------------------------------------------------------- backtest of the same period with the live code
# 2026-11-22: the backtest is kept between reports (TradeEA_data/reports/bt_cache.pkl). A report only recalculates from
# `safe` = 14 days before the previous report's last bar (earlier if a trade was still open there) to now; older trades come from
# the cache. A symbol is recalculated from the start when its EA set changed, when the EA code changed (hash of registry / core /
# eas/*.py) or when the report starts earlier than the cache. --full ignores the cache.
CACHE_OVERLAP = pd.Timedelta(days=14)


def code_version():
    import hashlib
    h = hashlib.sha1(); here = Path(__file__).parent
    for f in sorted([here / 'registry.py', here / 'core.py', here / 'runner.py'] + list((here / 'eas').glob('*.py'))):
        try:
            h.update(f.read_bytes())
        except Exception:
            pass
    return h.hexdigest()[:12]


def load_cache(f):
    import pickle
    try:
        return pickle.loads(Path(f).read_bytes()) if f and Path(f).exists() else {}
    except Exception as ex:
        log.warning('backtest cache not read (%s): full backtest', ex); return {}


def save_cache(f, cache):
    import pickle
    try:
        Path(f).write_bytes(pickle.dumps(cache))
    except Exception as ex:
        log.warning('backtest cache not saved (%s)', ex)


def backtest(broker, syms_keys, start, days_back, cache=None):
    from mt5_ea.live.runner import compute_symbol
    out, bars = [], {}
    ver = code_version()
    for sym, keys in sorted(syms_keys.items()):
        eas = [BY_KEY[k] for k in keys]
        warm = max(e.warm_days for e in eas)
        try:
            m = broker.bars(sym, days_back + warm + 5)
        except Exception as ex:
            log.warning('%s: no bars (%s)', sym, ex); continue
        bars[sym] = m[['t', 'o', 'h', 'l', 'c']].copy()
        c = (cache or {}).get(sym) if cache is not None else None
        use = c is not None and c.get('keys') == tuple(sorted(keys)) and c.get('ver') == ver and c.get('start') <= start and c.get('safe') is not None
        C = c['safe'] if use else start
        last_bar = pd.Timestamp(bars[sym].t.iat[-1])
        if use and c.get('last') is not None and pd.Timestamp(c['last']) >= last_bar:   # 2026-11-22: no new bar since the last report
            same = [r for r in c['trades'] if r['t'] >= start]                         # (weekend, run twice): nothing to recalculate
            out += same
            print(f"  バックテスト {sym}（{len(keys)} 本）：前回から新しい足がないので、前回の結果をそのまま使います", flush=True)
            continue
        old = [r for r in c['trades'] if r['t'] < C and r['t'] >= start] if use else []
        x = bars[sym].copy(); x['t'] = pd.to_datetime(x.t).astype('datetime64[us]')
        if use:
            x = x[x.t >= pd.Timestamp(C) - pd.Timedelta(days=warm + 1)].reset_index(drop=True)
        sym_out = []
        for z in 'ohlc':
            x[z] = to_space(sym, x[z].to_numpy())
        w1 = None
        if any(e.weekly for e in eas) and hasattr(broker, 'weekly'):
            try:
                w1 = broker.weekly(sym)
                if w1 is not None:
                    w1 = w1.copy()
                    for z in 'ohlc':
                        w1[z] = to_space(sym, w1[z].to_numpy())
            except Exception:
                w1 = None
        log.info('backtest %s (%d EAs)', sym, len(keys))
        print(f"  バックテスト {sym}（{len(keys)} 本）" + (f"：{pd.Timestamp(C):%m/%d} から（それより前は前回の分）" if use else '：最初から'), flush=True)
        try:
            res = compute_symbol(sym, x, warm, keys, w1)
        except Exception as ex:
            log.warning('%s: backtest failed (%s)', sym, ex); out += old; continue
        for k, r in res.items():
            tr = r.get('trades') if isinstance(r, dict) else None
            if tr is not None and len(tr):
                for _, z in tr.iterrows():
                    t = pd.Timestamp(z['t'])
                    if t < start or t < C:
                        continue
                    st0 = next((z[c] for c in ('stop0', 'sl0', 'sl') if c in z and pd.notna(z[c])), None)
                    sym_out.append(dict(key=k, sym=sym, t=t, side=int(z['side']), entry=float(from_space(sym, [z['entry']])[0]),
                                    sl=float(from_space(sym, [st0])[0]) if st0 is not None else None,
                                    exit=float(from_space(sym, [z['exit']])[0]) if pd.notna(z.get('exit')) else None,
                                    exit_t=pd.Timestamp(z['exit_t']) if pd.notna(z.get('exit_t')) else None, R=float(z['R']), open=False))
            for z in (r.get('open') or []) if isinstance(r, dict) else []:
                if 't' in z and pd.Timestamp(z['t']) >= start and pd.Timestamp(z['t']) >= C:
                    sym_out.append(dict(key=k, sym=sym, t=pd.Timestamp(z['t']), side=int(z['side']),
                                    entry=float(from_space(sym, [z['entry']])[0]) if 'entry' in z else None,
                                    sl=float(from_space(sym, [z['sl']])[0]) if z.get('sl') is not None else None, exit=None, exit_t=None, R=None, open=True))
        allt = old + sym_out; out += allt
        if cache is not None:                     # where the next report may start: 14 days before the last bar, before any trade still open there
            last = pd.Timestamp(bars[sym].t.iat[-1]); safe = last - CACHE_OVERLAP
            span = [r['t'] for r in allt if r['t'] < safe and (r['open'] or r['exit_t'] is None or r['exit_t'] >= safe)]
            if span:
                safe = min(span) - pd.Timedelta(minutes=15)
            cache[sym] = dict(keys=tuple(sorted(keys)), ver=ver, start=min(start, c['start']) if use else start, safe=max(safe, start), trades=allt,
                              last=last)
    return pd.DataFrame(out), bars


# 2026-11-22 (user): the period backtest with the costs the account really pays, so 突き合わせ compares like with like.
# Swap (XM, docs/OPEN_ITEMS.md 11/8): yearly rate of the price, today's values; FX / gold / silver are swap-free on the KIWAMI account.
# Indices: one day per night, Friday night 3 days. BTC: every night, weekends too. Long / short.
SWAP_YEAR = {'US30': (-0.065, 0.009), 'US500': (-0.065, 0.009), 'US100': (-0.065, 0.009), 'JP225': (-0.033, -0.013),
             'BTCUSD': (-0.259, -0.103)}
# Cost per trade as a share of the price, above what the engines already take (1.2e-4 price space = 0.012 % for these log-priced symbols)
EXTRA_COST = {'BTCUSD': 0.0008 - 0.00012, 'XAGUSD': 0.0004 - 0.00012}


def swap_days(sym, t, x):
    """Swap days held from t to x (server time): the server midnights crossed; indices count Friday night as 3, BTC every night."""
    if t is None or x is None or pd.isna(t) or pd.isna(x) or x <= t:
        return 0
    nights = pd.date_range(pd.Timestamp(t).normalize() + pd.Timedelta(days=1), pd.Timestamp(x).normalize(), freq='D')
    if sym == 'BTCUSD':
        return len(nights)
    # a rollover at midnight after Mon..Fri (the night starting Friday is charged 3 days); weekend midnights are not trading nights
    return sum(3 if (n - pd.Timedelta(days=1)).weekday() == 4 else 1 for n in nights if (n - pd.Timedelta(days=1)).weekday() < 5)


def costs_swaps(B):
    """B with R after swap and the extra cost (R_raw keeps the engine's R; swapR / costR the parts taken off)."""
    if not len(B):
        return B
    B = B.copy(); B['R_raw'] = B.R; B['swapR'] = 0.0; B['costR'] = 0.0
    for i, b in B.iterrows():
        if b.R is None or pd.isna(b.R) or b.sl is None or pd.isna(b.sl) or not b.entry:
            continue
        risk = abs(float(b.entry) - float(b.sl))
        if risk <= 0:
            continue
        rate = SWAP_YEAR.get(b.sym)
        sw = (rate[0] if b.side > 0 else rate[1]) / 365 * swap_days(b.sym, b.t, b.exit_t) * float(b.entry) / risk if rate else 0.0
        co = EXTRA_COST.get(b.sym, 0.0) * float(b.entry) / risk
        B.at[i, 'swapR'] = round(sw, 4); B.at[i, 'costR'] = round(co, 4); B.at[i, 'R'] = float(b.R) + sw - co
    return B


def match(T, B):
    """live trade <-> backtest trade of the same EA, side and signal bar (+-15 minutes), separately for each account."""
    T = T.copy(); T['bt'] = -1
    used = {}
    if len(B):
        for i, r in T.iterrows():
            u = used.setdefault(r.Account, set())
            c = B[(B.key == r.EA) & (B.side == r.side) & ((B.t - r.sim_t).abs() <= pd.Timedelta(minutes=15))]
            c = c[~c.index.isin(u)]
            if len(c):
                j = int(c.index[0]); u.add(j); T.at[i, 'bt'] = j
    return T, used


# ---------------------------------------------------------------- every pair of the app (weekend chart analysis, 2026-11-22)
PAIR_DAYS = {'D1': 3 * 365, 'H4': 250, 'H1': 60, 'M15': 28}     # + 400 days of M15 for the EA lines (same as the alerts window)     # how far back each timeframe is shown (file size: ~8 MB for 42 pairs)


def _dig(sym, broker=None, name=None):
    try:
        if broker is not None and hasattr(broker, 'mt5'):
            i = broker.mt5.symbol_info(name or broker.name(sym))
            if i is not None:
                return int(i.digits)
    except Exception:
        pass
    return 3 if sym.endswith('JPY') else (2 if sym in ('XAUUSD', 'US30', 'US500', 'US100', 'US2000', 'JP225', 'UK100', 'EU50', 'BTCUSD', 'BTCJPY', 'OIL', 'BRENT') else (3 if sym in ('XAGUSD', 'NATGAS') else 5))


def _tf_arrays(x, dig):
    tm = server_to_jst_min(x.index); ok = tm > 0
    return [tm[ok].tolist()] + [np.round(x[z].to_numpy()[ok], dig).tolist() for z in 'ohlc']


def pair_charts(broker, pairs):
    """{pair: {dig, D1, H4, H1, M15}} for every pair of the app. D1 from MT5's D1 bars (3 years; inside the history kept on disk),
    H4 / H1 / M15 from the last 250 days of M15 (what the alerts window already reads, so nothing new is downloaded)."""
    from mt5_ea.live import pair_env
    out = {}
    now = pd.Timestamp.now(tz='UTC').tz_localize(None) + pd.Timedelta(days=1)
    for p in pairs:
        try:
            m = pair_env.bars_any(broker, p, PAIR_DAYS['H4'])[['t', 'o', 'h', 'l', 'c']].copy()
            m['t'] = pd.to_datetime(m.t); m = m.set_index('t')
            dig = _dig(p, broker)
            o = {'dig': dig}
            d1 = None
            if hasattr(broker, 'mt5'):
                mt5 = broker.mt5
                for n in pair_env.ALIAS.get(p, (p,)):
                    try:
                        r = mt5.copy_rates_range(broker.name(n), mt5.TIMEFRAME_D1, (now - pd.Timedelta(days=PAIR_DAYS['D1'])).to_pydatetime(), now.to_pydatetime())
                        if r is not None and len(r):
                            d1 = pd.DataFrame(r).rename(columns=dict(open='o', high='h', low='l', close='c'))
                            d1['t'] = pd.to_datetime(d1.time, unit='s'); d1 = d1.set_index('t')[['o', 'h', 'l', 'c']]; break
                    except Exception:
                        continue
            if d1 is None:
                d1 = m.resample('1D', label='left', closed='left').agg({'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last'}).dropna()
            o['D1'] = _tf_arrays(d1, dig)
            end = m.index.max()
            for tf, rule in (('H4', '4h'), ('H1', '1h'), ('M15', None)):
                x = m[m.index >= end - pd.Timedelta(days=PAIR_DAYS[tf])]
                if rule:
                    x = x.resample(rule, label='left', closed='left').agg({'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last'}).dropna()
                o[tf] = _tf_arrays(x, dig)
            try:                                                       # the EA's H4 lines still alive (gateway / fortress / band)
                from mt5_ea.live import alerts
                m4 = pair_env.bars_any(broker, p, 400)[['t', 'o', 'h', 'l', 'c']]
                ls = alerts.ea_chart_objects(p, m4)                 # h lines + trendlines the EAs watch now
                t1 = server_to_jst_min([x['t1'] for x in ls]) if ls else []
                t2 = server_to_jst_min([x['t2'] if x['t2'] is not None else x['t1'] for x in ls]) if ls else []
                o['ea'] = [dict(type=x['type'], kind=x['kind'], tf=x['tf'], side=x['side'], t=int(a), p=round(x['p1'], dig),
                                t2=(int(b) if x['type'] == 't' else None), p2=(round(x['p2'], dig) if x['type'] == 't' else None))
                           for x, a, b in zip(ls, t1, t2) if a > 0 and (x['type'] != 't' or b > 0)]
            except Exception as ex:
                log.warning('EA lines %s: %s', p, ex); o['ea'] = []
            out[p] = o
            print(f"  チャート {p}（EA のライン {len(o['ea'])} 本）", flush=True)
        except Exception as ex:
            log.warning('pair chart %s: %s', p, ex); print(f'  チャート {p}：とばした（{str(ex)[:60]}）', flush=True)
    return out


def mark_auto(broker, repmarks, log_=print):
    """2026-11-22 (user): the trader's 「買いたい所 / 売りたい所」 on the all-pairs charts, sorted afterwards (alerts.classify_point):
    手法 1 / 2 / 6 / 7, the H4 line it sits on and how far, and the score items. Nothing to tick by hand."""
    from mt5_ea.live import alerts, pair_env
    from mt5_ea.live.trade_images import jmin_to_server
    out = []
    for r in repmarks or []:
        rid = str(r.get('ID') or '')
        if not rid.startswith('PAIR|'):
            continue
        try:
            ls = [l for l in json.loads(r.get('Lines') or '[]') if isinstance(l, dict) and l.get('type') in ('eb', 'es') and not l.get('del')]
        except Exception:
            ls = []
        if not ls:
            continue
        sym = rid[5:]
        try:
            m = pair_env.bars_any(broker, sym, 520)[['t', 'o', 'h', 'l', 'c']].copy(); m['t'] = pd.to_datetime(m.t)
        except Exception as ex:
            log.warning('marks %s: %s', sym, ex); continue
        for l in ls:
            te = jmin_to_server(l.get('t1'))
            if te is None or l.get('p1') is None:
                continue
            try:
                c = alerts.classify_point(sym, m, te, 1 if l['type'] == 'eb' else -1, float(l['p1']))
            except Exception as ex:
                log.warning('mark %s: %s', sym, ex); c = None
            out.append(dict(sym=sym, side=1 if l['type'] == 'eb' else -1, t=int(l['t1']), p=float(l['p1']), tf=l.get('tf') or '', note=l.get('note') or '', **(c or {})))
    if out:
        log_(f'  エントリーしたかった所 {len(out)} か所を、手法・点数に分けました')
    return out


# ---------------------------------------------------------------- page
def manual_trades(rows):
    """The trader's own closed trades (GAS ealManualTrades_) -> the report's 裁量 page. R as in the app: 実取得pips / StopLossPips,
    else 実リスクリワード; ルール通りの R = ルール準拠pips / StopLossPips."""
    f = lambda v: (lambda x: x if math.isfinite(x) else None)(float(v)) if str(v).strip() not in ('', 'None', 'nan') and _isnum(v) else None
    out = []
    for r in rows or []:
        p, sl, rr = f(r.get('実取得pips')), f(r.get('StopLossPips')), f(r.get('実リスクリワード'))
        sl = abs(sl) if sl is not None else None          # a few rows hold the SL width with a minus sign
        R = p / sl if p is not None and sl else rr
        rp = f(r.get('ルール準拠pips'))
        out.append(dict(d=str(r.get('EntryDate') or '')[:10].replace('-', '/'), x=str(r.get('ExitDate') or '')[:10].replace('-', '/'),
                        pair=str(r.get('PairName（元）') or r.get('PairName') or ''), side=str(r.get('Direction') or ''), rule=str(r.get('DowRule') or ''),
                        R=None if R is None else round(R, 3), ruleR=None if rp is None or not sl else round(rp / sl, 3), pf=f(r.get('損益')), lot=f(r.get('Lot')),
                        eref=str(r.get('エントリー振り返り') or ''), xref=str(r.get('決済振り返り') or ''), missed='見逃し' in str(r.get('ステータス') or ''),
                        tm=str(r.get('EntryTime') or '')[:5], plan=str(r.get('計画エントリー') or '') == 'ON',
                        score=str(r.get('エントリースコア') or '').strip(), zone=str(r.get('時間帯') or '').strip()))
    return out


def _isnum(v):
    try:
        float(v); return True
    except (TypeError, ValueError):
        return False


def build(data, refs, T, B, bars, days, pcharts=None, marks=None):
    accs = [a for a in ('demo', 'live') if len(T) and (T.Account == a).any()] or ['demo']
    # chart bars: Japan-time minutes; M15 / H1 / H4 / D1 (resampled in broker time, so D1 = the broker's day like MT5)
    charts = {}
    start = (T.entry_srv.min() if len(T) else pd.Timestamp.now()) - pd.Timedelta(days=7)
    for sym, m in bars.items():
        m = m.copy(); m['t'] = pd.to_datetime(m.t); m = m.set_index('t')
        dig = 3 if sym.endswith('JPY') else (2 if sym in ('XAUUSD', 'US30', 'US500', 'US100', 'JP225', 'BTCUSD') else (3 if sym == 'XAGUSD' else 5))
        out = {'dig': dig}
        for tf, rule, frm in (('M15', None, start), ('H1', '1h', start - pd.Timedelta(days=40)), ('H4', '4h', start - pd.Timedelta(days=200)), ('D1', '1D', None)):
            x = m if rule is None else m.resample(rule, label='left', closed='left').agg({'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last'}).dropna()
            if frm is not None:
                x = x[x.index >= frm]
            tm = server_to_jst_min(x.index)
            ok = tm > 0
            out[tf] = [tm[ok].tolist()] + [np.round(x[z].to_numpy()[ok], dig).tolist() for z in 'ohlc']
        charts[sym] = out
    jmin = lambda t: None if t is None or pd.isna(t) else (lambda v: None if v < 0 else v)(int(server_to_jst_min([pd.Timestamp(t)])[0]))
    txt = lambda v: '' if v is None or (isinstance(v, float) and not math.isfinite(v)) or str(v).strip().lower() in ('nan', 'none', 'nat') else str(v)
    num = lambda v, d=None: None if v is None or (isinstance(v, float) and not math.isfinite(v)) or pd.isna(v) else (round(float(v), d) if d is not None else float(v))
    def lines(v):
        try:
            x = json.loads(v) if v else []
            return x if isinstance(x, list) else []
        except Exception:
            return []
    trades = []
    for i, r in T.iterrows():
        trades.append(dict(i=int(i), id=str(r.TradeID), acc=r.Account, ea=r.EA, fam=r.fam, sym=r.Symbol, side=int(r.side), st=r.Status, ex=bool(r.excluded),
                           exw=txt(r.get('Excluded')), et=jmin(r.entry_srv), xt=jmin(r.exit_srv), ep=num(r.EntryPrice), sl=num(r.SLPrice), tp=num(r.TPPrice),
                           xp=num(r.ExitPrice), R=num(r.R, 3), pf=num(r.Profit, 0), lot=num(r.Lot), risk=num(r.RiskJPY), slip=num(r.Slip), spr=num(r.Spread),
                           v=txt(r.get('Verdict')), tags=txt(r.get('Tags')), cm=txt(r.get('Comment')), xv=txt(r.get('ExitVerdict')),
                           xtags=txt(r.get('ExitTags')), lines=lines(txt(r.get('Lines'))), why=txt(r.get('Reason')), btj=int(r.bt)))
    bt = []
    for j, b in B.iterrows() if len(B) else []:
        bt.append(dict(j=int(j), ea=b.key, fam=refs['fam'].get(b.key, 'OLD'), sym=b.sym, side=int(b.side), et=jmin(b.t), ep=num(b.entry), sl=num(b.get('sl')),
                       xt=jmin(b.exit_t), xp=num(b.exit), R=num(b.R, 3), open=bool(b.open),
                       sw=num(b.get('swapR'), 3), co=num(b.get('costR'), 3)))
    rm = {}
    for r in (data.get('repmarks') or []):
        rm[str(r.get('ID'))] = dict(v=txt(r.get('Verdict')), tags=txt(r.get('Tags')), cm=txt(r.get('Comment')), xv=txt(r.get('ExitVerdict')),
                                    xtags=txt(r.get('ExitTags')), lines=lines(txt(r.get('Lines'))))
    pm = {k[5:]: v['lines'] for k, v in rm.items() if k.startswith('PAIR|')}          # lines on the all-pairs charts (EA_ReportMarks ID 'PAIR|EURUSD')
    pairs = [dict(sym=p, lines=pm.get(p, [])) for p in (pcharts or {})]
    cfg = data.get('config') or {}
    on = {a: sorted(k for k, v in ((cfg.get(a) or {}).get('eas') or {}).items() if isinstance(v, dict) and v.get('mode', 'off') != 'off' and v.get('on', True)) for a in ('demo', 'live')}
    daily = [dict(d=str(r.get('Date'))[:10], acc=r.get('Account'), bal=r.get('Balance'), eq=r.get('Equity'), dd=r.get('DD')) for r in (data.get('daily') or [])]
    payload = dict(made=pd.Timestamp.now(tz=JST).strftime('%Y-%m-%d %H:%M'), accs=accs, trades=trades, btl=bt, repmarks=rm, charts=charts, daily=daily, on=on,
                   fams=refs['fams'], famOf=refs['fam'], exp=refs['exp'], famBt=refs['fam_bt'], bt=refs['bt'], btDone=bool(len(B)), days=days,
                   gas=os.getenv('EA_GAS_URL', ''), rkey=str(data.get('reportKey') or ''), mcKeys=refs.get('mc_keys', []), mcMonths=refs.get('mc_months', []),
                   pairs=pairs, pcharts=pcharts or {}, manual=manual_trades(data.get('manual')), markAuto=marks or [])
    html = (Path(__file__).with_name('report_template.html')).read_text(encoding='utf-8')
    global LAST_PAYLOAD
    LAST_PAYLOAD = payload                      # for the phone upload (the app's report.html reads the data from GAS)
    return html.replace('/*__DATA__*/null', json.dumps(clean(payload), ensure_ascii=False, separators=(',', ':'), default=str))


LAST_PAYLOAD = None


def clean(o):
    """NaN / inf / numpy numbers -> plain JSON values."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if not math.isfinite(float(o)) else float(o)
    return o


def app_url():
    """the trade app's address (GitHub Pages of this repository): EA_APP_URL, else from the git remote"""
    u = os.getenv('EA_APP_URL', '').strip()
    if u:
        return u.rstrip('/') + '/'
    try:
        import subprocess
        r = subprocess.run(['git', '-C', str(ROOT), 'remote', 'get-url', 'origin'], capture_output=True, text=True, timeout=20).stdout.strip()
        m = re.search(r'github\.com[:/]([^/]+)/([^/.]+)', r)
        if m:
            return f'https://{m.group(1).lower()}.github.io/{m.group(2)}/'
    except Exception:
        pass
    return ''


def phone_upload(f, out):
    """2026-11-22 (user): the report on the phone, like the trade app (no Google banner, quicker). The data goes to GAS as two JSON
    files (main; the all-pairs charts apart, loaded only when that tab opens); the app's report.html reads them. The URL stays
    the same: bookmark it / add it to the home screen once. Never fails the report."""
    try:
        import base64
        from urllib.parse import quote
        from mt5_ea.live import gas
        P = dict(LAST_PAYLOAD or {}); pc = P.pop('pcharts', None) or {}; P['pcharts'] = {}
        enc = lambda o: base64.b64encode(json.dumps(clean(o), ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')).decode()
        a = enc(P); b = enc(pc)
        r = gas.call('eaReportUpload', {'part': 'main', 'data64': a}, timeout=300)
        gas.call('eaReportUpload', {'part': 'pairs', 'data64': b}, timeout=300)
        g = os.getenv('EA_GAS_URL', '')
        url = f"{app_url()}report.html#k={r.get('viewKey')}&g={quote(g, safe='')}"
        (out / 'phone_url.txt').write_text(url + '\n', encoding='utf-8')
        print(f'スマホ用にも送りました（{len(a) * 3 / 4 / 1e6:.1f} MB ＋ 全通貨チャート {len(b) * 3 / 4 / 1e6:.1f} MB）。'
              f'スマホではこの URL を開く（ホーム画面に追加しておくと、アプリのように開ける。毎回同じ URL）:\n  {url}', flush=True)
    except Exception as ex:
        print(f'スマホ用には送れませんでした（{str(ex)[:150]}）。GAS 反映がまだなら、反映してからもう一度。', flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=0, help='how far back (0 = from the first EA trade)')
    ap.add_argument('--no-bt', action='store_true', help='skip the backtest of the same period (faster)')
    ap.add_argument('--out', default=os.getenv('EA_REPORT_DIR') or str(Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data') / 'reports'))
    ap.add_argument('--no-open', action='store_true')
    ap.add_argument('--data'); ap.add_argument('--bars-dir')
    ap.add_argument('--no-pairs', action='store_true', help='skip the all-pairs charts (smaller, faster)')
    ap.add_argument('--full', action='store_true', help='backtest the whole period again (ignore the saved backtest)')
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    print('EA の成績レポートを作ります', flush=True)
    refs = app_refs()
    data = load_gas(a.data); print(f'  GAS からトレード {len(data.get("trades") or [])} 件', flush=True)
    T = live_trades(data, refs)
    now = pd.Timestamp.now(tz=JST).tz_convert(SERVER_TZ).tz_localize(None)
    start = (now - pd.Timedelta(days=a.days)) if a.days else ((T.sig_srv.min() - pd.Timedelta(days=1)) if len(T) else now - pd.Timedelta(days=30))
    if len(T):
        T = T[T.entry_srv >= start - pd.Timedelta(days=1)].reset_index(drop=True)
    days_back = int((now - start) / pd.Timedelta(days=1)) + 2
    # EAs to backtest: every EA on in either account now, plus every EA that traded in the period
    cfg = data.get('config') or {}
    keys = set(T.EA) if len(T) else set()
    for acc in ('demo', 'live'):
        for k, v in ((cfg.get(acc) or {}).get('eas') or {}).items():
            if isinstance(v, dict) and v.get('mode', 'off') != 'off' and v.get('on', True):
                keys.add(k)
    keys = {k for k in keys if k in BY_KEY}
    syms_keys = {}
    for k in keys:
        syms_keys.setdefault(BY_KEY[k].symbol, []).append(k)
    for s in (set(T.Symbol) if len(T) else set()):
        syms_keys.setdefault(s, [])
    broker = CsvBars(a.bars_dir) if a.bars_dir else None
    if broker is None:
        from mt5_ea.live.broker import MT5Broker
        path = os.getenv('EA_REPORT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or os.getenv('EA_MT5_PATH') or ''
        if path:
            os.environ['EA_MT5_PATH'] = path          # read bars only; the demo terminal by default (any XM terminal has the same bars)
        broker = MT5Broker()
    if a.no_bt:
        B, bars = pd.DataFrame(), {}
        for s in syms_keys:
            try:
                bars[s] = broker.bars(s, days_back + 400)[['t', 'o', 'h', 'l', 'c']]
            except Exception as ex:
                log.warning('%s: no bars (%s)', s, ex)
    else:
        print(f'  同じ期間（{start:%Y-%m-%d} から）を本番のコードでバックテストし直します（数分かかります）', flush=True)
        cf = Path(a.out) / 'bt_cache.pkl'; Path(a.out).mkdir(parents=True, exist_ok=True)
        cache = {} if a.full or a.bars_dir else load_cache(cf)
        B, bars = backtest(broker, {s: k for s, k in syms_keys.items() if k}, start, max(days_back, 400), cache)
        if not a.bars_dir:
            save_cache(cf, cache)
        for s in syms_keys:
            if s not in bars:
                try:
                    bars[s] = broker.bars(s, days_back + 400)[['t', 'o', 'h', 'l', 'c']]
                except Exception:
                    pass
    B = costs_swaps(B)
    T, _ = match(T, B)
    pcharts = {}
    if not a.no_pairs and not a.bars_dir:
        try:
            from mt5_ea.live import gas, pair_env
            pl = pair_env.app_pairs(gas)
            print(f'  全通貨のチャート（{len(pl)} ペア、日足 3 年・H4 250 日・H1 60 日・M15 28 日）', flush=True)
            pcharts = pair_charts(broker, pl)
        except Exception as ex:
            log.warning('all-pairs charts: %s', ex); print(f'  全通貨のチャートは作れませんでした（{ex}）', flush=True)
    if not a.bars_dir:                                    # 2026-11-22: chart images of imported trades still without one (e.g. made over the weekend)
        try:
            from mt5_ea.live import gas as _gas, trade_images
            n = trade_images.run(broker, _gas, limit=30, log=lambda x: print(x, flush=True))
            if n:
                print(f'  取り込んだトレードの画像：{n} 件', flush=True)
        except Exception as ex:
            log.warning('trade images: %s', ex)
    marks = []
    if not a.bars_dir:
        try:
            marks = mark_auto(broker, data.get('repmarks'), log_=lambda x: print(x, flush=True))
        except Exception as ex:
            log.warning('marks: %s', ex)
    html = build(data, refs, T, B, bars, days_back, pcharts, marks)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    f = out / 'report_latest.html'                 # 2026-11-22 (user): always the same file, overwritten (bookmark it)
    f.write_text(html, encoding='utf-8')
    print(f'できました: {f}（毎回このファイルに上書き）', flush=True)
    if not a.bars_dir and not a.data:
        phone_upload(f, out)
    if not a.no_open:
        webbrowser.open(f.as_uri())
    return f


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        logging.exception('report failed')
        print(f'\nレポートを作れませんでした: {ex}', flush=True)
        sys.exit(1)
