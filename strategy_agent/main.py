import os
import json
import logging
import threading
from concurrent.futures import TimeoutError
from flask import Flask
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO, format='%(asctime )s - %(levelname)s - %(message)s')
app = Flask(__name__)

PROJECT_ID = os.environ.get('PROJECT_ID', 'default-project')
SUBSCRIPTION_ID = os.environ.get('SUBSCRIPTION_ID', 'default-sub')
TOPIC_ID_SIGNALS = os.environ.get('TOPIC_ID_SIGNALS', 'default-topic-signals')

publisher = pubsub_v1.PublisherClient()
topic_path_signals = publisher.topic_path(PROJECT_ID, TOPIC_ID_SIGNALS)
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

last_price = None
PRICE_CHANGE_THRESHOLD = 0.001

def process_market_data(message):
    global last_price
    try:
        data_str = message.data.decode('utf-8')
        trade_data = json.loads(data_str)
        current_price = float(trade_data.get('price', 0))
        symbol = trade_data.get('symbol', 'UNKNOWN')
        logging.info(f"Dato recibido para {symbol}: Precio = {current_price}")

        if last_price is not None:
            price_change = (current_price - last_price) / last_price
            if price_change > PRICE_CHANGE_THRESHOLD:
                signal = {
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": 0.001,
                    "reason": f"Price increased by {price_change:.4f}",
                    "timestamp": trade_data.get('trade_time')
                }
                signal_data = json.dumps(signal).encode('utf-8')
                future = publisher.publish(topic_path_signals, signal_data)
                future.result()
                logging.warning(f"SENAL DE COMPRA GENERADA! Precio: {current_price}")

        last_price = current_price
        message.ack()
    except Exception as e:
        logging.error(f"Error procesando mensaje: {e}")
        message.nack()

def run_subscriber():
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=process_market_data)
    logging.info(f"Escuchando mensajes en: {subscription_path}...")
    try:
        streaming_pull_future.result()
    except Exception as e:
        logging.error(f"Error en suscriptor: {e}")
        streaming_pull_future.cancel()

@app.route('/')
def index():
    return "Agente de Estrategias activo.", 200

subscriber_thread = threading.Thread(target=run_subscriber, daemon=True)
subscriber_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
