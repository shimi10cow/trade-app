# Trendline rules cross-check — 2026-10-18

## Verified source of truth
- Generation / 2-point reanchoring / 3-point selection: `research/chart_lab/TRENDLINE_RULES.md` (approved 2026-10-17).
- Causal generation implementation: `research/chart_lab/trendline_causal_engine.py`.
- Frozen Dow pivot implementation: `research/dow_frozen_v1/dow_final_engine.py`.
- Causal Dow/protected-swing specification: `research/dow_frozen_v1/DOW_RULES_20261018.md`.

## Approved two-point construction (preserved; do not replace with guesses)
- Connect only consecutive confirmed same-kind Dow pivots: higher lows or lower highs, regardless of major trend direction.
- Original pivot A–B separation >=15 completed bars. No upper limit.
- If any intervening wick violates the outer side of A–B, iteratively move A to offending wick extreme C and redraw C–B until clear. Keep only corrected C–B; C need not be a Dow pivot. Minimum-gap test applies to original A–B.
- No ATR intrusion filter for two-point lines. Pivot confirmation/relocation can create/revise candidates.

## Approved three-point construction
- Three consecutive same-kind pivots, successive movement >=0.12 ATR; adjacent gaps >=4 bars and <=75 W1 / 95 D1 / 115 H4 / 145 H1 / 175 M15.
- Draw first–third; middle deviation <=0.85 ATR; >0.35 ATR close intrusion on <=10% of intervening bars; max intrusion <=1.7 ATR; normalized slope 0.25–7.
- Suppress near duplicates using the thresholds and score recorded in TRENDLINE_RULES.md.

## Retirement rules — latest agreement 2026-10-18 (supersedes prior epoch-based deletion)
- Line classification is **dynamic**, based on current confirmed Dow major-trend direction versus line slope: same direction = impulsive (推進); opposite direction = corrective (調整). Do NOT freeze the line's classification at its initial creation. On Dow reversal, a surviving corrective line can become impulsive and usable by a future EA.
- **Impulsive line**: when the corresponding confirmed Dow trend reverses, retire the line immediately at the reversal's known-at bar. Track whether the line has been impulsive during the current trend epoch; a line that switches from impulsive to opposite-direction corrective must be retired, not silently reclassified and retained. A corrective line that becomes impulsive on a reversal survives that reversal, and retires when its new impulsive trend subsequently reverses.
- **Break-based retirement applies to lines of either class**: descending line -> completed candle CLOSE above projected line -> count 2 unique subsequent confirmed Dow LOW pivots -> retire on second confirmation; ascending line -> CLOSE below projected line -> count 2 unique subsequent confirmed Dow HIGH pivots -> retire on second confirmation.
- When a subsequent completed close returns to the inside of the line, reset the break-pivot counter to zero. Relocate of the same pivot is not a new pivot. Use causal known-at timestamps, no future data.
- Distinguish pivot-relocation-induced line construction invalidation (handled by generation engine) from breakout/Dow-trend retirement (separate lifecycle layer).
- The breakout + 2-pivot retirement is the **first implementation milestone**. Full impulsive-line retirement is gated on verified protected-high/low Dow reversal tracking; the latter is specified in DOW_RULES_20261018.md but NOT yet verified end-to-end.
- Preserve immutable history of creation, revision, classification, break/reset, pivot counts, trend changes and retirement reason/time. EA reads only active lines as-of the current completed bar.
- No arbitrary time-to-live or forced expiration. Long-lived W1 lines are acceptable.

## Important distinctions / open verification
- The 2026-10-17 TRENDLINE_RULES.md describes construction, not a completed causal retirement engine. Its 'current implementation gaps' section contains historical notes and may be stale; inspect the code, not only that section.
- Frozen retrospective Dow final pivot list may repaint; causal pivot_events() must be parity-tested for relocations and known-at behavior.
- The prior Complete HTML uses retrospective embedded line sets and must not be treated as proof of causal correctness.
- This document records agreed rules, not a claim that a verified working implementation or all-line zero-stale audit exists.
