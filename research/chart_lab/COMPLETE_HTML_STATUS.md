# EURUSD Chart Lab — integrated HTML snapshot

Snapshot created 2026-10-17: `eurusd_chart_lab_complete.html`.

- SHA256: `00603998f81139d6b1d0c3b9be93534ed5b46b280722c0872295080cf2892496`
- Size: 5,479,139 bytes
- Built by merging the local `eurusd_trendline_review_v4_fixed.html` editor with 2-point and 3-point line datasets from `eurusd_trendlines_all_tf_candles_fixed.html`.
- Original drawing/replay/JSON/image-export functionality retained; line timeframe toggles and separate 2-point/3-point toggles added.
- JavaScript syntax checked with `node --check`.
- Browser interaction smoke tests not yet completed.

**Important:** This is a snapshot manifest, **not the complete HTML file**. The full HTML was created in the ChatGPT working directory and delivered as a downloadable artifact. Upload of the 5.5 MB HTML itself to this repository is still pending; do not claim the GitHub version is complete until the actual file is committed.

Intended target path: `research/chart_lab/eurusd_chart_lab_complete.html`.

To finish locally after downloading the HTML:

```bash
mkdir -p research/chart_lab
cp /path/to/eurusd_chart_lab_complete.html research/chart_lab/
git add research/chart_lab/eurusd_chart_lab_complete.html
git commit -m "feat: save complete EURUSD Dow chart lab"
git push
```
