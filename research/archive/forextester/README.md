# Forex Tester VIP research dataset (EURUSD / USDJPY)

## Status (2026-10-14)
- Original M1 ZIPs: EURUSD2003.M1.zip and USDJPY2003.M1.zip, **retained in EA Project, not committed to GitHub**.
- Derived archive: ForexTester_VIP_EURUSD_USDJPY_M5_M15_2003_2026.zip (74,291,239 bytes ZIP payload; SHA-256 `2485b5db19ad1daacb41399e285ecafb0689520ef78d3595e95030acd2c193bf`). Downloadable from the ChatGPT conversation, not from this repository.
- EURUSD: 8,602,190 M1 rows, 1,741,198 M5 bars, 583,458 M15 bars.
- USDJPY: 8,572,606 M1 rows, 1,738,918 M5 bars, 581,999 M15 bars.
- Date range: 2003-05-06 00:00 through 2026-10-12 23:59 (M1).
- UTC+0 is an **export-time assumption** based on Forex Tester defaults; confirm before interpreting market sessions.
- Original dates unchanged. Output timestamp is bar OPEN. No forward-fill or synthetic bars. `m1_count` and `complete_m1` identify missing underlying minutes.
- M15 complete bar share: EURUSD 94.66%; USDJPY 92.83%. These figures are based on exact M1 count; low-activity minutes may be legitimately absent.
- OHLC consistency checks: zero contradictory bars in both M15 datasets. No duplicate M1 timestamps reported by converter.
- VOL values from Forex Tester are not assumed to be broker tick volumes.

## Analysis loading
```python
import pandas as pd
m15 = pd.read_csv('EURUSD_M15_UTC.csv.gz', parse_dates=['time_utc'])
m5 = pd.read_csv('EURUSD_M5_UTC.csv.gz', parse_dates=['time_utc'])
# Bar values become available at time_utc + 15min or + 5min respectively.
```

## Baseline status: NOT REPRODUCED
The recovered historical EA engine `research/backtest_recovery/full_backtest_engine_v1_recovered.py` depends on frozen `h4ext_<PAIR>_levels.csv` structural caches, which are missing. Its original data inputs and exact parameters also require reconciliation. **No valid 2003–2026 backtest result for the unchanged EA has been computed.** Archived 2015–2026 695/723-trade results are not substitutes for a new run.

## Repository policy
Keep source-data ZIPs and large generated datasets in the EA Project or external versioned data storage; keep reproducible preparation code, checksums, and verified summary reports in GitHub. Avoid uploading many exploratory result files.
