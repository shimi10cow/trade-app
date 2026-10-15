# EURUSD M15 frozen input manifest (2026-10-15)

Status: **LOCAL CACHE VERIFIED; binary not committed to GitHub**.

- Source local path: `/mnt/data/EURUSD2003_M15_research.pkl`
- Shape: 583458 rows × 5 columns (`time,open,high,low,close`)
- First timestamp: 2003-05-06 00:00:00
- Last timestamp: 2026-10-12 23:45:00
- SHA256: `5659e567d6e39d924bafcb15b82998d58f5b1919ad6fe9123d226752d31f93b5`
- Input source: `EURUSD2003.M1.zip`; source timezone not independently verified.

**Do not assume the binary exists in a new chat/container.** GitHub connector can write UTF-8 text, but this session cannot transfer the 23 MB local binary into that connector. No backtest trade CSV has been regenerated or committed in this step.

## Reproduction contract
- Engine: `research/core/engine_m15.py` (Git blob SHA `c6e63fb029d405db97f5fe5b409ace89bf8f40a7`)
- Rules: `research/core/NEW_EA_RULES_2026-10-15.md`
- Use `EA_M15_CACHE=/mnt/data/EURUSD2003_M15_research.pkl` when running `run_pair('EURUSD', Config())`.
- Preserve every trade including `point`, `time`, `ExitTime`, `side`, `R`, `regime_id`.
- Reconcile count and totals with earlier 1,117-trade retrospective study **before claiming equivalence**; its historical engine and research baseline may differ.
- Next: join **P1-only** trade timestamps to causal D1/H4 ZigZag Dow and H4 MA features; report P1 n, win rate, PF, sum R and maxDD for full 2003–2026.
