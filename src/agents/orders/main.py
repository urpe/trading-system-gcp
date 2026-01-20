import time
import logging
import os
import threading
from datetime import datetime, timezone
import requests
from google.cloud import firestore

# Configuración Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('OrdersAgent')

PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# URL del Portfolio Agent (Ahora delegamos la lógica contable a él)
PORTFOLIO_URL = os.environ.get("PORTFOLIO_URL", "http://portfolio:8080")

# --- CONFIGURACIÓN ---
TRADE_AMOUNT_USDT = 2000.0  # Tamaño fijo por operación ($2000)

def initialize_wallet():
    """Crea la billetera si no existe"""
    try:
        requests.get(f"{PORTFOLIO_URL}/balance", timeout=5)
        logger.info("✅ Conexión con Portfolio Agent establecida.")
    except Exception as e:
        logger.warning(f"⚠️ Esperando al Portfolio Agent... ({e})")

def execute_trade_via_api(signal_data):
    """Delega la ejecución al Portfolio Agent (Quien sabe manejar Shorts)"""
    symbol = signal_data['symbol']
    # Normalizamos la señal: 'TREND BUY' -> 'BUY', 'TREND SELL' -> 'SELL'
    signal_type = signal_data.get('signal', signal_data.get('type', 'HOLD')).split(' ')[-1]
    
    if signal_type not in ['BUY', 'SELL']:
        return

    price = float(signal_data['price'])
    
    # Calculamos cantidad basada en monto fijo de $2000
    amount = TRADE_AMOUNT_USDT / price
    
    payload = {
        'symbol': symbol,
        'side': signal_type,
        'price': price,
        'amount': amount
    }
    
    try:
        # Enviamos la orden al experto contable (Portfolio Agent)
        response = requests.post(f"{PORTFOLIO_URL}/update", json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ ORDEN EJECUTADA: {signal_type} {symbol} | Cantidad: {round(amount, 4)} | ${price}")
        else:
            logger.error(f"❌ Orden rechazada por Portfolio: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error de conexión con Portfolio: {e}")

def listen_for_signals():
    """Escucha la colección de señales en tiempo real"""
    # Usamos hora UTC actual para filtrar señales viejas al arrancar
    now = datetime.now(timezone.utc)
    
    signals_ref = db.collection('signals').where('timestamp', '>', now)
    
    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                signal_data = change.document.to_dict()
                logger.info(f"📩 Procesando señal: {signal_data.get('type')} {signal_data.get('symbol')}")
                threading.Thread(target=execute_trade_via_api, args=(signal_data,)).start()

    signals_ref.on_snapshot(on_snapshot)
    
    while True:
        time.sleep(1)

if __name__ == '__main__':
    logger.info("👐 AGENTE DE ÓRDENES V10 (API Mode) INICIADO")
    initialize_wallet()
    listen_for_signals()