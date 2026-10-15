# EURUSD H4 confirmed-pivot structure: preliminary empirical check (2026-10-15)

Source: `research/datasets/derived/eurusd_h4_structure/2026-10-15/` (3 CSVs verified on GitHub); locally executed on identical named CSV files.

## Method
37,805 H4 bars (2003-05-06 to 2026-10-12), 10,590 confirmed pivots (5,281 highs, 5,309 lows). A pivot is available only after two subsequent completed H4 bars (per dataset generation script). For each H4 bar, merge the most recent **available** high and low pivots, each compared with its preceding same-type pivot. Bullish = both higher; bearish = both lower; otherwise unclassified. Forward six-H4-bar signed close-to-close return divided by contemporaneous ATR14. Trend age counts contiguous classified H4 bars, reset on direction/unclassified state change.

**This is NOT an EA trade backtest**; overlapping forward windows, no costs, and the H4 bar-close timing convention must be checked against entry timestamps.

## Empirical results
23,659 classified H4 observations (62.58% of all H4 bars).

| Contiguous classified age (H4 bars) | Observations | Mean signed 6-bar return / ATR | Fraction positive |
|---|---:|---:|---:|
| 1–3 | 7,265 | -0.077 | 48.7% |
| 4–6 | 5,295 | -0.055 | 48.5% |
| 7–12 | 5,773 | +0.006 | 50.3% |
| 13–24 | 4,180 | +0.039 | 49.0% |
| 25–48 | 1,106 | +0.152 | 49.5% |
| 49+ | 40 | -0.485 | 42.5% |

| Period | Observations | Mean signed 6-bar return / ATR | Fraction positive |
|---|---:|---:|---:|
| 2003–2014 | 11,778 | -0.041 | 48.5% |
| 2015–2020 | 6,043 | +0.060 | 50.9% |
| 2021–2026 | 5,838 | -0.067 | 48.5% |

Overall mean -0.0215 ATR; positive 49.13%.

## Interpretation and next test
Simple confirmed HH+HL / LH+LL classification does **not** independently demonstrate an exploitable edge; differences by trend age are modest and nonstationary across eras. Do not promote this filter to EA production.

Next: join causal H4 features as of each original EA entry timestamp (not after); segment 359 and 284 trades by wave maturity, H4 pivot sequence and breakout quality; calculate wins/losses, R, PF, DD and year split; then rerun same engine ON/OFF with unchanged risk, spread and exit assumptions. Avoid optimizing age thresholds on the full sample.
