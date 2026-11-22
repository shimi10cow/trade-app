"""Entry / exit chart images for EA trades (2026-10-30).

Drawn on the EA PC right after an order is filled (entry) and after a close is seen (exit), from the broker's own M15 bars:
H1 candles, H1 MA20 / MA75, the H1 Dow highs / lows (the same 1.9 ATR pivots the EAs use), entry, stop, target and exit.
One PNG is about 50-80 KB and takes about a second; it never delays an order (drawn after it). If matplotlib is not
installed (py -m pip install matplotlib) or anything fails, no image is made and trading goes on as usual.
"""
import io
import logging
import os

import numpy as np
import pandas as pd

_FONT = None


def _setup():
    """matplotlib with a Japanese font if one is on this PC (Windows: Meiryo / Yu Gothic; Linux: IPA / Noto CJK)."""
    global _FONT
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    if _FONT is None:
        _FONT = ''
        for f in (r'C:\Windows\Fonts\meiryo.ttc', r'C:\Windows\Fonts\YuGothM.ttc', r'C:\Windows\Fonts\msgothic.ttc',
                  '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'):
            if os.path.exists(f):
                try:
                    font_manager.fontManager.addfont(f); _FONT = font_manager.FontProperties(fname=f).get_name(); break
                except Exception:
                    pass
    if _FONT:
        plt.rcParams['font.family'] = _FONT
    return plt


def h1_from_m15(m15):
    d = m15.set_index(pd.to_datetime(m15.t))
    return d.resample('1h', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna()


def draw(m15, side, entry_t, entry_px, sl, tp=None, title='', exit_t=None, exit_px=None, R=None, digits=5):
    """m15: broker M15 bars (t, o, h, l, c; broker prices and time). Returns PNG bytes or None."""
    try:
        plt = _setup()
    except Exception as ex:                                  # matplotlib not installed: no images
        logging.info('trade chart skipped: %s', ex)
        return None
    try:
        jp = bool(_FONT)
        h1 = h1_from_m15(m15)
        entry_t = pd.Timestamp(entry_t); end = pd.Timestamp(exit_t) + pd.Timedelta('6h') if exit_t is not None else entry_t + pd.Timedelta('3h')
        start = min(entry_t - pd.Timedelta('4D'), end - pd.Timedelta('5D'))
        g = h1[(h1.index >= start) & (h1.index <= end)]
        if len(g) < 10:
            return None
        ma20 = h1.c.rolling(20).mean().reindex(g.index); ma75 = h1.c.rolling(75).mean().reindex(g.index)
        fig, ax = plt.subplots(figsize=(10, 5.6), dpi=110)
        bg = '#0b1220'; fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
        xs = np.arange(len(g)); up = (g.c >= g.o).to_numpy(); col = np.where(up, '#22c55e', '#ef4444')
        ax.vlines(xs, g.l, g.h, color=col, lw=0.8)
        body = (g.c - g.o).abs().to_numpy(); tick = (g.h.max() - g.l.min()) * 0.002
        ax.bar(xs, np.maximum(body, tick), bottom=np.minimum(g.o, g.c), color=col, width=0.7)
        ax.plot(xs, ma20, color='#38bdf8', lw=1, label='H1 MA20'); ax.plot(xs, ma75, color='#a78bfa', lw=1, label='H1 MA75')
        try:                                                 # the H1 Dow highs / lows (as the EAs see them)
            from env_recognition.pivots import pivot_events
            hh = h1.reset_index().rename(columns={'index': 't'}); last = {}
            for e in pivot_events(hh[['o', 'h', 'l', 'c']].reset_index(drop=True)):
                last[e['id']] = (e['idx'], e['kind'], e['price'])
            pts = sorted(v for v in last.values() if g.index[0] <= hh.t.iat[v[0]] <= g.index[-1])
            if pts:
                px_ = [g.index.searchsorted(hh.t.iat[i]) for i, _, _ in pts]
                ax.plot(px_, [p for _, _, p in pts], color='#fbbf24', lw=1, alpha=0.7, label='H1 ダウ' if jp else 'H1 Dow')
                ax.scatter(px_, [p for _, _, p in pts], color='#fbbf24', s=12, zorder=4)
        except Exception as ex:
            logging.debug('pivots not drawn: %s', ex)
        ix = lambda t: g.index.searchsorted(pd.Timestamp(t).floor('h'))
        f = lambda v: f'{v:.{digits}f}'
        buy = side == 1
        ax.scatter([ix(entry_t)], [entry_px], marker='^' if buy else 'v', s=120, color='#22d3ee', zorder=5)
        ax.annotate(f"{('買い' if buy else '売り') if jp else ('BUY' if buy else 'SELL')} {f(entry_px)}", (ix(entry_t), entry_px), xytext=(8, -4),
                    textcoords='offset points', color='#22d3ee')
        lines = [(sl, '#f87171', ('損切り ' if jp else 'SL ') + f(sl))]
        if tp:
            lines.append((tp, '#4ade80', ('利確 ' if jp else 'TP ') + f(tp)))
        for y, c, l in lines:
            ax.axhline(y, color=c, lw=1, ls='--'); ax.text(len(g) - 1, y, l, color=c, ha='right', va='bottom', fontsize=9)
        if exit_t is not None and exit_px:
            rr = f'  {R:+.2f}R' if R is not None and np.isfinite(R) else ''
            c = '#4ade80' if (R or 0) >= 0 else '#f87171'
            ax.scatter([ix(exit_t)], [exit_px], marker='x', s=120, color=c, zorder=5)
            ax.annotate(f"{'決済' if jp else 'EXIT'} {f(exit_px)}{rr}", (ix(exit_t), exit_px), xytext=(-10, 10), textcoords='offset points', color=c, ha='right')
        step = max(1, len(g) // 8)
        ax.set_xticks(xs[::step]); ax.set_xticklabels([t.strftime('%m/%d %H:00') for t in g.index[::step]], color='#94a3b8', fontsize=8)
        ax.tick_params(colors='#94a3b8'); [s.set_color('#334155') for s in ax.spines.values()]; ax.grid(color='#1e293b', lw=0.5)
        ax.set_title(title, color='#e2e8f0', fontsize=12, loc='left')
        ax.legend(loc='upper left', facecolor=bg, labelcolor='#94a3b8', fontsize=8, frameon=False)
        fig.tight_layout(); buf = io.BytesIO(); fig.savefig(buf, format='png', facecolor=bg); plt.close(fig)
        return buf.getvalue()
    except Exception as ex:
        logging.warning('trade chart failed: %s', ex)
        return None


# ------------------------------------------------------------------ discretionary trades from the MT5 import (2026-11-22)
TFC = {'D1': '#60a5fa', 'H4': '#fb923c', 'H1': '#a78bfa', 'M15': '#facc15'}
TFN = {'D1': '日足', 'H4': 'H4', 'H1': 'H1', 'M15': 'M15'}
SHOWTF = {'D1': ['D1'], 'H4': ['H4', 'D1'], 'H1': ['H1', 'H4', 'D1'], 'M15': ['M15', 'H1', 'H4', 'D1']}   # images (user 11/22): H4 = H4 + D1


def draw_tf(m15, tf, side, entry_t, entry_px, sl, tp=None, exit_t=None, exit_px=None, R=None, digits=5, title='', focus='entry', lines=None, deals=None):
    """A sharp H4 / M15 chart of one trade (user: clear candles, not rough). m15: broker M15 bars (t, o, h, l, c, broker time).
    focus 'entry': the bars around the entry; 'exit': around the exit (the entry too when it fits).
    lines: the EA lines at the entry time (alerts.ea_chart_objects), drawn with the report's rules (砦 / 出入口 named, 抵抗体 white
    dotted, trendlines in the timeframe colour); only the timeframes a chart of `tf` shows. Returns PNG bytes or None."""
    try:
        plt = _setup()
    except Exception as ex:
        logging.info('trade chart skipped: %s', ex); return None
    try:
        jp = bool(_FONT)
        x = m15[['t', 'o', 'h', 'l', 'c']].copy(); x['t'] = pd.to_datetime(x.t); x = x.set_index('t')
        if tf != 'M15':
            x = x.resample({'H4': '4h', 'H1': '1h', 'D1': '1D'}[tf], label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna()
        entry_t = pd.Timestamp(entry_t); exit_t = pd.Timestamp(exit_t) if exit_t is not None and not pd.isna(exit_t) else None
        bar = pd.Timedelta({'H4': '4h', 'H1': '1h', 'D1': '1D', 'M15': '15min'}[tf])
        before, after = {'H4': (90, 25), 'H1': (100, 30), 'M15': (90, 30), 'D1': (90, 20)}[tf]
        anchor = exit_t if (focus == 'exit' and exit_t is not None) else entry_t
        start = anchor - before * bar
        if focus == 'exit' and exit_t is not None and entry_t >= exit_t - (before + after) * bar * 0.85:
            start = min(start, entry_t - 25 * bar)              # keep the entry in view when it fits
        end = anchor + after * bar
        g = x[(x.index >= start) & (x.index <= end)]
        if len(g) < 10:
            return None
        ma = {n: x.c.rolling(n).mean().reindex(g.index) for n in (20, 75, 200)}
        fig, ax = plt.subplots(figsize=(16, 9), dpi=150)          # 2400 x 1350 px
        bg = '#0b1220'; fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
        xs = np.arange(len(g)); O, H, L, C = (g[z].to_numpy(float) for z in 'ohlc'); up = C >= O
        w = 0.62
        for i in range(len(g)):                                    # candles: hollow white up, filled grey down (as the report)
            col = '#e5e7eb' if up[i] else '#94a3b8'
            ax.vlines(i, L[i], H[i], color=col, lw=0.9, zorder=2)
            lo, hi = min(O[i], C[i]), max(O[i], C[i]); hgt = max(hi - lo, (g.h.max() - g.l.min()) * 0.0008)
            ax.add_patch(plt.Rectangle((i - w / 2, lo), w, hgt, facecolor=bg if up[i] else '#64748b', edgecolor=col, lw=0.9, zorder=3))
        for n, c in ((20, '#ef4444'), (75, '#22c55e'), (200, '#f472b6')):
            ax.plot(xs, ma[n].to_numpy(), color=c, lw=1.4, label=f'MA{n}', zorder=4)
        ix = lambda t: float(g.index.searchsorted(pd.Timestamp(t).floor({'H4': '4h', 'H1': '1h', 'D1': '1D', 'M15': '15min'}[tf])))
        xmax = len(g) - 0.5
        # the price range follows the candles (and the trade's own marks in view): far lines do not squash the candles
        inview = [d['p'] for d in (deals or []) if g.index[0] <= pd.Timestamp(d['t']) <= g.index[-1] + bar]
        if not deals:
            inview += [v for v, tt in ((entry_px, entry_t), (exit_px, exit_t)) if v and tt is not None and g.index[0] <= pd.Timestamp(tt) <= g.index[-1] + bar]
        ylo, yhi = min([g.l.min()] + inview), max([g.h.max()] + inview); pad = (yhi - ylo) * 0.06; ylo, yhi = ylo - pad, yhi + pad
        inside = lambda v: v is not None and ylo <= v <= yhi
        # the EA lines at the entry time
        for l in lines or []:
            if l['tf'] not in SHOWTF.get(tf, [tf]):
                continue
            c = TFC.get(l['tf'], '#e2e8f0')
            if l['type'] == 'h':
                x0 = max(0.0, ix(l['t1'])) if l['t1'] >= g.index[0] else 0.0
                if l['kind'] == 'band':
                    ax.hlines(l['p1'], x0, xmax, colors='#e5e7eb', linestyles=(0, (1, 3)), lw=1.1, zorder=1)
                elif l['kind'] == 'user':                                  # the trader's own line (solid)
                    ax.hlines(l['p1'], x0, xmax, colors=c, lw=1.3, zorder=1)
                    if l.get('note'):
                        ax.text(x0 + 1, l['p1'], l['note'], color=c, fontsize=10, va='bottom', clip_on=True)
                else:
                    ax.hlines(l['p1'], x0, xmax, colors=c, linestyles=(0, (6, 4)), lw=1.3, zorder=1)
                    ax.text(x0 + 1, l['p1'], f"{TFN[l['tf']]} {'砦' if l['kind'] == 'fortress' else '出入口'}" if jp else l['kind'], color=c, fontsize=10, va='bottom', clip_on=True)
            elif l['type'] == 'b' and l.get('t2') is not None:     # a box from the report
                a, b2 = sorted((ix(l['t1']), ix(l['t2'])))
                if b2 < 0 or a > xmax:
                    continue
                ax.add_patch(plt.Rectangle((max(a, -0.5), min(l['p1'], l['p2'])), min(b2, xmax) - max(a, -0.5), abs(l['p2'] - l['p1']),
                                           facecolor=c, alpha=0.12, edgecolor=c, lw=1.2, zorder=1))
            elif l['type'] == 't' and l.get('t2') is not None:
                a, b = ix(l['t1']), ix(l['t2'])
                if b == a:
                    continue
                k = (l['p2'] - l['p1']) / (b - a)
                ax.plot([a, xmax], [l['p1'], l['p1'] + k * (xmax - a)], color=c, ls=(0, (6, 4)), lw=1.3, zorder=1)
        f = lambda v: f'{v:.{digits}f}'
        buy = side == 1
        if deals:                                                   # every execution on its own (user 11/22): ▲▼ entries, ✕ exits, with the lot
            for d in deals:
                tt = pd.Timestamp(d['t'])
                if not (g.index[0] <= tt <= g.index[-1] + bar):
                    continue
                isin = d['io'] in ('IN', 'INOUT')
                if isin:
                    ax.scatter([ix(tt)], [d['p']], marker='^' if buy else 'v', s=150, color='#f43f5e' if buy else '#3b82f6', zorder=6, edgecolors='white', linewidths=0.7)
                else:
                    ax.scatter([ix(tt)], [d['p']], marker='X', s=130, color='#fbbf24', zorder=6, edgecolors='white', linewidths=0.6)
                ax.annotate(f"{d['v']:g}", (ix(tt), d['p']), xytext=(7, 6 if isin else -12), textcoords='offset points', color='#cbd5e1', fontsize=9)
        elif g.index[0] <= entry_t <= g.index[-1] + bar:
            ax.scatter([ix(entry_t)], [entry_px], marker='^' if buy else 'v', s=220, color='#f43f5e' if buy else '#3b82f6', zorder=6, edgecolors='white', linewidths=0.8)
            ax.annotate(f"{('買い' if buy else '売り') if jp else ('BUY' if buy else 'SELL')} {f(entry_px)}", (ix(entry_t), entry_px), xytext=(10, -14 if buy else 10),
                        textcoords='offset points', color='#e2e8f0', fontsize=11)
        for y, c, lab in [(sl, '#f87171', '最初の損切り' if jp else 'SL'), (tp, '#4ade80', '利確' if jp else 'TP')]:
            if not y:
                continue
            if inside(y):
                ax.axhline(y, color=c, lw=1.2, ls='--', zorder=1); ax.text(xmax, y, f'{lab} {f(y)}', color=c, ha='right', va='bottom', fontsize=10, clip_on=True)
            else:                                                   # outside the range: a note at the edge instead of squashing the chart
                up_ = y > yhi
                ax.text(xmax, yhi if up_ else ylo, f"{'↑' if up_ else '↓'} {lab} {f(y)}", color=c, ha='right', va='top' if up_ else 'bottom', fontsize=10)
        if not deals and exit_t is not None and exit_px and g.index[0] <= exit_t <= g.index[-1] + bar:
            rr = f'  {R:+.2f}R' if R is not None and np.isfinite(R) else ''
            c = '#4ade80' if (R or 0) >= 0 else '#f87171'
            ax.scatter([ix(exit_t)], [exit_px], marker='X', s=200, color=c, zorder=6, edgecolors='white', linewidths=0.8)
            ax.annotate(f"{'決済' if jp else 'EXIT'} {f(exit_px)}{rr}", (ix(exit_t), exit_px), xytext=(-12, 12), textcoords='offset points', color=c, ha='right', fontsize=11)
        ax.set_ylim(ylo, yhi); ax.set_xlim(-1, len(g) + 1)
        step = max(1, len(g) // 10)
        fmt = '%m/%d' if tf in ('D1',) else '%m/%d %H:%M'
        ax.set_xticks(xs[::step]); ax.set_xticklabels([t.strftime(fmt) for t in g.index[::step]], color='#94a3b8', fontsize=9)
        ax.yaxis.tick_right(); ax.tick_params(colors='#94a3b8', labelsize=9); [s.set_color('#334155') for s in ax.spines.values()]
        ax.grid(color='#1e293b', lw=0.6)
        ax.set_title(title, color='#e2e8f0', fontsize=14, loc='left')
        ax.legend(loc='lower left', facecolor=bg, labelcolor='#94a3b8', fontsize=9, frameon=False)
        fig.subplots_adjust(left=0.02, right=0.93, top=0.94, bottom=0.07); buf = io.BytesIO(); fig.savefig(buf, format='png', facecolor=bg); plt.close(fig)
        return buf.getvalue()
    except Exception as ex:
        logging.warning('trade chart (%s) failed: %s', tf, ex)
        return None
