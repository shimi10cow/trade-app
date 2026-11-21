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
    return dict(fam=fam, fams=code, bt=bt, exp=exp, fam_bt=fam_bt)


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
    """naive broker times -> minutes since 1970 in Japan time (what the page shows)."""
    t = pd.DatetimeIndex(ts).tz_localize(SERVER_TZ, ambiguous='NaT', nonexistent='shift_forward').tz_convert(JST).tz_localize(None)
    return ((t - pd.Timestamp('1970-01-01')) // pd.Timedelta(minutes=1)).astype('int64')


# ---------------------------------------------------------------- live trades
def live_trades(data, refs):
    T = pd.DataFrame(data.get('trades') or [])
    if not len(T):
        return T
    T = T[~T.EA.astype(str).str.startswith('RES:')].copy()
    for c in ('EntryPrice', 'SLPrice', 'TPPrice', 'ExitPrice', 'Profit', 'R', 'Lot', 'RiskJPY', 'Slip', 'Spread'):
        T[c] = pd.to_numeric(T.get(c), errors='coerce')
    T['excluded'] = T.get('Excluded', '').fillna('').astype(str).str.strip() != ''
    T['sig_srv'] = [jst_to_server(x) for x in T.SignalTime]
    T['sim_t'] = T.sig_srv + pd.Timedelta(minutes=15)          # the backtest's trade time = close of the signal bar
    T['entry_srv'] = [jst_to_server(x) for x in T.EntryTime]
    T['exit_srv'] = [jst_to_server(x) for x in T.ExitTime]
    T['fam'] = T.EA.map(refs['fam']).fillna('OLD')
    T['side'] = np.where(T.Direction.astype(str).str.upper() == 'BUY', 1, -1)
    return T.sort_values('entry_srv').reset_index(drop=True)


# ---------------------------------------------------------------- backtest of the same period with the live code
def backtest(broker, syms_keys, start, days_back):
    from mt5_ea.live.runner import compute_symbol
    out, bars = [], {}
    for sym, keys in sorted(syms_keys.items()):
        eas = [BY_KEY[k] for k in keys]
        warm = max(e.warm_days for e in eas)
        try:
            m = broker.bars(sym, days_back + warm + 5)
        except Exception as ex:
            log.warning('%s: no bars (%s)', sym, ex); continue
        bars[sym] = m[['t', 'o', 'h', 'l', 'c']].copy()
        x = bars[sym].copy(); x['t'] = pd.to_datetime(x.t).astype('datetime64[us]')
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
        log.info('backtest %s (%d EAs)', sym, len(keys)); print(f'  バックテスト {sym}（{len(keys)} 本）', flush=True)
        try:
            res = compute_symbol(sym, x, warm, keys, w1)
        except Exception as ex:
            log.warning('%s: backtest failed (%s)', sym, ex); continue
        for k, r in res.items():
            tr = r.get('trades') if isinstance(r, dict) else None
            if tr is not None and len(tr):
                for _, z in tr.iterrows():
                    t = pd.Timestamp(z['t'])
                    if t < start:
                        continue
                    out.append(dict(key=k, sym=sym, t=t, side=int(z['side']), entry=float(from_space(sym, [z['entry']])[0]),
                                    exit=float(from_space(sym, [z['exit']])[0]) if pd.notna(z.get('exit')) else None,
                                    exit_t=pd.Timestamp(z['exit_t']) if pd.notna(z.get('exit_t')) else None, R=float(z['R']), open=False))
            for z in (r.get('open') or []) if isinstance(r, dict) else []:
                if 't' in z and pd.Timestamp(z['t']) >= start:
                    out.append(dict(key=k, sym=sym, t=pd.Timestamp(z['t']), side=int(z['side']),
                                    entry=float(from_space(sym, [z['entry']])[0]) if 'entry' in z else None, exit=None, exit_t=None, R=None, open=True))
    return pd.DataFrame(out), bars


def match(T, B):
    """live trade <-> backtest trade of the same EA, side and signal bar (+-15 minutes)."""
    T = T.copy(); T['bt'] = -1
    used = set()
    if len(B):
        for i, r in T.iterrows():
            c = B[(B.key == r.EA) & (B.side == r.side) & ((B.t - r.sim_t).abs() <= pd.Timedelta(minutes=15))]
            c = c[~c.index.isin(used)]
            if len(c):
                j = int(c.index[0]); used.add(j); T.at[i, 'bt'] = j
    return T, used


# ---------------------------------------------------------------- page
def build(data, refs, T, B, bars, days):
    accs = [a for a in ('demo', 'live') if len(T) and (T.Account == a).any()] or ['demo']
    used = set(T.bt[T.bt >= 0]) if len(T) else set()
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
    jmin = lambda t: None if t is None or pd.isna(t) else int(server_to_jst_min([pd.Timestamp(t)])[0])
    trades = []
    for i, r in T.iterrows():
        b = B.loc[r.bt] if r.bt >= 0 else None
        trades.append(dict(i=int(i), acc=r.Account, ea=r.EA, fam=r.fam, sym=r.Symbol, side=int(r.side), st=r.Status, ex=bool(r.excluded), exw=str(r.get('Excluded') or ''),
                           et=jmin(r.entry_srv), xt=jmin(r.exit_srv), ep=r.EntryPrice, sl=r.SLPrice, tp=r.TPPrice, xp=r.ExitPrice, R=None if pd.isna(r.R) else round(float(r.R), 3),
                           pf=None if pd.isna(r.Profit) else round(float(r.Profit)), lot=r.Lot, risk=r.RiskJPY, slip=None if pd.isna(r.Slip) else r.Slip,
                           spr=None if pd.isna(r.Spread) else r.Spread, v=str(r.get('Verdict') or ''), cm=str(r.get('Comment') or '')[:300], why=str(r.get('Reason') or ''),
                           bt=None if b is None else dict(t=jmin(b.t), ep=b.entry, xt=jmin(b.exit_t), xp=b.exit, R=None if b.R is None or pd.isna(b.R) else round(float(b.R), 3), open=bool(b.open))))
    bt_only = []
    if len(B):
        for j, b in B[~B.index.isin(used)].iterrows():
            bt_only.append(dict(ea=b.key, fam=refs['fam'].get(b.key, 'OLD'), sym=b.sym, side=int(b.side), t=jmin(b.t), ep=b.entry, xt=jmin(b.exit_t), xp=b.exit,
                                R=None if b.R is None or pd.isna(b.R) else round(float(b.R), 3), open=bool(b.open)))
    cfg = data.get('config') or {}
    on = {a: sorted(k for k, v in ((cfg.get(a) or {}).get('eas') or {}).items() if isinstance(v, dict) and v.get('mode', 'off') != 'off' and v.get('on', True)) for a in ('demo', 'live')}
    daily = [dict(d=str(r.get('Date'))[:10], acc=r.get('Account'), bal=r.get('Balance'), eq=r.get('Equity'), dd=r.get('DD')) for r in (data.get('daily') or [])]
    payload = dict(made=pd.Timestamp.now(tz=JST).strftime('%Y-%m-%d %H:%M'), accs=accs, trades=trades, bt_only=bt_only, charts=charts, daily=daily, on=on,
                   fams=refs['fams'], famOf=refs['fam'], exp=refs['exp'], famBt=refs['fam_bt'], bt=refs['bt'], btDone=bool(len(B)), days=days)
    html = (Path(__file__).with_name('report_template.html')).read_text(encoding='utf-8')
    return html.replace('/*__DATA__*/null', json.dumps(clean(payload), ensure_ascii=False, separators=(',', ':'), default=str))


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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=0, help='how far back (0 = from the first EA trade)')
    ap.add_argument('--no-bt', action='store_true', help='skip the backtest of the same period (faster)')
    ap.add_argument('--out', default=os.getenv('EA_REPORT_DIR') or str(Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data') / 'reports'))
    ap.add_argument('--no-open', action='store_true')
    ap.add_argument('--data'); ap.add_argument('--bars-dir')
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
        B, bars = backtest(broker, {s: k for s, k in syms_keys.items() if k}, start, max(days_back, 400))
        for s in syms_keys:
            if s not in bars:
                try:
                    bars[s] = broker.bars(s, days_back + 400)[['t', 'o', 'h', 'l', 'c']]
                except Exception:
                    pass
    T, _ = match(T, B)
    html = build(data, refs, T, B, bars, days_back)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    f = out / f'report_{pd.Timestamp.now(tz=JST):%Y%m%d_%H%M}.html'
    f.write_text(html, encoding='utf-8')
    print(f'できました: {f}', flush=True)
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
