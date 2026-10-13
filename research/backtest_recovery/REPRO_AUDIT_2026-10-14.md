# Historical EA backtest reproduction audit — 2026-10-14

## Result: NOT reproduced (blocked by original input dependencies)

Recovered original engine: `full_backtest_engine_v1(1).py`. It requires for each pair `<PAIR>2020.M15.csv` plus frozen `h4ext_<PAIR>_levels.csv` with active_time/expiry_time. Neither original input set nor H4 cache was located in available project files. Current `EURUSD_M5_MT5.csv` and `USDJPY_M5_MT5.csv` are different inputs and cannot establish exact reproduction without time/price/data parity and structural caches. Engine is a six-pair version, not confirmed to be the exact two-pair 695-trade version.

## Original historical trade ledgers recovered
- `INTEGRATED_M15_EURUSD_extreme_switch_trades.csv`: 401 trades; gross +104.8133R, net +89.2158R, net PF 1.3841. P1 225 / +58.5413R, P2 154 / +22.6310R, P3 22 / +8.0435R.
- `INTEGRATED_M15_USDJPY_extreme_switch_trades.csv`: 322 trades; gross +88.9091R, net +76.1735R, net PF 1.3987. P1 184 / +16.2884R, P2 120 / +36.3697R, P3 18 / +23.5154R.
- Combined: 723 trades; net +165.3893R. P1 409 trades, P2 274, P3 40.

## Target result from prior chat
- EURUSD 385, +91.48R, PF 1.416; USDJPY 310, +82.60R, PF 1.454.
- Combined 695, +174.08R, PF 1.433. P1 384, +80.61R; P2 264, +64.10R; P3 47, +29.38R.

## Interpretation
These historical ledgers are real recorded outputs, but they do not match target. Do NOT tune parameters to force counts. Next locate the exact input M15 files, H4 structural cache, and original 695-trade output/code version. Preserve input hashes and run the original engine unchanged before attempting any adapter or optimization. No backtest was executed successfully in this audit because required frozen structural caches are missing.
