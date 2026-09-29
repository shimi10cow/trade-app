"""Non-blocking Telegram notifications for Hybrid EA."""
import os, queue, threading, time, logging
import requests

TOKEN=os.getenv("EA_TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID=os.getenv("EA_TELEGRAM_CHAT_ID","").strip()
_q=queue.Queue(maxsize=500)
_started=False
_lock=threading.Lock()
_last_error={}

def configured(): return bool(TOKEN and CHAT_ID)

def _worker():
    while True:
        kind,text=_q.get()
        try:
            if configured():
                r=requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":text},timeout=5)
                r.raise_for_status()
        except Exception as e:
            logging.warning("Telegram notification failed: %s",e)
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
