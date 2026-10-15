# Reusable EURUSD M15 research cache

## Status (2026-10-15)
The chunked M1→M15 generator has been run locally on EURUSD2003.M1.zip:
8,602,190 M1 rows → **583,458 M15 bars**, 2003-05-06 00:00 through 2026-10-12 23:45.
The actual binary cache is an artifact, **not committed to GitHub**. A new chat/container cannot assume /mnt/data/ea_shared/EURUSD2003_M15.pkl exists. Attach/upload the cache if absent.

## Data contract
DataFrame columns: time (naive source-time datetime), open, high, low, close. OHLC is aggregated by 15-minute floor; no future bars. The source timezone is unknown and deliberately not converted.

## Usage
```bash
python research/ea_shared/cache_m15.py --source /mnt/data/EURUSD2003.M1.zip --output /mnt/data/ea_shared/EURUSD2003_M15.pkl
```
Before generating, **check whether a valid M15 cache already exists**. Do not rebuild it if it exists.

## Canonical engine caveat
`research/full_backtest_engine_v1_20261014.py` exists but presently reads legacy CSV paths (`{pair}2020.M15.csv`) and H4 structural-level files. It does **not** automatically consume this pickle and should not be described as a tested ready-to-run cache-backed runner. To use it, implement a data adapter, explicitly set all seven decisions, verify P3 is prohibited at entry, and compare results against a frozen baseline. The canonical code is a 2026-09-23 reconstruction and may differ from production EA.

## Frozen intended experiment configuration
M15 Early Phase only; q75 ON; MA expansion exception OFF; H4 RSI rejection OFF; P3 MFE irrelevant (P3 entry OFF); 240h delayed ZigZag ON with +2R normal trigger retained; MA ABCD rejection ON; H1 countertrend rejection OFF; H4 horizontal levels OFF; max simultaneous positions 2.

A1: SMA200 minimum slope 0.00002 vs zero (direction retained).
A2: SMA200/480 ATR tolerance 0.25 vs zero (MA ordering retained).
Run ON/OFF with the *same* engine, data, and all other parameters fixed. Save annual and full/2015+ trade metrics plus individual trades. Do not combine the effects of separate ON/OFF experiments arithmetically.
