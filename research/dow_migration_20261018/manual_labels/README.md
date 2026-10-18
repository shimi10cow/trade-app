# Recovered human-labelled EURUSD Dow pivots (2026-10-19)

## Confirmed original
- `eurusd_dow_annotations_v14_original_20261017.json` — archived annotation data, originally saved `2026-10-17T03:48:12.052Z`. Source: user's Library file `eurusd_dow_annotations_v14 (1).json`.
- `EURUSD_manual_swing_labels_20261017.csv` — all `swingByTF` points flattened without automatic reinterpretation; columns timeframe, time_iso, time_epoch_ms, kind, label_jp, source, saved_at.
- Counts: W1 30, D1 79, H4 181, H1 231, M15 282; total 803 (hi 403, lo 400).
- JSON `timeBasis=source-clock-naive-as-UTC-for-indexing`. This is an INDEXING convention, not proof of the actual timezone of the source market bars. CSV ISO dates simply decode stored epoch milliseconds. Do not shift times without checking original OHLC source-clock.
- No prices in `swingByTF` entries: they have `t` and `kind` only. Derive wick price by matching time to the exact source OHLC and selecting high/low; mark derived prices as such, never fabricate them.
- `kind` is only `hi` or `lo` in this archived dataset. User recalls also manually saying `どっちでもいい` / ambiguous. Those explicit ambiguous decisions are **not present as a third kind** in this JSON. Do not assert they were never said; find original conversation transcript or other annotation version.
- Another file `eurusd_dow_annotations_v14.json` (saved 2026-10-17T02:58:56.311Z) has only H1 labels and empty W1/D1/H4; do not overwrite the fuller later `(1)` version with it.
- A prior assistant reported matching manually marked swings to ATR ZigZag: `dow_offset_matches.csv` and `dow_offset_summary.csv`, with 643/803 wave-level matches. Those are **comparison outputs**, not a substitute for original user labels; the files were not recovered in this operation.

## Recommended for Claude Code
Load `eurusd_dow_annotations_v14_original_20261017.json` and compare `swingByTF` against causal detected pivots by TF. Keep manual labels and machine detections separate. Review time normalization and tolerance. Do not use the generated D1 horizontal lines as ground truth for human labels.
