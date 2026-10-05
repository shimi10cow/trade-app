"""Non-blocking Telegram notifications for Hybrid EA."""
import os, queue, threading, time, logging
import requests

def _credentials():
    # Read at use-time so tests/relaunchers can refresh credentials without module reload.
    return os.getenv("EA_TELEGRAM_BOT_TOKEN","").strip(),os.getenv("EA_TELEGRAM_CHAT_ID","").strip()
_q=queue.Queue(maxsize=500)
_started=False
_lock=threading.Lock()
_last_error={}

def configured():
    token,chat_id=_credentials()
    return bool(token and chat_id)

def connectivity_check(timeout=5):
    """Validate both bot token and destination chat without sending a message."""
    token,chat_id=_credentials()
    if not token or not chat_id:return False,"credentials missing"
    try:
        r=requests.get(f"https://api.telegram.org/bot{token}/getMe",timeout=timeout);r.raise_for_status()
        r=requests.get(f"https://api.telegram.org/bot{token}/getChat",params={"chat_id":chat_id},timeout=timeout);r.raise_for_status()
        return True,"OK"
    except Exception as e:return False,str(e)

def _worker():
    while True:
        kind,text=_q.get()
        try:
            delivered=False
            for attempt in range(3):
                token,chat_id=_credentials()
                if not token or not chat_id:break
                try:
                    r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",data={"chat_id":chat_id,"text":text},timeout=5)
                    r.raise_for_status();delivered=True;break
                except Exception as e:
                    if attempt==2:logging.warning("Telegram notification failed after retries (%s): %s",kind,e)
                    else:time.sleep(1.5*(attempt+1))
            if not delivered and not configured():logging.warning("Telegram notification dropped (%s): credentials missing",kind)
        finally:
            _q.task_done()

def start():
    global _started
    with _lock:
        if not _started:
            threading.Thread(target=_worker,daemon=True,name="telegram-notify").start()
            _started=True

def enabled(cfg,kind):
    if not configured() or not isinstance(cfg,dict): return False
    key={"signal":"notifySignal","entry":"notifyEntry","exit":"notifyExit","error":"notifyError","calendar":"notifyCalendar"}.get(kind)
    return bool(key and cfg.get(key, True if kind=="calendar" else False))

def send(kind,text,cfg):
    if not enabled(cfg,kind): return False
    start()
    try:
        _q.put_nowait((kind,text))
        return True
    except queue.Full:
        logging.warning("Telegram queue full; dropped %s notification",kind)
        return False

def error(text,cfg,key=None,throttle_sec=900):
    k=key or text; now=time.time()
    if now-_last_error.get(k,0)<throttle_sec: return False
    _last_error[k]=now
    return send("error",text,cfg)
