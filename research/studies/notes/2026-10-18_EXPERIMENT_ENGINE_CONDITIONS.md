# 2026-10-18 — Exact experiment conditions, execution engines, and result mapping

**Status:** Research audit / migration map. This file records historical exploratory results; it does **not** assert that all local experiment scripts are already committed. A separately provided ZIP `EA_Claude_Code_handoff_2026-10-18.zip` contains the source and results. Extract it and preserve file names. See `2026-10-18_CLAUDE_CODE_MIGRATION_HANDOFF.md` for broader context.

## Engines: do not mix

| Kind | Location | Scope |
|---|---|---|
| Canonical existing EA | `research/core/engine_m15.py` | Original shared H1/M15 trend-following engine; **not** the H4 reversal or W study runner |
| Canonical ON/OFF runner | `research/core/run_compare.py` | Runs original shared engine |
| H4 P detector | `research/studies/scripts/h4_reversal_m15_p12_signals.py` | Stochastic signal extraction; **not** full trade execution |
| H4 Dow research | ZIP: `h4_stoch_canonical_p12_rerun.py`, `h4_p_depth_diagnostic.py`, `h4_stoch_level_gate_rerun.py` | H4 event detection, P-depth / gate comparisons |
| W neckline research | ZIP: `h4_w_pattern_study.py` | W detection and original ZigZag SL runner |
| W SMA200 research | ZIP: `w_sma200_15r_two_positions.py` | SMA200 stop, +1.5R, 1 vs 2 concurrent |
| W SMA75 research | ZIP: `w_sma75_15r_two_positions.py` | SMA75 stop, +1.5R, 1 vs 2 concurrent |
| ZigZag helper dependency | ZIP: `fib_382_618_retest.py` | Causal `zig_events()` used by W/SMA studies |
| Other H4 helper | ZIP: `h4_trend_wave_tracker.py` | H4 ZigZag helper |

**Import dependency caution:** The standalone scripts use absolute `Path('/mnt/data')`, read `ea_shared/EURUSD2003_M15.pkl` and sibling CSVs, and sometimes import helpers from other ZIP scripts. Claude Code must replace these paths with configurable project paths, without altering the algorithm, and reproduce the CSVs before any refactoring.

## Market data and bar semantics
- Source: EURUSD Forex Tester historical M1, approximately 2003-05-06 to 2026-10-12; local derived M15 cache `ea_shared/EURUSD2003_M15.pkl`, 583,458 rows. Verify source timestamps and timezone before production use.
- H4/M15 resampling uses completed bars and right-side timestamps. ZigZag has **pivot index** and **later confirmation index**; the latter controls availability.
- M15 stochastic: raw %K14, K SMA3, D SMA5. BUY: K<20 then K/D upward crossover then K crosses 20 upward. SELL inverse above 80. M15 signal on completed bar, entry on next bar open.
- Exploratory costs: fixed 1 pip spread (EURUSD price 0.0001); BUY Ask entry/Bid exit, SELL Bid entry/Ask exit. Commission, slippage and historical spread variation are **not modeled**. Stop execution and same-bar fill ordering need independent audit.
- Metrics R = realized P/L divided by initial entry-to-stop risk; PF = sum positive R / absolute sum negative R; DD from cumulative R, **not account equity %**. Exact engine stop/fee conventions may differ.

## H4 Dow structural reversal / M15 study
- H4 event detector based on confirmed H4 ZigZag and protected swing break, H4 **close** beyond reference level; original detector is incomplete relative to the user's finalized Dow definition and does **not** implement independent W neckline events.
- Event active up to 240 hours (10 days) or next H4 regime; P numbering resets on H4 reversal; P1/P2 only in baseline.
- Level gate ON: at **M15 signal close**, BUY close above H4 broken level, SELL close below. Prior dips/wicks do not permanently cancel. This is not a required retest.
- Original research stop: last confirmed M15 ZigZag low/high +/-10 pips; +2R causal M15 ZigZag trailing; max 1 simultaneous position; fixed 1 pip spread.
- Baseline 843 H4 detected events; 1,018 P1/P2 signal candidates; gate ON 751 trades, -39.224R, PF0.926. Gate OFF 1,044 trades -94.670R PF0.874. P1–P4 gate ON 1,167 -104.872R PF0.875, OFF 1,676 -168.835R PF0.861; all P gate ON 2,668 -191.287R PF0.899, OFF 3,816 -242.102R PF0.911.
- Timing analysis of baseline 751 trades: 0–24h 508 -43.88R; 24–48h 104 +26.72R; 48–96h 134 -17.21R; 96–144h 5 -4.87R. **Retrospective grouping, not timing-gated resimulation**.
- Outputs: ZIP `h4_p_depth_comparison.csv`, `h4_p_depth_trades.csv`, `h4_p_all_signal_diagnostic.csv`, `h4_stoch_canonical_p12_rerun_trades.csv`.

## H4 W-bottom / W-top — standalone strategy, do NOT merge with Dow counts
- Confirmed H4 ZigZag sequence low-high-low (W bottom) or high-low-high (W top); two same-side extreme prices within H4 ATR14 * 0.5; neckline is middle opposite pivot; completed H4 close breaks neckline after second pivot confirmation, within 10 days.
- 281 W bottoms, 259 W tops, 540 events. This ATR threshold is **exploratory**, not the user's exact finalized W definition.
- M15 P1/P2 after event, within 240h / next event. Optional neckline level gate at signal close. Fixed 1 pip spread.
- Initial W runner: initial SL last confirmed M15 ZigZag swing +/-10 pips, +2R M15 ZigZag trailing, max 1 position. P1/P2 gate OFF 611 trades -18.24R PF0.957; gate ON 437 trades -3.94R PF0.987. P1–P4 gate OFF 992 -55.99R PF0.921; gate ON 678 -33.03R PF0.930.
- Outputs: ZIP `h4_w_pattern_study.py`, `h4_w_pattern_events.csv`, `h4_w_pattern_signals.csv`, `h4_w_pattern_comparison.csv`, `h4_w_pattern_trades.csv`.

## W runner with SMA200 / SMA75 initial stop
- Entry at next M15 open; stop based on **previous completed M15** moving average (`sma[j-1]`), with 10 pip buffer and minimum 10 pip risk. BUY stop = min(MA-0.001, Ask_entry-0.001); SELL stop = max(MA+0.001, Bid_entry+0.001). Skip if initial risk > 200 pips. This is **not** the original ZigZag swing SL.
- +1.5R favorable movement arms M15 confirmed-ZigZag trailing; update on following bar (not same bar). Trade timeout 1,920 M15 bars (~20 trading days). Max simultaneous 1 or 2; candidate P1/P2.
- SMA200:
  - gate OFF cap1: 562, -8.65R, PF0.976
  - gate OFF cap2: 940, +6.91R, PF1.012
  - gate ON cap1: 371, +0.60R, PF1.003
  - gate ON cap2: 623, -3.76R, PF0.990
- SMA75:
  - gate OFF cap1: -54.69R, PF0.896
  - gate OFF cap2: +8.93R, PF1.013
  - gate ON cap1: -22.15R, PF0.934
  - gate ON cap2: 670, +4.55R, PF1.010
- Scripts: ZIP `w_sma200_15r_two_positions.py`, `w_sma75_15r_two_positions.py`. Outputs: matching `*_comparison.csv`, `*_trades.csv`. Note source uses `numba.njit` for exit simulation.
- **Interpretation caution:** user's phrase 'HH75' was treated as SMA75; verify with user whether a different 75-period indicator was intended.
- **Audit caution:** the source calculates stop and trailing based on intrabar OHLC and has specific spread/stop-hit ordering. Review SELL stop fill, same-bar trigger priority, and simultaneous-trade risk before treating results as reliable. Profit factors near 1 imply no demonstrated edge.

## Additional exploratory engines and known invalid comparisons
- ZIP `h4_expansion_probe.py` / `h4_expansion_probe_trades.csv`: H4 ZigZag last confirmed low->BUY, high->SELL; M15 P1/P2. 3,454 trades +6R PF1.003. Contraction subgroup (981 +74.95R PF1.111) is **posthoc subset**, not a fresh filter-on execution.
- H1 gate mistakenly checking current signal above latest H1 swing gave 83 trades PF0.646: **wrong user intent, discard**. Correct intent is H1 structure reversal *during the formation-to-confirmation window of the H4 pivot*.
- ZIP `run_h1_h4_confirm.py`, `h1_h4_confirm_trades.csv`: provisional H1 reversal detector, 3,148 trades +38.36R PF1.018; does not fully implement user's Dow/W rules.
- ZIP `m5_h1_structure_study.py`: M5/H1 lead-time diagnostic; user deemed this unhelpful. Do not interpret temporal precedence as an edge.

## Mandatory Claude Code migration checklist
1. Import ZIP and produce file manifest with SHA256, role, dependencies, input/output paths and reproduction command; verify all mentioned filenames exist.
2. Preserve immutable copies of each script/CSV before refactor; run and compare summary metrics with documented results.
3. Commit **standalone engines and lightweight CSVs** under `research/studies/scripts/` and `research/studies/results/`, update `research/INDEX.md`. Keep 23MB cache and original M1 ZIP out of git unless user explicitly approves LFS.
4. Run causal no-lookahead tests, data timezone and bar closure tests, spread-side fill tests, same-bar SL/TP priority tests, concurrency and exposure tests.
5. Keep Dow and W distinct and retain ON/OFF level gate comparisons. Never attribute a result to `research/core/engine_m15.py` unless actually run by that engine.
6. After validation, compare W and Dow under **identical** SMA75/SMA200 stop, +1.5R trailing and cap1/cap2 configurations, including annual breakdown, drawdown, BUY/SELL and P1/P2.

