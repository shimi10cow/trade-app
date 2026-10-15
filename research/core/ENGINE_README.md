# M15 reusable research engine

- `engine_m15.py`: copied and adapted from `research/full_backtest_engine_v1_20261014.py`, preserving signal, P-count, SL, and trailing logic; flags disable the agreed filters.
- `run_compare.py`: deterministic A1 or A2 ON/OFF comparison. Requires numpy and pandas.
- `cache_m15.py`: M1 ZIP → M15 pickle; **run only if cache is absent**.

Run from repository root:
```bash
python research/ea_shared/run_compare.py --test A1
python research/ea_shared/run_compare.py --test A2
```
Expected cache: `/mnt/data/ea_shared/EURUSD2003_M15.pkl`. If your environment lacks it, attach the 23 MB pickle; do not assume files from other chats persist.

Default configuration: q75 ON, expansion OFF, H4 RSI OFF, H4 levels OFF, inverse trend OFF, P3 entry OFF (P count still consumed on signal), MA ABCD ON, delayed ZZ 240h ON, +2R ON, maximum 2 concurrent positions. A1 fixes MA tolerance to 0.25 ATR; A2 fixes SMA200 minimum slope to 0.00002.

**Validation status:** source has been committed, but full 583k-bar backtests have not yet been executed here. Reconstructed canonical engine may differ from live EA. No performance numbers should be asserted before execution. Compare any results to the same reconstructed baseline, not earlier engines.
