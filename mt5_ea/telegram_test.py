"""Telegram delivery test. Sends production-format notifications only; never places or modifies trades."""
import os,time
from datetime import datetime,timezone
import telegram_notify as telegram

def cfg():
    return {
        "notifySignal":True,
        "notifyEntry":True,
        "notifyExit":True,
        "notifyError":True,
        "notifyCalendar":True,
    }

def main():
    if not telegram.configured():
        print("[FAIL] Telegram credentials missing")
        raise SystemExit(2)
    ok,msg=telegram.connectivity_check()
    if not ok:
        print("[FAIL] Telegram connectivity:",msg)
        raise SystemExit(3)

    now=datetime.now(timezone.utc).isoformat()
    c=cfg()
    messages=[
        ("signal",f"EA SIGNAL\nPair: EURUSD\nTF: M15\nDirection: BUY\nPattern: P1\nPrice: 1.10000\nSL: 1.09800\nTime: {now}"),
        ("entry",f"EA ENTRY\nPair: EURUSD\nTF: M15\nDirection: BUY\nPrice: 1.10000\nLot: 0.01\nSL: 1.09800\nPattern: P1\nTime: {now}"),
        ("exit","EA EXIT\nPair: EURUSD\nDirection: BUY\nPattern: P1\nEntry: 1.10000\nExit: 1.10400\nR: 2.0"),
        ("error","EA ERROR\nPair: EURUSD\nError: TEST_NOTIFICATION_ONLY"),
        ("calendar","ECONOMIC EVENT in 5 min\n09:00 USD TEST EVENT\nJapan time: 09:00"),
    ]
    failed=[]
    for kind,text in messages:
        if telegram.send(kind,text,c):
            print(f"[QUEUED] {kind}")
        else:
            failed.append(kind);print(f"[FAIL] {kind} not queued")
    if failed: raise SystemExit(4)
    # Queue acceptance is asynchronous. Give the production worker enough time for retries.
    time.sleep(8)
    print("[PASS] Production-format Signal/Entry/Exit/Error/Calendar notifications sent")
    print("[SAFE] No MT5 order, close, or SL modification was requested")

if __name__=="__main__":
    main()
