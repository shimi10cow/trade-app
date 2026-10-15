## CRITICAL AUDIT WARNING (2026-10-15)
The original feature generator `research/ea_shared/dd_causal_wave_maturity_20261015_original.py` was archived. Its `build()` routine replaces the most recent same-direction pivot in the final historical event list when a later more-extreme pivot is confirmed. That **can retroactively erase an earlier pivot from the event history**, affecting feature values for entries before the replacement was known. The two-right-bars pivot confirmation by itself is insufficient to guarantee point-in-time causality. **All 359/284 subset metrics are provisional and must be recomputed with a time-causal event replay before any strategy decision.** Do not use these numbers to claim an out-of-sample or future-leakage-free edge. The full original per-trade feature CSV, 284/359 trade detail CSVs, and raw OHLC cache are NOT yet in this GitHub folder.

# EURUSD wave-maturity research results — 2026-10-15

**Research only. No live EA rule change.** The source study uses 1,117 EURUSD P1/P2 trades from 2003–2026, and retrospectively tags the entry context. This is **not** an ON/OFF rerun of the EA, and closed-equity maxDD is **not** intratrade floating DD.

## Files in this folder
- `DD_wave_subset_performance_20261015.csv`: wins, losses, PF, sumR, closed-equity maxDD, loss streak, etc. for 359 and 284 trades.
- `DD_wave_h1_h4_interaction.csv`: all eight H4/H1 weakness x MA distance groups.
- `DD_wave_annual_284.csv` and `DD_wave_annual_359.csv`: annual counts and R.

## Exact selection
For each original trade, calculate entry-time causal H4 and H1 **confirmed pivot impulse ratios** (most recent confirmed directional impulse / previous confirmed directional impulse), with 2 right-hand completed bars to confirm each pivot. Use only pivots confirmed before entry.
- 359 subset: `h4_impulse_ratio >= 0.70 AND h1_impulse_ratio < 0.75`.
- 284 subset: same, plus `d480 < 12` (precomputed SMA480 distance in ATR units). 
- Source: `DD_causal_wave_maturity_trades.csv` (derived from `DD_structure_trade_detail.csv` and M15 OHLC `EURUSD2003_M15.pkl`). The pivot-generation source was `dd_causal_wave_maturity.py`; further interaction analysis was `dd_wave_interaction_followup.py`. **These upstream inputs and scripts are not all committed here**, so this folder is not a fully self-contained end-to-end rebuild from raw M1.

## Reproduce subset summary and annual files
```bash
python research/ea_shared/reproduce_wave_subset_20261015.py --input /path/to/DD_causal_wave_maturity_trades.csv --out /path/to/output
```
The script also emits full subset trade CSVs locally. Reproducibility requires the exact upstream 1,117-trade feature CSV and entry-time feature definitions. Do not regenerate from a different EA version and expect exact matching results.

## Calculation
- Wins: R > 0; losses: R < 0; PF = sum(positive R) / abs(sum(negative R)).
- Closed-equity DD: sort subset by `exit_time` then `time`, cumulative sum of R starting at 0, subtract running maximum including initial zero; take minimum.
- Annual table: **entry year**, not exit year. 
- 359: 135W/224L, +100.531R, PF **1.451775** (corrected; previously quoted 1.544 was inconsistent with trade-level recomputation), closed-equity maxDD −17.561R.
- 284: 111W/173L, +105.664R, PF **1.613828**, closed-equity maxDD −14.412R.
- Around 24 calendar years, 284 / 24 = 11.83 entries per year. 2007 is unusually strong and may drive much of the result.

## Caveats
Post-hoc threshold exploration; data-snooping risk. P1/P2 can overlap and share risk. Pivot algorithm differs from EA production ZigZag. Validate with a fixed-rule chronological out-of-sample test, then an actual shared-engine ON/OFF backtest, and examine simultaneous open risk and floating DD before deployment.

**Source note**: Existing research note at `research/notes/2026-10-15_EURUSD_DD_wave_maturity_reference.md` quotes PF 1.544 for 359 trades; **this folder's recalculated PF 1.451775 supersedes it**.
