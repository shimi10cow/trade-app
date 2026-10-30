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
