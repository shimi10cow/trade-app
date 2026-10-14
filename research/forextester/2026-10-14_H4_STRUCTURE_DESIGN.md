# 2026-10-14 H4 structure research implementation

## Purpose
Use the previously recovered backtest engine with Forex Tester VIP EURUSD M15 bars and a causal H4 pivot-level cache. **Do not change entry/exit trading rules.** Keep generated level CSVs, trade ledgers and temporary engine copies outside GitHub. Only reproducible code, design and validated positive research findings should be committed.

## Files and folders
- `research/backtest_recovery/full_backtest_engine_v1_recovered.py`: archived reference engine (read-only).
- `research/forextester/prepare_mtf.py`: M1→M5/M15 conversion; input original M1 ZIPs are immutable.
- `research/forextester/2026-10-14_BACKTEST_RESULTS.md`: completed **H4 OFF** results and known limitations.
- `research/forextester/2026-10-14_H4_STRUCTURE_DESIGN.md`: this design.
- `research/forextester/2026-10-14_H4_EURUSD_RESEARCH.py`: deterministic H4 cache builder, quick causal checks and ON/OFF runner.

## Time and event ordering
- Forex Tester raw timestamps assumed UTC+0; no clock shifts.
- M15 timestamp is bar **open**. The original recovered engine labels entry at the current M15 row's time while using its completed OHLC; preserve this convention for the archived experiment, and separately audit look-ahead implications before using for live trading.
- H4 bars are aggregated from M15, and become available at their close boundary. A pivot becomes actionable only after confirmation.
- A level remains active until first subsequent H4 revisit; do not use later knowledge to mark it inactive before the revisit has actually occurred.

## H4 structural cache
1. Aggregate M15 into H4 using recovered engine's `resample_ohlc`.
2. Compute ATR(14), then recovered `causal_pivots_bootstrap` with 1.5×ATR and confirmation availability.
3. Each confirmed pivot creates a horizontal level at its pivot price.
4. `active_time` = pivot confirmation time; `expiry_time` = availability time of the first subsequent H4 bar whose high-low intersects that price (or 2100-01-01 if none).
5. On entry, reject buy if an active level is above entry and within 0.6×H4 ATR; reject sell if an active level is below entry and within 0.6×H4 ATR.
6. Never infer a level's earlier availability from its later expiration.
7. Cache is a **reconstructed proxy**, not the original missing `h4ext_..._levels.csv` frozen data. Do not claim exact original H4 behavior.

## Backtest plan
- Start loading from 2014-01-01 for indicator warmup, evaluate trades entered 2015-01-01 onward.
- Run EURUSD with H4 ON and OFF on **identical** data and all other parameters unchanged.
- Record counts of candidate evaluations and H4 rejections; verify ON/OFF trades differ in the expected direction.
- Report trades, net R, PF, DD, win rate, and limitations. Historical reference EURUSD 2015–2026 = 385 trades, +91.48R, PF 1.416, but matching it is not a goal.
- No new trading filters and no tuning to old results.

## Current execution status
- H4 level generation succeeded: 3,928 levels (2014–2026).
- An initial ON run using a vectorized level query and faster tuple iteration was launched on 2026-10-14, but **exceeded 200 seconds and did not complete**. Do not report H4 ON/OFF statistics as if measured.
- Further profiling and precomputation are needed before publishing the comparison. Avoid promising background execution.
- The recovered engine also contains older rules (e.g. 240-hour trailing and P3 MFE) and does not apply realistic spread/slippage. Keep these caveats explicit; no modifications have been made in this experiment.
