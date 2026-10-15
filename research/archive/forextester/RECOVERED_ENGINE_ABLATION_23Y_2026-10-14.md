# 2003–2026 Forex Tester: recovered engine / H4-cache ablation (2026-10-14)

**Not a reproduction of the current live EA.** This is the recovered 2026-09-23 backtest engine, running on Forex Tester VIP M15 data, with the missing frozen H4 structural-level rejection filter **disabled**. Its vintage rules, spread handling and M15 execution semantics may differ from the current strategy. These results must not be advertised as the current EA performance.

## Recomputed results

| Scope | Trades | Net R | PF | Win % | Max DD R |
|---|---:|---:|---:|---:|---:|
| EURUSD | 1,381 | +167.316 | 1.192 | 35.63 | -35.023 |
| USDJPY | 1,304 | +101.567 | 1.120 | 33.59 | -59.939 |
| Total | 2,685 | +268.883 | 1.157 | 34.64 | -81.638 |

## 2015–2026 overlap on new data, still without H4 filter

| Scope | Trades | Net R | PF |
|---|---:|---:|---:|
| EURUSD | 664 | +160.586 | 1.410 |
| USDJPY | 633 | +138.133 | 1.360 |

Historical 2015–2026 reference (695 trades / +174.08R / PF 1.433) is **not matched**. Differences are expected due to missing H4 cache and data source differences; do not equate.

## Phase breakdown over 2003–2026

| Pair | P | Trades | Net R | PF |
|---|---|---:|---:|---:|
| EURUSD | P1 | 666 | +60.379 | 1.142 |
| EURUSD | P2 | 630 | +116.724 | 1.301 |
| EURUSD | P3 | 85 | -9.786 | 0.830 |
| USDJPY | P1 | 604 | +12.273 | 1.031 |
| USDJPY | P2 | 613 | +64.819 | 1.162 |
| USDJPY | P3 | 87 | +24.475 | 1.475 |

## Reproducibility
- Source engine: `research/backtest_recovery/full_backtest_engine_v1_recovered.py`.
- Input: `ForexTester_VIP_EURUSD_USDJPY_M5_M15_2003_2026.zip` from EA Project.
- Driver and full 2,685-trade ledgers in conversation artifact `EA_23y_recovered_H4_ablation_results.zip`.
- Python code disables `load_levels` and `structural_level_reject` only; no fabricated H4 cache.
- Positions use the recovered engine's entry-at-M15-close, stop and causal ZigZag logic, **without a realistic broker spread/slippage adjustment**.
- Important: `run_pair` models each pair independently. Combined Max DD is calculated by exit timestamp from both pairs, without a global simultaneous-position gate.
- Do not interpret raw R as actual return, because costs, account risk and execution differ.

## Follow-up
Recover the original H4 level cache or reconstruct it and validate on the 2015–2026 historical reference; audit original engine's indicator parameterization, spread and position concurrency; rerun baseline before strategy optimization.
