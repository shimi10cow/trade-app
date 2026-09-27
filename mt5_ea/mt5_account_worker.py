"""Isolated MT5 reader for one additional account. Never places or modifies orders."""
import json,os,sys,pathlib
import MetaTrader5 as mt5
from mt5_position_sync import _scan_connected

def main():
    req=json.loads(sys.argv[1]);cfg=req["config"];magic=int(req["magic"])
    login=int(cfg["login"]);server=str(cfg["server"]);path=str(cfg.get("terminalPath") or "")
    password=""
    env=str(cfg.get("passwordEnv") or "")
    if env:password=os.getenv(env,"")
    # Preferred mode: each copied terminal is logged in once by the user and keeps
    # its own saved credentials. No trading password needs to be stored in this app.
    if password:
        kwargs={"login":login,"server":server,"password":password}
        ok=mt5.initialize(path,**kwargs) if path else mt5.initialize(**kwargs)
    else:
        ok=mt5.initialize(path) if path else mt5.initialize()
    if not ok:raise RuntimeError(f"initialize failed: {mt5.last_error()}")
    try:
        a=mt5.account_info()
        if not a or str(a.login)!=str(login) or str(a.server)!=server:raise RuntimeError("account/server lock mismatch")
        state=pathlib.Path(__file__).parent/f"mt5_position_sync_{server.replace(' ','_').replace('/','_')}_{login}.json"
        print(json.dumps({"ok":True,"events":_scan_connected(magic,state)},ensure_ascii=False))
    finally:mt5.shutdown()
if __name__=="__main__":
    try:main()
    except Exception as e:
        print(json.dumps({"ok":False,"error":str(e)},ensure_ascii=False));sys.exit(1)
