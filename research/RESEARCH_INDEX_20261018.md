# Research index / 保存場所・エンジン・検証条件・結果 (2026-10-18)

**START HERE for Claude Code.** Repository: `shimi10cow/trade-app`. This index distinguishes verified GitHub paths, previously reported results, and missing/unverified assets. Do not equate a recorded metric with a reproducible backtest.


## UPDATE 2026-10-18: engines located after repository reorganization — READ THIS FIRST
The prior inventory looked only at obsolete paths. **The original common engine was NOT missing: it was MOVED in the 2026-10-15 repository reorganization (see research/INDEX.md, commit 86f7278).** Do not confuse a 404 at the old path with missing source code.

| Role | VERIFIED CURRENT GitHub path | Notes |
|---|---|---|
| Canonical EA backtest engine | [research/core/engine_m15.py](core/engine_m15.py) | Fetched successfully; current shared engine, not proof of historical-result parity |
| ON/OFF comparison runner | [research/core/run_compare.py](core/run_compare.py) | Fetched successfully |
| M15 cache helper | [research/core/cache_m15.py](core/cache_m15.py) | Fetched successfully |
| Legacy full engine | [research/archive/legacy_scripts/full_backtest_engine_v1_20261014.py](archive/legacy_scripts/full_backtest_engine_v1_20261014.py) | Fetched successfully; archived |
| Recovered backtest engine | [research/archive/backtest_recovery/full_backtest_engine_v1_recovered.py](archive/backtest_recovery/full_backtest_engine_v1_recovered.py) | Fetched successfully; archived |
| MA/wave experiment engine | [research/studies/ma_wave_filter_research.py](studies/ma_wave_filter_research.py) | Fetched successfully; research engine |
| Canonical research navigation | [research/INDEX.md](INDEX.md) | Existing official research directory map |
| Experiment × engine × results matrix | [research/handoffs/EXPERIMENT_ENGINE_MATRIX_20261018.md](handoffs/EXPERIMENT_ENGINE_MATRIX_20261018.md) | Detailed conditions, results, engine provenance |
| Backtest code reading / CSV filenames | [research/handoffs/BACKTEST_ENGINE_AND_CONDITIONS_20261018.md](handoffs/BACKTEST_ENGINE_AND_CONDITIONS_20261018.md) | Actual source-read conditions for trail_variant_engine.py; source in external ZIP |
| H4/W/SMA experiments | [research/studies/notes/2026-10-18_EXPERIMENT_ENGINE_CONDITIONS.md](studies/notes/2026-10-18_EXPERIMENT_ENGINE_CONDITIONS.md) | Exact research rules, historical figures, external ZIP dependencies |
| Wave subset result manifest | [research/results/2026-10-15_wave_maturity/README.md](results/2026-10-15_wave_maturity/README.md) | Exists; subset has lookahead concerns |

**Correction to section 2 below:** `research/ea_shared/engine_m15.py` and `research/ea_shared/run_compare.py` are OLD PATHS. Their canonical current counterparts are in `research/core/`. The old full engine is under `research/archive/legacy_scripts/`. Likewise some earlier paths in handoffs are stale. Consult `research/INDEX.md` first.

### Additional experiment provenance, not to conflate
- `EXPERIMENT_ENGINE_MATRIX_20261018.md` records LEGACY-SIMPLE/H4, FOREX-H4OFF, EUR436, WAVE-359/284, FILTER-A/B, P4-CAP, RECENT-272 with separate engines and caveats. Not all are fully reproducible.
- `2026-10-18_EXPERIMENT_ENGINE_CONDITIONS.md` documents H4 reversal/P1-P2 (751 trades, −39.224R, PF .926 gate ON; 1044, −94.670R, PF .874 OFF), W neckline, SMA200/SMA75 initial SL, +1.5R vs +2R trailing, cap1/cap2, spread assumptions. These are **different studies**, not the old shared EA and not the new trendline EA.
- `BACKTEST_ENGINE_AND_CONDITIONS_20261018.md` documents a standalone `trail_variant_engine.py` from an **external ZIP**, not confirmed committed. It uses H1 slope shift(12), raw Stoch14 SMA3/SMA5, +240h delayed trail and fixed-spread settings that may differ from original strategy. Do not silently treat it as identical to `core/engine_m15.py`.
- Historical reported 1974-trade and 1681-trade multi-symbol results should **not** be labeled EURUSD-only; see experiment matrix.
- Some scripts and results exist only in `EA_Claude_Code_handoff_2026-10-18.zip` or `EA_Claude_handoff_research_20261018.zip` as described by older handoffs. Those ZIPs are not verified as GitHub repository files. Check whether the actual attachment is available before attempting reproduction.

## 1. Confirmed repository files (checked via GitHub fetch_file on 2026-10-18)

| Category | Path (relative to repo root) | Purpose | Status |
|---|---|---|---|
| Master handoff | [research/CLAUDE_CODE_HANDOFF_20261018.md](CLAUDE_CODE_HANDOFF_20261018.md) | Overall history, implementation plan, cautions | Exists; docs |
| Research index | [research/RESEARCH_INDEX_20261018.md](RESEARCH_INDEX_20261018.md) | This inventory; results-to-engine provenance | This commit |
| Frozen Dow | [research/dow_frozen_v1/dow_final_engine.py](dow_frozen_v1/dow_final_engine.py) | Original Numba pivot detector; retrospective output can repaint | Exists; frozen reference |
| Dow rules | [research/dow_frozen_v1/DOW_RULES_20261018.md](dow_frozen_v1/DOW_RULES_20261018.md) | Protected swing, major/provisional Dow, W, horizontal zones | Exists; downstream unverified |
| Causal line engine | [research/chart_lab/trendline_causal_engine.py](chart_lab/trendline_causal_engine.py) | Pivot confirm/relocate + 2/3-point line create/revise/retire events | Exists; not production-certified |
| Line generation spec | [research/chart_lab/TRENDLINE_RULES.md](chart_lab/TRENDLINE_RULES.md) | 2/3-point thresholds, anchors, causality | Exists; some historical gap notes stale |
| Latest lifecycle spec | [research/chart_lab/TRENDLINE_RULES_REVIEW_20261018.md](chart_lab/TRENDLINE_RULES_REVIEW_20261018.md) | Dynamic impulse/correction + retirement | Exists; latest agreed rule |
| Chart feature map | [research/chart_lab/FEATURE_MAP.md](chart_lab/FEATURE_MAP.md) | UI features, provenance, chart cautions | Exists |
| Manual HTML chart | [research/chart_lab/eurusd_chart_lab_complete.html](chart_lab/eurusd_chart_lab_complete.html) | Interactive chart baseline | Exists; retrospective lines, NOT causal replay |

**Important:** `fetch_file` confirms the path exists, not that its logic passes tests. The HTML's visual alignment/complete behavior has not been verified here.

## 2. Obsolete or unverified paths (NOT necessarily missing source — see correction above)

| Claimed path | Intended role | Action |
|---|---|---|
| `research/ea_shared/engine_m15.py` | Old M15 EA common backtest engine | **OLD PATH**; current code in research/core/ (verified), see update above |
| `research/ea_shared/run_compare.py` | Old ON/OFF comparison runner | **OLD PATH**; current runner in research/core/ (verified) |
| `research/full_backtest_engine_v1_20261014.py` | Earlier full backtest engine | **OLD PATH**; archived source in research/archive/legacy_scripts/ (verified) |
| `research/dow_frozen_v1/dow_frozen_causal_v1.py` | Causal frozen Dow adapter | **404** at this path; locate/restore |
| `research/dow_frozen_v1/build_causal_horizontal_zones_v9.py` | Historical horizontal-zone v9 | **404** at this path; v9 was also reported flawed |

The first three are confirmed MOVED and committed at new paths; do not claim the remaining historical adapters are committed unless independently located. Check canonical research/INDEX.md.

## 3. Strategy research / previously reported backtests (not re-executed or independently verified here)

### Common research baseline, subject to experiment-specific overrides
- Market: EURUSD for many individual tests; **LEGACY-SIMPLE and LEGACY-H4 aggregate multiple symbols** (2015–2026). Historical Forex Tester minute-derived M15 data for EURUSD-specific 2003–2026 experiments.
- M15 cache reportedly **583,458 candles**, 2003-05-06 to 2026-10-12. Cache itself NOT confirmed committed to GitHub.
- H1 trend: SMA200 / SMA480; SMA480 24h slope. M15 Stoch 14,3,3 (slowing=5 / D=3 as historically described; **verify code**). P1/P2 trade group; some tests trade P3 but exclude it only at aggregation; P5 disallowed; H1 W1 only.
- Risk/exits historically described: M15 SMA200 +10p (spread inclusive, min 10p), ZigZag ATR14×1.5 trail activated at +2R; initial spread/risk controls. Some later alternative experiments used +1.5R trail or HH75 stops; do not mix with baseline.
- Recent ON/OFF tests were requested with H4 horizontal filter OFF, max 2 simultaneous positions, +2R regular ZigZag maintained, P3 **executed but excluded from displayed aggregates**, all other rules held fixed. Confirm each runner's actual settings before trusting comparisons.

| ID / test | Variable / comparison | Reported result | Engine/data provenance | Confidence |
|---|---|---|---|---|
| Earlier simple baseline | Historical strategy, 2015–2026 | 1,974 trades; +359.6R; PF 1.308; max DD −42.3R | Exact engine/version and data snapshot NOT verified here | Reported only |
| H4 filter variant | H4 96h +25pt, 2015–2026 | 1,681 trades; +327.41R; PF 1.332; max DD −34.84R | Exact engine/version and parameter definition NOT verified here | Reported only |
| ⑦ H1 countertrend reject | ON vs OFF, EURUSD 2003–2026 | Total R +177.10 vs +176.70; 5-trade difference, −0.40R | Previously reported from independent/shared engine; missing runner path | Reported only; ON/OFF ordering must be checked |
| ⑥ MA ABCD reject | ON vs OFF, EURUSD 2015+ | OFF deteriorated total R by 14.20R; PF 1.440→1.379; max DD −26.56R→−28.35R | Previously reported; missing runner path | Reported only |
| ⑤ 240h delayed ZigZag | ON vs OFF, EURUSD 2003–2026 | Described as measured; detailed metrics NOT available in verified sources inspected for this index | Exact results artifact / runner unverified | **Do not invent numbers** |
| q75 reject | ON vs OFF, EURUSD 2003–2026 | Requested repeatedly; final numeric results NOT verified in inspected sources | Exact runner/results unverified | Not established |
| Other filter tests | MA expansion exception, H4 RSI, H4 horizontal, P3 grouping | Historical configuration discussions; no independently verified complete comparison table in inspected sources | Unknown | Not established |
| Other EA result discussed | 272 trades, +72.86R, avg +0.268R/trade, PF 1.456, DD −11.12R | Conditions/timeframe/engine not sufficiently identified | Unknown | Do NOT attribute to baseline or new Dow EA |

These figures come from prior research summaries and discussions, NOT execution during this documentation pass. No raw per-trade output, commit hash, seed, data fingerprint or command-line invocation is confirmed for the reported numbers.

### Reproduction metadata required for EACH experiment
Create one manifest per experiment, e.g. `research/experiments/<ID>/README.md`, `config.json`, `results.json`, `trades.csv`, `run.sh` (when source/data available):
- unique ID; goal/hypothesis; date; instrument; source file path + SHA256; timezone and broker candle-close semantics; M1->M15 aggregation; exact date boundaries
- engine source path + Git commit SHA; runner path + commit SHA; Python/dependency versions; command and flags
- all fixed settings + only changed setting(s), including P3 trade vs aggregation behavior, max positions, SL/trail, spread, risk sizing and warmup
- full-period, 2015+, and yearly trade counts, sum R, PF, max DD, plus per-trade ledger; note exclusions
- whether **reproduced** / **historically reported only** / **not run**; no invented precision or missing metrics.

## 4. Dow/line/horizontal research conditions and engine links

| Research | Engine | Exact source rules | Verification state |
|---|---|---|---|
| Frozen Dow pivot | `research/dow_frozen_v1/dow_final_engine.py` | W1 (7,1.9,+.15,.4), D1 (7,1.9,-.15,.4), H4 (7,2.0,+.3,.4), H1 (7,2.4,-.15,.25), M15 (7,2.1,+.3,.25); ATR7 Wilder EWMA, ER20, wick extremes, later-bar threshold confirmation, relocation | File exists; causal parity must be tested |
| Causal 2-point lines | `research/chart_lab/trendline_causal_engine.py` | Consecutive same-kind confirmed pivots; higher lows/lower highs; original gap >=15; wick-based iterative A→C reanchor; no ATR intrusion filter | File exists; line lifecycle not yet production verified |
| Causal 3-point lines | same engine | 3 consecutive pivots, each >=.12ATR, gaps 4..TF max, middle deviation <=.85ATR, close intrusion <=10% >.35ATR, max 1.7ATR, slope .25..7, near-duplicate scoring | File exists; historic parity and edge cases need testing |
| Major/provisional Dow, W, zones | `research/dow_frozen_v1/DOW_RULES_20261018.md` | Close beyond pivot wick; maintain protected low/high on eligible confirmed structure, late confirmation known-at; W-top/bottom; zones first later full-body expiry | Specification exists; downstream implementation not verified |
| Line break + 2 pivots retirement | `research/chart_lab/TRENDLINE_RULES_REVIEW_20261018.md` | Descending: close above + 2 unique confirmed lows; ascending: close below + 2 unique confirmed highs; inside close resets; relocate not double counted | Agreed spec; lifecycle implementation pending |
| Impulsive line retirement | same rules + protected-swing Dow state | Classify by CURRENT major Dow direction; corrective→impulsive on reversal survives; retire impulsive when its trend reverses | Agreed spec; requires verified major Dow engine |
| Manual chart | `research/chart_lab/eurusd_chart_lab_complete.html` | Visual inspection W1/D1/H4/H1/M15, 2/3-point overlays | Retrospective display, not validation of known-at |

## 5. User-provided data in ChatGPT runtime, NOT automatically GitHub
Paths previously supplied to ChatGPT:
`/mnt/data/EURUSD2003.M1.zip`, `/mnt/data/USDJPY2003.M1.zip`, `/mnt/data/EURUSD_M5_MT5.csv`, `/mnt/data/USDJPY_M5_MT5.csv`, `/mnt/data/JP225_M15_MT5.csv`, `/mnt/data/UK100_M15_MT5.csv`, `/mnt/data/US500_M15_MT5.csv`.
These are **local conversation uploads**, not GitHub repository paths. Their existence in Claude Code, file integrity and licensing need independent checks. Do not commit large data automatically.

## 6. Directory organization recommended (non-destructive)
```
research/
  RESEARCH_INDEX_20261018.md          # entry point, verified vs missing files
  CLAUDE_CODE_HANDOFF_20261018.md     # full technical history and roadmap
  dow_frozen_v1/                     # frozen pivot + Dow/zone specifications
  chart_lab/                         # trendline engines, rules, interactive chart
  experiments/                       # PROPOSED: per-test reproducible manifests/results
  ea_shared/                         # PROPOSED/UNVERIFIED: older engine and runner; restore if found
```
Do not move/rename legacy files blindly: external scripts may import their original paths. Add links and metadata first. This index is the location map.

## 7. Next actions for Claude Code
1. Read this index and master handoff. Inventory actual git tree, branches and history; resolve missing engine paths.
2. Recover each original test engine/runner and raw outputs; fill per-experiment manifests with **verified** conditions and metrics; rerun with data fingerprints when possible.
3. Keep frozen Dow detector unchanged. Validate bar-close causal pivot stream, then protected swing/reversal state, then line creation/retirement.
4. Build lifecycle tests before exposing lines to EA. Separate the old stochastic EA from the new Dow/line research; never label an old backtest as a Dow-line result.
