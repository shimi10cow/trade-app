# Claude Code migration handoff — EURUSD Dow / protected swings
Date: 2026-10-18
Status: RESEARCH / NOT PRODUCTION READY. User-visible HTML is NOT accepted.

## User's current request and priority
Migrate all Dow research to Claude Code. FIRST finish EURUSD D1 major Dow protected low/high and correctly aligned, continuous historical horizontal boxes. H4/H1/M15, provisional trend, W patterns and expired zones are deferred, NOT deleted from the long-term spec. Do not repeatedly request user screenshots: verify rendered browser chart yourself.

## Non-negotiable distinction: UI vs logic
`research/chart_lab/eurusd_chart_lab_complete.html` is ONLY a UI/interaction/layout reference (chart, scrolling, zoom, replay, editable objects). NEVER copy its pre-existing Dow, horizontal line, zone, or trendline output as authoritative. Recompute every event independently from confirmed OHLC, then render it using the chart's actual time and price coordinates. Keep D1-only overlay clean; old red auto-trendlines must not obscure it. The latest generated HTML is defective; don't call it verified because JS syntax passes.

## Frozen pivot recognition
Canonical GitHub detector: `research/dow_frozen_v1/dow_final_engine.py`.
Local event adapter: `dow_frozen_causal_v1.py` (in downloadable source bundle, see MANIFEST).
W1: ATR7 x1.9 ER20 >=0.40 boost +15%; D1: ATR7 x1.9 ER20 >=0.40 boost -15%; H4: ATR7 x2.0 ER20 >=0.40 boost +30%; H1: ATR7 x2.4 ER20 >=0.25 boost -15%; M15: ATR7 x2.1 ER20 >=0.25 boost +30%.
TR=max(H-L, abs(H-prevClose), abs(L-prevClose)); ATR EWMA alpha=1/7 adjust=False. ER20=abs(close[t]-close[t-20])/sum(abs(close change) over last 20).
High/low pivots alternate, use WICKS, and confirm when counter-move exceeds ATR/ER threshold. Record `anchor_time` (pivot candle) separately from `known_at` (recognition candle). Only act at or after known_at. Record `confirmed` and `relocated` pivot events; relocations of the same pivot_id must update its anchor/price and active drawing. No future leakage.

## Agreed major Dow break/protected logic
- Break high only if confirmed candle CLOSE > previous relevant Dow high WICK. Break low only if CLOSE < relevant Dow low WICK. NOT full-body breakout.
- Uptrend: maintain current protected low and extreme high. On a new high breakout, update protected low ONLY to the corresponding formally confirmed Dow low of that breakout leg. If none recognized, keep old protected low; do not guess a raw low or enqueue pending breakouts.
- If the relevant low is formally confirmed later, compare its anchor_time to the prior high breakout and the actual leg boundaries. If formed BEFORE breakout and belongs to that leg, move protected low at known_at; otherwise await a future breakout.
- Downtrend is symmetrical with protected high and low breakouts.
- On EVERY candle, close below active protected low reverses uptrend to down; close above active protected high reverses downtrend to up. Do not skip when pivot recognition/relocation happens on the same candle.
- On change, old CURRENT protected reference disappears; for historical inspection, its box/segment ends precisely at the update or reversal candle. A broken point can separately create a historical zone (currently disabled).
- Narrow exception discussed for trend reversal initialization: opposite initial reference may be known raw wick extreme of the immediately preceding trend epoch. Its exact boundary must be independently audited; don't substitute arbitrary rolling 60-bar extremes.
- Audit ambiguous cases: same-bar relocation/reversal, delayed recognition after multiple breakouts, epoch start boundaries, and leg correspondence. Never equate event-count agreement with semantic proof.

## Later-stage rules (disabled in CURRENT D1 build)
Provisional downtrend: confirmed L1,H1,L2,H2 with H2<H1, historical close break below L1, then CLOSE below L2 initiates provisional down immediately, protecting H2 (do not wait for L3); mirror uptrend. Independent state machine; never alias major protection.
W top in major up: confirmed A high,B low,C high; no CLOSE > A wick from A through C (C wick may exceed); after C recognition, CLOSE < B wick triggers B zone. Mirror W bottom. Max 2 outcomes per major trend epoch; if B coincides with major protected pivot, retain both event reasons on one geometric zone.
Historical zone: outer edge pivot wick; inner edge closest body edge over associated structural wave (not one candle); anchor at pivot candle, activation at recognition/break candle, never show before activation in replay. Expire on first LATER candle whose entire body crosses opposite edge: min(O,C)>zone.high or max(O,C)<zone.low. Do not assign immutable support/resistance semantics.

## D1 experimental run and audit outputs (2026-10-18)
- D1 candles: 3,095. Frozen pivot events: 377; relocation events reported: 26; protected line segments: 95; protected update events reported: 57; reversal events: 37.
- Generated `d1_rebuild.py`, `D1_rebuild_events.csv`, `D1_rebuild_lines.json`, `audit_d1_sequential.py`, `audit_d1_updates.py`, `audit_d1_semantic_full.py`, plus audit JSON/CSV.
- Sequential audit: 0 detected anchor price mismatches, 0 reversal breaches inside active segments. Update consistency audit reported 0 mismatches; semantic audit reported 0 invalid recognition/anchor at line start.
- IMPORTANT: these audits are NOT independent proof that all 57 moves select the correct leg or that every required move was emitted. Previous assistant overclaimed verification. The generated state machine may itself be wrong; inspect it independently and build prefix-replay / independent oracle tests.
- Specific implementation risk: if active protected pivot_id is `relocated`, its anchor/price can change while existing segment geometry remains stale if `move()` short-circuits on unchanged pivot_id. Compare emitted segment price/anchor with active pivot at EVERY bar, not only when new pivot_id selected.
- Other risks: late-confirmed low/high may be linked to wrong breakout leg; initial raw extreme epoch window may be wrong; start/end timestamp semantics and replay clipping may be wrong.

## HTML attempts and observed failures
Generated variants: `EURUSD_D1_protected_rebuilt_complete.html`, `EURUSD_D1_boxes_complete_format.html`, `EURUSD_D1_boxes_history_fixed.html`, `EURUSD_D1_boxes_aligned_verified.html`.
User screenshots prove defects: initially only ~one box; next boxes scattered/disconnected and not aligned to candle prices/times; red trendlines crossing whole chart; missing proper historical segment continuity. The latest `aligned_verified` filename is misleading: actual browser rendering was NOT verified and user has NOT approved it.
Use Complete ONLY for presentation format. Box colors previously cyan=protected low and purple=protected high, small adjacent Japanese label 押し安値 / 戻り高値 + price. Render all historically active intervals in visible window, including terminated intervals, with accurate x and y mapping. Old active references should not remain open after an update. In replay, hide anything unknown at replay time.
Mandatory checks before delivery: automated browser screenshot (Playwright/Chromium), coordinate calibration at known wick/time, visible interval count vs dataset, pan/zoom/replay tests, labels, no spurious red lines, and no JS exceptions. Report measured tests, not guesses.

## Reproduction guidance
Local `d1_rebuild.py` extracted D1 OHLC from embedded `const SERIES=` in Complete HTML; it does NOT treat its existing Dow lines as ground truth. Prefer raw data and deterministic preprocessing if available. Use UTC/timezone consistently and detect milliseconds vs seconds vs candle indices. Inspect source scripts in accompanying migration ZIP, compare GitHub frozen engine.
First run and independently verify D1, then correct native Complete overlay and take screenshot, then add H4 and later features.
