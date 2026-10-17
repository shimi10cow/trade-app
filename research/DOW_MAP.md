# Research map — Dow swing detection

## Frozen baseline (2026-10-17)
- [Dow v1 module map](./dow_frozen_v1/README.md)
- [Complete rule and engine specification](./dow_frozen_v1/DOW_RULES_AND_ENGINE.md)
- [Executable engine](./dow_frozen_v1/dow_final_engine.py)
- [EURUSD reproduction runner](./dow_frozen_v1/build_dow_final.py)
- [Final EURUSD per-timeframe counts](./dow_frozen_v1/dow_final_counts.csv)

This is a standalone research module, not an automatic replacement of the EA live/backtest engine. ATR cap OFF, high/low relocation ON; same algorithm across symbols and W1/D1/H4/H1/M15. EURUSD-only manual validation. Repainting means historical pivot positions cannot be used as if known in real time.

For live EA integration, add event-time snapshots and explicit confirmation timestamps before enabling signals.
