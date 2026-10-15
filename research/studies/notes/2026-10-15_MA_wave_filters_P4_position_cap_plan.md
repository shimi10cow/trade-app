# EURUSD MA strategy: wave filters and P4 / position-cap study (2026-10-15)

## Status
Exploratory trade-level retrospective filtering, **not** live-validated and **not** a causal filter-on rerun. Do not enable on live EA without further testing.

## Baseline
EURUSD 2003–2026 M15; P1–P3, maximum 2 concurrent positions, 1,398 trades, +162.96R, PF1.183, maxDD -58.18R (local reproduced engine; costs excluded).

## Two candidate filters — preserve BOTH
**Filter A (H4+H1)**: most recent causally confirmed H4 impulse / previous H4 impulse >= 0.70; most recent causally confirmed H1 impulse / previous H1 impulse < 0.75.
**Filter B (H4+H1+MA)**: Filter A AND abs(H1 price - H1 SMA480)/H1 ATR14 < 12.
Pivots: confirmed 2-left/2-right fractal pivots with 2 completed right-hand candles. Features must use only information available at signal time. The local reproduction of features has not exactly matched original 359/284 count; reconcile before live use.

## Retrospective P1–P3 result (not engine rerun)
Unfiltered: 1398, +162.96R, PF1.183, DD -58.18R.
Filter A: 483, +95.07R, PF1.319, retrospective DD -20.10R.
Filter B: 388, +110.24R, PF1.472, retrospective DD -13.09R.
2015 onward Filter B: 182 trades, +79.26R, PF1.816, retrospective DD -13.00R.
Annual results should be checked for concentration, robustness and lookahead. Original P1+P2 exploratory counts 359/284 differed from local P1–P3 recomputation; see research/studies/notes/2026-10-15_EURUSD_DD_wave_maturity_reference.md.

## Required controlled tests
Factorial compare P max = 3 vs 4, concurrent position cap = 2 vs 3 vs 4 vs unlimited, filters OFF/A/B. Re-run engine from source M15 for each setting; no merely selecting rows from prior executions because position cap changes which signals can fill. Preserve identical other entry/exit conditions, no future leakage, report total and 2015+ trade count, PF, R, DD, win rate, annual R, and P breakdown. Account for shared risk / correlation before deployment.
