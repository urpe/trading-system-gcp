import time
import threading
from datetime import datetime, timezone
from google.cloud import firestore
from src.config.settings import config
from src.shared.utils import get_logger, robust_http_request

logger = get_logger("OrdersSvc")
db = firestore.Client(project=config.PROJECT_ID)
processed_ids = set()

def execute_order(signal: dict):
    # Decodificación Inteligente
    raw = str(signal).upper()
    side = 'BUY' if 'BUY' in raw else 'SELL' if 'SELL' in raw else None
    
    if not side:
        logger.warning(f"🤷 Unknown intent: {signal}")
        return

    price = float(signal.get('price', 0))
    if price <= 0: return

    payload = {
        "symbol": signal['symbol'],
        "side": side,
        "price": price,
        "amount": config.TRADE_AMOUNT / price
    }
    
    try:
        url = f"{config.SVC_PORTFOLIO}/update"
        resp = robust_http_request('POST', url, json_data=payload)
        if resp.status_code == 200:
            logger.info(f"🚀 EXECUTED: {side} {signal['symbol']}")
    except Exception as e:
        logger.error(f"💀 Failed: {e}")

def signal_handler(doc_id, data):
    if doc_id in processed_ids: return
    processed_ids.add(doc_id)
    if len(processed_ids) > 2000: processed_ids.clear()
    
    # Filtro de tiempo (Python side)
    ts = data.get('timestamp')
    if ts:
        try:
            if hasattr(ts, 'timestamp'): ts = ts.timestamp()
            now = datetime.now(timezone.utc).timestamp()
            if (now - ts) > 300: return # Ignorar viejas (>5min)
        except: pass

    logger.info(f"📨 Signal: {data.get('symbol')}")
    execute_order(data)

def start_listener():
    logger.info("📡 Listening for signals...")
    # Listener Híbrido V13
    ref = db.collection('signals').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10)
    
    def on_snapshot(col_snap, changes, read_time):
        for change in reversed(changes):
            if change.type.name in ['ADDED', 'MODIFIED']:
                t = threading.Thread(target=signal_handler, args=(change.document.id, change.document.to_dict()))
                t.start()
                
    ref.on_snapshot(on_snapshot)
    while True: time.sleep(1)

if __name__ == '__main__':
    start_listener()
