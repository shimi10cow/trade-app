"""Year-by-year entry viewer for the existing EA (long data), tagged with the H4 Dow trend stage.

python dow_strategy/build_stage_viewer.py <out_dir> [years...]   (needs results/long_features_1.csv)
Writes <out_dir>/index.html (summary by year x stage) and <out_dir>/<year>.html (chart pages).
W1/D1/H4 overlays are computed once on the full 2003-2026 history; M15 and H1 are computed per year
from a few months before the year (speed). Only the year's window is embedded.
"""
import bisect
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
from env_recognition import dow_trend, zones, lines  # noqa: E402
from env_recognition.build_html import epoch_s, final_pivots  # noqa: E402

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / 'stage_viewer_template.html'
TFS = ('W1', 'D1', 'H4', 'H1', 'M15')
LEAD = {'W1': pd.DateOffset(years=4), 'D1': pd.DateOffset(years=1), 'H4': pd.DateOffset(months=3),
        'H1': pd.DateOffset(weeks=4), 'M15': pd.DateOffset(days=7)}
DOC = '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">' \
      '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>\n'
r5 = lambda x: round(float(x), 5)


PER_YEAR = {'M15': pd.DateOffset(months=2), 'H1': pd.DateOffset(months=6)}   # computed per year (warm-up) for speed
_FULL = {}


def compute(tf, y=None):
    if tf not in _FULL:
        _FULL[tf] = load(tf, 'long').reset_index(drop=True)
    df = _FULL[tf]
    if y is not None:
        tt = pd.to_datetime(df.t)
        df = df[(tt >= pd.Timestamp(f'{y}-01-01') - PER_YEAR[tf] - LEAD[tf]) & (tt < pd.Timestamp(f'{y + 1}-01-01'))].reset_index(drop=True)
    res = dow_trend.run(df, tf)
    return dict(df=df, res=res, zones=zones.build(df, res), lines=lines.run(df, tf, res), t=epoch_s(df.t),
                tt=pd.to_datetime(df.t), sma20=df.c.rolling(20).mean(), sma75=df.c.rolling(75).mean())


def payload(C, s0, s1):
    df, res, t = C['df'], C['res'], C['t']
    inw = lambda i: s0 <= i < s1
    candles = [[t[i], r5(df.o[i]), r5(df.h[i]), r5(df.l[i]), r5(df.c[i])] for i in range(s0, s1)]
    sma = {p: [[t[i], r5(C[f'sma{p}'][i])] for i in range(s0, s1) if pd.notna(C[f'sma{p}'][i])] for p in (20, 75)}
    prot = [[t[i], None if tr is None else r5(p), tr] for i, (tr, p) in enumerate(res['bars'][s0:s1], s0)]
    pprot = [[t[i], None if tr is None else r5(p), tr] for i, (tr, p) in enumerate(res['prov_bars'][s0:s1], s0)]
    known = {}
    for e in res['pivot_events']:
        known.setdefault(e['id'], e['available_idx'])
    piv = [[t[p['idx']], p['kind'], r5(p['price']), p['label'], t[known[p['id']]]]
           for p in dow_trend.label_counts(final_pivots(res['pivot_events'])) if inw(p['idx'])]
    ev = []
    for e in res['events']:
        if not inw(e['idx']):
            continue
        a = e['action']
        if a == 'REVERSAL':
            ev.append([t[e['idx']], 'rev', e['to'], r5(e['broken_price']), t[e['broken_anchor']]])
        elif a == 'BREAKOUT':
            ev.append([t[e['idx']], 'bo', e['trend'], r5(e['ref_price']), t[e['ref_anchor']]])
        elif a in ('breakout_protect', 'late_protect', 'reversal_protect', 'reversal_protect_raw', 'init_up', 'init_down'):
            ev.append([t[e['idx']], a, e['trend'], r5(e['price']), t[e['anchor']]])
    pev = [[t[e['idx']], e['to'], r5(e.get('broken_price') or (e.get('h2') if e['to'] == 'up' else e.get('l2')))]
           for e in res['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and inw(e['idx'])]
    wev = [[t[e['idx']], e['action'], r5(e['a']), r5(e['b']), r5(e['c']), t[e['b_anchor']]]
           for e in res['w_events'] if inw(e['idx'])]
    clip = lambda i: t[min(max(i, 0), len(t) - 1)]
    zout = [[clip(z['anchor']), clip(z['activation']), t[z['expiry']] if z['expiry'] is not None and z['expiry'] < s1 else None,
             r5(z['bottom']), r5(z['top']), '・'.join(z['sources'])]
            for z in C['zones'] if z['activation'] < s1 and (z['expiry'] is None or z['expiry'] >= s0)]
    rel = lambda i: None if i is None or i >= s1 else i - s0
    lout = [[x['anchor_idx'] - s0, r5(x['anchor_price']), x['end_idx'] - s0, r5(x['end_price']),
             x['created'] - s0, rel(x['retired']), x['kind'], x['reason'] or '', x['type']]
            for x in C['lines']['lines'] if x['created'] < s1 and (x['retired'] is None or x['retired'] >= s0)]
    return dict(ulab=[], extra=[], lines=lout, candles=candles, sma20=sma[20], sma75=sma[75], prot=prot, pprot=pprot,
                piv=piv, ev=ev, pev=pev, wev=wev, zones=zout)


def window(C, tf, y):
    a = pd.Timestamp(f'{y}-01-01') - LEAD[tf]
    b = pd.Timestamp(f'{y + 1}-01-01')
    tt = C['tt']
    return int(tt.searchsorted(a)), int(tt.searchsorted(b))


def trades_of(F, y):
    sec = lambda ts: int((pd.Timestamp(ts) - pd.Timestamp('1970-01-01')) // pd.Timedelta(seconds=1))
    out = []
    G = F[F.time.dt.year == y].sort_values('time')
    for n, x in enumerate(G.itertuples(), 1):
        jp = lambda v: 'up' if v else None
        out.append(dict(n=n, t=sec(x.time), side=int(x.side), p=int(x.point), entry=round(x.entry, 5),
                        sl=round(x.initial_sl, 5), xt=sec(x.ExitTime), xp=round(float(x.exit), 5), R=round(float(x.Rc), 2),
                        risk=round(x.risk / 1e-4, 1), stg=int(x.h4_stage), nrev=int(x.nrev), trail=x.trail_reason if isinstance(x.trail_reason, str) else '',
                        d1=('up' if x.side == 1 else 'down') if x.d1 else ('down' if x.side == 1 else 'up'),
                        h4=('up' if x.side == 1 else 'down') if x.h4 else ('down' if x.side == 1 else 'up'),
                        h1=('up' if x.side == 1 else 'down') if x.h1 else ('down' if x.side == 1 else 'up')))
    return out


def nav(years, cur):
    links = ['<a href="index.html">一覧</a>'] + [f'<a href="{y}.html"{" aria-current=\"page\"" if y == cur else ""}>{y}</a>' for y in years]
    return ''.join(links)


def stat(r):
    if not len(r):
        return '—'
    w = r > 0
    pf = r[w].sum() / max(1e-9, -r[~w].sum())
    return f'{len(r)}回 {r.sum():+.1f}R PF{pf:.2f}'


def index_html(F, years):
    groups = [('全部', lambda G: G.index == G.index), ('段階0', lambda G: G.h4_stage == 0), ('段階1', lambda G: G.h4_stage == 1),
              ('段階2', lambda G: G.h4_stage == 2), ('段階3以上', lambda G: G.h4_stage >= 3), ('H4と逆', lambda G: G.h4_stage < 0)]
    rows = []
    for y in years + ['計']:
        G = F[(F.time.dt.year >= years[0]) & (F.time.dt.year <= years[-1])] if y == '計' else F[F.time.dt.year == y]
        cells = ''.join(f'<td>{stat(G.Rc[m(G)].to_numpy())}</td>' for _, m in groups)
        head = f'<th><a href="{y}.html">{y}</a></th>' if y != '計' else '<th>合計</th>'
        rows.append(f'<tr>{head}{cells}</tr>')
    return f'''<title>トレンド段階ビューア</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Layout: one column, short intro, then a year x stage table that links to the chart pages. */
:root{{--bg:#f6f7f9;--panel:#fff;--fg:#1b2230;--muted:#667085;--line:#d9dee7;--accent:#2457c5;
  --font:"IBM Plex Sans JP","Hiragino Sans","Noto Sans JP",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#11151c;--panel:#171c25;--fg:#e4e8ef;--muted:#8b95a7;--line:#2a3140;--accent:#6c9cff;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#11151c;--panel:#171c25;--fg:#e4e8ef;--muted:#8b95a7;--line:#2a3140;--accent:#6c9cff;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:var(--font);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:16px}}
h1{{font-size:18px;margin:0 0 8px;text-wrap:balance}} p{{max-width:68ch;line-height:1.7;margin:0 0 10px;color:var(--muted)}}
.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--panel);margin-top:12px}}
table{{border-collapse:collapse;font:12px var(--mono);font-variant-numeric:tabular-nums;width:100%}}
td,th{{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}
thead th{{color:var(--muted);font-weight:600}} a{{color:var(--accent);font-weight:600}}
</style>
<h1>トレンド段階ビューア（既存EA・EURUSD）</h1>
<p>既存EA（MA＋ストキャス）のエントリーを、エントリー時点のH4ダウの段階で色分けしたチャートです。段階＝H4が転換してから高値（売りは安値）を終値で更新した回数。0＝転換直後、3以上＝終盤。</p>
<p>年をクリックするとその年のチャートが開きます。M15〜W1の切替、押し安値/戻り高値、ダウの高安、水平帯、トレンドライン付き。成績はスプレッド1.2pips控除後。</p>
<div class="wrap"><table><thead><tr><th>年</th>{''.join(f'<th>{g}</th>' for g, _ in groups)}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
'''


if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    years = [int(y) for y in sys.argv[2:]] or list(range(2020, 2027))
    F = pd.read_csv(HERE / 'results' / 'long_features_1.csv', parse_dates=['time', 'ExitTime'])
    C = {tf: compute(tf) for tf in TFS if tf not in PER_YEAR}
    print('computed', flush=True)
    h4 = C['H4']
    rev = sorted(e['idx'] for e in h4['res']['events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL')
    close = list(h4['tt'] + TF_LEN['H4'])
    nrev = []
    for t in F.time:
        k = bisect.bisect_right(close, t + pd.Timedelta(minutes=15)) - 1
        nrev.append(bisect.bisect_right(rev, k) - bisect.bisect_right(rev, k - 90))
    F['nrev'] = nrev
    (out / 'index.html').write_text(index_html(F, years), encoding='utf-8')
    tpl = TEMPLATE.read_text(encoding='utf-8')
    for y in years:
        for tf in PER_YEAR:
            C[tf] = compute(tf, y)
        data = {tf: payload(C[tf], *window(C[tf], tf, y)) for tf in TFS}
        data['trades'] = trades_of(F, y)
        html = (tpl.replace('/*TITLE*/', f'段階ビューア {y}').replace('/*H1*/', f'既存EAのエントリー {y}年（色＝H4ダウの段階）')
                .replace('/*NAV*/', nav(years, y)).replace('/*DATA*/null', json.dumps(data, separators=(',', ':'))))
        (out / f'{y}.html').write_text(DOC + html, encoding='utf-8')
        print(y, round(len(html) / 1e6, 2), 'MB', len(data['trades']), 'trades', flush=True)
