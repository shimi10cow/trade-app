"""EA entry point: multi-timeframe environment recognition as of a point in time.

    env = EnvRecognizer({'D1': df_d1, 'H4': df_h4, 'H1': df_h1})   # OHLC frames t,o,h,l,c (bar OPEN time)
    s = env.state_at(pd.Timestamp('2026-07-20 12:00'))              # uses only bars CLOSED by then
    s['H4']['trend'], s['H4']['protected'], s['H4']['zones'], s['H4']['lines'] ...

Timing contract
  - A bar is usable once its close time (open + TF length) <= ts. Partial bars are never used.
  - Entry at the open of bar k: call state_at(open time of k) -> everything known at the close of k-1.
  - All events are causal (tested: truncating the data never changes earlier states).
Caveats
  - Bar boundaries/timezone must match the broker used by the EA (D1/W1 especially).
  - Needs warm-up history (a few hundred bars per TF) before the first state is reliable.
"""
import bisect
import pandas as pd
from . import dow_trend, zones as zmod, lines as lmod

TF_LEN = {'W1': pd.Timedelta(days=7), 'D1': pd.Timedelta(days=1), 'H4': pd.Timedelta(hours=4),
          'H1': pd.Timedelta(hours=1), 'M15': pd.Timedelta(minutes=15)}


class EnvRecognizer:
    def __init__(self, frames):
        self.tf = {}
        for tf, df in frames.items():
            df = df.reset_index(drop=True)
            res = dow_trend.run(df, tf)
            self.tf[tf] = dict(df=df, res=res, zones=zmod.build(df, res), lines=lmod.run(df, tf, res),
                               close=list(pd.to_datetime(df.t) + TF_LEN[tf]))
            brk = {}
            for e in self.tf[tf]['lines']['events']:
                if e['action'] in ('break', 'reset', 'revise'):
                    brk.setdefault(e['key'], []).append((e['idx'], e['action'] == 'break'))
            self.tf[tf]['brk'] = brk

    def last_closed(self, tf, ts):
        """Index of the last bar of `tf` whose close time <= ts (or -1)."""
        return bisect.bisect_right(self.tf[tf]['close'], pd.Timestamp(ts)) - 1

    def tf_state(self, tf, k):
        d = self.tf[tf]
        if k < 0:
            return None
        res = d['res']
        trend, prot = res['bars'][k]
        ptrend, pprot = res['prov_bars'][k]
        close = float(d['df'].c[k])
        zs = []
        for z in zmod.active_asof(d['zones'], k):
            pos = 'above' if close > z['top'] else 'below' if close < z['bottom'] else 'inside'
            zs.append(dict(bottom=z['bottom'], top=z['top'], sources=list(z['sources']),
                           price_is=pos, anchor_time=d['df'].t[z['anchor']],
                           active_since=d['df'].t[z['activation']]))
        ls = []
        for ln in lmod.active_asof(d['lines'], k):
            cls = None if trend is None else ('impulse' if ln['direction'] == trend else 'correction')
            ls.append(dict(key=ln['key'], type=ln['type'], direction=ln['direction'], cls=cls,
                           value=ln['value'], broken=self._broken(d, ln['key'], k),
                           created_time=d['df'].t[ln['created']]))
        return dict(bar_time=d['df'].t[k], close=close, trend=trend, protected=prot,
                    prov_trend=ptrend, prov_protected=pprot, zones=zs, lines=ls)

    @staticmethod
    def _broken(d, key, k):
        st = False
        for idx, is_break in d['brk'].get(key, []):
            if idx > k:
                break
            st = is_break
        return st

    def state_at(self, ts):
        return {tf: self.tf_state(tf, self.last_closed(tf, ts)) for tf in self.tf}

    def trend_table(self, base_tf):
        """Per base-TF bar: every TF's major/provisional trend and protected level known at that bar's
        OPEN (i.e. from bars closed before it). For fast backtests."""
        base = self.tf[base_tf]['df']
        out = pd.DataFrame({'t': base.t})
        for tf, d in self.tf.items():
            ks = [self.last_closed(tf, t) for t in base.t]
            for name, src in (('trend', 'bars'), ('prov', 'prov_bars')):
                bars = d['res'][src]
                out[f'{tf}_{name}'] = [bars[k][0] if k >= 0 else None for k in ks]
                out[f'{tf}_{name}_level'] = [bars[k][1] if k >= 0 else None for k in ks]
        return out
