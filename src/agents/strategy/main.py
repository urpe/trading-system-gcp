import time
import json
import logging
import os
import threading
from google.cloud import firestore, pubsub_v1
from google.api_core.exceptions import NotFound, AlreadyExists

# Importamos nuestro optimizador
from optimizer import StrategyOptimizer

# Configuración Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StrategyAgent')

PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# Configuración Pub/Sub
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()

# Nombres de recursos
TOPIC_NAME = f"projects/{PROJECT_ID}/topics/market-updates"
SUBSCRIPTION_NAME = f"projects/{PROJECT_ID}/subscriptions/strategy-sub"

# --- FUNCIÓN DE AUTO-REPARACIÓN (CREAR OREJAS) ---
def ensure_subscription_exists():
    """Asegura que la suscripción a Pub/Sub exista. Si no, la crea."""
    try:
        # Intentamos obtener la suscripción
        subscriber.get_subscription(request={"subscription": SUBSCRIPTION_NAME})
        logger.info("✅ La suscripción 'strategy-sub' ya existe.")
    except NotFound:
        logger.warning("⚠️ Suscripción no encontrada. Creando 'strategy-sub'...")
        try:
            subscriber.create_subscription(
                request={"name": SUBSCRIPTION_NAME, "topic": TOPIC_NAME}
            )
            logger.info("✅ Suscripción creada exitosamente.")
        except Exception as e:
            logger.error(f"❌ Error crítico creando suscripción: {e}")

# --- MEMORIA DEL ROBOT ---
STRATEGY_MEMORY = {} 
optimizer = StrategyOptimizer(db)

def optimize_cycle():
    """Ciclo de Optimización Walk-Forward (Cada 12h)"""
    while True:
        try:
            logger.info("🔄 Iniciando Ciclo de Optimización Walk-Forward...")
            docs = db.collection('market_data').stream()
            active_symbols = [d.id for d in docs]
            
            for symbol in active_symbols:
                fast, slow = optimizer.find_best_params(symbol)
                STRATEGY_MEMORY[symbol] = {
                    'fast': fast, 
                    'slow': slow,
                    'last_update': time.time()
                }
                # Guardar en BD (Opcional)
                db.collection('config').document('strategy_params').set(STRATEGY_MEMORY)
            
            logger.info("✅ Optimización completada. Durmiendo 12 horas.")
            time.sleep(43200)
            
        except Exception as e:
            logger.error(f"❌ Error en optimización: {e}")
            time.sleep(60)

# --- LÓGICA DE TRADING ---
def calculate_indicators(symbol, current_price):
    params = STRATEGY_MEMORY.get(symbol, {'fast': 10, 'slow': 30}) # Default
    
    docs = db.collection('historical_data').document(symbol).collection('1h')\
        .order_by('timestamp', direction=firestore.Query.DESCENDING).limit(params['slow'] + 20).stream()
    
    closes = [d.to_dict()['close'] for d in docs]
    closes.reverse()
    closes.append(current_price)
    
    if len(closes) < params['slow']: return None
    
    sma_fast = sum(closes[-params['fast']:]) / params['fast']
    sma_slow = sum(closes[-params['slow']:]) / params['slow']
    
    # RSI
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-15, len(closes)-1)]
    gains = sum(x for x in deltas if x > 0)
    losses = sum(abs(x) for x in deltas if x < 0)
    rsi = 50
    if losses > 0:
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        
    return {'sma_fast': sma_fast, 'sma_slow': sma_slow, 'rsi': rsi, 'params_used': params}

def callback(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        symbol = data['symbol']
        price = float(data['price'])
        
        indicators = calculate_indicators(symbol, price)
        if not indicators:
            message.ack()
            return

        sma_f = indicators['sma_fast']
        sma_s = indicators['sma_slow']
        rsi = indicators['rsi']
        params = indicators['params_used']
        
        signal = "HOLD"
        reason = ""
        
        if sma_f > sma_s and rsi < 70:
            signal = "BUY"
            reason = f"Golden Cross ({params['fast']}/{params['slow']}) + RSI {round(rsi,1)}"
        elif sma_f < sma_s:
            signal = "SELL"
            reason = f"Death Cross ({params['fast']}/{params['slow']})"

        if signal != "HOLD":
            logger.info(f"🔔 SEÑAL {symbol}: {signal} | Precio: {price} | Params: {params}")
            db.collection('signals').add({
                'symbol': symbol,
                'type': signal,
                'price': price,
                'reason': reason,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'strategy_params': params
            })

        message.ack()
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        message.ack()

if __name__ == '__main__':
    logger.info("🧠 CEREBRO V9.2 (Self-Healing) INICIADO")
    
    # 1. AUTO-REPARACIÓN: Crear suscripción si falta
    ensure_subscription_exists()
    
    # 2. Hilo Optimización
    opt_thread = threading.Thread(target=optimize_cycle)
    opt_thread.daemon = True
    opt_thread.start()
    
    # 3. Escuchar Mercado
    try:
        future = subscriber.subscribe(SUBSCRIPTION_NAME, callback=callback)
        future.result()
    except KeyboardInterrupt:
        future.cancel()