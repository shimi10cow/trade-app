# Verification conditions, engines and result provenance — 2026-10-18

## 1. What was actually tested (D1 Dow horizontal protected levels)
- Instrument: **EURUSD**.
- Timeframe: **D1**. The latest extracted embedded chart dataset contained **3,095 D1 candles**. Confirm exact start/end from data at runtime; the current documentation does not establish dates precisely.
- Source: D1 OHLC parsed from `const SERIES=` in historical `dow_handoff/eurusd_d1_complete_protected_review.html`; **only OHLC was reused**, not its old Dow lines, boxes or overlays. This is not the original M1 ZIP.
- Causal pivot detector: `research/dow_frozen_v1/dow_final_engine.py`; event-sourced adapter `dow_handoff/dow_frozen_causal_v1.py` (ZIP, not yet in GitHub).
- Protected-line state machine: `research/dow_migration_20261018/artifacts/d1_rebuild.py` (in GitHub, **experimental**).
- Chart UI template: `research/chart_lab/eurusd_chart_lab_complete.html` (**layout only**).

### Frozen recognition parameters
| TF | ATR period | ATR multiplier | ER period | ER threshold | Multiplier boost if ER threshold met |
|---|---:|---:|---:|---:|---:|
| W1 | 7 | 1.9 | 20 | 0.40 | +15% |
| D1 | 7 | 1.9 | 20 | 0.40 | -15% |
| H4 | 7 | 2.0 | 20 | 0.40 | +30% |
| H1 | 7 | 2.4 | 20 | 0.25 | -15% |
| M15 | 7 | 2.1 | 20 | 0.25 | +30% |

`TR=max(high-low,abs(high-prev_close),abs(low-prev_close))`; ATR=EWMA(alpha=1/7, adjust=False); `ER20=abs(close[t]-close[t-20])/sum(abs(close[j]-close[j-1]) for j=t-19..t)`. `threshold=ATR * multiplier * (1+boost if ER>=cutoff else 1)`. Adapter's default `start=60` (warmup; verify implications), process one bar at a time; high/low pivots alternate. A pivot is only usable at `known_at`, which may be later than `anchor_time`. Track relocations.

### D1 protection logic held fixed
- Trend break: candle **CLOSE** beyond prior Dow pivot **WICK** (not whole body).
- In uptrend, new high breakout can advance protected low only to an already confirmed, corresponding low of that leg; if not yet confirmed, retain existing level. Late-confirmed low can be applied at confirmation time only if it was anchored before the breakout and belongs to the correct leg. Mirror for downtrend.
- Check active protected level for CLOSE-based reversal on **every candle**, including pivot event candles.
- On update or reversal, close previous active line at the event time. Preserve its bounded historical segment for chart history; do not show it as still current.
- **Known risk:** experimental state machine does not reliably redraw active line when same pivot_id is relocated, and leg-association correctness has not been independently proven.

## 2. Reported outputs and what they mean
| Artifact | Reported observation | What was / was not proven |
|---|---|---|
| `D1_rebuild_events.csv` | 377 pivot recognition events (includes 26 relocations), 37 reversal events | Event trace of this implementation, not an independent oracle |
| `D1_rebuild_lines.json` | 95 line segments, 57 protection updates reported | Segments produced by experimental engine; not all wave associations verified |
| `D1_sequential_audit_report.json` | 0 detected anchor/price mismatches among 95, 0 missed reversals within active segments | Invariant checks; not exhaustive correctness |
| `D1_update_completeness_audit.json` | 0 mismatches vs recorded update events | Internal consistency only |
| `D1_semantic_audit_report.json` | 0 invalid recognized pivot use/line-start anchors reported | Not independent proof of correct protected leg |
| HTML screenshots | User observed missing/scattered boxes, misaligned price/time, red line clutter | **Rendering failed user acceptance** |

These are *D1 Dow research* results, **NOT EA strategy backtest performance**. Do not conflate with EA PF/R/MaxDD reports from the separate strategy research.

## 3. Exact engine/source paths and relationships
```
research/
├── dow_frozen_v1/
│   ├── dow_final_engine.py               # Canonical frozen pivot detector
│   └── DOW_RULES_20261018.md             # Canonical prior rules
├── chart_lab/
│   └── eurusd_chart_lab_complete.html    # UI FORMAT ONLY
└── dow_migration_20261018/
    ├── README.md                         # START HERE
    ├── FILE_MAP.md                       # Locations and status
    ├── CLAUDE_CODE_HANDOFF.md            # Functional spec
    ├── VERIFICATION_MATRIX.md            # This file: test settings & evidence
    ├── TEST_HISTORY.md                   # Audit and failure history
    ├── ARTIFACT_MANIFEST.md              # Offline ZIP import
    ├── UPLOAD_STATUS_20261018.md         # What is actually uploaded
    └── artifacts/
        └── d1_rebuild.py                 # Experimental D1 protection engine
```

Offline ZIP includes the causal event adapter `dow_handoff/dow_frozen_causal_v1.py`, audit source scripts, generated data and rejected HTML. **These are not yet pushed**; see `ARTIFACT_MANIFEST.md`.

## 4. How to reproduce / what to run
1. Obtain the offline ZIP and unzip under `research/dow_migration_20261018/artifacts/`; keep relative `dow_handoff/` paths.
2. Inspect `artifacts/d1_rebuild.py` and `artifacts/dow_handoff/dow_frozen_causal_v1.py`. They currently refer to `/mnt/data` absolute paths: **parameterize them for Claude Code** before running. Do not claim immediately runnable on a clean checkout.
3. Install `python`, `pandas`, `numpy`; extract OHLC D1 series from the historical HTML or independently rebuild from M1 and record any differences.
4. Generate `D1_rebuild_events.csv` and `D1_rebuild_lines.json`; run `audit_d1_sequential.py`, `audit_d1_updates.py`, `audit_d1_semantic_full.py`.
5. Independently verify every line update/reversal against a fresh per-candle state oracle, not only by comparing engine output with its own trace.
6. Render HTML, launch Chromium/Playwright, take screenshots, test x/y alignment, replay, zoom/pan, label and exact expiration bar.
7. Record software versions, input hash, start/end timestamps, test commands, outputs and screenshot references. Earlier runs did not preserve all these provenance details.

## 5. Distinct EA strategy backtest — do NOT mix into D1 chart results
Prior separate EA work used EURUSD 2003–2026 M1 ZIP resampled to M15 (~583,458 bars) and an engine under `research/ea_shared/engine_m15.py` with `research/ea_shared/run_compare.py`. Strategy conditions included H1 SMA200/480, H1 SMA480 slope 24h, M15 stochastic 14/3/3, P1/P2 tracking, P3 trade/exclusion rules differing by experiment, SMA200-based initial SL +10 pips, +2R ZigZag ATR14*1.5 trailing, H4 horizontal rejection OFF, max two concurrent positions. Various ON/OFF filter experiments (q75, MA ABCD, reverse H1 trend, delayed ZigZag) have **different test switches** and must be documented per experiment, not aggregated as one fixed baseline. No EA performance figure is being newly verified by this migration.

## 6. Completion status
Specification and provenance documented; **actual D1 renderer and protected leg semantics not fully validated**. Existing HTML files are rejected/unapproved.
