import os
import json
import logging
import threading
from flask import Flask
from google.cloud import pubsub_v1
from binance.client import Client
from binance.exceptions import BinanceAPIException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

try:
    PROJECT_ID = os.environ['PROJECT_ID']
    SUBSCRIPTION_ID_SIGNALS = os.environ['SUBSCRIPTION_ID_SIGNALS']
    BINANCE_API_KEY = os.environ['BINANCE_API_KEY']
    BINANCE_API_SECRET = os.environ['BINANCE_API_SECRET']
except KeyError as e:
    logging.error(f"Error: La variable de entorno {e} no está definida.")
    exit("Faltan variables de entorno críticas.")

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID_SIGNALS)

try:
    binance_client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)
    logging.info("Cliente de Binance Testnet inicializado correctamente.")
    status = binance_client.get_system_status()
    logging.info(f"Estado del sistema Binance Testnet: {status['msg']}")
except BinanceAPIException as e:
    logging.error(f"Error al conectar con Binance Testnet: {e}")
    exit("No se pudo inicializar el cliente de Binance.")

def process_signal(message):
    try:
        signal_str = message.data.decode('utf-8')
        signal = json.loads(signal_str)
        logging.info(f"Señal recibida: {signal}")

        action = signal.get('action')
        symbol = signal.get('symbol')
        quantity = signal.get('quantity')

        if not all([action, symbol, quantity]):
            logging.error("La señal recibida es inválida o incompleta.")
            message.ack()
            return

        side = Client.SIDE_BUY if action == 'BUY' else Client.SIDE_SELL

        logging.warning(f"Ejecutando orden de PRUEBA: {action} {quantity} {symbol}")
        try:
            test_order = binance_client.create_test_order(
                symbol=symbol,
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=quantity
            )
            logging.info(f"Orden de prueba enviada con éxito. Respuesta: {test_order}")
        except BinanceAPIException as e:
            logging.error(f"Error al ejecutar la orden en Binance: {e}")
        except Exception as e:
            logging.error(f"Error inesperado al procesar la orden: {e}")

        message.ack()
    except Exception as e:
        logging.error(f"Error fatal procesando la señal: {e}", exc_info=True)
        message.nack()

def run_subscriber():
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=process_signal)
    logging.info(f"Escuchando señales en la suscripción: {subscription_path}...")
    try:
        streaming_pull_future.result()
    except Exception as e:
        logging.error(f"Error en el suscriptor de señales: {e}")
        streaming_pull_future.cancel()

@app.route('/')
def index():
    return "Agente de Órdenes (v1 - Testnet) está activo.", 200

if __name__ == "__main__":
    subscriber_thread = threading.Thread(target=run_subscriber, daemon=True)
    subscriber_thread.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
