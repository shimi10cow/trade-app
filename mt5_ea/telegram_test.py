import os, importlib

def main():
    os.environ.setdefault("EA_TELEGRAM_BOT_TOKEN","")
    os.environ.setdefault("EA_TELEGRAM_CHAT_ID","")
    import telegram_notify as n
    assert n.enabled({}, "signal") is False
    assert n.enabled({"notifySignal":True}, "unknown") is False
    print("[PASS] Telegram fail-closed without credentials")
    print("[PASS] Telegram event toggle mapping loaded")

if __name__=="__main__": main()
