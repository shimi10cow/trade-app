#!/usr/bin/env python3
"""Import the five ChatGPT-generated candle ZIP archives into research/data/cache.

Refuses duplicate paths and path traversal. Verifies each ZIP member CRC.
Does not modify or synthesize any candle/spread value.
"""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

NAMES = ("EURUSD", "USDJPY", "JP225", "UK100", "US500")
ROOT = Path(__file__).resolve().parents[2]

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip-dir", required=True)
    ap.add_argument("--output", default=str(ROOT / "research/data/cache"))
    args = ap.parse_args()
    dest = Path(args.output).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    entries = []
    for sym in NAMES:
        zp = Path(args.zip_dir) / f"EA_cache_{sym}_20261020.zip"
        if not zp.is_file():
            raise FileNotFoundError(zp)
        with zipfile.ZipFile(zp) as z:
            bad = z.testzip()
            if bad:
                raise ValueError(f"Corrupt member in {zp}: {bad}")
            for member in z.infolist():
                if member.is_dir():
                    continue
                relative = Path(member.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"Unsafe member: {member.filename}")
                target = (dest / relative).resolve()
                if not target.is_relative_to(dest):
                    raise ValueError(f"Unsafe target: {target}")
                if target.exists():
                    raise FileExistsError(f"Refusing to overwrite: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as inp, target.open("wb") as out:
                    while chunk := inp.read(4 * 1024 * 1024):
                        out.write(chunk)
                entries.append({"path": str(target.relative_to(dest)),
                                "sha256": sha256(target), "bytes": target.stat().st_size,
                                "archive": zp.name})
    (dest / "UPLOAD_MANIFEST.json").write_text(
        json.dumps({"files": entries}, indent=2), encoding="utf-8")
    print(f"Imported {len(entries)} files to {dest}")
    print("Next: git lfs track 'research/data/cache/**/*.gz' 'research/data/cache/**/*.zip'")
    print("Then: git add .gitattributes research/data/cache && git commit && git push")

if __name__ == "__main__":
    main()
