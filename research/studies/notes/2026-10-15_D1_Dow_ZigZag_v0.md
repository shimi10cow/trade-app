# D1 Dow + causal ZigZag v0, full-period EURUSD (2026-10-15)

## Input and scope
Input local `h4_structure_bars.csv` (EURUSD 2003-05-06 through 2026-10-12), derived from original M1. D1 OHLC obtained by UTC-naive/calendar-day resampling of H4 OHLC. Broker session timezone not yet verified. 7,329 D1 bars, mapped as-of to 37,805 H4 bars.

## D1 Dow v0
Local pivot high: strictly greater than 2 preceding and 2 following daily highs; pivot low analog. **Only usable after the close of the second right-side daily bar**, not on pivot date. Counted 1,999 confirmed high/low pivots. Compare most recent 2 confirmed highs and 2 confirmed lows: up if both higher; down if both lower; mixed otherwise; unconfirmed until sufficient history. D1 day-state counts: up 2,409, down 2,285, mixed 2,615, unconfirmed 20. H4 mapping uses most recent available D1 state as of H4 bar opening.

## D1 ATR ZigZag v0 exploratory
Daily ATR14 (simple mean of true range); swing turn confirmed after price reverses by 1.5 * **prior-day ATR** from running high/low. 1,351 confirmed turns; median confirmation lag 2 daily bars. This is a **separate experimental D1 ZigZag**, not the production M15 trailing ZigZag. Intrabar order cannot be reconstructed from D1 OHLC; exact same-bar reversal handling and initial state must be checked against M1 data before using as EA entry feature.

## Local output files (not uploaded to GitHub)
- `/mnt/data/d1_study_20261015/d1_structure_bars.csv`
- `/mnt/data/d1_study_20261015/d1_confirmed_pivots.csv`
- `/mnt/data/d1_study_20261015/d1_atr_zigzag_confirmed.csv`
- `/mnt/data/d1_study_20261015/h4_with_d1_dow_state.csv`

## Next work
1. Validate D1 calendar timezone and causal available_at against actual M15 P1 entry timestamps.
2. Add D1 confirmed Dow pivot wave ordinal, swing age, swing ATR magnitude and reversal lag; keep Dow and ATR ZigZag separate.
3. Join D1 + H4 features to **actual original P1 trade rows**, preserving original entries/exits. The original P1 trade list is not yet available in current runtime/GitHub, so P1 win rate/PF cannot be computed yet.
4. Independently characterize all H4 impulse waves (MFE, duration, retracement) without selecting only profitable P1 signals.
5. Do not introduce D1 rejection filter or change live EA before validation.
