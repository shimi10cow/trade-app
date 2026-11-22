# Prototype (2026-11-22): axis positions are fixed for one iPhone screenshot of OANDA Japan USD/JPY (1179x2556). Checked: 156.95 buy orders read 0.18% vs 0.19% on the tooltip.
"""Read OANDA order / position book bars from a screenshot: bar length in pixels -> % using the gridlines."""
import sys
import numpy as np
from PIL import Image

a = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(int)
sat = a.max(2) - a.min(2)
bar = (sat > 25) & ~((np.abs(a - [125, 169, 0]).sum(2) < 30))          # coloured, not the green price line
# axes found from the image (gridlines): price rows 160 -> 1010, 158 -> 1373, 156 -> 1736
Y160, Y156 = 1010, 1736; PPY = (Y156 - Y160) / 4.0
price = lambda y: 160 - (y - Y160) / PPY
CH = {'注文': dict(x0=242, pct=0.4, px=(324 - 160) / 2), 'ポジション': dict(x0=785, pct=0.6, px=(868 - 702) / 2)}
out = []
for name, c in CH.items():
    for y in range(760, 1760):
        row = bar[y]
        def run(direction):
            n, x, miss = 0, c['x0'], 0
            while 0 <= x < a.shape[1] and miss <= 2:
                if row[x]:
                    n += 1 + miss; miss = 0
                else:
                    miss += 1
                x += direction
            return n
        L, R = run(-1), run(1)
        out.append((name, y, L * c['pct'] / c['px'], R * c['pct'] / c['px']))
import pandas as pd
D = pd.DataFrame(out, columns=['図', 'y', '左', '右'])
D['価格'] = D.y.map(price)
D.to_csv('ob_rows.csv', index=False)
# bars: group rows into 0.05 price buckets
D['帯'] = (D['価格'] / 0.05).round() * 0.05
G = D.groupby(['図', '帯'])[['左', '右']].max().reset_index()
G = G[(G.左 > 0.005) | (G.右 > 0.005)]
print(G.groupby('図')[['左', '右']].sum().round(2))
G.to_csv('ob_buckets.csv', index=False)
