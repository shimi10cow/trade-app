"""Read-only verification for all configured additional MT5 accounts."""
import json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).parent
cfg_path=ROOT/"mt5_accounts.json"
if not cfg_path.exists():
    raise SystemExit("FAIL: mt5_accounts.json not found; run setup_mt5_accounts.ps1 first")
rows=json.loads(cfg_path.read_text(encoding="utf-8-sig")).get("accounts",[])
bad=[]
for c in rows:
    req=json.dumps({"config":c,"magic":560001},ensure_ascii=False)
    r=subprocess.run([sys.executable,str(ROOT/"mt5_account_worker.py"),req],capture_output=True,text=True,timeout=20)
    try:x=json.loads(r.stdout or "{}")
    except Exception:x={"ok":False,"error":(r.stderr or r.stdout).strip()}
    if x.get("ok"):
        print(f"[PASS] {c['login']} / {c['server']}")
    else:
        bad.append(str(c["login"]));print(f"[FAIL] {c['login']} / {c['server']} : {x.get('error','unknown')}")
print()
print("RESULT:","PASS" if not bad else "LOGIN REQUIRED")
if bad:
    print("Login/check these terminals:",", ".join(bad));sys.exit(1)
