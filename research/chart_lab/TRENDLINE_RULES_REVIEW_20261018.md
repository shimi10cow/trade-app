# Trendline rules cross-check — 2026-10-18

## Verified source of truth
- Generation / 2-point reanchoring / 3-point selection: `research/chart_lab/TRENDLINE_RULES.md` (approved 2026-10-17).
- Causal generation implementation: `research/chart_lab/trendline_causal_engine.py`.
- Frozen Dow pivot implementation: `research/dow_frozen_v1/dow_final_engine.py`.
- Causal Dow/protected-swing specification: `research/dow_frozen_v1/DOW_RULES_20261018.md`.

## Approved two-point construction (preserved; do not replace with guesses)
- Connect only consecutive confirmed same-kind Dow pivots: higher lows or lower highs, regardless of major trend direction.
- Original pivot A–B separation >=15 completed bars. No upper limit.
- If any intervening wick violates the outer side of A–B, iteratively move A to offending wick extreme C and redraw C–B until clear. Keep only corrected C–B; C need not be a Dow pivot. Minimum-gap test applies to original A–B.
- No ATR intrusion filter for two-point lines. Pivot confirmation/relocation can create/revise candidates.

## Approved three-point construction
- Three consecutive same-kind pivots, successive movement >=0.12 ATR; adjacent gaps >=4 bars and <=75 W1 / 95 D1 / 115 H4 / 145 H1 / 175 M15.
- Draw first–third; middle deviation <=0.85 ATR; >0.35 ATR close intrusion on <=10% of intervening bars; max intrusion <=1.7 ATR; normalized slope 0.25–7.
- Suppress near duplicates using the thresholds and score recorded in TRENDLINE_RULES.md.

## Retirement rules clarified in user discussions 2026-10-18 (separate from generation)
- Each line must be tracked bar by bar, from its actual known-at creation/revision event. Do not use future-confirmed pivots retroactively.
- Downward-sloping resistance line: on upside close break, count two subsequently confirmed Dow LOW events; retire when second is confirmed, regardless of relative low prices.
- Upward-sloping support line: on downside close break, count two subsequently confirmed Dow HIGH events; retire when second is confirmed, regardless of relative high prices.
- User also specified that when a break fails and price returns inside, a subsequent fresh break can restart the count. Avoid an eternal line due to reset behavior.
- Independently retire when the Dow trend epoch to which a line belongs actually ends, including corrective trendlines that run counter to the major Dow trend. Retire at whichever condition occurs first.
- A line may be valid during the most recent unfinished trend. Historical retired line segments remain visible but stop exactly at their retirement bar, not the viewport right edge. Never extend indefinitely due to unknown/missing trend association.
- Use the SAME frozen causal Dow pivot events and their known-at timestamps for both trendline construction and retirement; do not introduce a separate ATR-based swing detector.
- For audit, record line ID, generation time, revisions, break/rebreak events, counted pivot confirmations, Dow trend changes, retirement reason/time, and inspect all H4 lines. No claim of zero stale lines without actual replay verification.

## Important distinctions / open verification
- The 2026-10-17 TRENDLINE_RULES.md describes construction, not a completed causal retirement engine. Its 'current implementation gaps' section contains historical notes and may be stale; inspect the code, not only that section.
- Frozen retrospective Dow final pivot list may repaint; causal pivot_events() must be parity-tested for relocations and known-at behavior.
- The prior Complete HTML uses retrospective embedded line sets and must not be treated as proof of causal correctness.
- This document records agreed rules, not a claim that a verified working implementation or all-line zero-stale audit exists.
