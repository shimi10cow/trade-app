# 2026-10-14 | Forex Tester VIP 2003–2026 backtest and dataset preparation

## Scope and provenance
- EURUSD / USDJPY Forex Tester 6 VIP, M1 2003-05-06 to 2026-10-12.
- Raw ZIPs `EURUSD2003.M1.zip` and `USDJPY2003.M1.zip` are the primary data; leave unchanged.
- Derived M5/M15 OHLCV files (CSV.GZ) generated from M1, UTC+0 assumed, original timestamps not shifted.
- 8,602,190 EURUSD and 8,572,606 USDJPY M1 rows.
- 1,741,198 EURUSD and 1,738,918 USDJPY M5 bars.
- 583,458 EURUSD and 581,999 USDJPY M15 bars.
- Missing-minute bars are flagged by `m1_count` / `complete_m1`, not fabricated. Reproduction script uses all existing bars, including partial bars.
- Original ZIPs and prepared data are **not stored in this GitHub repository**. The derived data archive is `ForexTester_VIP_EURUSD_USDJPY_M5_M15_2003_2026.zip` (see EA Project conversation). Data preparation source: `research/forextester/prepare_mtf.py`.
- The exact reproduction script for the results below is `research/forextester/2026-10-14_run_recovered_h4_absent.py`. Engine: `research/backtest_recovery/full_backtest_engine_v1_recovered.py`.

## Results actually completed: recovered historical engine, H4 structural-level rejection OFF
| Scope | Trades | Net R | PF | Win rate | Max DD R |
|---|---:|---:|---:|---:|---:|
| EURUSD | 1,381 | +167.316 | 1.192 | 35.63% | -35.023 |
| USDJPY | 1,304 | +101.567 | 1.120 | 33.59% | -59.939 |
| Combined | 2,685 | +268.883 | 1.157 | 34.64% | -81.638 |

The combined DD uses exit-time ordering of pair-level trades; it does not simulate account-wide concurrency.

### P breakdown
| Pair | Phase | Trades | Net R | PF |
|---|---|---:|---:|---:|
| EURUSD | P1 | 666 | +60.379 | 1.142 |
| EURUSD | P2 | 630 | +116.724 | 1.301 |
| EURUSD | P3 | 85 | -9.786 | 0.830 |
| USDJPY | P1 | 604 | +12.273 | 1.031 |
| USDJPY | P2 | 613 | +64.819 | 1.162 |
| USDJPY | P3 | 87 | +24.475 | 1.475 |

### 2015–2026 overlap on Forex Tester data, H4 OFF
| Pair | Trades | Net R | PF |
|---|---:|---:|---:|
| EURUSD | 664 | +160.586 | 1.410 |
| USDJPY | 633 | +138.133 | 1.360 |

Historical archived comparison: 695 trades, +174.08R, PF 1.433, **not matched**. This is not a requirement to optimize against; different inputs and omitted H4 explain why it is not directly comparable.

## Caveats / status
1. **H4 level rejection has not been successfully run end-to-end.** A candidate H4 pivot reconstruction exists locally, but its full backtest timed out. Do not label the numbers above 'H4 enabled'.
2. The recovered engine uses its own vintage configuration. Existing rules were retained for the above run; no new entry/exit rules were added.
3. **Spread/slippage is not implemented in this recovered-engine run.** Inspecting the recovered code shows entry = M15 close, SL based on SMA200 and minimum risk, with no spread adjustment. Earlier historical assumptions cannot be claimed to be inherited here. Consequently the PF/R figures are optimistic relative to a cost-aware simulation.
4. Not a live EA validation or proof of 23-year profitability. No current EA rules were modified.
5. H4 candidate filter uses causal pivots with ATR(14) × 1.5, expiration at first retouch, rejection within H4 ATR × 0.6. This is an unverified proxy for missing frozen H4 level cache, **not** a validated reconstruction and not used for the reported numbers.

## Next check
Run H4 candidate on a shorter 2025–2026 window, verify the filter rejects actual signals and compare H4 ON vs OFF on the same data. Do not add new trading rules to improve PF.
