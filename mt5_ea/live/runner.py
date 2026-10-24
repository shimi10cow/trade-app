"""Live EA runner (2026-10-24): one process per MT5 terminal (demo account / live account).

Every closed M15 bar (checked every few seconds):
  1. per symbol: last WINDOW days of M15 bars -> research price space -> Frames (+ Env)
  2. per enabled EA of that symbol: run the research-identical logic -> simulated open positions + pending entries
  3. reconcile with the MT5 positions of that EA (magic number):
       - simulated position still open  -> move the broker stop to the simulated stop (only ever tightening)
       - simulated position closed (time / signal exit) but still open at the broker -> close at market
       - pending entry on the last closed bar -> new order (mode 'auto') or notification only (mode 'signal')
  4. heartbeat + config from the app (GAS) every few minutes; trade records via the outbox
RSI(2) (daily EAs) is only evaluated in the slot just before the session close (23:45-23:55 broker time).
Missed bars (PC off) are never traded afterwards: only signals on the last closed bar become orders.
Config (EA_Config from the app, cached in live_config.json): running, base_risk, per EA mode ('auto'/'signal'/'off'), weight.
"""
import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import gas, sizing
from . import reservations as RV
from .core import Frames, from_space, to_space
from .env import Env
from .registry import ADOPTED, BY_KEY

HERE = Path(__file__).resolve().parent
STATE_F = Path(os.getenv('EA_STATE_FILE', HERE / 'live_state.json'))
CONFIG_F = Path(os.getenv('EA_CONFIG_FILE', HERE / 'live_config.json'))
ACCOUNT_KIND = os.getenv('EA_ACCOUNT_KIND', 'demo')          # demo | live
MAGIC_BASE = 770000
MAGIC = {e.key: MAGIC_BASE + i for i, e in enumerate(ADOPTED)}
KEY_OF = {v: k for k, v in MAGIC.items()}
DAILY = {'M@US30', 'M@US500'}
TP_R = {'DS@JP225': 2.0, 'DS@US500': 2.0}                  # fixed 2R targets (broker-side TP)
JST = 'Asia/Tokyo'; SERVER_TZ = 'Europe/Athens'

DEFAULT_CONFIG = dict(running=False, base_risk=0.01, eas={e.key: dict(mode='off', weight=e.weight) for e in ADOPTED})


def compute_symbol(sym, m, warm, keys):
    """EA logic for one symbol (pure calculation, no broker access): returns {key: result}. Runs in a worker process."""
    start = m.t.iat[0] + pd.Timedelta(days=warm)
    F = Frames(m, start, h_days=warm, m_days=warm)
    env, out = None, {}
    for key in keys:
        if env is None and key not in DAILY:
            env = Env(F.m15_all)
        out[key] = BY_KEY[key].run(F, env)
    return out


_POOL = None


def _pool():
    """Worker processes for the per-symbol calculation (EA_WORKERS, default: CPU cores - 1, at most 8; 1 = no pool)."""
    global _POOL
    n = int(os.getenv('EA_WORKERS') or max(1, min(8, (os.cpu_count() or 2) - 1)))
    if n <= 1:
        return None
    if _POOL is None:
        from concurrent.futures import ProcessPoolExecutor
        _POOL = ProcessPoolExecutor(max_workers=n)
    return _POOL


def to_jst(t):
    return pd.Timestamp(t).tz_localize(SERVER_TZ, ambiguous='NaT', nonexistent='shift_forward').tz_convert(JST).strftime('%Y-%m-%d %H:%M+09:00')


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception:
        return default


def save_json(p, x):
    tmp = Path(str(p) + '.tmp'); tmp.write_text(json.dumps(x, ensure_ascii=False, indent=1, default=str), encoding='utf-8'); tmp.replace(p)


class Runner:
    def __init__(self, broker, notify=None, account_kind=ACCOUNT_KIND, state_file=STATE_F, config_file=CONFIG_F):
        self.b = broker; self.notify = notify or (lambda kind, text: logging.info('[%s] %s', kind, text))
        self.kind = account_kind; self.state_file = state_file; self.config_file = config_file
        self.state = load_json(state_file, dict(peak=0.0, tickets={}, done_signals=[], last_bar={}))
        self.config = load_json(config_file, DEFAULT_CONFIG)

    # ------------------------------------------------------------------ config / state
    def ea_cfg(self, key):
        c = self.config.get('eas', {}).get(key, {})
        mode = c.get('mode', 'off') if c.get('on', True) else 'off'          # app: symbol switched off = EA off for it
        return dict(mode=mode, weight=float(c.get('weight', BY_KEY[key].weight)))

    def set_config(self, cfg):
        if cfg:
            if self.state.get('tg_stop'):                       # Telegram stop not yet written to the app: keep it stopped
                cfg = dict(cfg, running=False)
            self.config = cfg; save_json(self.config_file, cfg)

    def emergency_stop(self):
        """Telegram /stop: no new orders from now on (positions keep their server-side stops). Also written to the app."""
        self.config = dict(self.config, running=False); save_json(self.config_file, self.config)
        self.state['tg_stop'] = True; self.save()
        self._push_stop()

    def _push_stop(self):
        try:
            r = gas.call('eaStop', dict(account=self.kind))
            if isinstance(r, dict) and r.get('success'):
                self.state['tg_stop'] = False; self.save()
        except Exception as ex:
            logging.warning('eaStop failed (will retry): %s', ex)

    def save(self):
        self.state['done_signals'] = self.state['done_signals'][-500:]
        save_json(self.state_file, self.state)

    # ------------------------------------------------------------------ one step
    def step(self):
        """Run every symbol whose last closed M15 bar is new. Returns a short report."""
        acct = self.b.account(); eq = float(acct['equity'])
        self.state['peak'] = max(float(self.state.get('peak') or 0), eq)
        report = []
        by_sym = {}
        for e in ADOPTED:
            if self.ea_cfg(e.key)['mode'] != 'off' or self._live_positions(e.key):
                by_sym.setdefault(e.symbol, []).append(e)
        jobs = []
        for sym, eas in by_sym.items():
            try:
                job = self._prepare_symbol(sym, eas)
                if job:
                    jobs.append(job)
            except Exception as ex:
                self._symbol_error(sym, ex)
        pool = _pool() if len(jobs) > 1 else None
        futs = {}
        if pool:
            try:
                futs = {j['sym']: pool.submit(compute_symbol, j['sym'], j['m'], j['warm'], j['keys']) for j in jobs}
            except Exception as ex:                       # pool broken: fall back to one by one
                logging.warning('process pool unavailable (%s): computing one by one', ex)
                global _POOL
                _POOL = None; futs = {}
        for j in jobs:
            try:
                res = futs[j['sym']].result(timeout=600) if j['sym'] in futs else compute_symbol(j['sym'], j['m'], j['warm'], j['keys'])
                report += self._finish_symbol(j, res, eq)
            except Exception as ex:
                self._symbol_error(j['sym'], ex)
        try:
            report += self._step_reservations(eq)
        except Exception as ex:
            logging.exception('reservations step failed')
            gas.enqueue('eaLog', dict(account=self.kind, level='error', message=f'reservations: {ex}'[:500]))
        self.save()
        return report

    # ------------------------------------------------------------------ reservation entries (予約)
    def refresh_reservations(self):
        """Read the waiting reservations of this account right before the bar closes (cheap GET)."""
        try:
            r = gas.call('eaResList', dict(account=self.kind))
            if isinstance(r, dict) and isinstance(r.get('reservations'), list):
                self.state['reservations'] = r['reservations']
        except Exception as ex:
            logging.warning('reservation list failed: %s', ex)

    def _step_reservations(self, eq):
        out = []
        done = self.state.setdefault('res_done', [])
        last_seen = self.state.setdefault('res_last', {})
        for r in self.state.get('reservations') or []:
            rid = str(r.get('ResID') or '')
            if not rid or rid in done or str(r.get('Account') or 'demo') != self.kind or str(r.get('Status')) != 'WAIT':
                continue
            sym = str(r['Symbol']).upper(); side = 1 if str(r['Direction']).upper() == 'BUY' else -1
            m15 = self.b.bars(sym, 12)[['t', 'o', 'h', 'l', 'c']]
            frame = RV.h1_bars(m15) if str(r.get('Trigger')).upper() == 'H1' else m15
            if not len(frame):
                continue
            lt = str(frame.t.iat[-1])
            if last_seen.get(rid) == lt:                     # this bar of the trigger frame was already checked
                continue
            last_seen[rid] = lt
            hit = RV.trigger_on_last(frame, side, RV.to_server(r.get('CreatedAt')))
            if hit:
                hit['mas'] = RV.mas(m15)
                out += self._enter_res(r, rid, sym, side, hit, eq)
        live_ids = {str(r.get('ResID')) for r in self.state.get('reservations') or []}
        self.state['res_last'] = {k: v for k, v in last_seen.items() if k in live_ids}
        self.state['res_done'] = done[-200:]
        return out

    def _enter_res(self, r, rid, sym, side, hit, eq):
        key = 'RES:' + rid; side_j = '買い' if side == 1 else '売り'
        bid, ask = self.b.quote(sym); px = ask if side == 1 else bid
        sl, sl_note = RV.stop_for(str(r.get('SLMode') or ''), side, px, hit, r.get('SLPrice'))
        if side * (px - sl) <= 0:
            self.notify('error', f'予約 {sym} {side_j}: 損切り {sl:.5g} が今の値段 {px:.5g} の逆側なので見送り（予約は残す）')
            return [f'{key} skip: stop on the wrong side']
        tp = float(r['TPPrice']) if str(r.get('TPPrice') or '').strip() else None
        if tp is not None and side * (tp - px) <= 0:
            tp = None
        lots, money, note = RV.lots_for_res(self.b.spec(sym), eq, str(r.get('LotMode') or 'pct'), r.get('LotValue') or 0.5, abs(px - sl))
        rec = dict(account=self.kind, ea=key, source='RES', symbol=sym, side=side, signal_time=to_jst(hit['t']), price=px, spread=(ask - bid) if (ask and bid) else '', sl=sl, tp=tp or '',
                   lots=lots, risk_jpy=round(money), mult=1, weight=1, note=note + sl_note, reason=f"予約 {r.get('Trigger')} エントリー")
        if not self.config.get('running', False) or lots <= 0:
            why = '全体停止中' if not self.config.get('running', False) else note
            self.notify('signal', f'予約のシグナル {sym} {side_j} {px:.5g}（{why}・予約は残す）')
            gas.enqueue('eaSignal', dict(rec, status=why))
            return [f'{key} signal only ({why})']
        o = self.b.open(sym, side, lots, sl, tp, RV.RES_MAGIC, f'RES {rid}'[:31])
        self.state['tickets'][str(o['ticket'])] = dict(key=key, sim_t='', side=side, entry=o['price'], sl0=sl, lots=o['volume'],
                                                         opened=str(self.b.server_now(sym)), risk_jpy=money, res=rid)
        self.state['res_done'].append(rid)
        self.notify('entry', f'予約エントリー {sym} {side_j} {o["price"]:.5g} {o["volume"]}lot 損切り {sl:.5g}（{note}）')
        gas.enqueue('eaTradeOpen', dict(rec, ticket=o['ticket'], fill=o['price'], lots=o['volume'], entry_time=to_jst(self.b.server_now(sym) or hit['t'])))
        gas.enqueue('eaResFilled', dict(account=self.kind, res_id=rid, trade_id=f'{self.kind}:{o["ticket"]}'))
        return [f'{key} open {o["ticket"]} {side_j} {o["volume"]} @ {o["price"]}']

    def _live_positions(self, key):
        return [p for p in self.b.positions({MAGIC[key]})]

    def _symbol_error(self, sym, ex):
        logging.error('%s step failed: %s', sym, ex, exc_info=ex)
        self.notify('error', f'EA {sym}: {ex}')
        gas.enqueue('eaLog', dict(account=self.kind, level='error', message=f'{sym}: {ex}'[:500]))

    def _prepare_symbol(self, sym, eas):
        """Broker side before the calculation: bars, which EAs run now. None = nothing new for this symbol."""
        days = max(e.window_days for e in eas); warm = max(e.warm_days for e in eas)
        bars = self.b.bars(sym, days)
        if len(bars) < 1000:
            raise RuntimeError(f'only {len(bars)} M15 bars')
        last_t = str(bars.t.iat[-1])
        now = self.b.server_now(sym) or (bars.t.iat[-1] + pd.Timedelta(minutes=15))
        in_daily_slot = now.hour == 23 and 45 <= now.minute <= 55
        new_bar = self.state['last_bar'].get(sym) != last_t
        daily_todo = in_daily_slot and any(e.key in DAILY and self.state.get('daily_done', {}).get(e.key) != str(now.date()) for e in eas)
        if not new_bar and not daily_todo:
            return None
        self.state['last_bar'][sym] = last_t
        run = [e for e in eas if not (e.key in DAILY and (not in_daily_slot or self.state.get('daily_done', {}).get(e.key) == str(now.date())))]
        if not run:
            return None
        m = bars[['t', 'o', 'h', 'l', 'c']].copy()
        m['t'] = m.t.astype('datetime64[us]')               # one time unit everywhere (MT5 gives seconds)
        for z in 'ohlc':
            m[z] = to_space(sym, m[z].to_numpy())
        return dict(sym=sym, m=m, warm=warm, keys=[e.key for e in run], now=now,
                    days_list=sorted(set(pd.to_datetime(bars.t).dt.normalize())))

    def _finish_symbol(self, j, res, eq):
        """Broker side after the calculation: orders / stops for each EA of the symbol, in registry order."""
        out = []
        for key in j['keys']:
            out += self._reconcile(BY_KEY[key], res[key], j['sym'], eq, j['days_list'], j['now'])
            if key in DAILY:
                self.state.setdefault('daily_done', {})[key] = str(j['now'].date())
        return out

    # ------------------------------------------------------------------ reconcile one EA
    def _reconcile(self, e, res, sym, eq, days_list, now):
        key = e.key; cfg = self.ea_cfg(key); out = []
        live = self._live_positions(key)
        sim_open = {(str(pd.Timestamp(p['t'])), int(p['side'])): p for p in res['open'] if 't' in p}
        tickets = self.state['tickets']
        for pos in live:
            info = tickets.get(str(pos.ticket))
            if not info:
                continue                                    # not ours / unknown: leave it alone
            sp = sim_open.get((info['sim_t'], pos.side))
            if sp is None:
                closed = res['trades']
                hit = None
                if len(closed):
                    c2 = closed[(pd.to_datetime(closed.t) == pd.Timestamp(info['sim_t'])) & (closed.side == pos.side)]
                    hit = c2.iloc[0] if len(c2) else None
                if hit is not None and hit.get('why') not in ('stop', 'target'):
                    self.b.close(pos, f'{key} exit'); out.append(f'{key} close {pos.ticket} ({hit.get("why")})')
                    self.notify('exit', f'EA 決済 {key} {"買い" if pos.side == 1 else "売り"} #{pos.ticket}（{hit.get("why")}）')
                continue
            new_sl = float(from_space(sym, sp['sl']))
            if (pos.side == 1 and new_sl > pos.sl + 1e-12) or (pos.side == -1 and (pos.sl == 0 or new_sl < pos.sl - 1e-12)):
                self.b.modify(pos, sl=new_sl); out.append(f'{key} sl {pos.ticket} -> {new_sl:.5g}')
        # new entries (never for an EA in mode 'off': it is only computed to keep managing its open positions)
        for p in ([] if cfg['mode'] == 'off' else res['pending']):
            sig = f"{key}|{p['signal_t']}|{p['side']}"
            if sig in self.state['done_signals'] or not e.entry_ok(p['signal_t']):
                continue
            self.state['done_signals'].append(sig)
            out += self._enter(e, cfg, p, sym, eq, days_list, now)
        return out

    def _enter(self, e, cfg, p, sym, eq, days_list, now):
        key, s = e.key, int(p['side'])
        bid, ask = self.b.quote(sym)
        px = ask if s == 1 else bid
        x = float(to_space(sym, [px])[0])
        if 'ref' in p:                                      # engine style: stop = ref -/+ buffer, min risk
            sl_x = p['ref'] - s * p['buf']
            if s * (x - sl_x) <= 0:
                self.notify('signal', f'EA 見送り {key}: 損切りが逆側'); return [f'{key} skip: stop on the wrong side']
            if s * (x - sl_x) < p.get('min_risk', 0):
                sl_x = x - s * p['min_risk']
        else:                                               # RSI(2) / engine_m15: stop given
            sl_x = p.get('sl', p.get('sl0'))
        sl = float(from_space(sym, [sl_x])[0]); dist = abs(px - sl)
        tp = None
        if key in TP_R:
            tp = float(from_space(sym, [x + s * TP_R[key] * abs(x - sl_x)])[0])
        tdm = sizing.trading_day_of_month(days_list, p['signal_t'])
        mult = sizing.calendar_mult(sym, s, p['signal_t'], tdm)
        lots, money, note = sizing.lots_for(self.b.spec(sym), eq, float(self.state['peak']), float(self.config.get('base_risk', 0.01)), mult, cfg['weight'], dist,
                                          dd_half=self.config.get('dd_half', True) is not False)
        side_j = '買い' if s == 1 else '売り'
        rec = dict(account=self.kind, ea=key, symbol=sym, side=s, signal_time=to_jst(p['signal_t']), price=px, spread=(ask - bid) if (ask and bid) else '', sl=sl, tp=tp or '',
                   lots=lots, risk_jpy=round(money), mult=mult, weight=cfg['weight'], note=note, reason=p.get('tag', ''))
        if cfg['mode'] == 'signal' or not self.config.get('running', False) or lots <= 0:
            why = 'シグナルのみ' if cfg['mode'] == 'signal' else ('全体停止中' if not self.config.get('running') else note)
            self.notify('signal', f'EA シグナル {key} {side_j} {px:.5g} 損切り {sl:.5g}（{why}）')
            gas.enqueue('eaSignal', dict(rec, status=why))
            return [f'{key} signal only ({why})']
        r = self.b.open(sym, s, lots, sl, tp, MAGIC[key], f'{key}')
        sim_t = p['t'] if 't' in p else pd.Timestamp(p['signal_t']) + pd.Timedelta(minutes=15)
        self.state['tickets'][str(r['ticket'])] = dict(key=key, sim_t=str(pd.Timestamp(sim_t)), side=s, entry=r['price'], sl0=sl, lots=r['volume'],
                                                         opened=str(now), risk_jpy=money)
        self.notify('entry', f'EA エントリー {key} {side_j} {r["price"]:.5g} {r["volume"]}lot 損切り {sl:.5g}（{note}）')
        gas.enqueue('eaTradeOpen', dict(rec, ticket=r['ticket'], fill=r['price'], lots=r['volume'], entry_time=to_jst(now)))
        return [f'{key} open {r["ticket"]} {side_j} {r["volume"]} @ {r["price"]}']

    # ------------------------------------------------------------------ closed trades -> records
    def sweep_closed(self, deal_reader=None):
        """Tickets we opened that are no longer open: send the result once."""
        open_t = {str(p.ticket) for p in self.b.positions(set(MAGIC.values()) | {RV.RES_MAGIC})}
        for t, info in list(self.state['tickets'].items()):
            if t in open_t:
                continue
            exit_px = profit = None; exit_time = None
            if deal_reader:
                exit_px, profit, exit_time = deal_reader(int(t))
            risk = float(info.get('risk_jpy') or 0)
            gas.enqueue('eaTradeClose', dict(account=self.kind, ticket=t, ea=info['key'], exit=exit_px, profit=profit,
                                             exit_time=to_jst(exit_time) if exit_time is not None else '', R=(profit / risk) if (profit is not None and risk) else ''))
            self.notify('exit', f'EA 決済 {info["key"]} #{t} 損益 {profit if profit is not None else "?"}円')
            del self.state['tickets'][t]
        self.save()

    def heartbeat(self):
        a = self.b.account()
        x = dict(account=self.kind, login=a.get('login'), balance=a['balance'], equity=a['equity'], peak=self.state.get('peak'),
                 dd=(1 - a['equity'] / self.state['peak']) if self.state.get('peak') else 0, positions=len(self.b.positions(set(MAGIC.values()) | {RV.RES_MAGIC})),
                 outbox=gas.pending_count(), time=to_jst(self.b.server_now() or pd.Timestamp.now()))
        if self.state.get('tg_stop'):
            self._push_stop()
        try:
            r = gas.call('eaHeartbeat', x)
            if isinstance(r, dict) and r.get('config'):
                self.set_config(r['config'])
            if isinstance(r, dict) and isinstance(r.get('reservations'), list):
                self.state['reservations'] = r['reservations']
        except Exception as ex:
            logging.warning('heartbeat failed: %s', ex)
        return x
