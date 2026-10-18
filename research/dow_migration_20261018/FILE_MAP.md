# File map — what lives where

## A. Canonical GitHub files (already present)

| File | Role | Trust / usage |
|---|---|---|
| `research/dow_frozen_v1/dow_final_engine.py` | Frozen causal swing/pivot recognition engine | Canonical recognition baseline; review actual source before editing |
| `research/dow_frozen_v1/DOW_RULES_20261018.md` | Earlier rule record | Read alongside migration handoff; investigate discrepancies |
| `research/chart_lab/eurusd_chart_lab_complete.html` | Existing chart UI, interactions and formatting | **UI ONLY**. Its old Dow / horizontal line / zone output is not ground truth |
| `research/dow_migration_20261018/artifacts/d1_rebuild.py` | D1 protected line state machine from research | **Experimental**; pivot relocation and wave-association bugs possible |

## B. Migration documents (GitHub)

| File | Contents |
|---|---|
| `README.md` | This research's entry point and continuation order |
| `CLAUDE_CODE_HANDOFF.md` | Full rules, experiment summary, known failure modes and next actions |
| `FILE_MAP.md` | Detailed location/role/status index |
| `TEST_HISTORY.md` | Past work and validation limitations |
| `ARTIFACT_MANIFEST.md` | Archive inventory and import commands |
| `UPLOAD_STATUS_20261018.md` | Honest uploaded/not-uploaded accounting |

## C. Offline ZIP — NOT YET PUSHED TO GITHUB

Conversation download: `CLAUDE_CODE_DOW_MIGRATION_20261018.zip` (~7 MB; 37 files). **These paths are inside ZIP**, not necessarily live repository paths. Suggested import root: `research/dow_migration_20261018/artifacts/`.

### Engine and data extraction
| ZIP member | Purpose | Status |
|---|---|---|
| `d1_rebuild.py` | Generate D1 state events and line segments | Experimental; GitHub copy also exists |
| `dow_handoff/dow_frozen_causal_v1.py` | Causal pivot adapter / events | Research baseline |
| `dow_handoff/d1_basic_dow_review.py` | Early D1 review script | Historical prototype |
| `dow_handoff/build_causal_horizontal_zones_v8.py` | Older zones algorithm | Historical, not current D1 source |
| `dow_handoff/build_causal_horizontal_zones_v9.py` | Subsequent zones iteration | Historical |
| `dow_handoff/build_causal_horizontal_zones_v10.py` | Subsequent zones iteration | Historical |

### Audit and generated evidence
| ZIP member | Purpose | Status |
|---|---|---|
| `audit_d1_sequential.py` | Check each line's anchor/price and protected-break handling | Partial invariant audit |
| `audit_d1_updates.py` | Check consistency of recorded protection updates | Not independent semantic proof |
| `audit_d1_semantic_full.py` | Check causal recognition/anchors | Does not prove all wave associations |
| `D1_rebuild_events.csv` | Generated event trace | Generated evidence, not ground truth |
| `D1_rebuild_lines.json` | Generated historical segments | Generated evidence, not ground truth |
| `D1_sequential_line_audit.csv` | Per-segment audit | Audit artifact |
| `D1_sequential_audit_report.json` | Invariant audit summary | Partial |
| `D1_update_completeness_audit.json` | Event consistency summary | Partial |
| `D1_semantic_audit_report.json` | Recognition/anchor audit summary | Partial |
| `dow_handoff/dow_frozen_causal_events.json` | Pivot events | Baseline generated data |
| `dow_handoff/dow_frozen_causal_audit.json` | Pivot audit | Prior evidence |
| `dow_handoff/eurusd_d1_protected_changes.csv` | Earlier protected changes | Prior evidence |
| `dow_handoff/eurusd_v9_completeness_audit.json` | Earlier v9 audit | Historical |
| `dow_handoff/eurusd_zone_v8_events.json` | Earlier v8 zones | Historical |

### HTML/chart generation and failures
| ZIP member | Purpose | Status |
|---|---|---|
| `build_d1_verified_html.py` | HTML build attempt | Must independently verify output |
| `test_d1_html.py` | HTML test attempt | Does not substitute browser screenshot |
| `reformat_boxes.py` | Box formatting experiment | Historical |
| `fix_d1_boxes.py` | Box display patch | Historical |
| `fix_d1_visual.py` | Chart visual patch | Historical |
| `EURUSD_D1_protected_rebuilt_complete.html` | Early D1 output | **Rejected** |
| `EURUSD_D1_boxes_complete_format.html` | Box-format attempt | **Rejected** |
| `EURUSD_D1_boxes_history_fixed.html` | Historical segment attempt | **Rejected**; user screenshot shows scattered boxes |
| `EURUSD_D1_boxes_aligned_verified.html` | Last alignment attempt | **Unverified, not approved**, despite filename |
| `eurusd_dow_D1.png` | User screenshot showing one visible box / stray red lines | Failure evidence |
| `eurusd_dow_D1 (1).png` | User screenshot showing scattered boxes | Failure evidence |
| `dow_handoff/eurusd_d1_complete_protected_review.html` | Earlier full D1 chart | Historical; not canonical |
| `dow_handoff/eurusd_d1_complete_protected_review.png` | Earlier chart screenshot | Historical |
| `dow_handoff/build_d1_complete_review.py` | Earlier review builder | Historical |
| `dow_handoff/merge_complete_zones.py` | Older zone/Complete merge | Historical |

### Written specifications
| ZIP member | Purpose |
|---|---|
| `dow_handoff/DOW_RULES_20261018.md` | Agreed detailed rules at that snapshot |
| `dow_handoff/EA_DOW_HANDOFF_20261018.md` | Full project handoff including later-stage rules |

## D. Large market data
`EURUSD2003.M1.zip`, `USDJPY2003.M1.zip`, MT5 M5/M15 CSV and derived cache files were supplied to the ChatGPT project separately. **Not included in this ZIP and not claimed to be in GitHub**. They may need explicit transfer to Claude Code. Do not substitute chart-embedded D1 data for original M1 unless documenting the difference.

## Practical rule
**Read `README.md` → `CLAUDE_CODE_HANDOFF.md` → `TEST_HISTORY.md` → inspect code.** Do not assume a ZIP-only file is already in GitHub.
