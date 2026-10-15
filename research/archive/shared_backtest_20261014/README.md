# Shared EA ablation research (2026-10-14)

## Current implementation
The shared code comprises `engine.py`, `runner.py`, and `fastpivot_patch.py`. The runner loads the local M1 ZIP, creates M15 and cached features, executes the engine, and writes trade, annual and period summaries. The seven ablations are independently selected by `--disable`: `q75`, `expansion`, `h4_rsi`, `p3_mfe`, `delayed_zz`, `ma_abcd`, `inverse_h1`. `--compare` launches a baseline and one ablation in separate processes, sharing the same feature cache. These are implementation descriptions, **not claims of end-to-end validation**.

## Frozen experiment design
- EURUSD M1 history from `EURUSD2003.M1.zip` (available data through October 2026), resampled to M15.
- H4 structural horizontal-level rejection OFF (`--h4 off`). This is NOT the same as H4 RSI filtering: H4 RSI remains ON in baseline.
- Maximum two concurrent open positions.
- Simulate P1/P2/P3 normally. For reported P1/P2 results, **filter completed trade history** using `--p p12`; do not disable P3 entries. The P3 impact on position availability remains. The reported P1/P2-only cumulative R and DD are *diagnostics on filtered trades*, not the actual account equity or DD when P3 positions also exist.
- Only the assigned one filter may change between A and B; use identical data, event sequencing and other rules.
- No look-ahead; bar completion/availability must be respected.

## Reproducible local command
Place `EURUSD2003.M1.zip` in a local directory, e.g. `/mnt/data`, alongside any generated cache under `/mnt/data/ea_cache`.

```bash
python research/shared_backtest_20261014/runner.py --pair EURUSD --h4 off --p p12 --disable expansion --compare --data-dir /mnt/data --tag exp02
```

Replace `expansion` with the specific assigned experiment filter. Python 3.11+, numpy, pandas, numba are required. Initial M1 processing may be expensive; future runs can reuse cached features. Outputs are written to `/mnt/data/ea_cache` as CSV and pickle. Runs with `--compare` spawn two independent subprocesses (baseline ON and condition OFF).

### IMPORTANT — GitHub connector vs. local Python
A GitHub connector's `fetch_file` returns source text to the chat but **does not automatically create a file** in the Python/container runtime. The raw M1 ZIP is not in GitHub. Before starting a full run, ensure the three source files exist in the actual Python runtime and that the ZIP is accessible under `--data-dir`. If git clone/network access fails, reconstruct the local source files from the GitHub connector's fetched text; use a connector/browser/runtime path that transfers those bytes. A comparison script merely committed to GitHub **does not constitute executing a backtest**. Never fabricate results.

## Experiment output and isolation
Each experiment should write its code and final output under `research/experiments/0X_.../`. Do not modify shared baseline or other experiments from parallel chats. Do not confuse all-trade simulation history with filtered P1/P2 performance reports. Require complete runtime logs, both ON/OFF trade histories, 2003+ and 2015+ tables, and annual metrics; no result is valid without executed code.

## Implementation limits
The engine is a reconstructed research baseline, not a certified live-EA equivalent. The shared runner has not been end-to-end regression-tested over the complete dataset. H4 structural caches are unnecessary with `--h4 off`. Historic preliminary EURUSD H4-OFF (P1/P2/P3 combined) results existed but are **not** substitutes for the new P1/P2 ablation measurements.
