# EA Backtest Recovery Index (2026-10-14)

## Purpose
Preserve provenance of the 2015–2026 M15 Extreme Switch + Retracement Gate results. **Do not treat the recovered engine as the exact 695-trade implementation until verified.**

## Historical target (EURUSD + USDJPY)
- EURUSD 385 trades, +91.48R, PF 1.416
- USDJPY 310 trades, +82.60R, PF 1.454
- Total 695 trades, +174.08R, PF 1.433, max DD -22.84R (historical record)
- P1: 384 trades, +80.61R, PF 1.356
- P2: 264 trades, +64.10R, PF 1.423
- P3: 47 trades, +29.38R, PF 2.227

## Recovered from previous EA project conversations / files
- `full_backtest_engine_v1(1).py` (dated 2026-09-23, ~20KB): canonical FX EA full backtest engine v1.0; generates M15 signals causally; original input convention `<PAIR>2020.M15.csv` and frozen H4 structural caches. **Not proven identical to the 695-trade run.**
- `EA_Backtest_Handoff_2026-09-23.docx`: historical backtest handoff.
- `INTEGRATED_M15_EURUSD_extreme_switch_trades.csv` and `INTEGRATED_M15_USDJPY_extreme_switch_trades.csv`: historical ledgers with `point`, `regime_id`, `entry_i`, `R_gross`, `R_net` (must locate and verify rows).
- Past chat around 2026-09-26 contains the complete M15 rule specification.
- Existing live EA implementation: `mt5_ea/m15_strategy.py`; **do not modify live code as part of research**.

## Known mismatch / caution
Recovered canonical engine lists six pairs and uses H4 cache inputs; user-provided MT5 M5 CSVs differ from original M15 data inputs. No numerical reproduction has been established. Prior provisional 863-trade fixed-2R reconstruction is **not** a valid baseline.

## Next steps
1. Recover exact historical EURUSD/USDJPY integrated ledgers and inspect P distribution / row count / R column.
2. Compare source code and handoff specification to the historical 695-trade rules.
3. Preserve original source unchanged and add a separate adapter for M5-to-M15 only if timing conventions match.
4. Run exact source with pinned inputs; compare trade-by-trade and P-by-P, recording data hashes, parameters, costs, time conventions and commit SHA.
5. Only label a result 'reproduced' after matching the trade ledger within documented tolerance.
