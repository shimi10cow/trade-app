# EA research handoff to Claude — 2026-10-18

## Status / source of truth
This is a handoff index, **not** a claim that all CSV datasets have been pushed to GitHub. The complete research artifact bundle was assembled separately from the ChatGPT execution environment (100 files, 2026-10-18). Obtain and extract `EA_Claude_handoff_research_20261018.zip` before running the analyses.

## Project
EURUSD M1 history 2003–2026, resampled to M15; study a selective H1 trend / M15 stochastic entry EA. Baseline: M15 SMA200-based SL (10 pip buffer, minimum 10 pip), +1.5R ZigZag trailing, maximum two positions. Historic study matched 436 trades. Do not silently substitute 2015+ for full 2003–2026.

## Priority research files in archive
- `ea_shared/sl_sma_trail_zig15_spread_1.2_filter_B_P3_cap2.csv` — 436-trade baseline
- `EURUSD_SL_wave_vs_SMA_matched_436.csv` — paired SL diagnostics
- `EURUSD_2003_2026_pullback_duration_ratio_H4_436.csv`
- `EURUSD_2003_2026_pullback_deepdive_436.csv`
- `EURUSD_H4_opposed_break_split_44.csv`
- `EURUSD_H4_break_pullback_all436.csv`
- `EURUSD_entry_hour_JST_2003_2026.csv`
- `ea_shared/trail_variant_engine.py` — partial research engine; inspect dependencies before running
- `d1_study_20261015/` and `ea_research/` — H4/D1 structure studies

## Preliminary findings (exploratory, NOT independently validated)
H4 Dow opposed 44 trades; H4 opposed without structural breakout was an underperforming subset. H4 mixed/uncertain often profitable. Fast adverse candles and low retest counts were explored but not robustly stable across 2003–2014 vs 2015–2026. No filter has yet been adopted. Prefer preserving trade count near 436 and testing selective exclusions only.

## Important validity cautions
- All trade classifications are **post-hoc diagnostics**; a true filter requires rerunning the full position-occupancy backtest.
- H4 pivot detection uses confirmed swings and is not necessarily the user's precise discretionary Dow theory.
- The 24-hour structural break and 2-pip M15 retrace tests are provisional.
- Some prior M5 and M15 datasets have inconsistent price bases; do not combine without reconciliation.
- Prior time-of-day JST analysis assumed the source time zone was UTC, which is not verified.
- Confirm 436-trade baseline, P3 handling, spread, SL and trailing in the actual engine before relying on results.
- Avoid forward leakage, sample-size overinterpretation, and in-sample optimization.

## Next work
1. Reproduce 436-trade baseline and verify its trade ledger.
2. Verify H4 Dow labeling and breakout timestamps with causal confirmed pivots.
3. Examine H4 opposed/no-break entries and M15 pullback formation; preserve winners.
4. Run proper full-period entry-filter backtests and report trades, total R, PF, DD and era-by-era results.
