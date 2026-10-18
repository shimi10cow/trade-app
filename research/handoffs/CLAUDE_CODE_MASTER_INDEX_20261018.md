# Claude Code research migration master index — 2026-10-18

Repository: shimi10cow/trade-app
Status: research handoff, not proof of full reproducibility or live-readiness.

## Start here
1. research/CLAUDE_CODE_HANDOFF_20261018.md — authoritative Dow/trendline/zone specification and outstanding verification.
2. research/dow_frozen_v1/DOW_RULES_20261018.md and dow_final_engine.py — frozen causal pivots.
3. research/chart_lab/TRENDLINE_RULES.md and TRENDLINE_RULES_REVIEW_20261018.md — construction and latest retirement rules.
4. research/chart_lab/specs/2026-10-18_dow_horizontal_zones_rules.md — horizontal zones.
5. research/handoffs/CLAUDE_EA_RESEARCH_20261018.md — separate historical EA research and missing bundle warning.
6. research/core/NEW_EA_RULES_2026-10-15.md and research/results/ — experiments and outcomes.
7. research/archive/ — legacy experiments, not automatically authoritative.

## Distinct workstreams
A. Discretionary market structure: causal W1/D1/H4/H1/M15 Dow; protected lows/highs; provisional trends; W top/bottom; zones; two/three-point lines and lifecycle. Current priority is D1 chronology and visual alignment. Never use retrospectively known pivots as real-time signals. Do not call the v9 zones or HTML overlays validated.
B. Earlier trend-following EA: H1 SMA200/480 and 24h SMA480 slope, M15 Stoch 14,3,3; P1/P2, variable P3 accounting, P5 prohibited; SMA200-based SL with 10-pip buffer/minimum; ZigZag ATR14 x1.5 trailing after +2R in the older baseline. Some later 436-trade research uses +1.5R: do NOT merge these variants.
C. Experimental entry filters: q75, MA ABCD, H1 inverse trend, H4 horizontal levels, H4 RSI, delayed ZigZag, H4 opposed breakout, time of day and wave maturity. Only compare within identical engines and datasets, reporting configuration hashes and all fills.

## Historical numbers — reported, not freshly reproduced
2015–2026 simple multi-symbol: 1,974 trades, +359.6R, PF 1.308, max DD -42.3R.
H4 96h+25pt variant: 1,681 trades, +327.41R, PF 1.332, DD -34.84R.
Earlier EURUSD 2003–2026 M15 derived cache: 583,458 bars (not assumed present in repository).
Earlier H1 inverse trend ON/OFF: +177.10R vs +176.70R (verify exact test source).
MA ABCD removal in 2015+ reportedly reduced R by 14.20R (verify).
Another research branch: 436-trade baseline, with different trailing threshold. See research/handoffs/CLAUDE_EA_RESEARCH_20261018.md.
User-reported recent performance: 272 trades, +72.86R, +0.268R/trade, PF 1.456, max DD -11.12R. Provenance/configuration NOT established; do not attribute to an engine without matching ledger.

## Non-negotiable validation
- Preserve old versions and trading-app functionality; work on a feature branch.
- Verify that every referenced file actually exists, and log missing artifacts.
- No lookahead: store anchor time, confirmation time, activation time, revision time and invalidation time.
- Pivot relocation is not a new pivot. Trendline break retirement requires two UNIQUE subsequently confirmed pivots of the appropriate kind, reset on close back inside.
- For major-trend reversal, retain and archive the broken protected level as a zone event. Existing historical zones must not shift retroactively.
- Backtest same engine/data for ON/OFF; changing position occupancy requires full rerun, not ledger row deletion.
- Record spread/slippage, time zone, symbol pip size, input hashes, config, date ranges, trade count, sum R, PF, DD, win rate, annual breakdown, long/short, trade ledger.
- Explicitly distinguish agreed specification, implemented code, passed test, exploratory result, and unresolved bug.
- Never claim raw ZIP/PKL/CSV files are in GitHub without checking their paths.

## Claude Code first tasks
1. Read all documents above and build a file inventory with SHA/size and broken-link report.
2. Execute frozen Dow tests and independent chronological D1 replay; compare activation times and price coordinates, not just end-state plots.
3. Audit zone geometry, candle alignment and event lifecycle. Do not substitute static retrospective HTML overlays.
4. Reproduce each selected backtest from a frozen engine and exact input ledger; flag missing data rather than inventing results.
5. Produce a machine-readable experiment registry (experiment ID, engine SHA, data hash, settings, result path, status).
6. Only after reproducibility and structural correctness, evaluate additional filters or live EA behavior.

## Safety
No live trading authorization. Preserve DRY_RUN=True and LIVE_ARMED=False unless the user explicitly approves a separate deployment change. Do not commit credentials, broker account secrets, tokens or private data.
