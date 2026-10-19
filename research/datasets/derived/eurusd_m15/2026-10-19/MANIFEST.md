# EURUSD M15 dataset — 2003–2026

## Dataset prepared 2026-10-19
- Source local cache: `/mnt/data/ea_shared/EURUSD2003_M15.pkl` (Forex Tester EURUSD M1-derived M15).
- Export file: `EURUSD_M15_2003_2026.csv.gz`.
- 583,458 rows, five columns `time,open,high,low,close`.
- Time range: 2003-05-06 00:00:00 through 2026-10-12 23:45:00.
- Compression: gzip; exported prices with 5 decimal places.
- Compressed size: 6,509,xxx bytes approximately (6.51 MB).
- SHA256 of exported gzip: `05a48f524d5f17e326d60e86c38df5fd7dc206dcefe1f595dfeb65094dcf7175`.
- Timezone is not independently established; treat time labels as source dataset timestamps.
- **STATUS: compressed data file has been generated in the chat workspace and is NOT YET COMMITTED TO GITHUB.** Do not claim it is available in this repository.

## Destination when uploading
`research/datasets/derived/eurusd_m15/2026-10-19/EURUSD_M15_2003_2026.csv.gz`

## User-side upload (Claude Code terminal)
After downloading the generated file to your local machine:

```bash
mkdir -p research/datasets/derived/eurusd_m15/2026-10-19
cp /path/to/EURUSD_M15_2003_2026.csv.gz research/datasets/derived/eurusd_m15/2026-10-19/
git add research/datasets/derived/eurusd_m15/2026-10-19/
git commit -m "data: add EURUSD M15 OHLC 2003-2026"
git push origin main
```

Load with pandas: `pd.read_csv('research/datasets/derived/eurusd_m15/2026-10-19/EURUSD_M15_2003_2026.csv.gz', parse_dates=['time'])`.
