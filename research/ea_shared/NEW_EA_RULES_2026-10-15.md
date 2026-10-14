# 新EA — Entry/Exit Rule Snapshot (2026-10-15)

Status: research baseline / EURUSD M15 Early Phase only. H1 independent Stochastic strategy excluded.
Source engine: `research/ea_shared/engine_m15.py` (as of 2026-10-15). This document records the current **implemented** logic; it is not a claim of exact parity with live EA or original historical engine.

## Data / causal conventions
- Base: EURUSD M15; derive H1/H4 from M15. Completed H1/H4 candles available only from following time boundary.
- M15 stochastic raw %K: 14-period HH/LL; smoothed K = rolling mean(3); D = rolling mean(5) of smoothed K.
- H1 SMA20/75/200/480; ATR14. H1 SMA200 and SMA480 slopes computed as `SMA(t)/SMA(t-12 H1 bars)-1`. No SMA200 minimum slope magnitude threshold; **direction check remains**.
- M15 ATR14 and SMA200 for stop placement. H4 ATR14 and RSI14 are computed but H4 RSI rejection is OFF.

## H1 regime / trend
- Regime side is sign(SMA20-SMA75) on last completed H1. On a nonzero side change, reset P counts and stochastic state.
- Buy requires H1 SMA200 slope >= 0 and SMA200 >= SMA480 (zero ATR tolerance).
- Sell requires H1 SMA200 slope <= 0 and SMA200 <= SMA480 (zero ATR tolerance).
- MA expansion exception OFF.

## M15 stochastic signal and P
- BUY state: K<20 -> K crosses above D -> K crosses above 20 (with previous K <=20), in successive state transitions.
- SELL inverse: K>80 -> K crosses below D -> K crosses below 80.
- Completed signal must agree with H1 regime direction.
- P count is per regime and direction and consumed at completed signal time, **even when a later filter rejects it**.
- P1 and P2 permitted; P3 and beyond rejected before entry. This makes P3 MFE conditions inapplicable.

## Entry rejection filters
- q75 ON: trend strength = min(H1 SMA200 slope, SMA480 slope) for buy, and min(negative slopes) for sell. Per-direction past-history 75th percentile after 100 qualifying strengths; reject if current strength exceeds q75. Append current strength after test. (Implementation-defined rolling/global history: history accumulates.)
- MA ABCD rejection ON. Let P=close, A=H1 SMA20, B=H1 SMA75, C=H1 SMA200, D=H1 SMA480.
  - Buy reject if (P<C and P<D) or (A<C and A<D) or (P<C and A<C) or (P<D and A<D).
  - Sell reject with inequalities reversed.
- H4 horizontal levels OFF; H4 RSI OFF; H1 inverse-trend rejection OFF.
- Max simultaneous open positions: 2.
- No new entries during offline catch-up (live-operation policy; not modeled by this historical backtester).

## Entry price and exits (current research engine)
- Entry at signal-completion M15 close.
- Initial SL based on M15 SMA200 +/- 10 pips; enforce at least 10 pips risk. Buy SL = min(SMA200-10p, entry-10p); sell SL = max(SMA200+10p, entry+10p).
- Existing SL checked on M15 bars after entry; on touch exit at SL.
- Causal M15 ZigZag ATR14 x1.5; pivot usable only after confirmation. Trail activates at +2R OR position age >=240 hours; tighten stop toward latest confirmed opposite pivot, never loosen.
- Positions still open at end of dataset marked to last close.
- Backtest currently does not separately add spreads/commissions/slippage. Live safety spread/risk guards are not modeled here.

## ①–⑨ decisions
1. q75 reject ON.
2. MA expansion exception OFF.
3. H4 RSI reject OFF.
4. P3 entries OFF (not merely excluded in reports).
5. 240-hour delayed ZigZag ON; +2R trail ON.
6. MA ABCD reject ON.
7. H1 inverse-trend reject OFF.
8. H1 SMA200 minimum slope 0.00002 removed; sign test retained.
9. SMA200/480 relation 0.25 ATR tolerance removed; exact ordering required.

## Scope / reproducibility
- Use this frozen snapshot when discussing the **new EA**. Do not confuse it with the legacy all-ON/P3-inclusive baseline.
- Actual executed research code `final_research.py` and its trade CSVs are not yet committed; reported metrics were produced by a local reconstruction and must not be presented as an independently reproduced run of this GitHub file.
- This document records the strategy as currently implemented; future optimization should branch from this dated baseline.
