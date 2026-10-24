"""Write results/tri_intervals.csv (tf, known, end, w0, shape, bo) from triangles.detect2 for H4 and H1:
known = close of the bar that made the triangle known, end = close of the breakout (or end) bar."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import triangles as TR  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
rows = []
for tf in ('H4', 'H1'):
    T = pd.to_datetime(TR.FR[tf][0].t)
    for x in TR.detect2(tf):
        rows.append(dict(tf=tf, known=T[x['created']] + TF_LEN[tf], end=T[min(x['end'], len(T) - 1)] + TF_LEN[tf], w0=x['w0'], shape=x['shape'], bo=x['bo']))
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('results') / 'tri_intervals.csv'
pd.DataFrame(rows).to_csv(out, index=False); print(len(rows), out)
