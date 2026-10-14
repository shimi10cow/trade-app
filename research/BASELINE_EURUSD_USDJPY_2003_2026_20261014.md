# Frozen research baselines — 2026-10-14

These two backtests completed using Forex Tester VIP M1 data resampled to M15, the recovered canonical engine `research/full_backtest_engine_v1_20261014.py`, and a **provisional** H4 structural-level generator. The original historical H4-level algorithm has not been recovered, so "frozen" means a comparison benchmark for this implementation, **not a certified exact implementation of the originally specified EA**.

| Symbol | Dates | Trades | Total R | PF | Win rate | Max drawdown (R) |
|---|---|---:|---:|---:|---:|---:|
| EURUSD | 2003-05-06 to 2026-10-12 | 1290 | +158.744548 | 1.1942405 | 35.4264% | -32.3989999 |
| USDJPY | 2003-05-06 to 2026-10-12 | 1195 | +98.609519 | 1.1272372 | 33.4728% | -56.4859083 |

**2015 onward subsets, from the same full-history runs (not independently warm-started):**

| Symbol | Trades | Total R | PF | Win rate | Max DD (R) |
|---|---:|---:|---:|---:|---:|
| EURUSD | 619 | +148.370531 | 1.4026422 | 39.0953% | -22.1068892 |
| USDJPY | 582 | +122.105464 | 1.3437223 | 36.9416% | -31.5391864 |

### Provenance / reproducibility
- Data source: `EURUSD2003.M1.zip`, `USDJPY2003.M1.zip` (Forex Tester VIP; source archives not stored in GitHub).
- Resampling: M1 OHLC to M15, left-labeled 15-minute bars. M15 bars EURUSD 583,458; USDJPY 581,999.
- H4 level generation: confirmed 2-left/2-right pivot, confirmed close beyond latest pivot, activate on next H4 bar, expire after first H4 revisit. Reject a trade if the active directional level is within 0.60 x H4 ATR14.
- Level counts: EURUSD 8,989; USDJPY 8,980.
- Entry, exit and risk rules: consult archived canonical Python engine; runner monkey-patches the structural rejection and accelerates causal pivots with Numba.
- Runtime: EURUSD 67.48 seconds; USDJPY 60.95 seconds.
- Execution evidence: local `eurusd_2003_2026_log.txt`, `usdjpy_2003_2026_log.txt`.
- Full actual run scripts: local `eurusd_2003_2026_run.py`, `usdjpy_2003_2026_run.py`; accelerator `fastpivot_patch.py`. **These have not yet been committed to GitHub.** The existing `research/eurusd_2003_2026_run.py` and `research/usdjpy_2003_2026_run.py` are notes only, not complete executable scripts.
- Raw H4 levels: local `h4ext_EURUSD_levels_2003_2026.csv`, `h4ext_USDJPY_levels_2003_2026.csv`. Not yet committed.
- Metrics are trade-R metrics, not compound account returns. Execution-cost assumptions and exact historical fidelity need audit.

**Baseline change policy:** Keep these values as immutable comparison points. Record any change in logic, data source, warm-up, spread or slippage separately; do not silently overwrite them.
