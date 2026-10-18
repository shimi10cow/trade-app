# EA / Dow research — Claude Code entry point (2026-10-18)

**START HERE.** This folder documents migration of the EURUSD D1 Dow protected-swing / horizontal box research to Claude Code.

> **State: D1 display NOT accepted.** Do not present any existing generated D1 HTML as completed or visually verified. The user's screenshots show misaligned and missing boxes.

## Read in this order
1. [CLAUDE_CODE_HANDOFF.md](CLAUDE_CODE_HANDOFF.md) — consolidated requirements, frozen rules, implementation risks, prior experiments, and what to test next.
2. [FILE_MAP.md](FILE_MAP.md) — precise paths, purpose, status, and priority of each source/artifact.
3. [TEST_HISTORY.md](TEST_HISTORY.md) — chronological experiments, numbers, evidence vs remaining uncertainty.
4. [ARTIFACT_MANIFEST.md](ARTIFACT_MANIFEST.md) — ZIP archive and manual import instructions.
5. [UPLOAD_STATUS_20261018.md](UPLOAD_STATUS_20261018.md) — which files are actually in GitHub versus only in the ZIP.

## Key decisions
- The Complete HTML is a **UI layout / controls reference ONLY**. Reuse none of its old Dow calculations or historical line coordinates.
- Frozen Dow detector is separate from the state machine for major trend and protected pivot updates, which is separate from the HTML renderer.
- Scope **now**: D1 confirmed major Dow, protected low/high and historical boxes. **Later**: H4/H1/M15, provisional trend, W patterns and expired zones.
- Candle CLOSE crossing pivot WICK determines structural break. Do not replace this with full-body breakout.
- Pivot `anchor_time` and `known_at` must remain separate; no future leakage.
- A protected pivot relocation must update the active segment's geometry; changing only a dictionary entry is insufficient.
- On replacement, the former active line stops at that time. Historical charts must retain correctly bounded segments. In replay, show only what was known at the replay candle.
- Required next deliverable: D1-only HTML with native chart coordinates, clear cyan 押し安値 and purple 戻り高値 boxes, small labels, visible historical intervals, no stray red trendlines, and screenshots from an actual browser verifying pan/zoom/replay.

## Repo's already existing canonical assets
- [Frozen detector](../dow_frozen_v1/dow_final_engine.py)
- [Chart Complete UI template](../chart_lab/eurusd_chart_lab_complete.html)
- [Migrated D1 line generator — unapproved](artifacts/d1_rebuild.py)

## Quick continuation for Claude Code
1. Read the above docs; inspect the frozen detector and imported source bundle.
2. If the ZIP has not yet been committed, import it according to [ARTIFACT_MANIFEST.md](ARTIFACT_MANIFEST.md). Do not silently claim the ZIP is in GitHub.
3. Reproduce event output and independently validate the *semantics* of every protection update, especially leg association, delayed pivot confirmation, same-bar reversals, and pivot relocation.
4. Rebuild the chart overlay from scratch with the actual chart's time/price scale; do not simply paint absolute CSS boxes or reuse Complete's old overlays.
5. Browser-test (screenshots + numeric assertions) before sharing any HTML.
6. Record changes, baseline statistics, screenshots, and test results in this folder.

## User acceptance criterion
The user must be able to inspect every past D1 protected low/high and see the box appear, move, and disappear on the correct candle at the correct wick price. A passing syntax test or internally consistent event count does **not** establish this.
