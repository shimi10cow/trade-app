# D1 Dow research: work done, observed results, unresolved tests

## Scope
EURUSD D1 only, 3,095 candles in the last generated run. Earlier multi-timeframe, provisional trends, W formations and zones were discussed but are deferred while major D1 protection is validated.

## Frozen event recognition
Used a causal confirmed-pivot adapter over the frozen detector. Generated event trace reported **377 pivot events** and **26 pivot relocation events**. These are counts from that particular implementation and data extract, not universal ground truth.

## Protected line reconstruction
`d1_rebuild.py` produced **95 line segments**, **57 protection updates**, and **37 trend reversals** in the earlier run. Verify by rerunning the exact source and data. Separate pivot anchor time from recognition time. Source code is not independently established correct.

## Audits
- `audit_d1_sequential.py` reported 0 anchor-price mismatches among 95 segments and 0 missed reversals within active intervals, after a bug in the audit itself (candle index vs millisecond timestamp) was corrected.
- `audit_d1_updates.py` reported 0 recorded-update mismatches and 0 active-pivot relocation misses.
- `audit_d1_semantic_full.py` reported 0 missing recognition events or line-start anchor mismatches.
- **Limitation:** these checks largely compare related outputs. They do NOT prove the chosen low/high is the one belonging to the broken-out leg or prove no logically required update was missed. They also do not validate browser placement.
- Specific likely flaw in `d1_rebuild.py`: `move(i,pid,...)` exits if `pid==prot`, but relocation can change active pivot's anchor/price without redrawing the current segment.

## HTML iterations and observed defects
1. `EURUSD_D1_protected_rebuilt_complete.html`: claimed Complete-style display; user found layout/box presentation unacceptable.
2. `EURUSD_D1_boxes_complete_format.html`: attempted format matching, still essentially only one visible box in screenshot, large unrelated red trendlines.
3. `EURUSD_D1_boxes_history_fixed.html`: rendered more historical boxes, but user screenshot showed disconnected boxes, incorrect apparent alignment and red trendlines.
4. `EURUSD_D1_boxes_aligned_verified.html`: further attempt; **not verified in actual browser and not approved**. Never interpret “verified” in filename as test evidence.

## Minimum acceptance test plan
1. Independently calculate expected protected low/high at every candle from frozen confirmed pivots and rule-based breakout leg association.
2. Compare every generated update/expiry and trend reversal to independent expected state, including late confirmation and relocation.
3. For each visible interval, verify exact time x-coordinates and price y-coordinates against the native chart coordinate API. No CSS pixel-position guesswork.
4. Test full historical segments, replay-time visibility, pan/zoom, changing viewport and date boundaries.
5. Use actual browser automation (Playwright or equivalent) to take screenshots and inspect overlay placement before sending to user.
6. Explicitly mark failed cases and unresolved ambiguity; do not claim “all checked” without evidence.

## Current conclusion
Research artifacts exist; the display is NOT finished. Resume from frozen rules and raw OHLC, not from rejected visual output.
