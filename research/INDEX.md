# EA Research — Canonical Index
Updated 2026-10-15. **START HERE for AI sessions.**

## Active research execution
- `research/core/engine_m15.py` — shared M15 backtest engine.
- `research/core/run_compare.py` — ON/OFF runner.
- `research/core/cache_m15.py` — cache helper.
- `research/core/README.md`, `ENGINE_README.md`, `NEW_EA_RULES_2026-10-15.md` — read rules before changing engine.
These are research engines, NOT automatically live EA production files.


## H4 reversal / M15 P1-P2 stochastic (2026-10-15)
- `research/studies/scripts/h4_reversal_m15_p12_signals.py` — causal 3-stage M15 Stochastic signal extractor; P1/P2 counted per supplied H4 reversal regime.
- `research/studies/notes/2026-10-15_H4_reversal_M15_P1P2.md` — signal definition, H4 breakout-level gate, Fib diagnostic-only policy, timing, and limitations.
- Signal implementation saved; integrated H4 backtest **not yet run**. Original core uses raw14 → SMA3(K) → SMA5(D); check MT5 naming before claiming 14-5-3 parity.

## Reusable datasets
- `research/datasets/derived/eurusd_m15/2026-10-15/MANIFEST.md` — verified 583,458-row local M15 cache, SHA256 and reproducibility contract; **23 MB binary NOT uploaded to GitHub**. Do not repeat M1 resampling when local cache exists.
- P1/P2 trade-level ledger is **not yet committed**; prior 1,117-trade retrospective note is not a substitute for the ledger.

- `research/datasets/derived/eurusd_h4_structure/2026-10-15/h4_annual_structure_summary.csv` — H4 annual summary, uploaded.
- `h4_structure_bars.csv` and `h4_confirmed_pivots.csv` — NOT YET uploaded; previous local paths `/mnt/data/ea_research/`.
- Original EURUSD M1 ZIP is external/session-local, not present in this repository.
- Dataset generator: `research/studies/scripts/structure_study_20261015.py`.
No data should be treated as live-safe without timestamp/pivot availability checks.

## Studies
- `research/studies/notes/2026-10-15_EURUSD_DD_wave_maturity_reference.md` — 1117 trade retrospective analysis; corrected 359-trade PF=1.452, 284-trade PF=1.614; NOT an EA ON/OFF rerun.
- `research/studies/notes/2026-10-15_EURUSD_price_structure_research_plan.md` — H4/H1 structural hypotheses.
- `research/studies/experiments/` — prior exploratory comparisons.

## Archive
- `research/archive/backtest_recovery/` — recovered historical backtest and audits.
- `research/archive/forextester/` — older ForexTester experiments.
- `research/archive/shared_backtest_20261014/` — previous engine.
- `research/archive/legacy_scripts/` — superseded standalone scripts and historical reports.
- `research/archive/RESEARCH_MAP_20261015.md` — superseded navigation map.

## Migration note
Reorganized 36 paths in commit `86f7278`. Existing file contents preserved. Any external scripts importing old paths must be updated; **runtime/import regression testing has NOT been performed**. Do not assume production deployment unaffected without checking imports. Do not use archived engine as current source.

## Rules for future work
1. Check this index, then current engine and study.
2. Prefer `core/` for reusable research engine, `datasets/` for reusable data, `studies/` for experiments, `archive/` for superseded work.
3. Record reproducibility: source data, timestamps, timezone, bar-close convention, confirmation lag, parameters, commit SHA, costs and exposure.
4. Update this index when adding/moving files.
