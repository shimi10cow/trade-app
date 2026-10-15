# EURUSD wave maturity — P1/P2 drilldown status (2026-10-15)

## VERIFIED findings
The previously reported 359-trade subset (H4 impulse ratio >= 0.70, H1 impulse ratio < 0.75) has +100.531R and PF 1.452. The 284-trade subset adds H1 SMA480 distance <12 ATR, with +105.664R, PF 1.614, win rate 39.1%. These are retrospective subset stats, not a fresh EA run.

## Why P1/P2 cannot currently be reported
The code `research/core/calc_wave_subset_dd_20261015.py` loads `/mnt/data/ea_shared/DD_causal_wave_maturity_trades.csv`. This raw per-trade feature dataset is **not in GitHub**, and was not present in the available local runtime as of this check. It contains the required `point` and `R` columns. The H4 structure CSVs are bar/pivot datasets, not trade-level rows. The P1/P2 figures cannot be inferred from aggregate PF/R.

## Required recovery
1. Recover `DD_causal_wave_maturity_trades.csv` from the original study runtime/export, OR reproduce it with identical strategy, feature-generation code, data and parameters.
2. Save under `research/datasets/derived/eurusd_wave_maturity/2026-10-15/trades_with_features.csv`.
3. Produce per-point P1/P2 for each subset: n, wins, losses, zero, win rate, sumR, PF, avgR, max closed-trade DD; include annual split.
4. Save a complete subset trade list for 359 and 284, code, parameters, data provenance and report.
5. Update `research/INDEX.md`. Do not invent P1/P2 results from unrelated samples.

## Existing script limitations
`calc_wave_subset_dd_20261015.py` calculates overall stats but **does not group by point**. Must add `groupby('point')` to generate P1/P2. Its fixed local path must be made configurable.
