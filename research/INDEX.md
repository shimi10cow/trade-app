# EA Repository Navigation — canonical index

Updated 2026-10-15. Read this file FIRST. This is a navigation specification; not all proposed folders have been migrated.

## Status categories
- **ACTIVE**: currently intended for use; validate latest commit and config before execution.
- **REUSABLE DATA**: immutable source or derived datasets with generation metadata.
- **RESEARCH**: exploratory hypotheses, reports, scripts, not production logic.
- **LEGACY**: retained for reproducibility, never silently substituted for ACTIVE.

## Existing paths (verified)
| Status | Path | Purpose |
|---|---|---|
| ACTIVE research | `research/ea_shared/engine_m15.py` | shared backtest engine (verify code/config) |
| ACTIVE research | `research/ea_shared/run_compare.py` | comparison runner |
| RESEARCH | `research/notes/2026-10-15_EURUSD_DD_wave_maturity_reference.md` | retrospective 1117 trade analysis, 284-trade subset |
| RESEARCH | `research/notes/2026-10-15_EURUSD_price_structure_research_plan.md` | H4/H1 structure hypotheses |
| REUSABLE DATA | `research/data/eurusd_h4_structure/2026-10-15/h4_annual_structure_summary.csv` | uploaded annual H4 aggregates |
| REUSABLE CODE | `research/scripts/structure_study_20261015.py` | H4 dataset generation |
| LEGACY | `research/full_backtest_engine_v1_20261014.py` | old engine; do not use by default |
| NAVIGATION | `research/RESEARCH_MAP.md` | earlier research index, including upload status |

## Not uploaded yet
`h4_structure_bars.csv` and `h4_confirmed_pivots.csv` are local-only and should be uploaded to `research/data/eurusd_h4_structure/2026-10-15/`. Do not assume GitHub contains them.

## Target layout (proposed, NOT migrated)
```
research/
  INDEX.md                # this navigation map
  core/                   # stable reusable research engine and configs
  datasets/
    source/               # raw immutable market data (large datasets may live outside Git)
    derived/              # reusable H1/H4 features with lineage and hashes
  studies/
    YYYY-MM-DD_topic/     # hypotheses, notebooks/scripts, results, trade lists
  archive/                # superseded prototypes and historical scripts
```

## Safety for migration
Do not bulk-move production files or modify EA logic. First map references/imports, then move with compatibility shims or adjust imports, verify tests, and archive rather than delete. Record source date, timezone, bar-close convention, pivot confirmation lag, input hashes, script version and completeness for every dataset. The 284-trade subset is retrospective, not independently EA-tested.
