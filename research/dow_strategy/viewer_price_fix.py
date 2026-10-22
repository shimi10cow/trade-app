"""Convert viewer JSON prices from the computing scale back to real prices (2026-10-22).
Workspaces compute on scaled prices (JPY pairs / 100, gold & BTC natural log). In the viewer files every float inside
list rows is a price (times and indices are ints); in trade dicts only entry / sl / xp are prices.
Usage: python viewer_price_fix.py <data_dir> mult:100|exp <decimals>"""
import sys, json, math
from pathlib import Path
D = Path(sys.argv[1]); mode = sys.argv[2]; nd = int(sys.argv[3])
f = (lambda v: round(v * float(mode.split(':')[1]), nd)) if mode.startswith('mult') else (lambda v: round(math.exp(v), nd))
TR = ('entry', 'sl', 'xp')
def walk(o):
    if isinstance(o, list):
        return [f(v) if isinstance(v, float) else walk(v) for v in o]
    if isinstance(o, dict):
        if 'entry' in o and 'side' in o:
            return {k: (f(v) if k in TR and isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in o.items()}
        return {k: walk(v) for k, v in o.items()}
    return o
n = 0
for p in sorted(D.glob('*.json')):
    if p.name in ('pf_all.json', 'pbc.json'):
        continue
    x = json.loads(p.read_text(encoding='utf-8'))
    p.write_text(json.dumps(walk(x), ensure_ascii=False, separators=(',', ':')), encoding='utf-8'); n += 1
print('converted', n, 'files in', D)
