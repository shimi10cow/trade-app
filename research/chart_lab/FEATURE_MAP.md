# EA Chart Lab — feature map

## Purpose
Canonical reference for the interactive EURUSD Dow/Trendline research chart. Keep the full drawing/review experience, rather than replacing it with a read-only chart.

## Existing local sources (2026-10-17)
- `eurusd_trendline_review_v4_fixed.html`: full drawing/review controls and embedded candles.
- `eurusd_trendlines_all_tf_candles_fixed.html`: latest evenly spaced candle chart and W1/D1/H4/H1/M15 2-point and 3-point line visibility.
- `eurusd_line_chart_v1.html`: earlier editable chart.
- `dow_final_engine.py`: Dow pivot calculation.
- `trendline_dow_two_point_v5.py`: earlier two-point research implementation.

These filenames refer to local research artifacts; **the full HTML files are not committed by this document**.

## Preserve from editable chart
- W1/D1/H4/H1/M15 chart switching
- pan, zoom, jump to latest, candle-by-candle replay
- draw trendline, horizontal zone, parallel channel
- BUY/SELL position annotations
- select, duplicate, delete, undo, clear
- JSON export/import of annotations
- PNG/image export
- Dow pivots/structure visibility

## Integrate from latest line review
- Continuous/equally spaced candle indexing (no weekend gaps)
- Per-timeframe line visibility toggles; independent 2-point/3-point toggles
- Two-point lines: consecutive confirmed Dow same-kind pivots; rising lows/falling highs; minimum original-pivot interval 15 bars; replace A→B with C→B when an intervening candle extreme crosses the candidate, do not keep both; no intrusion rejection filter.
- Three-point lines: preserve the previously approved 3-point rules and their existing saved lines.
- Preserve timeframe provenance of each annotation and line.

## Critical implementation caveats
- Two-point anchor C may be a candle extreme rather than a confirmed Dow pivot.
- The 15-bar minimum was applied to original A→B, not the adjusted C→B.
- No-lookahead validation and automated drawing tests still required.
- Ensure JSON roundtrip, annotation selection/duplicate/delete, replay, BUY/SELL, line layers and screenshot still work after integration.

## Status
Feature map recorded. Full merged HTML and source artifacts still need to be committed and tested before this can be considered a completed canonical version.
