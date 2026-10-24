"""MT5 import (2026-10-24, docs/EA_SYSTEM_PLAN.md "MT5 の取り込み").

Reads the deals of the trader's own XM accounts (not the EA accounts) and sends them to the app backend in one call.
One import MT5 (its own copy, not the EA terminals) in which every account was logged in once with its read-only investor
password and "save password" on; the importer switches between the accounts with mt5.login (no password passed: the
terminal uses the saved one). The terminal is closed once at the end (2026-10-25: one window instead of one per account).
Started by hand on the PC (desktop button; 2026-10-25: the EA no longer starts it):  py -m mt5_ea.live.importer [--reread90]
Its own process (the MetaTrader5 package talks to one terminal per process); the EA can keep running or be stopped.
The merge settings come from the app's MT5 tab unless --group-hours / --merge-across are given.

Accounts: %USERPROFILE%\\TradeEA_data\\import_accounts.json (not in git), e.g.
  [{"login": 12345678, "server": "XMTrading-MT5 3", "path": "C:\\\\MT5_import\\\\terminal64.exe", "label": "KIWAMI 1"}, ...]
  (every account the same path; "portable": true if that copy runs in portable mode)
Per account only deals after the last import are read (first time / --reread90: the last 90 days).
Positions (= MT5 position id) are merged into trades on the PC: same symbol and direction, entered within GROUP_HOURS of the
trade's first entry or while the trade is still open; across accounts when merge_across is on. GAS only appends.
"""
import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mt5_ea.live import gas  # noqa: E402

SERVER_TZ = 'Europe/Athens'
DATA = Path(os.getenv('EA_DATA_DIR') or (Path.home() / 'TradeEA_data'))
ACCOUNTS_F = Path(os.getenv('EA_IMPORT_ACCOUNTS') or DATA / 'import_accounts.json')
STATE_F = DATA / 'import_state.json'
IN_, OUT_, INOUT_, OUTBY_ = 0, 1, 2, 3
ENTRY_JA = {IN_: 'IN', OUT_: 'OUT', INOUT_: 'INOUT', OUTBY_: 'OUT_BY'}
APP_PAIR = {'XAUUSD': 'GOLD', 'GOLD': 'GOLD', 'XAGUSD': 'SILVER', 'SILVER': 'SILVER', 'NGAS': 'NATGAS', 'NATGAS': 'NATGAS'}


def jst(server_epoch):
    """MT5 time (server time written as if UTC) -> 'yyyy-MM-dd HH:mm+09:00' (Japan time with the offset)."""
    t = pd.to_datetime(int(server_epoch), unit='s').tz_localize(SERVER_TZ, ambiguous='NaT', nonexistent='shift_forward')
    return t.tz_convert('Asia/Tokyo').strftime('%Y-%m-%d %H:%M') + '+09:00'


def logical(sym):
    s = str(sym).upper().replace('#', '').replace('.', '').strip()
    for suf in ('MICRO', 'CASH'):
        s = s.replace(suf, '')
    return s


def app_pair(sym):
    s = logical(sym)
    return APP_PAIR.get(s, s)


def read_account(acc, since_epoch):
    """Deals of one account since since_epoch (server time). Returns execution rows."""
    import MetaTrader5 as mt5
    ok = mt5.initialize(acc['path'], portable=True) if acc.get('portable') else mt5.initialize(acc['path'])
    if not ok:
        raise RuntimeError(f"MT5 initialize failed {mt5.last_error()}")
    try:
        info = mt5.account_info()
        if info is None or int(info.login) != int(acc['login']):          # switch accounts inside the one import MT5
            mt5.login(int(acc['login']), server=acc.get('server'), timeout=20000)   # no password: the terminal's saved one
            info = mt5.account_info()
            if info is None or int(info.login) != int(acc['login']):
                raise RuntimeError(f"取り込み用 MT5 でこの口座のパスワードが保存されていない"
                                   f"（ログイン中 {getattr(info, 'login', None)}、{mt5.last_error()}）")
        frm = pd.Timestamp(since_epoch, unit='s').to_pydatetime(); to = (pd.Timestamp.utcnow().tz_localize(None) + pd.Timedelta(days=2)).to_pydatetime()
        deals = mt5.history_deals_get(frm, to) or []
        orders = {o.ticket: o for o in (mt5.history_orders_get(frm, to) or [])}
        rows = []
        for d in deals:
            if int(d.type) not in (0, 1) or not d.symbol:            # buy / sell only (no balance, credit ...)
                continue
            o = orders.get(d.order)
            # direction of the POSITION: an IN deal's side; an OUT deal closes the opposite side
            side = 'BUY' if int(d.type) == 0 else 'SELL'
            if int(d.entry) in (OUT_, OUTBY_):
                side = 'SELL' if side == 'BUY' else 'BUY'
            rows.append(dict(ExecID=f"{acc['login']}:{d.ticket}", Account=str(acc['login']), PositionID=str(d.position_id), Deal=str(d.ticket),
                             Symbol=logical(d.symbol), Direction=side, InOut=ENTRY_JA.get(int(d.entry), str(d.entry)), DealTime=jst(d.time),
                             _t=int(d.time), DealPrice=float(d.price), Volume=float(d.volume), Profit=float(d.profit), Swap=float(d.swap),
                             Commission=float(d.commission) + float(getattr(d, 'fee', 0) or 0), SL=float(getattr(o, 'sl', 0) or 0) if o else 0.0,
                             TP=float(getattr(o, 'tp', 0) or 0) if o else 0.0, Magic=int(d.magic), Comment=str(d.comment or '')[:60]))
        return rows
    finally:
        mt5.shutdown()


def close_terminal(path):
    """Import terminals are not kept running: close the copy we started (by its exe path, never the EA terminal)."""
    if os.name != 'nt':
        return
    ps = f"Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq '{path}' }} | Stop-Process -Force"
    subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, timeout=30)


def positions(rows):
    """Execution rows -> one dict per (account, position id)."""
    by = {}
    for r in rows:
        by.setdefault((r['Account'], r['PositionID']), []).append(r)
    out = []
    for (acc, pid), rs in by.items():
        ins = [r for r in rs if r['InOut'] in ('IN', 'INOUT')]; outs = [r for r in rs if r['InOut'] in ('OUT', 'OUT_BY')]
        if not ins:                                 # entry happened before the read window: GAS links it through its executions
            ins = []
        vin = sum(r['Volume'] for r in ins); vout = sum(r['Volume'] for r in outs)
        first = min(rs, key=lambda r: r['_t'])
        out.append(dict(account=acc, pid=pid, symbol=first['Symbol'], direction=first['Direction'], rows=rs,
                        t0=min((r['_t'] for r in ins), default=first['_t']), t1=max((r['_t'] for r in outs), default=None),
                        vin=vin, vout=vout, closed=vin > 0 and vout >= vin - 1e-9))
    return out


def group_trades(rows, group_hours=24, merge_across=True):
    """Merge positions into trades (same symbol / direction; entered within group_hours of the trade's first entry or
    before the trade was fully closed). Returns trades with aggregated numbers + the execution ids."""
    ps = sorted(positions(rows), key=lambda p: p['t0'])
    groups = []
    for p in ps:
        g = next((g for g in groups if g['symbol'] == p['symbol'] and g['direction'] == p['direction']
                  and (merge_across or g['accounts'] == {p['account']})
                  and (p['t0'] - g['t0'] <= group_hours * 3600 or g['open_until'] is None or p['t0'] <= g['open_until'])), None)
        if g is None:
            g = dict(symbol=p['symbol'], direction=p['direction'], t0=p['t0'], open_until=-1, ps=[], accounts=set())
            groups.append(g)
        g['ps'].append(p); g['accounts'].add(p['account'])
        g['open_until'] = None if any(not q['closed'] for q in g['ps']) else max(q['t1'] or 0 for q in g['ps'])
    return [aggregate([r for p in g['ps'] for r in p['rows']]) for g in groups]


def aggregate(rs):
    ins = [r for r in rs if r['InOut'] in ('IN', 'INOUT')]; outs = [r for r in rs if r['InOut'] in ('OUT', 'OUT_BY')]
    vin = sum(r['Volume'] for r in ins); vout = sum(r['Volume'] for r in outs)
    wavg = lambda xs: (sum(r['DealPrice'] * r['Volume'] for r in xs) / sum(r['Volume'] for r in xs)) if xs and sum(r['Volume'] for r in xs) else None
    first = min(rs, key=lambda r: r['_t'])
    closed = vin > 0 and vout >= vin - 1e-9
    sl = next((r['SL'] for r in sorted(ins, key=lambda r: r['_t']) if r['SL']), 0.0)
    tp = next((r['TP'] for r in sorted(ins, key=lambda r: r['_t']) if r['TP']), 0.0)
    return dict(symbol=first['Symbol'], app_pair=app_pair(first['Symbol']), direction=first['Direction'],
                accounts=sorted({r['Account'] for r in rs}), exec_ids=[r['ExecID'] for r in rs],
                positions=len({(r['Account'], r['PositionID']) for r in rs}),
                entry_time=min((r['DealTime'] for r in ins), default=first['DealTime']), entry_price=wavg(ins),
                exit_time=max((r['DealTime'] for r in outs), default='') if closed else '', exit_price=wavg(outs) if closed else None,
                lot=round(vin, 4), profit=round(sum(r['Profit'] + r['Swap'] + r['Commission'] for r in rs), 2),
                swap=round(sum(r['Swap'] for r in rs), 2), open=not closed, sl=sl, tp=tp, exec_count=len(rs))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--request', default='')
    ap.add_argument('--group-hours', type=float, default=None)      # default: the app's MT5 tab settings (24 h)
    ap.add_argument('--merge-across', default=None)
    ap.add_argument('--reread90', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    if a.group_hours is None or a.merge_across is None:                  # settings saved in the app's MT5 tab
        try:
            st = (gas.call('eaImportSettings', {}, timeout=20) or {}).get('settings') or {}
        except Exception:
            st = {}
        if a.group_hours is None:
            a.group_hours = float(st.get('groupHours') or 24)
        if a.merge_across is None:
            a.merge_across = '0' if st.get('mergeAcross') is False else '1'
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    accounts = json.loads(ACCOUNTS_F.read_text(encoding='utf-8'))
    state = json.loads(STATE_F.read_text(encoding='utf-8')) if STATE_F.exists() else {}
    now = int(pd.Timestamp.utcnow().timestamp()) + 3 * 3600          # roughly server time
    rows, acc_out, errors = [], [], []
    for acc in accounts:
        key = str(acc['login'])
        since = now - 90 * 86400 if (a.reread90 or key not in state) else int(state[key]) - 3 * 86400   # 3 days overlap: partly closed positions
        try:
            rs = read_account(acc, since)
            rows += rs
            acc_out.append(dict(login=key, label=acc.get('label', ''), deals=len(rs), last=max((r['_t'] for r in rs), default=state.get(key, since))))
        except Exception as ex:
            logging.exception('account %s', key); errors.append(f"{acc.get('label') or key}: {ex}")
    for path in dict.fromkeys(acc['path'] for acc in accounts):      # close each import MT5 once, after all accounts
        close_terminal(path)
    trades = group_trades(rows, a.group_hours, a.merge_across not in ('0', 'false', 'off'))
    for r in rows:
        r.pop('_t', None)
    payload = dict(request_id=a.request, executions=rows, trades=trades, errors=errors,
                   accounts=[dict(x, last=jst(x['last']) if x['last'] else '') for x in acc_out],
                   settings=dict(group_hours=a.group_hours, merge_across=a.merge_across, reread90=a.reread90))
    logging.info('import: %d executions, %d trades, %d errors', len(rows), len(trades), len(errors))
    if a.dry_run:
        print(json.dumps(payload, ensure_ascii=False, default=str)[:3000]); return payload
    r = gas.call('eaImportBatch', payload, timeout=120)
    if not (isinstance(r, dict) and r.get('success')):
        raise SystemExit(f'GAS import failed: {r}')
    for x in acc_out:
        if x['last']:
            state[x['login']] = int(x['last'])
    STATE_F.write_text(json.dumps(state), encoding='utf-8')
    logging.info('GAS: %s', {k: v for k, v in r.items() if k != 'success'})
    return r


if __name__ == '__main__':
    main()
