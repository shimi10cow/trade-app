# EURUSD Dow trendline generation — specification (2026-10-17)

## Status and scope
Python implementation: `research/chart_lab/trendline_causal_engine.py`. This is a **causal candidate/event engine**, not yet a production-certified EA signal module. The previous visual-review HTML is a retrospective display and must not be used to infer past signal availability. W1/D1/H4/H1/M15 supported. Timeframes are computed separately; higher-timeframe overlays are a display feature.

## Frozen Dow engine
Parameters (ATR Wilder7, ER20 = absolute 20-bar close change / sum of absolute close changes):
| TF | ATR base multiplier | ER boost | ER cutoff |
|---|---:|---:|---:|
| W1 | 1.9 | +0.15 | 0.40 |
| D1 | 1.9 | -0.15 | 0.40 |
| H4 | 2.0 | +0.30 | 0.40 |
| H1 | 2.4 | -0.15 | 0.25 |
| M15 | 2.1 | +0.30 | 0.25 |

Threshold = base × ATR7 × (1 + boost if ER20 >= cutoff, else 1). Pivot extremes use candle wicks. An opposite pivot is confirmed after a threshold reversal on a **later** bar than the extreme. A confirmed last pivot can be relocated to a newer extreme before the next opposite pivot; each relocation must be logged as a new event. No ATR inflation cap. This reproduces the frozen Dow detector's core state machine, not an immutable final pivot table.

## Two-point line rules (approved)
1. Consider only **consecutive confirmed Dow lows** or **consecutive confirmed Dow highs**, separately; do not skip a Dow pivot to connect nonadjacent points.
2. Low-to-low requires a higher second low; high-to-high requires a lower second high. **No filter by current Dow trend direction**, so correction/triangle/acceleration lines are allowed.
3. The original Dow pivot-to-pivot interval must be **at least 15 candles** (changed from 20). There is no maximum interval specified for 2-point lines.
4. Draw candidate A→B, then if an intervening **wick** crosses the outer side, iteratively move A to the offending extreme C and redraw C→B until no intervening wick violates the segment. Keep **only C→B**, never both. C need not be a confirmed Dow pivot. The 15-bar test applies to original A→B, **not** the final C→B.
5. **No price-intrusion rejection** (the old 0.35 ATR / 15% / 1.7 ATR rules do not apply to 2-point lines).
6. Each newly confirmed Dow pivot or relocation may create/revise a line; no fixed cap on total generated lines. A pivot pair under 15 bars is skipped, **not** automatically replaced by a pair that skips an intervening Dow pivot.
7. Preserve history of line versions. Later line validity (touch, break, flip, staleness) is **not** a generation filter; calculate it as-of each EA entry.

## Three-point line rules (unchanged research thresholds)
- Three consecutive Dow lows with each higher by >=0.12 ATR, or three consecutive highs each lower by >=0.12 ATR.
- Each adjacent same-kind interval >=4 bars and <=95 D1 / 115 H4 / 145 H1 / 175 M15 / 75 W1 (W1 reference setting).
- Line first→third; middle point deviation <=0.85 ATR.
- More than 10% of intervening closes intruding >0.35 ATR rejects; maximum intrusion >1.7 ATR rejects.
- Normalized slope magnitude (first→third price change / median ATR across segment) between 0.25 and 7.
- Historical review suppressed near-duplicates by proximity of end index: 65 D1, 85 H4, 110 H1, 130 M15, 45 W1; replace old if score improves by >0.12, where score = 2×intrusion fraction + 0.4×middle deviation + 0.1×max(0, normalized slope -3).
- The Python engine now implements the documented near-duplicate suppression on each pivot event. Previously suppressed candidates can be reinstated when an active candidate is invalidated. Historical archived D1/H4 line-set parity has not been independently established.

## Causality and time indexing
- `pivot_events()` emits `confirm` and `relocate` with `available_idx` equal to the index of the candle whose **close** makes the event observable.
- `generate_lines()` uses only pivots and candle prices available at each event, and emits immutable `create`/`revise`/`retire` events. The `anchor_idx` and `end_idx` describe **geometry**, not when the line became usable.
- `available_idx` is the bar-close observation index. For entry decisions made at the **open** of candle k, use only events with `available_idx < k`; at the close of candle k, `available_idx <= k` is permissible only if execution timing allows it.
- For resampled H1/H4/D1/W1, never expose a partial candle as a completed candle. Convert indexes to timestamps only after resampling and defining broker timezone/session.
- A relocated pivot revises a line at the **relocation bar**; never rewrite earlier entry features. If the changed pivot makes a candidate ineligible, emit a **retire** event at that bar close. `asof_lines()` removes retired lines from the active registry. A newly eligible representative emits **create**, and an existing line with changed geometry emits **revise**.

## Current implementation gaps before live EA/backtest
1. A revision that makes a previously valid line ineligible (e.g., a pivot relocation reverses its slope or violates min_gap) does **not yet emit an invalidation/retirement event**. `asof_lines()` is consequently not a complete active-line registry; do not use it for production entry filtering.
2. Three-point near-duplicate suppression is documented but not yet causalized/implemented.
3. Frozen original Dow code should be parity-tested bar-by-bar against `pivot_events()` (including relocation edge cases).
4. The interactive HTML still embeds retrospective line data and has **not** been rebuilt from this event engine.
5. Full-history, multi-symbol validation, broker timestamps, and regression tests are pending.

## Reproduction
```python
import pandas as pd
from research.chart_lab.trendline_causal_engine import generate_lines
df = pd.DataFrame(...)  # chronological, closed bars; columns t,o,h,l,c
events = generate_lines(df, 'H4', start=60, min_gap=15)
# Each event includes available_idx, geometry indices/prices and create/revise action.
```

## Source of truth
- `trendline_causal_engine.py`: causal candidate events.
- `TRENDLINE_RULES.md`: this complete parameter/behavior specification.
- `FEATURE_MAP.md`: chart UI and EA integration map.
- `eurusd_chart_lab_complete.html`: manual/research chart; do not treat its retrospective drawings as live events.
