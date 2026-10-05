import os

def main():
    import telegram_notify as n
    assert n.enabled({"notifySignal":True}, "unknown") is False
    if not n.configured():
        print("[WARN] Telegram credentials are not configured")
        return 2
    ok,detail=n.connectivity_check()
    if not ok:
        print("[FAIL] Telegram connectivity: "+detail)
        return 3
    assert n.enabled({"notifySignal":True},"signal") is True
    assert n.enabled({"notifyEntry":True},"entry") is True
    assert n.enabled({"notifyExit":True},"exit") is True
    assert n.enabled({"notifyError":True},"error") is True
    assert n.enabled({},"calendar") is True
    print("[PASS] Telegram token + chat verified")
    print("[PASS] Signal/Entry/Exit/Error/Calendar notification mapping loaded")
    return 0

if __name__=="__main__": raise SystemExit(main())
