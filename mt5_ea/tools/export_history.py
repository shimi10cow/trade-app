"""Export the trader's own MT5 history for research (2026-11-02).

Run on the PC (the same import MT5 and accounts as the MT5 import button):
    py -m mt5_ea.tools.export_history --from 2024-01-01
Writes research/data/user_history/:
    deals.csv.gz     every buy/sell deal of every account in TradeEA_data\\import_accounts.json
    bars_<SYMBOL>.csv.gz   M15 bars (broker time) for every symbol that was traded, from 30 days before the first deal
    manifest.json    counts and periods
The GitHub repository is PUBLIC, so the deals are anonymised before they are written: account numbers -> A1, A2, ...;
the account's label (on this PC it is the account number) is never written -- only the server name; no profit / swap /
commission / comment; lot sizes only as a ratio to that account's median lot (keeps scale-in weights).
Bars are read in 120-day pieces (each well under MT5's "max bars in chart"), each piece retried 3 times; pieces that still
fail are listed in manifest.json and the console, so only those need a re-run (--symbols SYM1,SYM2 re-reads just those).
Prices, times, direction, IN/OUT, position id and the order's SL/TP are kept (that is what the analysis needs).
Read-only: no orders, no changes to any account.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from mt5_ea.live.importer import ACCOUNTS_F, SERVER_TZ, jst, logical, close_terminal  # noqa: E402

OUT = ROOT / 'research' / 'data' / 'user_history'


def login(mt5, acc):
    ok = mt5.initialize(acc['path'], portable=True) if acc.get('portable') else mt5.initialize(acc['path'])
    if not ok:
        raise RuntimeError(f"MT5 initialize failed {mt5.last_error()}")
    info = mt5.account_info()
    if info is None or int(info.login) != int(acc['login']):
        mt5.login(int(acc['login']), server=acc.get('server'), timeout=20000)
        info = mt5.account_info()
        if info is None or int(info.login) != int(acc['login']):
            raise RuntimeError(f"password not saved in the import MT5 for this account ({mt5.last_error()})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='frm', default='2024-01-01')
    ap.add_argument('--no-bars', action='store_true')
    ap.add_argument('--symbols', default='', help='re-read only these symbols\' bars (comma separated, logical names); deals are not rewritten')
    a = ap.parse_args()
    import MetaTrader5 as mt5
    OUT.mkdir(parents=True, exist_ok=True)
    accounts = json.loads(Path(ACCOUNTS_F).read_text(encoding='utf-8'))
    frm = pd.Timestamp(a.frm).to_pydatetime(); to = (pd.Timestamp.utcnow().tz_localize(None) + pd.Timedelta(days=2)).to_pydatetime()
    rows, raw_syms, report = [], {}, []
    for n, acc in enumerate(accounts, 1):
        label = f'A{n}'
        try:
            login(mt5, acc)
            deals = mt5.history_deals_get(frm, to) or []
            orders = {o.ticket: o for o in (mt5.history_orders_get(frm, to) or [])}
            k = 0
            acc_rows = []
            for d in deals:
                if int(d.type) not in (0, 1) or not d.symbol:
                    continue
                o = orders.get(d.order)
                acc_rows.append(dict(acct=label, server=str(acc.get('server', '')), position=str(d.position_id), symbol=logical(d.symbol), raw_symbol=d.symbol,
                                     deal_side='BUY' if int(d.type) == 0 else 'SELL', entry={0: 'IN', 1: 'OUT', 2: 'INOUT', 3: 'OUT_BY'}.get(int(d.entry), str(d.entry)),
                                     server_time=pd.Timestamp(int(d.time), unit='s').strftime('%Y-%m-%d %H:%M:%S'), jst=jst(d.time),
                                     price=float(d.price), volume=float(d.volume),
                                     sl=float(getattr(o, 'sl', 0) or 0) if o else 0.0, tp=float(getattr(o, 'tp', 0) or 0) if o else 0.0,
                                     magic=int(d.magic)))
                raw_syms.setdefault(d.symbol, acc)
                k += 1
            if acc_rows:
                med = pd.Series([r['volume'] for r in acc_rows]).median() or 1.0
                for r in acc_rows:
                    r['lot_ratio'] = round(r.pop('volume') / med, 3)
            rows += acc_rows
            report.append(dict(acct=label, server=str(acc.get('server', '')), deals=k))
            print(f'{label} ({acc.get("server", "")}): {k} deals', flush=True)
        except Exception as ex:                       # keep going with the other accounts
            report.append(dict(acct=label, server=str(acc.get('server', '')), error=str(ex)))
            print(f'{label}: ERROR {ex}', flush=True)
        finally:
            mt5.shutdown()
    D = pd.DataFrame(rows)
    only = {x.strip().upper() for x in a.symbols.split(',') if x.strip()}
    if only:                                           # bars re-run: keep the deals file as it is
        raw_syms = {k: v for k, v in raw_syms.items() if logical(k) in only}
    else:
        D.to_csv(OUT / 'deals.csv.gz', index=False, compression='gzip')
    bars = {}
    if not a.no_bars and len(D):
        first = pd.Timestamp(D.server_time.min()) - pd.Timedelta(days=30)
        for sym, acc in raw_syms.items():
            try:
                login(mt5, acc)
                mt5.symbol_select(sym, True)
                parts, failed = [], []
                p0 = first
                end = pd.Timestamp(to)
                while p0 < end:
                    p1 = min(end, p0 + pd.Timedelta(days=120))
                    r = None
                    for _ in range(3):
                        r = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, p0.to_pydatetime(), p1.to_pydatetime())
                        if r is not None:
                            break
                        time.sleep(1)
                    if r is None:
                        failed.append(f"{p0:%Y-%m-%d}..{p1:%Y-%m-%d} {mt5.last_error()}")
                    elif len(r):
                        parts.append(pd.DataFrame(r))
                    p0 = p1
                if not parts:
                    bars[sym] = dict(error='no bars', failed=failed); print(f'{sym}: no bars {failed[:2]}', flush=True); continue
                b = pd.concat(parts).drop_duplicates('time').sort_values('time')
                b['time'] = pd.to_datetime(b.time, unit='s').dt.strftime('%Y-%m-%d %H:%M')
                b[['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread']].to_csv(OUT / f'bars_{logical(sym)}.csv.gz', index=False, compression='gzip')
                bars[sym] = dict(rows=len(b), first=b.time.iat[0], last=b.time.iat[-1], failed=failed)
                print(f'{sym}: {len(b)} M15 bars {b.time.iat[0]} .. {b.time.iat[-1]}' + (f'  FAILED pieces: {failed}' if failed else ''), flush=True)
            except Exception as ex:
                bars[sym] = f'error {ex}'; print(f'{sym}: ERROR {ex}', flush=True)
            finally:
                mt5.shutdown()
    for p in dict.fromkeys(acc['path'] for acc in accounts):
        close_terminal(p)
    if only:
        print(f'bars re-read: {bars}', flush=True)
        return
    (OUT / 'manifest.json').write_text(json.dumps(dict(made=pd.Timestamp.now().isoformat(), server_tz=SERVER_TZ, frm=a.frm, accounts=report,
                                                      deals=len(D), bars=bars), ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'done: {len(D)} deals, {len(bars)} symbols -> {OUT}', flush=True)


if __name__ == '__main__':
    main()
