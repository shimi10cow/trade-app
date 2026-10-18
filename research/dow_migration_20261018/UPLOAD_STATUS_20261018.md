# Actual GitHub upload status — 2026-10-18

## Uploaded in this migration
- `CLAUDE_CODE_HANDOFF.md` — agreed rules, scope, test results, rendering failures, next steps.
- `ARTIFACT_MANIFEST.md` — 37-file offline archive inventory and extraction instructions.
- `artifacts/d1_rebuild.py` — actual Python source for D1 event-to-line state machine, **known issues / NOT APPROVED**.

## Already in repository (from previous work)
- `research/dow_frozen_v1/dow_final_engine.py` — frozen detector.
- `research/dow_frozen_v1/DOW_RULES_20261018.md` — canonical rules.
- `research/chart_lab/eurusd_chart_lab_complete.html` — UI format reference only.

## NOT uploaded
- The 37-file `CLAUDE_CODE_DOW_MIGRATION_20261018.zip` (~7 MB compressed) and its large HTML/CSV/JSON/source contents. GitHub connector supports UTF-8 file content, but cannot read local container bytes directly; this runtime also cannot reach github.com via git. The ZIP is supplied separately in the ChatGPT conversation for manual ingestion into Claude Code/repository. **Do not claim all sources have been pushed.**
- Large raw FX datasets.

## Required next step
Download the ZIP from the conversation, unzip to `research/dow_migration_20261018/artifacts/`, inspect for duplicates and generated HTML, and commit. Keep the canonical detector unchanged until tests establish necessity. Rebuild and screenshot-test D1 overlay; latest HTML is not user-approved.
