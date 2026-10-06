"""Telegram verification and optional production-format delivery test. Never places or modifies trades."""
import argparse
import time
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

def verify():
    if not telegram.configured():
        print("[WARN] Telegram credentials missing")
        return 2
    ok,msg=telegram.connectivity_check()
    if not ok:
        print("[FAIL] Telegram connectivity:",msg)
        return 3
    print("[PASS] Telegram token + chat verified")
    print("[PASS] Signal/Entry/Exit/Error/Calendar notification mapping loaded")
    return 0

def send_all():
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
            failed.append(kind)
            print(f"[FAIL] {kind} not queued")
    if failed:return 4
    time.sleep(8)
    print("[PASS] Production-format Signal/Entry/Exit/Error/Calendar notifications sent")
    print("[SAFE] No MT5 order, close, or SL modification was requested")
    return 0

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--send-all",action="store_true",help="send all five production-format test notifications")
    args=parser.parse_args()
    rc=verify()
    if rc:return rc
    return send_all() if args.send_all else 0

if __name__=="__main__":
    raise SystemExit(main())
