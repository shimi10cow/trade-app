# Dow swing detection — frozen v1 (2026-10-17)

## Scope
Same engine for all symbols and W1/D1/H4/H1/M15. Parameters depend on timeframe, not symbol. Only EURUSD has been compared with human annotations. ATR inflation cap OFF; high/low relocation ON.

## Parameters
| TF | Wilder ATR period | Base ATR multiplier | ER20 trend adjustment | ER20 threshold |
|---|---:|---:|---:|---:|
| W1 | 7 | 1.9 | +0.15 | 0.40 |
| D1 | 7 | 1.9 | -0.15 | 0.40 |
| H4 | 7 | 2.0 | +0.30 | 0.40 |
| H1 | 7 | 2.4 | -0.15 | 0.25 |
| M15 | 7 | 2.1 | +0.30 | 0.25 |

## Engine contract
Source of truth: `dow_final_engine.py`, `calculate(df, tf, start=60, end=None)`; OHLC columns `t,o,h,l,c`.
- True range = max(H-L, abs(H-prevClose), abs(L-prevClose)). ATR7 = `ewm(alpha=1/7, adjust=False)`.
- ER20 = abs(C[i]-C[i-20]) / sum of abs close-to-close changes for previous 20 candles.
- Reversal threshold = ATR7 * base multiplier * (1+trend adjustment when ER20 >= threshold).
- Candidate extremes use wicks, not bodies. Same-candle extreme update and reversal confirmation is prohibited.
- High and low pivots alternate. A failed save does not flip direction.
- Relocation ON: if a new higher high occurs before an intervening low is confirmed, move the previously confirmed high to the new highest wick. Symmetric for lows. Do NOT invent intervening opposite pivots.
- Relocation can affect subsequent reversal decisions and total pivot counts; it is NOT guaranteed count-neutral.
- Repainting warning: a previously confirmed pivot can move. Historical final pivot lists MUST NOT be treated as point-in-time signal availability for an EA. Store as-of pivot snapshots and recognition timestamps separately.
- Source-clock-naive bar timestamps encoded to epoch milliseconds for chart import; no broker timezone conversion is implied.

## Validation boundary
EURUSD counts are from the manual-annotation window with ±30 bars, not full history. Other symbols are not validated. The counts do not establish recognition accuracy of the relocated version.

## Files and map
- `dow_final_engine.py`: executable detection logic, source of truth
- `build_dow_final.py`: reproducible EURUSD chart/annotation runner; expects chart HTML and annotations JSON in /mnt/data (adjust B for local execution)
- `dow_final_counts.csv`: EURUSD per-timeframe output counts
- `eurusd_dow_final_relocate_import.json`: EURUSD import snapshot, if stored
- `README.md`: repository research map for this module

Frozen policy: do not enable ATR cap or synthesize intermediate pivots without a new separately tested version.
