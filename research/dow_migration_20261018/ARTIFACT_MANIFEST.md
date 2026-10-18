# Migration artifact manifest (2026-10-18)

**GitHub committed:** `CLAUDE_CODE_HANDOFF.md` (research specification, historical work, failures, validation plan). Existing canonical files in repo: `research/dow_frozen_v1/dow_final_engine.py`, `research/dow_frozen_v1/DOW_RULES_20261018.md`, and `research/chart_lab/eurusd_chart_lab_complete.html`.

**Source bundle created in the conversation:** `CLAUDE_CODE_DOW_MIGRATION_20261018.zip` (37 files, ~7.3 MB). The GitHub connector cannot read the local /mnt/data file bytes, and direct GitHub network access is unavailable in this runtime; **this ZIP is not committed to GitHub**. To complete the migration, copy the ZIP into the repository and run:

```bash
mkdir -p research/dow_migration_20261018/artifacts
unzip CLAUDE_CODE_DOW_MIGRATION_20261018.zip -d research/dow_migration_20261018/artifacts
git add research/dow_migration_20261018
git commit -m "research: archive D1 Dow implementation, audits and rejected HTML previews"
git push
```

Bundle contains: `d1_rebuild.py`, `audit_d1_sequential.py`, `audit_d1_updates.py`, `audit_d1_semantic_full.py`, `build_d1_verified_html.py`, `test_d1_html.py`, `reformat_boxes.py`, `fix_d1_boxes.py`, `fix_d1_visual.py`, `D1_rebuild_events.csv`, `D1_rebuild_lines.json`, `D1_semantic_audit_report.json`, `D1_sequential_audit_report.json`, `D1_sequential_line_audit.csv`, `D1_update_completeness_audit.json`, four rejected `EURUSD_D1_*.html` variants, two user failure screenshots, plus `dow_handoff/` containing full 21 KB detailed handoff, rules, frozen causal adapter, v8/v9/v10 prototypes, audit event JSONs, earlier HTML and scripts.

Do not mistake a checked-in handoff or archived HTML for an accepted working implementation. Current priority: D1 protected swings + visually verified native chart alignment. Historical raw M1 ZIP/other large market datasets are deliberately excluded from this compact bundle and were not committed.
