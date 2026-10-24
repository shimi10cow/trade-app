"""Broker access for the live EAs (2026-10-24): one interface, two implementations.

  MT5Broker   : the XM KIWAMI account through the MetaTrader5 package (Windows, terminal logged in)
  PaperBroker : a simulated account for tests / dry runs on this machine: fills market orders at the given price,
                checks stops / targets on every new bar (stop first, like the research)

Bars are M15 in broker (server) time, columns t, o, h, l, c, closed bars only.
Positions carry: ticket, symbol (logical, e.g. XAUUSD), side (+1/-1), volume, price_open, sl, tp, magic, comment, time.
"""
import logging
import time
from dataclasses import dataclass, field

import pandas as pd

from .sizing import SymbolSpec

XM_SYMBOLS = {'XAUUSD': 'GOLD#', 'XAGUSD': 'SILVER#', 'JP225': 'JP225Cash#', 'US500': 'US500Cash#', 'US30': 'US30Cash#',
              'EURUSD': 'EURUSD#', 'USDJPY': 'USDJPY#', 'BTCUSD': 'BTCUSD#', 'ETHUSD': 'ETHUSD#'}
# Names differ between XM account types (KIWAMI '#', Standard none, Micro 'micro', demo servers ...): try these bases in order,
# each with the suffixes below, then fall back to any symbol on the account whose name starts with a base.
XM_BASES = {'XAUUSD': ['GOLD', 'XAUUSD'], 'XAGUSD': ['SILVER', 'XAGUSD'], 'JP225': ['JP225Cash', 'JP225'], 'US500': ['US500Cash', 'US500'],
            'US30': ['US30Cash', 'US30'], 'BTCUSD': ['BTCUSD'], 'ETHUSD': ['ETHUSD']}
SUFFIXES = ['#', '', '.', 'micro', '#.']


@dataclass
class Position:
    ticket: int
    symbol: str
    side: int
    volume: float
    price_open: float
    sl: float
    tp: float
    magic: int
    comment: str
    time: pd.Timestamp


class MT5Broker:
    def __init__(self, deviation=20):
        import os
        import MetaTrader5 as mt5
        self.mt5 = mt5; self.deviation = deviation; self._names = {}
        path = os.getenv('EA_MT5_PATH', '').strip()          # which terminal (demo / live copies) this process uses
        if not (mt5.initialize(path) if path else mt5.initialize()):
            raise RuntimeError(f'MT5 initialize failed: {mt5.last_error()}')

    # ---- symbols
    def name(self, sym):
        import os
        if sym not in self._names:
            forced = os.getenv('EA_SYMBOL_' + sym, '').strip()          # manual override, e.g. EA_SYMBOL_XAUUSD=GOLDm
            bases = XM_BASES.get(sym, [sym])
            cand = ([forced] if forced else []) + [b + x for b in bases for x in SUFFIXES]
            found = next((c for c in cand if self.mt5.symbol_info(c) is not None), None)
            if not found:
                allnames = [s_.name for s_ in (self.mt5.symbols_get() or [])]
                found = next((n for b in bases for n in sorted(allnames) if n.upper().startswith(b.upper())), None)
            if not found:
                raise RuntimeError(f'{sym}: symbol not found on this account (tried {cand[:6]}...)')
            self.mt5.symbol_select(found, True); self._names[sym] = found
        return self._names[sym]

    def logical(self, broker_name):
        for k, v in self._names.items():
            if v == broker_name:
                return k
        for k, v in XM_SYMBOLS.items():
            if v == broker_name:
                return k
        return broker_name.rstrip('#').replace('Cash', '')

    def spec(self, sym):
        i = self.mt5.symbol_info(self.name(sym))
        return SymbolSpec(i.volume_min, i.volume_step, i.volume_max, i.trade_tick_size, i.trade_tick_value)

    # ---- data
    def bars(self, sym, days):
        mt5 = self.mt5
        to = pd.Timestamp.utcnow().tz_localize(None) + pd.Timedelta(days=1)
        r = mt5.copy_rates_range(self.name(sym), mt5.TIMEFRAME_M15, (to - pd.Timedelta(days=days)).to_pydatetime(), to.to_pydatetime())
        if r is None or len(r) < 10:
            raise RuntimeError(f'{sym}: no M15 history ({mt5.last_error()})')
        d = pd.DataFrame(r)
        d['t'] = pd.to_datetime(d.time, unit='s')        # MT5 encodes server time as if UTC -> naive broker time
        d = d.rename(columns=dict(open='o', high='h', low='l', close='c'))[['t', 'o', 'h', 'l', 'c', 'spread']]
        return d.iloc[:-1].reset_index(drop=True)           # the last bar is still forming

    def server_now(self, sym='EURUSD'):
        tk = self.mt5.symbol_info_tick(self.name(sym))
        return pd.to_datetime(tk.time, unit='s') if tk else None

    def quote(self, sym):
        tk = self.mt5.symbol_info_tick(self.name(sym))
        return (tk.bid, tk.ask) if tk else (None, None)

    # ---- account / positions
    def account(self):
        a = self.mt5.account_info()
        return dict(login=a.login, server=a.server, balance=a.balance, equity=a.equity, currency=a.currency,
                    margin_free=a.margin_free, trade_mode=a.trade_mode)

    def positions(self, magics=None):
        out = []
        for p in self.mt5.positions_get() or []:
            if magics is not None and int(p.magic) not in magics:
                continue
            out.append(Position(int(p.ticket), self.logical(p.symbol), 1 if p.type == self.mt5.POSITION_TYPE_BUY else -1, p.volume,
                                p.price_open, p.sl, p.tp, int(p.magic), p.comment, pd.to_datetime(p.time, unit='s')))
        return out

    def deals_for(self, ticket):
        return list(self.mt5.history_deals_get(position=ticket) or [])

    # ---- orders
    def _send(self, req):
        mt5 = self.mt5
        info = mt5.symbol_info(req['symbol'])
        for mode in (int(getattr(info, 'filling_mode', 0) or 0), mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN):
            if mode not in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN):
                continue
            r = mt5.order_check({**req, 'type_filling': mode})
            if r is not None and r.retcode == 0:
                res = mt5.order_send({**req, 'type_filling': mode})
                if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
                    raise RuntimeError(f'order_send failed: {res} {mt5.last_error()}')
                return res
        raise RuntimeError(f'order_check rejected: {mt5.last_error()}')

    def open(self, sym, side, volume, sl, tp, magic, comment):
        mt5 = self.mt5; name = self.name(sym); bid, ask = self.quote(sym)
        req = dict(action=mt5.TRADE_ACTION_DEAL, symbol=name, volume=float(volume), type=mt5.ORDER_TYPE_BUY if side == 1 else mt5.ORDER_TYPE_SELL,
                   price=ask if side == 1 else bid, sl=float(sl), tp=float(tp or 0), deviation=self.deviation, magic=int(magic),
                   comment=comment[:31], type_time=mt5.ORDER_TIME_GTC)
        res = self._send(req)
        return dict(ticket=int(res.order), price=res.price, volume=res.volume)

    def modify(self, pos: Position, sl=None, tp=None):
        mt5 = self.mt5
        req = dict(action=mt5.TRADE_ACTION_SLTP, position=pos.ticket, symbol=self.name(pos.symbol),
                   sl=float(pos.sl if sl is None else sl), tp=float(pos.tp if tp is None else tp), magic=pos.magic)
        r = mt5.order_send(req)
        if r is None or r.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f'modify failed: {r} {mt5.last_error()}')

    def close(self, pos: Position, comment='close'):
        mt5 = self.mt5; bid, ask = self.quote(pos.symbol)
        req = dict(action=mt5.TRADE_ACTION_DEAL, symbol=self.name(pos.symbol), volume=float(pos.volume), position=pos.ticket,
                   type=mt5.ORDER_TYPE_SELL if pos.side == 1 else mt5.ORDER_TYPE_BUY, price=bid if pos.side == 1 else ask,
                   deviation=self.deviation, magic=pos.magic, comment=comment[:31], type_time=mt5.ORDER_TIME_GTC)
        return self._send(req)


@dataclass
class PaperBroker:
    """Simulated account. Feed bars with set_bars(); call on_bar(sym, bar) to process stops / targets of a new bar."""
    balance: float = 300000.0
    specs: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)
    now: pd.Timestamp = None
    _pos: list = field(default_factory=list)
    closed: list = field(default_factory=list)
    _ticket: int = 1000

    def spec(self, sym):
        return self.specs.get(sym) or SymbolSpec(0.01, 0.01, 100.0, 0.01, 1.0)

    def set_bars(self, sym, df):
        self.data[sym] = df

    def bars(self, sym, days):
        d = self.data[sym]; d = d[d.t + pd.Timedelta(minutes=15) <= self.now]
        return d[d.t >= self.now - pd.Timedelta(days=days)].reset_index(drop=True)

    def server_now(self, sym='EURUSD'):
        return self.now

    def last_close(self, sym):
        return self.bars(sym, 2).c.iat[-1]

    def quote(self, sym):
        c = self.last_close(sym); return c, c

    def account(self):
        eq = self.balance + sum(self._pnl(p, self.last_close(p.symbol)) for p in self._pos)
        return dict(login=0, server='paper', balance=self.balance, equity=eq, currency='JPY', margin_free=eq, trade_mode=0)

    def _pnl(self, p, px):
        s = self.spec(p.symbol)
        return p.side * (px - p.price_open) / s.tick_size * s.tick_value * p.volume

    def positions(self, magics=None):
        return [p for p in self._pos if magics is None or p.magic in magics]

    def open(self, sym, side, volume, sl, tp, magic, comment, price=None):
        px = self.last_close(sym) if price is None else price
        self._ticket += 1
        self._pos.append(Position(self._ticket, sym, side, volume, px, sl, tp or 0.0, magic, comment, self.now))
        return dict(ticket=self._ticket, price=px, volume=volume)

    def modify(self, pos, sl=None, tp=None):
        if sl is not None: pos.sl = sl
        if tp is not None: pos.tp = tp

    def close(self, pos, comment='close', price=None):
        px = self.last_close(pos.symbol) if price is None else price
        self._finish(pos, px, comment)

    def _finish(self, pos, px, why):
        self.balance += self._pnl(pos, px)
        self._pos = [p for p in self._pos if p.ticket != pos.ticket]
        self.closed.append(dict(ticket=pos.ticket, symbol=pos.symbol, side=pos.side, volume=pos.volume, open=pos.price_open, close=px,
                                magic=pos.magic, comment=pos.comment, open_t=pos.time, close_t=self.now, why=why))

    def on_bar(self, sym, bar):
        """Stops / targets on a newly closed bar (stop first). Positions opened at this bar's open are included."""
        for p in [p for p in self._pos if p.symbol == sym]:
            if p.sl and ((bar.l <= p.sl) if p.side == 1 else (bar.h >= p.sl)):
                self._finish(p, p.sl, 'sl')
            elif p.tp and ((bar.h >= p.tp) if p.side == 1 else (bar.l <= p.tp)):
                self._finish(p, p.tp, 'tp')
