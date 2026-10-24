"""Self-update for the live EA PC (2026-10-24). Python standard library only, so it also runs before anything else is set up.

  py updater.py <install folder>            download the program files of GitHub main into <install folder>\\app if main changed
  py updater.py <install folder> --check    print 'update' when main changed (no download)

Only the files the EA needs are fetched (mt5_ea, research/env_recognition, research/core), a few MB, into a fresh folder that
replaces the old one only when every file arrived. The commit is written to app\\VERSION. EA records are not in this folder
(they live in %USERPROFILE%\\TradeEA_data), so an update never touches them.
"""
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

REPO = os.getenv('EA_REPO', 'shimi10cow/trade-app')
BRANCH = os.getenv('EA_BRANCH', 'main')
KEEP = ('mt5_ea/', 'research/env_recognition/', 'research/core/', 'research/__init__.py')
EXT = ('.py', '.ps1', '.bat', '.txt', '.md', '.json')


def get(url, binary=False):
    req = urllib.request.Request(url, headers={'User-Agent': 'TradeEA-updater', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else json.loads(data.decode('utf-8'))


def latest_sha():
    return get(f'https://api.github.com/repos/{REPO}/commits/{BRANCH}')['sha']


def current_sha(app):
    f = Path(app) / 'VERSION'
    return f.read_text().strip() if f.exists() else ''


def update(root):
    root = Path(root); app = root / 'app'
    sha = latest_sha()
    if sha == current_sha(app):
        print('up to date', sha[:7]); return False
    tree = get(f'https://api.github.com/repos/{REPO}/git/trees/{sha}?recursive=1')['tree']
    files = [t['path'] for t in tree if t['type'] == 'blob' and t['path'].startswith(KEEP) and t['path'].endswith(EXT)]
    new = root / 'app_new'
    shutil.rmtree(new, ignore_errors=True)
    for p in files:
        dst = new / p; dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(get(f'https://raw.githubusercontent.com/{REPO}/{sha}/{p}', binary=True))
    (new / 'VERSION').write_text(sha)
    old = root / 'app_old'
    shutil.rmtree(old, ignore_errors=True)
    if app.exists():
        app.rename(old)
    new.rename(app)
    print(f'updated to {sha[:7]} ({len(files)} files)')
    return True


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent)
    try:
        if '--check' in sys.argv:
            print('update' if latest_sha() != current_sha(Path(root) / 'app') else 'same')
        else:
            update(root)
    except Exception as e:          # no network: keep running the program that is already there
        print('update check failed:', e)
