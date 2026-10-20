#!/usr/bin/env python3
"""Rebuild multi-timeframe OHLC caches without fabricating historical spreads.

Requires: pandas, pyarrow (for parquet). Optional --format csv avoids pyarrow.
Input archives/files are NOT committed by this script. Git LFS is recommended for large outputs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "EURUSD": {"m1": "EURUSD2003.M1.zip", "mt5": "EURUSD_M5_MT5.csv", "pip_size": 0.0001},
    "USDJPY": {"m1": "USDJPY2003.M1.zip", "mt5": "USDJPY_M5_MT5.csv", "pip_size": 0.01},
    "JP225": {"mt5": "JP225_M15_MT5.csv"},
    "UK100": {"mt5": "UK100_M15_MT5.csv"},
    "US500": {"mt5": "US500_M15_MT5.csv"},
}
FREQS = {"M5": "5min", "M15": "15min", "H1": "1h", "H4": "4h", "D1": "1D"}
COLS = ["open", "high", "low", "close"]
AGG = {"open": "first", "high": "max", "low": "min", "close": "last",
       "tick_volume": "sum", "real_volume": "sum"}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_mt5(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    required = {"time", *COLS}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing MT5 columns: {required - set(df.columns)}")
    # Preserve clock values exactly as recorded; timezone-aware values become UTC.
    s = df["time"].astype(str)
    aware = s.str.contains(r"(?:Z|[+-]\d\d:\d\d)$", regex=True).all()
    if aware:
        t = pd.to_datetime(s, utc=True).dt.tz_localize(None)
        timezone = "UTC from source offset"
    else:
        t = pd.to_datetime(s, errors="raise")
        timezone = "SOURCE_UNSPECIFIED_NO_CONVERSION"
    df["time"] = t
    return df, timezone

def read_m1_zip(path):
    with zipfile.ZipFile(path) as z:
        members = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"Expected one CSV in {path}: {members}")
        with z.open(members[0]) as f:
            df = pd.read_csv(f, usecols=["<DTYYYYMMDD>", "<TIME>", "<OPEN>", "<HIGH>",
                                         "<LOW>", "<CLOSE>", "<VOL>"],
                             dtype={"<DTYYYYMMDD>": str, "<TIME>": str})
    d = df["<DTYYYYMMDD>"].str.zfill(8) + df["<TIME>"].str.zfill(4)
    df["time"] = pd.to_datetime(d, format="%Y%m%d%H%M", errors="raise")
    df = df.rename(columns={"<OPEN>": "open", "<HIGH>": "high", "<LOW>": "low",
                            "<CLOSE>": "close", "<VOL>": "tick_volume"})
    return df[["time", *COLS, "tick_volume"]], "SOURCE_UNSPECIFIED_NO_CONVERSION"

def normalize(df):
    df = df.dropna(subset=["time", *COLS]).sort_values("time")
    df = df.drop_duplicates("time", keep="last").set_index("time")
    for col in COLS:
        df[col] = pd.to_numeric(df[col], errors="raise")
    for col in ("tick_volume", "real_volume"):
        if col not in df:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any() or (
        df["low"] > df[["open", "close", "high"]].min(axis=1)
    ).any():
        raise ValueError("Invalid OHLC ordering")
    return df

def aggregate(df, freq):
    # Calendar aligned. D1/H4 depend on source timezone; no timezone is guessed.
    out = df.resample(freq, label="left", closed="left", origin="start_day").agg(AGG)
    count = df["close"].resample(freq, label="left", closed="left", origin="start_day").count()
    out = out[count > 0]
    # MT5 'spread' is in broker points, not pips; no fabricated intrabar value.
    # Preserve source spread diagnostics separately rather than summing/averaging blindly.
    return out.reset_index()

def save(df, path, fmt):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet":
        df.to_parquet(path, index=False, compression="zstd")
    else:
        df.to_csv(path, index=False)

def run(args):
    src = Path(args.input_dir)
    dest = Path(args.output_dir)
    records = []
    for symbol, cfg in FILES.items():
        sources = [("m1", cfg["m1"])] if "m1" in cfg else []
        if "mt5" in cfg:
            sources.append(("mt5", cfg["mt5"]))
        for kind, name in sources:
            path = src / name
            if not path.exists():
                print(f"SKIP missing: {path}")
                continue
            print(f"Reading {symbol} {kind}: {path}", flush=True)
            df, tz = read_m1_zip(path) if kind == "m1" else read_mt5(path)
            spread_info = {
                "source_column": "spread" if "spread" in df else None,
                "unit": "MT5 broker points (point_size requires symbol metadata)" if "spread" in df else None,
                "zero_count": int((df["spread"] == 0).sum()) if "spread" in df else None,
                "nonzero_count": int((df["spread"] != 0).sum()) if "spread" in df else None,
                "note": "No historical spread information in ForexTester M1 ZIP" if kind == "m1" else
                        "Zero may mean missing/unreported; never treat as proven zero execution cost.",
            }
            df = normalize(df)
            levels = ({"M1": None, **FREQS} if kind == "m1" else
                      ({"M5": None, "M15": "15min", "H1": "1h", "H4": "4h", "D1": "1D"}
                       if symbol in ("EURUSD", "USDJPY") else
                       {"M15": None, "H1": "1h", "H4": "4h", "D1": "1D"}))
            for tf, freq in levels.items():
                bars = df.reset_index() if freq is None else aggregate(df, freq)
                # Prevent accidentally treating M1-derived and MT5-derived bars as identical.
                out = dest / symbol / kind / tf / f"{symbol}_{kind}_{tf}.{args.format}"
                save(bars, out, args.format)
                rec = {"symbol": symbol, "source_kind": kind, "timeframe": tf,
                       "source_file": name, "source_sha256": sha256(path),
                       "output": str(out.relative_to(dest)), "output_sha256": sha256(out),
                       "bars": len(bars), "first": str(bars["time"].iloc[0]),
                       "last": str(bars["time"].iloc[-1]), "source_timezone": tz,
                       "spread": spread_info, "pip_size": cfg.get("pip_size"),
                       "resample": "left-labeled, left-closed, calendar aligned; partial bars retained"}
                records.append(rec)
                print(f"  {tf}: {len(bars):,} bars -> {out}", flush=True)
    manifest = {"schema_version": 1, "warning": "No spread is synthesized. Timezones are NOT assumed.",
                "sources": records}
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(records)} datasets, manifest: {dest / 'MANIFEST.json'}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default=".")
    p.add_argument("--output-dir", default="research/data/cache")
    p.add_argument("--format", choices=["parquet", "csv"], default="parquet")
    run(p.parse_args())
