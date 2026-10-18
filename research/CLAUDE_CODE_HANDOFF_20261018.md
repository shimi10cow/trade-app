# Claude Code migration handoff — FX EA / Dow / trendline / horizontal zones

> **START HERE:** [RESEARCH_INDEX_20261018.md](RESEARCH_INDEX_20261018.md) lists confirmed file locations, missing engine paths, each experiment's conditions, reported metrics, and provenance. Read the index BEFORE attempting to run an old backtest.
Date: 2026-10-18. Status: specification + research handoff, NOT a verified working EA.
Repo: shimi10cow/trade-app. Work in a feature branch; preserve existing trading-app functionality and frozen reference detectors.

## Objective and scope
Reproduce discretionary Dow market structure in an entirely causal, testable, multi-timeframe Python EA research engine. Priority now: accurate Dow structure, trendline creation and retirement, horizontal zones; NOT profitability optimization or HTML polishing. User wants all research on GitHub and to continue in Claude Code.

## Authoritative files — read first
- research/dow_frozen_v1/dow_final_engine.py — frozen pivot detector; do not silently modify.
- research/dow_frozen_v1/DOW_RULES_20261018.md — major/provisional Dow, protected swing, W-top/bottom, zones, known-at.
- research/chart_lab/trendline_causal_engine.py — causal line-candidate events; research code, NOT production certified.
- research/chart_lab/TRENDLINE_RULES.md — exact 2/3-point generation rules.
- research/chart_lab/TRENDLINE_RULES_REVIEW_20261018.md — **latest** retirement rules; supersedes its earlier version and any contradictory legacy notes.
- research/chart_lab/FEATURE_MAP.md — chart/EA UI integration.
- research/chart_lab/eurusd_chart_lab_complete.html — manual chart baseline; historical overlay is NOT evidence of real-time signal availability.
- research/ea_shared/engine_m15.py and research/ea_shared/run_compare.py — **OLD PATHS following repo reorganization**; canonical verified replacements are `research/core/engine_m15.py` and `research/core/run_compare.py`. See `research/INDEX.md` and `research/RESEARCH_INDEX_20261018.md`.
Some older source documents contain stale 'implementation gaps' sections; inspect actual code and run tests rather than assuming they reflect current status.

## Frozen causal Dow pivot detector
Timeframe parameters (ATR period, base multiplier, ER boost, ER cutoff):
W1=(7,1.9,+0.15,0.40), D1=(7,1.9,-0.15,0.40), H4=(7,2.0,+0.30,0.40), H1=(7,2.4,-0.15,0.25), M15=(7,2.1,+0.30,0.25).
ATR: Wilder-style EWMA alpha=1/7; ER20=abs(close[i]-close[i-20])/sum(abs(close changes),20); threshold=base*ATR*(1+boost if ER>=cutoff else 1). Extremes use candle wicks; confirmation occurs on a later candle after sufficient opposite movement. Latest pivot may relocate. Events require anchor_idx AND known_at/available_idx. Do NOT use final historical pivot tables to generate earlier entries. Compare causal stream with frozen implementation, including relocation.

## Dow major-trend and protected swing
Use the complete DOW_RULES_20261018.md as the normative spec, not a simplistic HH/HL detector.
- Break a pivot high iff completed CLOSE > pivot HIGH WICK; low iff completed CLOSE < pivot LOW WICK. A single candle can trigger a reversal.
- In major uptrend maintain a **protected Dow low** (押し安値); in downtrend maintain a **protected Dow high** (戻り高値).
- On an uptrend new high break, advance protected low only to an eligible confirmed Dow low structurally between the prior high and breakout. If none exists, retain previous low; do not fabricate a pivot.
- A later-confirmed pivot with an earlier anchor can update the protected swing at its actual confirmation time if it structurally belongs to the breakout leg; never backdate. Mirror for downtrend.
- Close beyond protected low/high causes major trend reversal at the known-at bar. Record the prior protected level as horizontal-zone event. Opposite trend initialization has a specifically documented raw-wick exception.
- Provisional (仮) trend is separate from major trend; use the exact L1/H1/L2/H2 structure in the source document. W-top/bottom events have max 2 per major-trend epoch and may coincide with a major reversal.
- Existing horizontal zone v9 is explicitly flawed/unverified. Do NOT treat it as finished.

## Trendline creation — preserve approved generation behavior
Two-point: only consecutive confirmed same-kind Dow pivots (higher low-to-low or lower high-to-high), independent of major trend. Original pivot separation >=15 candles, no maximum. If intervening wick crosses the outer side, iteratively move first anchor to offending wick extreme C until valid; retain ONLY corrected C-B, and C need not be a Dow pivot. Minimum gap applies to original pair. No ATR intrusion rejection.
Three-point: consecutive same-kind 3 pivots, each advancing >=0.12 ATR; adjacent gap 4..(W1 75, D1 95, H4 115, H1 145, M15 175). Draw first-third, middle deviation <=0.85 ATR; close intrusion >0.35 ATR allowed at most 10% of intervening bars; maximum <=1.7 ATR; normalized slope 0.25..7. Near-duplicate end-index windows W1 45/D1 65/H4 85/H1 110/M15 130, replacement only on score improvement >0.12. Do not change these parameters without explicit user request.
Generate append-only create/revise/retire events at known-at; pivot relocation may revise/invalidate construction. Historical line geometry is not necessarily usable from its anchor date.

## Latest trendline lifecycle and retirement (agreed; implementation NOT yet verified)
Line slope vs CURRENT confirmed major Dow direction classifies impulsive 推進 (same direction) or corrective 調整 (opposite). This classification changes on major Dow reversals. A surviving corrective line may become an impulsive line; user wants to use such a line for later EA entries. **When an impulsive line's trend reverses, retire that line immediately**, rather than reclassifying it into a corrective line. Therefore track prior classification/impulsive epoch or equivalent state. A corrective line must not be retired merely because its major trend reverses and makes it impulsive.
Independent break retirement for either class:
- Descending line: CLOSE above line, then TWO UNIQUE subsequently confirmed Dow LOW pivots => retire at second confirmation.
- Ascending line: CLOSE below line, then TWO UNIQUE subsequently confirmed Dow HIGH pivots => retire at second confirmation.
- If price closes back on inside of the line before second confirmation, reset count; next fresh break restarts.
- Pivot relocation is NOT a new pivot count. A construction-invalidating relocation is a separate reason for retire/revise.
- No arbitrary TTL; W1 long-lived lines are acceptable.
- Both rules are applied to each line's own timeframe Dow state, not hard-coded H4; H4 is the worked example. Never count future-confirmed pivots as though known earlier.
- Precise same-bar ordering, break-bar pivot inclusion and line-revision interaction need deterministic tests and explicit recording before production.
**Implementation order agreed with user:** implement/test break + 2 confirmed pivots FIRST, then add impulsive-trend-reversal retirement only after protected-swing/major-Dow state machine is verified. Until both stages pass, DO NOT use as production EA entry signals.

## Horizontal zones
Outer edge = pivot wick; inner edge = nearest body edge in full relevant structural wave using only information known by activation. Become known only at breakout/activation, although visually anchored to earlier pivot. Expire at first LATER candle whose entire body passes the far zone edge. Historical events must be immutable; keep source labels (major protected swing, provisional, W top/bottom), deduplicate overlapping physical zones without discarding source labels. Do not hard-code permanent support/resistance identity.

## Historical work and validation findings
1. Frozen Dow pivot detection and manual chart overlays researched W1/D1/H4/H1/M15; user repeatedly rejected HTML plots with missing/misaligned candles, incorrectly aligned boxes and truncated chart coverage. Do not call those displays verified.
2. Separate causal pivot-event and 2-/3-point trendline engine exists; historical HTML uses retrospective embedded line sets, NOT true known-at replay.
3. Protected swing migration, delayed pivot confirmation, major reversals, provisional trends, W tops/bottoms and horizontal zones were specified. The downstream zone engine v9 is flawed and still requires audit.
4. Trendline retirement rules were simplified, then amended: dynamic correction/impulse classification; impulse retires on major trend reversal; break + 2 opposite-kind confirmed pivots; inside return resets. Earlier rule 'retire every line on any trend epoch ending' is REJECTED.
5. No independent, full-history all-line zero-stale audit or production-quality causal line lifecycle has been demonstrated. Do not assert completion.

## Separate earlier EA strategy/backtest track — do not conflate
Strategy researched: H1 trend SMA200/480, SMA480 24h slope; M15 Stoch 14,3,3; M15 entry/exit, P1/P2 favored, P3 excluded in some comparisons, P5 forbidden; initial SL around M15 SMA200+10p with min 10p, spread cap, ZigZag ATR14*1.5 trail starting +2R. Research includes q75, MA ABCD, H1 countertrend, 240h delayed ZigZag and H4 filters. Historical reported figures (NOT re-run in this handoff): 2015–2026 simple 1974 trades +359.6R PF1.308 DD -42.3R; H4 96h+25pt 1681 trades +327.41R PF1.332 DD -34.84R. EURUSD 2003–2026 M15 cache reportedly 583458 candles. The engine and runner were MOVED from historical `research/ea_shared/` to verified `research/core/` paths. Archived full engine exists at `research/archive/legacy_scripts/full_backtest_engine_v1_20261014.py`. These source files exist but must still be matched to each historical run; see `RESEARCH_INDEX_20261018.md` and `research/handoffs/EXPERIMENT_ENGINE_MATRIX_20261018.md`. Check provenance and reproducibility before trusting results; this is a different system from the Dow-line EA.
Potential input files in ChatGPT environment (not asserted uploaded to GitHub): EURUSD2003.M1.zip, USDJPY2003.M1.zip, EURUSD_M5_MT5.csv, USDJPY_M5_MT5.csv, JP225_M15_MT5.csv, UK100_M15_MT5.csv, US500_M15_MT5.csv. Large datasets must be separately transferred/located, not assumed present in Claude Code.

## Claude Code recommended execution order / acceptance gates
1. Read `research/INDEX.md`, `research/handoffs/EXPERIMENT_ENGINE_MATRIX_20261018.md`, and `research/studies/notes/2026-10-18_EXPERIMENT_ENGINE_CONDITIONS.md`; inventory repository tree, docs, tests and data; produce manifest with hashes, timestamps, symbol/timezone, OHLC resampling assumptions. No silent strategy modifications.
2. Establish reproducible Python environment + pytest fixtures; add small synthetic OHLC scenarios and sample replay traces.
3. Audit frozen Dow parity (confirm/relocate, anchor/known-at) and causal availability with bar-by-bar replay. Freeze reference behavior.
4. Verify 2/3-point line creation/reanchor/dedup/revise/invalidate against hand-labeled scenarios and actual EURUSD data.
5. Implement independent lifecycle module for close break, reset and 2 unique post-break confirmed pivots; record event log, test repeated break/reset, same-bar events and relocations.
6. Implement/audit protected low/high state machine, late confirmation and major Dow reversal; verify H4/D1 and then other TF. Cross-check every reversal and missing event.
7. Add dynamic impulse/correction classification and impulse reversal retirement, retaining corrective-to-impulsive line; regression test up->down->up and mirror.
8. Integrate zone/W/provisional events and validate historical geometry/expiry without lookahead.
9. Full chronological replay, compare active line registry with expected state at every bar; log unexplained long-lived lines, missing lines and mismatched geometry; do NOT force-expire to hide errors.
10. Only after all gates, expose active lines/zones to EA and optional chart UI. Entry at open k uses events available_idx < k. At close k, events available_idx <= k only if order timing permits.
Keep audit artifacts and tests on GitHub. Do not overwrite the frozen detector or trade app. If source/docs disagree, document conflict and ask user only about genuine unresolved rule choices.

## Known caveats / unresolved implementation decisions
- Source TRENDLINE_RULES.md has a stale gap list contradicting its newer description of implemented retire/dedup; code is the current implementation reference but must be tested.
- Line event IDs/keys and unique Dow pivot IDs must survive revisions; do not double-count relocate.
- Same-bar event ordering, boundary equality (close exactly on line), pivots confirmed on breakout bar and revised line geometry need explicit consistent tests. Do not invent extra expiry conditions.
- Dynamic major-trend classification is not available reliably until protected-swing state is validated. Phase 1 must mark impulse retirement pending rather than silently claim fully valid EA signals.
- No repository changes here imply execution of new backtests or successful chart validation.
