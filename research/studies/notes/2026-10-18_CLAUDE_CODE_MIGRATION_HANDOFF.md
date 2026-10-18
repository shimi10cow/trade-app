# Claude Code migration handoff — 2026-10-18

## Scope and honesty
This note transfers the **research decisions, result ledger, and local-artifact manifest**. The 2026-10-16–18 exploratory scripts and CSVs are packaged in the separately provided `EA_Claude_Code_handoff_2026-10-18.zip` and **are not yet individually committed to GitHub**. Do not assume the local ZIP is present in this repository. Import it with Claude Code, then commit `research/studies/scripts/` and `research/studies/results/` after code review. Original M1 ZIP files are large and must not be blindly pushed to git.

## Existing canonical repository
- `research/INDEX.md` (start here)
- `research/core/engine_m15.py` and `research/core/run_compare.py` (canonical existing EA, not identical to standalone exploratory engines)
- `research/studies/scripts/h4_reversal_m15_p12_signals.py`
- `research/studies/notes/2026-10-15_H4_reversal_M15_P1P2.md`
- `research/datasets/derived/eurusd_m15/2026-10-15/MANIFEST.md`

## Source data and reproducibility
- EURUSD2003.M1.zip, 2003–2026, Forex Tester M1; derived cache `ea_shared/EURUSD2003_M15.pkl`, 583,458 M15 bars (2003-05-06 to 2026-10-12). Cache and raw ZIP are **not GitHub assets**.
- Additional local data: EURUSD_M5_MT5.csv, USDJPY_M5_MT5.csv, USDJPY2003.M1.zip, JP225/UK100/US500 M15 CSV.
- H4 from causal completed M15 resampling; confirm exact resample boundaries and source timezone before comparing results. Pivot price timestamp differs from its later confirmation timestamp. No look-ahead allowed.
- Exploratory scripts commonly model 1.0 pip fixed spread. BUY entry Ask, SELL entry Bid; correct exit-side spread, stop fills, and avoid double counting. Slippage, dynamic spreads and commissions not proven incorporated.
- The scripts are **research prototypes**, not a verified reproduction of the live EA; results are exploratory and need independently reproduced before use.

## Original M15 stochastic P1/P2
- Actual existing core implementation: raw %K(14), smoothed K=SMA(raw,3), D=SMA(K,5); do not silently replace with textbook MT5 14,3,3.
- BUY state sequence: K below 20 -> K crosses above D -> K crosses above 20; SELL symmetric at 80. Three steps occur on completed M15 bars; enter next bar open. P count resets per H4 reversal regime for these studies. Signal counting before downstream gate matters.
- P3+ can be evaluated diagnostically; base strategy P1/P2.

## H4 Dow reversal experiment
- Concept: break protected H4 return high/low with completed H4 close; alternative W bottom/top neckline break is **separate**, not silently merged.
- Existing prototype H4 Dow reversal detector **not equivalent to all possible return-high breaks**: first determines structural trend from confirmed H4 ZigZag; W neckline detector absent. Therefore 843 events is an **implementation-specific count**, not total true Dow transitions.
- Entry M15 P1/P2 within max 240h from reversal and before subsequent regime transition. H4 level gate: at M15 signal close BUY must be above broken H4 level, SELL below. Earlier wick/close dips do not permanently invalidate the regime. This is not a compulsory retest.
- Reproduced historical baseline: 843 H4 events; 1,018 P1/P2 candidates; 751 executed trades, -39.22R PF .926 with level gate; no gate 1,044 trades -94.67R PF .874. Gate P1–P4: 1,167 -104.87R PF .875; no gate P1–P4: 1,676 -168.84R PF .861; all P with gate 2,668 -191.29R PF .899; without 3,816 -242.10R PF .911.
- 751 baseline entry timing posthoc: 0–24h 508 -43.88R; 24–48h 104 +26.72R; 48–96h 134 -17.21R; 96–144h 5 -4.87R. This is posthoc, not a fresh timing-filter-on backtest.

## W-bottom/top separate H4 experiment
- Separate W definition (exploratory, **not user's finalized Dow/W rules**): two confirmed H4 ZigZag lows (or highs) separated by opposite pivot; two extremes within H4 ATR14 * 0.5; H4 closing breakout of intervening neckline within 10 days of second pivot confirmation.
- Detected 281 W bottoms + 259 W tops = 540 events.
- Initial M15 P1/P2 with stop at most recent confirmed M15 ZigZag extreme +/-10 pips, +2R M15 ZigZag trail, max 1 open position, fixed 1 pip spread: no level gate 611 trades -18.24R PF .957; gate 437 trades -3.94R PF .987. P1–P4: no gate 992 -55.99R PF .921; gate 678 -33.03R PF .930.
- Changed to M15 SMA200 +/-10p stop, min 10 pip stop distance, +1.5R ZigZag trailing, max 1 or 2 positions: gate OFF / 1 pos 562 -8.65R PF .976; OFF / 2 pos 940 +6.91R PF1.012; gate ON / 1 pos 371 +0.60R PF1.003; ON / 2 pos 623 -3.76R PF .990.
- Changed **only SL anchor** to M15 SMA75 under +1.5R trail: gate OFF / 1 pos -54.69R PF .896; OFF / 2 pos +8.93R PF1.013; gate ON / 1 pos -22.15R PF .934; ON / 2 pos +4.55R PF1.010 (670 trades for latter). These small PF differences do NOT establish an edge.
- User wants keep +1.5R trailing and compare 1 vs 2 positions; further validate MA75 vs MA200 stops and max DD, by year, stopout behavior. 'HH75' was interpreted as SMA75 in last experiment; confirm this interpretation before hard-coding a permanent rule.

## Other exploratory studies and important nonconclusions
- H4 confirmed ZigZag low -> BUY, high -> SELL with M15 P1/P2 (not Dow): 3,454 trades +6.00R PF1.003. H4 ZigZag confirms pivot only **after** reversal reaches ~ATR14*1.5; pivot time and confirmation time distinct.
- Posthoc H4 amplitude contraction subgroup (<0.8 ratio): 981 of those trades +74.95R PF1.111. **Posthoc subset, not filter-on re-simulation**.
- A mistaken H1 gate required current M15 signal close above latest H1 high and produced 83 trades PF .646: **invalid interpretation, disregard**. User meant: during formation-to-confirmation of H4 ZigZag pivot, H1 structure had already reversed (return high/low or W neckline). Approx exploratory H1 confirmation rerun 3,148 trades +38.36R PF1.018; detector is provisional, not faithful to complete Dow/W definitions.
- M5-to-H1 structural lead-time counts were judged uninformative by user; do not spend more research time on that without a clear predictive test.
- Other local exploratory files cover Fibonacci retrace, H4 wave, no-retest/level-retest, trend maturity and DD clustering. See archive manifest and scripts. Do not conflate unrelated engines.

## What the user expects from Claude Code
1. Import complete local ZIP into a clean research folder and create a **tracked source/result inventory** (filename, SHA256, purpose, dependencies, reproducing command). Preserve original code and outputs before refactoring.
2. Keep Dow reversal and W top/bottom **separate** at first, with deduplicated overlap diagnostic only later.
3. Inspect actual code for all timing, H4 reversal, neckline, SMA SL, spread, trailing, concurrency and P counting assumptions; fix discovered errors explicitly, never silently rewrite historical results.
4. Re-run same source data and report trades, net R, PF, max DD, by-year/period, BUY/SELL, P1/P2, exposure, cost sensitivity, and causal validation.
5. Commit documented research source and lightweight results to `research/studies/`; large raw datasets and caches stay local or tracked by manifest / LFS only with user approval.
6. Never claim an uncommitted local file is on GitHub. Do not overwrite existing canonical core with exploratory code.
