# Historical 723-trade initial SL width audit

Source: recovered INTEGRATED_M15_EURUSD_extreme_switch_trades.csv (401) and INTEGRATED_M15_USDJPY_extreme_switch_trades.csv (322). R_net includes cost. Descriptive retrospective grouping only; no strategy modification or rerun.

## EURUSD (pips, within-pair quartiles)
|SL range|N|Win%|PF|Net R|
|---|---:|---:|---:|---:|
|13.0–25.0|101|44.6|1.580|33.58|
|25.0–37.8|100|40.0|1.239|14.94|
|37.8–57.1|100|37.0|1.100|6.38|
|57.1–159.7|100|50.0|1.716|34.33|

## USDJPY
|SL range|N|Win%|PF|Net R|
|---|---:|---:|---:|---:|
|15.1–27.9|81|37.0|1.151|8.27|
|27.9–45.0|80|40.0|1.465|23.29|
|45.0–63.0|80|45.0|1.483|21.89|
|63.0–241.2|81|46.9|1.552|22.72|

## By P label
|P|N|Median SL pips|PF|Net R|
|---|---:|---:|---:|---:|
|P1|409|40.8|1.304|74.83|
|P2|274|40.6|1.372|59.00|
|P3|40|36.1|2.685|31.56|

P3 EURUSD: N22, median SL 28.5 pips, PF 1.593; USDJPY N18, median SL 48.7 pips, PF 5.550. Small samples.

## Spread/risk
Fixed historical spread EURUSD 1.3 pips; USDJPY 1.5 pips. All 723 initial risk/spread ratios >=10, i.e. spread <10% of risk. This is not independent of SL width.

## Interpretation limits
These are conditional associations, not proof that changing SL improves performance. Initial SL is recorded but the originating structural anchor (SMA200, swing point, etc.) is not recorded. SL/ATR, distance to SMA200 and swing structure require price bars aligned to entry timestamps and exact causal indicator rules. Quartile boundaries are defined per pair using all available history; exploratory analysis only. Historical trades and target 695-trade baseline remain different versions.
