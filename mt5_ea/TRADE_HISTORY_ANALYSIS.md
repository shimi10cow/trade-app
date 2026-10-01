# REAL Trade History Analysis

Read-only research tool for the user's actual MT5 trading history. It is intentionally separate from the live EA and the app UI.

## What it does

1. Reads every enabled dedicated MT5 account in `mt5_accounts.json`.
2. Pulls closed deal history (default: 10 years).
3. Reconstructs MT5 positions and merges nearby split/continuous positions into analysis Trade Groups.
4. Reads the app's `Entries` through the existing GAS `getEntries` endpoint.
5. Uses only app rows whose status is exactly `決済`; `決済（見逃し）` is excluded.
6. Loosely enriches MT5 Trade Groups with app context (DowRule, TL, H1/H4 MA judgement, session, reviews).
7. Reconstructs H1 market features at the actual MT5 entry time (MA20/75/200/480, slopes, ATR14, Stochastic).
8. Excludes only quick **and** no-move trades. A quick trade with a meaningful loss remains in the analysis.
9. Produces local JSON + CSV. It does not write to MT5, GAS, or the app.

## Safety

`mt5_history_worker.py` contains no order-send or position-modification call. Each terminal is locked to the configured login/server before history is read. The live EA process is not imported or switched.

## First run

The eight dedicated terminals must already exist and be logged in (the same setup used by `verify_mt5_accounts.py`).

```powershell
cd mt5_ea
py verify_mt5_accounts.py
py trade_history_analysis.py
```

Useful options:

```powershell
py trade_history_analysis.py --years 10
py trade_history_analysis.py --group-gap-hours 24
py trade_history_analysis.py --min-samples 10
py trade_history_analysis.py --no-features
```

Outputs:

- `analysis_output/master_trades.csv`: one row per analysis Trade Group.
- `analysis_output/trade_analysis.json`: overall and factor-level statistics.

## Defaults that are intentionally adjustable

- Split-position grouping: same account + symbol + direction, overlapping or within 24 hours.
- Quick/no-move exclusion: holding < 15 minutes AND absolute move < 3 pips AND absolute P/L < JPY 1,000.
- App matching: same pair + direction, within 4 calendar days. MT5 remains authoritative for exact entry/exit times and P/L.
- Minimum bucket size: 5 trades.

These are research defaults, not trading rules. Review the first generated `master_trades.csv` before interpreting factor results.
