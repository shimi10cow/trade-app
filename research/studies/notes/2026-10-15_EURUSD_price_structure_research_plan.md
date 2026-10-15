# EURUSD price-structure research — 2026-10-15

Status: hypothesis and data preparation; NOT trade-level validation.

## Objective
Understand EURUSD 2003–2026 H4/H1 swing shape, swing duration, horizontal support/resistance and regime-dependent drawdowns. Do not optimize solely for the retrospective 284-trade subset. No EA rule changes.

## Historical horizontal-level definitions recovered
- September structural-level version: H4 Push/Return/Double Top/Bottom candidate levels; reject BUY when nearest active overhead level or SELL when nearest active lower level is within 0.60 H4 ATR; first revisit consumes level.
- Another implementation: 2-left/2-right confirmed H4 fractal, activation on close beyond pivot, line active next H4 bar, expiry at first revisit. This was identified as a proxy, NOT the exact original structural-level generator.
- Earlier discretionary concept: wick tip of pullback low / rebound high; body-to-wick zone; breakout only when candle close clears wick tip.
Do not conflate these versions.

## Testable hypotheses
1. H4 impulse preservation, correction depth, retracement duration and time-to-new-extreme jointly separate continuation from exhaustion.
2. H1 swing contraction can represent a favorable pullback only when H4 impulse is preserved; assess H1 reacceleration and failed swing updates.
3. Horizontal level type, normalized distance, zone width, age and number of prior touches interact with continuation probability.
4. Swing horizontal duration (hours) and price displacement (ATR) distinguish trend, congestion and exhaustion better than amplitude alone.
5. Trade-level P1/P2 overlap and wave clustering exaggerate apparent independence. Aggregate by causal swing episode and simulate concurrent exposure.
6. Stable year-by-year edge is more important than isolated large positive years. Report leave-one-year-out, especially excluding 2007, chronological out-of-sample, drawdowns and negative-year counts.

## Data preparation completed
Read /mnt/data/EURUSD2003.M1.zip; 146274 nonempty H1 bars and 37805 nonempty H4 bars. Extracted 10590 confirmed H4 fractal pivots (two bars on each side, only available after two future bars finish). Generated local:
- /mnt/data/ea_research/h4_confirmed_pivots.csv
- /mnt/data/ea_research/h4_structure_bars.csv
- /mnt/data/ea_research/h4_annual_structure_summary.csv
- /mnt/data/ea_research/structure_study_20261015.py
These are raw structural features, not an ON/OFF EA backtest. The original 1117-trade ledger was not available in this runtime, so no new PF, trade-level year distribution or DD claims are made.

## Next analysis
Recover the original 1117-trade ledger and entry timestamps; compute all structural features strictly as-of entry, with pivot confirmation lag and line lifecycle. Compare broad bins, continuous gradients, annual regimes, leave-one-year-out and wave-cluster bootstrap; pre-register candidate thresholds before independent EA reruns. Keep full 2003–2026 period. 
