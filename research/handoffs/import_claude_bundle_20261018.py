#!/usr/bin/env python3
"""Upload the extracted Claude EA research bundle to the current git repository.

Run from a local clone with GitHub push access:
  python research/handoffs/import_claude_bundle_20261018.py /path/to/EA_Claude_handoff_research_20261018.zip

This does NOT run any backtests. It imports original research artifacts intact.
"""
from pathlib import Path
import hashlib, json, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "research" / "handoffs" / "ea_bundle_20261018"
MAX_FILE = 95 * 1024 * 1024

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python research/handoffs/import_claude_bundle_20261018.py <bundle.zip>")
    source = Path(sys.argv[1]).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Archive not found: {source}")
    TARGET.mkdir(parents=True, exist_ok=True)
    manifest = []
    with zipfile.ZipFile(source) as z:
        for entry in z.infolist():
            if entry.is_dir():
                continue
            p = Path(entry.filename)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError(f"Unsafe archive path: {entry.filename}")
            if entry.file_size > MAX_FILE:
                raise ValueError(f"File too large for standard GitHub push: {entry.filename}")
            raw = z.read(entry)
            dest = TARGET / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            manifest.append({"path":str(p), "bytes":len(raw), "sha256":hashlib.sha256(raw).hexdigest()})
    manifest.sort(key=lambda d:d["path"])
    (TARGET/"MANIFEST.json").write_text(json.dumps({"archive":source.name,"file_count":len(manifest),"files":manifest},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Imported {len(manifest)} files to {TARGET}")
    print("Next:")
    print("  git add research/handoffs/ea_bundle_20261018 research/handoffs/import_claude_bundle_20261018.py")
    print("  git commit -m 'data: import EA research artifacts for Claude handoff'")
    print("  git push origin main")
    print("Verify on GitHub that MANIFEST.json and all research files exist.")

if __name__ == "__main__":
    main()
