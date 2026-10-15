# EA DD Research — Wave maturity reference (2026-10-15)

Status: **Exploratory, retrospective classification only. NOT a validated live filter.**

Scope: EURUSD 2003–2026, 1,117 existing P1/P2 trades; +132.065R overall, PF ~1.185, maxDD ~-53.6R. These statistics are not ON/OFF EA reruns. The wave indicators use confirmed H1/H4 swing pivots (two right-side completed bars); this differs from the live EA ZigZag. No future pivots are allowed in feature construction.

## Key finding
- H4 impulse maintained/expanded (latest prior confirmed impulse >=70% of preceding impulse) AND H1 impulse contracted (<75%): **359 trades, +100.531R, PF 1.452 (recalculated from trade-level detail; previous 1.544 was incorrect)**.
- Add H1 SMA480 distance <12 H1 ATR: **284 trades, +105.664R, mean +0.372R, PF 1.614, win rate 39.1%**.
- Same wave state with SMA480 distance >=12 ATR: **75 trades, -5.133R, PF 0.898**.
- 284 trades over approximately 24 calendar years = about 11.8/year, not a guaranteed annual rate or independent EA trading frequency.

## Full wave x MA480 distance table
| H4 impulse weak | H1 impulse weak | SMA480 >=12ATR | n | Sum R | PF |
|---|---|---|---:|---:|---:|
| No | No | No | 381 | +48.066 | 1.203 |
| No | No | Yes | 69 | -3.564 | 0.924 |
| No | Yes | No | 284 | +105.664 | 1.614 |
| No | Yes | Yes | 75 | -5.133 | 0.898 |
| Yes | No | No | 160 | -3.303 | 0.969 |
| Yes | No | Yes | 37 | -13.761 | 0.510 |
| Yes | Yes | No | 98 | -0.793 | 0.988 |
| Yes | Yes | Yes | 13 | +4.888 | 1.659 |

## Other findings to retain
- H4 impulse <70% and H4 correction >60% of impulse: 290 trades, -19.45R, PF 0.902; year-block bootstrap 95% CI for mean-R contrast [-0.480, -0.004]R, exploratory/multiple-testing caveat.
- H4 impulse <70% + deep correction + SMA480 >=12ATR: 47 trades, -11.49R, PF 0.667.
- H4 maintained + deep correction: 542 trades, +141.75R; deep correction alone should not be rejected.
- H4 weak + H1 maintained: 197 trades, -17.06R; P1 125 trades -23.01R vs P2 72 trades +5.95R.
- H4 weak + H1 weak: 111 trades +4.10R; P1 67 trades +14.46R vs P2 44 trades -10.36R.
- H4 weak with most recent confirmed H4 swing 3–7 days old: 23 trades, -13.58R, PF 0.285. This is age since *last confirmed swing*, not age since trend inception.
- Earlier causal pre-entry 6h analysis: 1–2 ATR move *against* entry side: 324 trades +78.51R, PF 1.389; >1 ATR move *with* entry side: 49 trades -9.77R, PF 0.686. MA480 distance changes the result.
- SMA480 >=12ATR overall: 194 trades, -17.57R. This does NOT explain all DDs (e.g., 2009–2010 DD without such trades).
- P1 unrealized loss alone is not a valid P2 rejection: 216 P2 trades +54.38R, PF 1.410; combined with SMA480 >=12ATR: 41 trades -11.51R, PF 0.614.

## Interpretation / next research
Hypothesis: A preserved H4 impulse with a smaller H1 impulse can represent a favorable pullback, especially without extreme SMA480 overextension. However, this may be data-mined and may not generalize. Study H1 reacceleration under H4 weakness, actual H4 trend age (not pivot age), P1/P2 trade correlation, and distinct sideways-market DD mechanisms. Then perform locked-rule ON/OFF reruns in the shared EA engine, with chronological out-of-sample testing, costs, concurrent risk, annual stability, PF, total R and maxDD. No EA rules changed.

## Source artifacts (local research files; not all committed)
- DD_wave_h1_h4_interaction.csv
- DD_wave_age_interaction.csv
- DD_wave_pullback_interaction.csv
- DD_wave_point_interaction.csv
- DD_wave_episode_interaction.csv
- DD_wave_interaction_year_bootstrap.csv
- DD_causal_wave_maturity_summary.csv
- DD_causal_wave_maturity_trades.csv
- dd_wave_interaction_followup.py
- dd_causal_wave_maturity.py

Recorded 2026-10-15.
