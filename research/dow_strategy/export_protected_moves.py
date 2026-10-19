"""Export every move of the major protected level (押し安値/戻り高値) with the time it became known.
Columns: known_at (close of the bar that caused it), event, trend, protected (new level),
anchor_time (bar of that swing), prev_protected.  Usage: python dow_strategy/export_protected_moves.py [TF ...]"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
from env_recognition import dow_trend  # noqa: E402

NAME = {'REVERSAL': '転換', 'reversal_protect': '転換→新しい押安/戻高', 'reversal_protect_raw': '転換→新しい押安/戻高',
        'BREAKOUT': '高安更新', 'breakout_protect': '更新→押安/戻高を直近安値/高値へ移動'}
for tf in sys.argv[1:] or ['H4', 'H1']:
    df = load(tf, 'long').reset_index(drop=True)
    t = pd.to_datetime(df.t)
    r = dow_trend.run(df, tf)
    rows, prev = [], None
    for e in r['events']:
        if e.get('machine') != 'major' or e['action'] not in NAME and not e['action'].startswith('init_'):
            continue
        rows.append(dict(known_at=t[e['idx']] + TF_LEN[tf], event=NAME.get(e['action'], e['action']), trend=e['trend'],
                         protected=e.get('prot_price'), anchor_time=t[e['prot_anchor']] if e.get('prot_anchor') is not None else None,
                         prev_protected=prev))
        prev = e.get('prot_price')
    out = Path(__file__).with_name('results') / f'protected_moves_{tf}.csv'
    pd.DataFrame(rows).to_csv(out, index=False)
    print(tf, len(rows), out)
