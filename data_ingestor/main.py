import asyncio
import json
import os
import logging
import threading
import websockets
from flask import Flask
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

PROJECT_ID = os.environ.get('PROJECT_ID', 'default-project')
TOPIC_ID = os.environ.get('TOPIC_ID', 'default-topic')
TRADING_PAIR = os.environ.get('TRADING_PAIR', 'btcusdt')

BINANCE_WEBSOCKET_URI = f"wss://stream.binance.com:9443/ws/{TRADING_PAIR}@trade"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

async def binance_ws_client():
    logging.info(f"Iniciando cliente WebSocket para {TRADING_PAIR}...")
    while True:
        try:
            async with websockets.connect(BINANCE_WEBSOCKET_URI) as websocket:
                logging.info(f"Conectado a {BINANCE_WEBSOCKET_URI}")
                while True:
                    try:
                        message_str = await websocket.recv()
                        message_json = json.loads(message_str)
                        trade_data = {
                            "event_type": message_json.get("e"),
                            "event_time": message_json.get("E"),
                            "symbol": message_json.get("s"),
                            "trade_id": message_json.get("t"),
                            "price": message_json.get("p"),
                            "quantity": message_json.get("q"),
                            "trade_time": message_json.get("T"),
                            "is_buyer_maker": message_json.get("m"),
                        }
                        data_to_publish = json.dumps(trade_data).encode('utf-8')
                        future = publisher.publish(topic_path, data_to_publish)
                        future.result()
                        logging.info(f"Publicado: Precio de {trade_data['symbol']} es {trade_data['price']}")
                    except websockets.exceptions.ConnectionClosed:
                        logging.warning("Conexion cerrada. Reconectando...")
                        break
                    except Exception as e:
                        logging.error(f"Error procesando mensaje: {e}")
        except Exception as e:
            logging.error(f"Error en conexion WebSocket: {e}. Reintentando en 5 segundos...")
            await asyncio.sleep(5)

def run_ws_client():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(binance_ws_client())

@app.route('/')
def index():
    return f"Agente de Ingesta para {TRADING_PAIR} activo.", 200

# Iniciar el cliente WebSocket en un hilo separado al cargar el modulo
ws_thread = threading.Thread(target=run_ws_client, daemon=True)
ws_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
