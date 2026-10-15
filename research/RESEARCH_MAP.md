# EA Research Map — Start Here

Updated: 2026-10-15. **Canonical navigation entry for future AI sessions.**

## Research notes
- `research/notes/2026-10-15_EURUSD_DD_wave_maturity_reference.md`: 1117-trade retrospective DD study; corrected 359-trade PF 1.452, 284-trade PF 1.614. Not independently backtested.
- `research/notes/2026-10-15_EURUSD_price_structure_research_plan.md`: H4/H1 swing, horizontal level, time-width hypotheses and data preparation.

## EA logic (inspect source before running)
- `research/ea_shared/engine_m15.py`: shared M15 research engine.
- `research/ea_shared/run_compare.py`: ON/OFF comparison runner.
- Do not assume research fractal pivots are identical to live ZigZag.

## 2026-10-15 aggregated data
Local session generated (not yet committed to GitHub):
- `/mnt/data/ea_research/h4_structure_bars.csv`: 37,805 H4 OHLC/ATR/structure rows, ~4.9 MB.
- `/mnt/data/ea_research/h4_confirmed_pivots.csv`: 10,590 confirmed H4 fractals, ~542 KB; `available_at` prevents future use.
- `/mnt/data/ea_research/h4_annual_structure_summary.csv`: 24 annual rows.
- `/mnt/data/ea_research/structure_study_20261015.py`: reproducible source script. Input: `/mnt/data/EURUSD2003.M1.zip`.

**Availability warning:** /mnt/data paths are session-local, not GitHub-backed or persistent across chats. The large CSV files have NOT been uploaded; do not report otherwise. Restore from source ZIP with script if absent, or upload through a Git-capable local runtime. The GitHub connector cannot access the local filesystem directly. Do not infer data presence from this map.

## Data checksums (SHA256)
- h4_structure_bars.csv: `eb0dfd033f6b7113e768c67ce65209483541eb3d375403b3eb75c18c30177e3e`
- h4_confirmed_pivots.csv: `7258deb703f7c79149ae3dce0a6169bc5e2ca494647b0497c1f839f0b517df02`
- h4_annual_structure_summary.csv: `d014d05d1dbbffd94b9697027a3d031ea3ec31a3ae80561f649d21b6ae40439b`
- structure_study_20261015.py: `4bd8ab7a9142328d8c361b8b6bba89559c4a20d5c8bd11a67c071fecdc2d3750`

## Next
Persist the four generated files to `research/data/eurusd_h4_structure/2026-10-15/` and update this map to mark them committed; verify file hashes. Then link 1117 trade ledger by entry timestamps for year-by-year, wave-cluster and structural analyses. No new PF/DD claims until joined.
