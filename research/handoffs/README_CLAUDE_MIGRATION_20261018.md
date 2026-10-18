# Claude Code EA research migration (2026-10-18)

## What has been done
- Collected 100 research files into `EA_Claude_handoff_research_20261018.zip` (about 16MB compressed, 69,101,095 bytes uncompressed).
- Created `research/handoffs/CLAUDE_EA_RESEARCH_20261018.md` describing methodology, findings and caveats.
- Added `import_claude_bundle_20261018.py` to extract all 100 files into the repository, preserve relative paths and generate a SHA-256 manifest.

## What is **not** done
- The 100 data/code files are **not uploaded** by this commit. A GitHub connector cannot read the local archive, and the local execution environment has no outbound network.
- No historical M1 ZIP (EURUSD / USDJPY, each around 100MB) is in the 100-file bundle.
- Not every historical source script is in the bundle; there are 4 Python scripts in the archive. Check dependencies before running any backtest.
- GitHub code parity and reproducibility of every reported result have not been independently validated.

## How to finish the GitHub upload on your Windows machine
1. Download the research ZIP linked in the ChatGPT conversation.
2. Clone `https://github.com/shimi10cow/trade-app` or open an up-to-date local clone.
3. Run:
```powershell
python research/handoffs/import_claude_bundle_20261018.py "$env:USERPROFILE\Downloads\EA_Claude_handoff_research_20261018.zip"
git add research/handoffs/ea_bundle_20261018 research/handoffs/import_claude_bundle_20261018.py research/handoffs/README_CLAUDE_MIGRATION_20261018.md
git commit -m "data: import EA research artifacts for Claude handoff"
git push origin main
```
4. Inspect `research/handoffs/ea_bundle_20261018/MANIFEST.json`: exactly 100 entries and SHA-256 hashes.
5. If large raw history is required, use separate storage or Git LFS; do not accidentally commit it to the normal repository.

## Analysis history / key datasets
- Baseline EURUSD M15: 436 historical trades, 2003–2026; SMA200 SL and +1.5R ZigZag trailing.
- Wave-SL vs SMA200-SL diagnostics and matched trade tables.
- M15 pullback duration, rebound strength, retests and H4 Dow alignment.
- H4 opposed 44-trade breakout split and 436-trade H4 breakout/pullback exploration.
- Entry hour and daypart analysis in *provisional* JST (source timezone not verified).
- H4/D1 causal structure and pivot studies.
- EA experiments on spread, P1/P3, trailing, position cap and trend phases.

## Cautions
These are exploratory post-hoc comparisons, **not** confirmed causal filters. Re-run full EA when changing filters, including occupancy effects. Confirm source timezone, spread, stochastic parameters, pivot lookahead, SL and trailing definitions, and P3 treatment. Historical M5 and M15 price series may differ. Avoid claiming results are reproduced until a clean run matches the trade ledger.
