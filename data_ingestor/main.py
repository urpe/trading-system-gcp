#!/usr/bin/env python3
import os, json, logging, asyncio, websockets, threading
from datetime import datetime
from flask import Flask, jsonify
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)

PROJECT_ID = os.environ.get('PROJECT_ID', 'mi-proyecto-trading-12345')
TOPIC_ID = os.environ.get('TOPIC_ID', 'datos-crudos')
TRADING_PAIR = os.environ.get('TRADING_PAIR', 'btcusdt').lower()

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

async def binance_ingestor():
    uri = f"wss://stream.binance.com:9443/ws/{TRADING_PAIR}@ticker"
    logger.info(f"Iniciando ingesta para {TRADING_PAIR.upper()}")
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"Conectado a Binance para {TRADING_PAIR.upper()}")
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    payload = {
                        "symbol": data['s'],
                        "price": float(data['c']),
                        "high": float(data['h']),
                        "low": float(data['l']),
                        "volume": float(data['v']),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    data_str = json.dumps(payload).encode("utf-8")
                    publisher.publish(topic_path, data_str)
        except Exception as e:
            logger.error(f"Error: {e}")
            await asyncio.sleep(5)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "pair": TRADING_PAIR.upper()}), 200

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(binance_ingestor())

if __name__ == "__main__":
    new_loop = asyncio.new_event_loop()
    t = threading.Thread(target=start_background_loop, args=(new_loop,))
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
