import time
import json
import logging
import os
import threading
from google.cloud import firestore, pubsub_v1
from google.api_core.exceptions import NotFound

# Importamos optimizador existente
from optimizer import StrategyOptimizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StrategyAgent')

PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# Pub/Sub
subscriber = pubsub_v1.SubscriberClient()
SUBSCRIPTION_NAME = f"projects/{PROJECT_ID}/subscriptions/strategy-sub"
TOPIC_NAME = f"projects/{PROJECT_ID}/topics/market-updates"

# --- CONTROL DE TRÁFICO (SOLUCIÓN AL ERROR 400) ---
LAST_PROCESSED = {} 
COOLDOWN_SECONDS = 60 # Analizar solo 1 vez por minuto por moneda

STRATEGY_MEMORY = {} 
optimizer = StrategyOptimizer(db)

def ensure_subscription_exists():
    try:
        subscriber.get_subscription(request={"subscription": SUBSCRIPTION_NAME})
    except NotFound:
        try:
            subscriber.create_subscription(request={"name": SUBSCRIPTION_NAME, "topic": TOPIC_NAME})
            logger.info("✅ Suscripción creada.")
        except Exception:
            pass

def optimize_cycle():
    while True:
        try:
            # Lógica simple de optimización para mantener el hilo vivo
            time.sleep(43200) # 12 horas
        except Exception:
            time.sleep(60)

def calculate_indicators(symbol, current_price):
    # Lógica simplificada para evitar lecturas masivas
    try:
        params = STRATEGY_MEMORY.get(symbol, {'fast': 10, 'slow': 30})
        # Leemos solo lo necesario
        docs = db.collection('historical_data').document(symbol).collection('1h')\
            .order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50).stream()
        
        closes = [d.to_dict()['close'] for d in docs]
        if not closes: return None
        closes.reverse()
        closes.append(current_price)

        if len(closes) < 30: return None

        # Medias Móviles Simples (SMA)
        sma_fast = sum(closes[-params['fast']:]) / params['fast']
        sma_slow = sum(closes[-params['slow']:]) / params['slow']
        
        # RSI Simple
        deltas = [closes[i+1] - closes[i] for i in range(len(closes)-15, len(closes)-1)]
        gains = sum(x for x in deltas if x > 0)
        losses = sum(abs(x) for x in deltas if x < 0)
        rsi = 50
        if losses > 0:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))
            
        return {'sma_fast': sma_fast, 'sma_slow': sma_slow, 'rsi': rsi, 'params': params}
    except Exception:
        return None

def callback(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        symbol = data['symbol']
        price = float(data['price'])
        
        # --- FILTRO CRÍTICO ---
        now = time.time()
        if now - LAST_PROCESSED.get(symbol, 0) < COOLDOWN_SECONDS:
            message.ack()
            return
        LAST_PROCESSED[symbol] = now
        # ----------------------

        indicators = calculate_indicators(symbol, price)
        if indicators:
            sma_f = indicators['sma_fast']
            sma_s = indicators['sma_slow']
            rsi = indicators['rsi']
            
            signal = "HOLD"
            reason = ""
            
            # Lógica
            if sma_f > sma_s and rsi < 70:
                signal = "BUY"
                reason = "Golden Cross"
            elif sma_f < sma_s:
                signal = "SELL"
                reason = "Death Cross"
            elif rsi > 80:
                signal = "SELL"
                reason = "RSI Overbought"

            if signal != "HOLD":
                logger.info(f"🔔 {symbol}: {signal} | ${price} | RSI {round(rsi,1)}")
                # Guardar señal
                db.collection('signals').add({
                    'symbol': symbol,
                    'type': 'TREND',
                    'signal': signal,
                    'price': price,
                    'reason': reason,
                    'timestamp': firestore.SERVER_TIMESTAMP
                })

        message.ack()
    except Exception:
        message.ack()

if __name__ == '__main__':
    logger.info("🧠 CEREBRO REPARADO (Anti-Colapso) INICIADO")
    ensure_subscription_exists()
    
    t = threading.Thread(target=optimize_cycle)
    t.daemon = True
    t.start()
    
    future = subscriber.subscribe(SUBSCRIPTION_NAME, callback=callback)
    try:
        future.result()
    except KeyboardInterrupt:
        future.cancel()







        