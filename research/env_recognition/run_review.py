"""python -m env_recognition.run_review D1 [chart|full] outdir"""
import sys
from pathlib import Path
import pandas as pd
from .data import load
from . import dow_trend
from .plot import plot

tf, src, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
df = load(tf, src)
res = dow_trend.run(df, tf)
ev = pd.DataFrame(res['events'])
ev.insert(1, 'time', df.t.iloc[ev.idx].values)
ev.to_csv(out / f'{tf}_{src}_dow_events.csv', index=False)
print(tf, src, len(df), 'bars', ev.action.value_counts().to_dict())
span = int(sys.argv[4]) if len(sys.argv) > 4 else 300
for a in range(60, len(df), span):
    b = min(len(df), a + span)
    plot(df, res, a, b, out / f'{tf}_{src}_{a:05d}.png', f'EURUSD {tf} {df.t.iloc[a]:%Y-%m-%d} – {df.t.iloc[b-1]:%Y-%m-%d}')
