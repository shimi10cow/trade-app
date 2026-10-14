"""Convert Forex Tester 6 M1 CSV ZIP exports into analysis-ready M5 and M15 bars.
Usage: python research/forextester/prepare_mtf.py --input-dir data --output-dir prepared
Original ZIPs remain unchanged. CSV time assumed UTC (verify export timezone).
Requires pandas. OHLCV is resampled with left-labelled, left-closed bars.
Missing minutes are NOT filled. Bars carry observed M1 count.
"""
import argparse
import json
import zipfile
from pathlib import Path
import pandas as pd

COLUMNS = ["ticker", "date", "hhmm", "open", "high", "low", "close", "volume"]

def process(pair, input_dir, output_dir):
    src = input_dir / f"{pair}2003.M1.zip"
    with zipfile.ZipFile(src) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"Corrupt ZIP: {src}")
        with archive.open(archive.namelist()[0]) as stream:
            df = pd.read_csv(stream, dtype={"<DTYYYYMMDD>": str, "<TIME>": str})
    df.columns = COLUMNS
    stamp = pd.to_datetime(df["date"].str.zfill(8) + df["hhmm"].str.zfill(4), format="%Y%m%d%H%M", utc=True)
    if stamp.duplicated().any():
        raise ValueError(f"{pair}: duplicate minute timestamps")
    df.index = stamp
    df = df.sort_index()
    df["m1_count"] = 1
    def resample(data, freq):
        return data.resample(freq, label="left", closed="left", origin="start_day").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last",
             "volume": "sum", "m1_count": "sum"}).dropna(subset=["open"])
    base = df[["open", "high", "low", "close", "volume", "m1_count"]]
    m5 = resample(base, "5min")
    m15 = resample(m5, "15min")
    for label, frame, expected in [("M5", m5, 5), ("M15", m15, 15)]:
        frame["complete_m1"] = frame["m1_count"].eq(expected)
        frame.index.name = "time_utc"
        frame.to_csv(output_dir / f"{pair}_{label}_UTC.csv.gz", compression="gzip")
    meta = {"pair": pair, "source": src.name, "timezone": "UTC assumed; verify export settings",
            "m1_rows": len(df), "m1_start": str(df.index.min()), "m1_end": str(df.index.max()),
            "m5_rows": len(m5), "m15_rows": len(m15),
            "m5_partial": int((~m5["complete_m1"]).sum()),
            "m15_partial": int((~m15["complete_m1"]).sum()),
            "note": "Raw VOL not assumed to be broker tick volume. Incomplete bars are flagged, not imputed."}
    (output_dir / f"{pair}_quality.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(meta)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("prepared"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for pair in ("EURUSD", "USDJPY"):
        process(pair, args.input_dir, args.output_dir)
