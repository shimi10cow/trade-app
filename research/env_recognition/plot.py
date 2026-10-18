"""Static review chart: candles, Dow pivots (HH/HL/LH/LL at anchor), protected level, trend shading."""
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from .pivots import final_pivots
from . import dow_trend


def plot(df, res, a, b, path, title=''):
    o, h, l, c = (df[z].to_numpy(float) for z in 'ohlc')
    x = np.arange(a, b)
    fig, ax = plt.subplots(figsize=(22, 8))
    trend = [res['bars'][i][0] for i in x]
    prot = np.array([res['bars'][i][1] for i in x], float)
    for i, tr in zip(x, trend):
        if tr:
            ax.axvspan(i - .5, i + .5, color='#2e7d32' if tr == 'up' else '#c62828', alpha=.06, lw=0)
    up = c[x] >= o[x]
    ax.add_collection(LineCollection([[(i, l[i]), (i, h[i])] for i in x], colors='#555', lw=.6))
    polys = [[(i - .35, o[i]), (i + .35, o[i]), (i + .35, c[i]), (i - .35, c[i])] for i in x]
    ax.add_collection(PolyCollection(polys, facecolors=np.where(up, '#ffffff', '#333333'), edgecolors='#333', lw=.5))
    # protected level as step line (state at close of each bar)
    ax.step(x, prot, where='post', color='#1565c0', lw=1.6, label='protected swing')
    piv = dow_trend.label_counts(final_pivots(res['pivot_events']))
    for p in piv:
        if a <= p['idx'] < b:
            hi = p['kind'] == 'hi'
            ax.plot(p['idx'], p['price'], 'v' if hi else '^', color='#ef6c00', ms=6)
            ax.annotate(p['label'], (p['idx'], p['price']), xytext=(0, 9 if hi else -15),
                        textcoords='offset points', ha='center', fontsize=8, color='#ef6c00')
    for e in res['events']:
        if e['action'] == 'REVERSAL' and a <= e['idx'] < b:
            ax.axvline(e['idx'], color='#6a1b9a', lw=1, ls='--')
            ax.hlines(e['broken_price'], e['broken_anchor'], e['idx'], color='#6a1b9a', lw=2)
            ax.annotate(f"{e['frm']}->{e['to']}", (e['idx'], e['broken_price']), fontsize=8, color='#6a1b9a')
        if e['action'] == 'BREAKOUT' and a <= e['idx'] < b:
            ax.plot(e['idx'], c[e['idx']], 'o', mfc='none', mec='#1565c0', ms=7)
    ticks = x[::max(1, len(x) // 12)]
    ax.set_xticks(ticks, [str(df.t.iloc[i])[:10] for i in ticks], fontsize=8)
    ax.set_xlim(a - 1, b)
    ax.set_ylim(l[x].min() * .998, h[x].max() * 1.002)
    ax.set_title(title); ax.legend(loc='upper left'); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
