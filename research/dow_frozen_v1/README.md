# Dow frozen v1 — research map

Main specification: [DOW_RULES_AND_ENGINE.md](./DOW_RULES_AND_ENGINE.md)

| File | Role |
|---|---|
| [dow_final_engine.py](./dow_final_engine.py) | Executable ATR7/ER20 ZigZag and relocation algorithm |
| [build_dow_final.py](./build_dow_final.py) | EURUSD chart-annotation-window export/reproduction |
| [dow_final_counts.csv](./dow_final_counts.csv) | EURUSD final counts by timeframe |
| [DOW_RULES_AND_ENGINE.md](./DOW_RULES_AND_ENGINE.md) | Parameters, logic, repaint/live cautions |

Status: frozen 2026-10-17. Applies to all symbols, W1/D1/H4/H1/M15. EURUSD validated only. Does not replace existing EA engines automatically. Do not use hindsight-relocated pivots as live signals.
