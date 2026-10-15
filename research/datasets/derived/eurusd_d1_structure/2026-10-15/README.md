# EURUSD D1 structure — 2026-10-15 (provisional)

Purpose: causal D1 Dow/pivot/ZigZag features for EURUSD P1 initial H4-wave research. **Not production trading rules**.

Source: `research/datasets/derived/eurusd_h4_structure/2026-10-15/h4_structure_bars.csv`. Period 2003-05-06 to 2026-10-12, 7,329 D1 days, 37,805 H4 bars.

Local outputs generated in research session (not yet synchronized as CSV into this repository):
- `d1_structure_bars.csv` — D1 OHLC, Dow classification, last confirmed highs/lows, availability timestamp (7,329 rows)
- `d1_confirmed_pivots.csv` — left/right 2 D1 candle pivots, **available after 2 subsequent D1 bars close** (1,999 rows)
- `d1_atr_zigzag_confirmed.csv` — tentative ATR14 × 1.5 reversal ZigZag (1,351 confirmed turns; median confirmation lag 2 bars). OHLC intrabar ambiguity remains, so do not use as trading signals without review.
- `h4_with_d1_dow_state.csv` — D1 Dow states mapped to H4 bar open, as-of availability (37,805 rows)

Dow state counts: up 2,409, down 2,285, mixed 2,615, unconfirmed 20.

**Important:** Results were computed locally; do not assume these four CSV files are present in GitHub until they are actually uploaded. Do not treat retrospective extreme timestamps as availability times. All research should use the **full 2003–2026 period**; do not separately report 2015+.

Next: validate D1 pivot and ZigZag semantics, link P1 trades and H4 impulse outcomes, then compare exit variants.
