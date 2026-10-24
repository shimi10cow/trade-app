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
            self.config = cfg; save_json(self.config_file, cfg)

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
        for sym, eas in by_sym.items():
            try:
                report += self._step_symbol(sym, eas, eq)
            except Exception as ex:
                logging.exception('%s step failed', sym)
                self.notify('error', f'EA {sym}: {ex}')
                gas.enqueue('eaLog', dict(account=self.kind, level='error', message=f'{sym}: {ex}'[:500]))
        self.save()
        return report

    def _live_positions(self, key):
        return [p for p in self.b.positions({MAGIC[key]})]

    def _step_symbol(self, sym, eas, eq):
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
            return []
        self.state['last_bar'][sym] = last_t
        m = bars[['t', 'o', 'h', 'l', 'c']].copy()
        for z in 'ohlc':
            m[z] = to_space(sym, m[z].to_numpy())
        start = m.t.iat[0] + pd.Timedelta(days=warm)
        F = Frames(m, start, h_days=warm, m_days=warm)
        env = None
        days_list = sorted(set(pd.to_datetime(bars.t).dt.normalize()))
        out = []
        for e in eas:
            if e.key in DAILY and not in_daily_slot:
                continue
            if e.key in DAILY and self.state.get('daily_done', {}).get(e.key) == str(now.date()):
                continue
            if env is None and e.key not in DAILY:
                env = Env(F.m15_all)
            res = e.run(F, env)
            out += self._reconcile(e, res, sym, eq, days_list, now)
            if e.key in DAILY:
                self.state.setdefault('daily_done', {})[e.key] = str(now.date())
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
        lots, money, note = sizing.lots_for(self.b.spec(sym), eq, float(self.state['peak']), float(self.config.get('base_risk', 0.01)), mult, cfg['weight'], dist)
        side_j = '買い' if s == 1 else '売り'
        rec = dict(account=self.kind, ea=key, symbol=sym, side=s, signal_time=to_jst(p['signal_t']), price=px, sl=sl, tp=tp or '',
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
        open_t = {str(p.ticket) for p in self.b.positions(set(MAGIC.values()))}
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
                 dd=(1 - a['equity'] / self.state['peak']) if self.state.get('peak') else 0, positions=len(self.b.positions(set(MAGIC.values()))),
                 outbox=gas.pending_count(), time=to_jst(self.b.server_now() or pd.Timestamp.now()))
        try:
            r = gas.call('eaHeartbeat', x)
            if isinstance(r, dict) and r.get('config'):
                self.set_config(r['config'])
        except Exception as ex:
            logging.warning('heartbeat failed: %s', ex)
        return x
