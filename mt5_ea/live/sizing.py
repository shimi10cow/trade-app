"""Lot size and risk rules for the live EAs (2026-10-24, docs/EA_SYSTEM_PLAN.md / RESEARCH_LOG §98-102, §106).

risk per trade = equity x base risk (default 1.0%)
                 x calendar multiplier (1.5 on the first 3 trading days of the month, and on gold Friday buys)
                 x lot weight (gold S / Q: 0.5 by default, 1.0 selectable)
                 x 0.5 while the account is 10% or more below its peak
lots = that money / (loss per lot if the stop is hit), rounded DOWN to the broker's volume step.
If even the minimum lot would lose more than MAX_MINLOT_RISK (1.5%) of equity, the trade is skipped (logged, not traded).
Prices here are broker prices (not the research price space).
"""
import math
from dataclasses import dataclass

import pandas as pd

MAX_MINLOT_RISK = 0.015
DD_HALF_AT = 0.10


@dataclass
class SymbolSpec:
    """From MT5 symbol_info: volume_min / volume_step / volume_max, trade_tick_size, trade_tick_value (account currency
    per tick per 1 lot)."""
    volume_min: float
    volume_step: float
    volume_max: float
    tick_size: float
    tick_value: float

    def loss_per_lot(self, stop_dist):
        return stop_dist / self.tick_size * self.tick_value


def calendar_mult(symbol, side, t, trading_day_of_month):
    """t = signal time (broker time); trading_day_of_month = 1 for the month's first trading day of that symbol."""
    if trading_day_of_month <= 3:
        return 1.5
    if symbol == 'XAUUSD' and side == 1 and pd.Timestamp(t).dayofweek == 4:
        return 1.5
    return 1.0


def trading_day_of_month(days, t):
    """days = sorted unique trading dates of the symbol (from its bars); position of t's date within its month (1-based)."""
    d = pd.Timestamp(t).normalize()
    month = [x for x in days if x.year == d.year and x.month == d.month and x <= d]
    return len(month) if month else 1


def lots_for(spec: SymbolSpec, equity, peak, base_risk, mult, weight, stop_dist, dd_half=True):
    """Returns (lots, risk_money, note). lots = 0 means skip."""
    if stop_dist <= 0 or equity <= 0:
        return 0.0, 0.0, 'bad stop'
    dd = 1 - equity / peak if peak > 0 else 0.0
    half = dd_half and dd >= DD_HALF_AT                  # app switch 'DD10%で半分'
    risk = base_risk * mult * weight * (0.5 if half else 1.0)
    money = equity * risk
    per_lot = spec.loss_per_lot(stop_dist)
    lots = math.floor(money / per_lot / spec.volume_step + 1e-9) * spec.volume_step
    lots = min(lots, spec.volume_max)
    if lots < spec.volume_min:
        if spec.volume_min * per_lot <= MAX_MINLOT_RISK * equity:
            lots = spec.volume_min
            return round(lots, 8), lots * per_lot, f'min lot (risk {lots * per_lot / equity:.2%})'
        return 0.0, spec.volume_min * per_lot, f'skip: min lot risk {spec.volume_min * per_lot / equity:.2%} > {MAX_MINLOT_RISK:.1%}'
    return round(lots, 8), lots * per_lot, f'risk {risk:.2%}' + (' (DD half)' if half else '')
