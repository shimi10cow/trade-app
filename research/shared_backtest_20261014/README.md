# Shared EA research baseline (2026-10-14)

## Status
This is a **common starting point, not yet a fully validated one-command ablation framework**. The baseline engine is the reconstructed research engine, not certified identical to live EA. The existing H4 OFF trade results are verified by their local logs. The new shared runner has **not yet been end-to-end regression-tested**.

## Canonical research rules
- Instrument: EURUSD first; USDJPY used later for cross-pair validation.
- History: Forex Tester VIP M1 from 2003-05-06 to 2026-10-12, resampled M15.
- H4 structural horizontal-level rejection: OFF.
- Research selection: P1/P2 only, P3 prohibited; P numbering is based on completed signals.
- Maximum positions and all other rules unchanged.
- Experiments 01–07 must each start from the **same exact executable engine, input and cached features**; toggle only one rule per run.
- **IMPORTANT**: Current runner's `--p p12` is only a post-hoc filter of completed trades, NOT a faithful P3-disabled re-simulation. It prints a warning. Do not report these as a newly validated P1/P2 baseline. The proper P3-entry guard must be added inside the simulation loop, with regression tests.
- `--disable` toggles currently fail closed (rather than silently producing wrong experiment results). Implement each switch in the engine and validate it before running experiments.

## Source files
- Frozen engine: [research/full_backtest_engine_v1_20261014.py](../full_backtest_engine_v1_20261014.py)
- Shared bootstrap runner: [runner.py](runner.py)
- Accelerated ZigZag: [fastpivot_patch.py](fastpivot_patch.py)
- Existing cached-engine variant on local session: `/mnt/data/engine_fast_quantile.py`; **not yet in GitHub**.
- Raw input archives: `EURUSD2003.M1.zip`, `USDJPY2003.M1.zip`. Not committed to GitHub.
- Local feature caches: `/mnt/data/ea_cache/EURUSD_2003_2026_engine-v1-fastpivot-v1-20261014.pkl` and USDJPY equivalent (each ~144MB); not committed to GitHub. Caches are session-local and **not automatically shared with other chat sessions**.

## Verified existing H4 OFF results (P1/P2/P3 included)
| Pair | Period | Trades | TotalR | PF | MaxDD | WinRate |
|---|---|---:|---:|---:|---:|---:|
| EURUSD | 2003–2026 | 1381 | 167.316279 | 1.191914 | -35.022541 | 35.6264% |
| EURUSD | 2015–2026 | 664 | 160.586473 | 1.410191 | -24.106889 | 39.7590% |
| USDJPY | 2003–2026 | 1304 | 101.567030 | 1.120356 | -59.939248 | 33.5890% |
| USDJPY | 2015–2026 | 633 | 138.133192 | 1.359896 | -29.925933 | 37.4408% |

## For each experiment
1. Check out the same engine commit. Verify SHA256 of input archive and cache version.
2. Verify the P1/P2-only baseline with an in-engine P3 prohibition (do not merely drop P3 trades).
3. Execute baseline and one-factor ablation in isolated output directories.
4. Report full-period and 2015+ metrics, yearly counts/R, trade differences, execution time measured from actual runtime.
5. Save experiment source and result in separate directories. Do not overwrite baseline or modify other experiments' files.
6. If any input/code is unavailable, report that precisely; do not claim that the entire backtest was executed.

## Dependencies
Python 3.11, numpy, pandas, numba. Data and caches should be placed under a shared mounted project directory or downloaded from an explicit durable artifact store. GitHub alone does not magically synchronize local /mnt/data files.
