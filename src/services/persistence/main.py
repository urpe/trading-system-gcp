import os
import json
import time
from datetime import datetime
from src.shared.memory import memory # <--- SHARED CLIENT
from src.shared.database import init_db, SessionLocal, Signal, MarketSnapshot
from src.shared.utils import get_logger

# Configuración de Logs V17
logger = get_logger("PersistenceWorker")

# Inicializar Base de Datos Local
init_db()
logger.info("💾 Base de Datos Local (SQLite) Inicializada.")

# Configuración de Persistencia
WRITE_INTERVAL = 60  # Guardar snapshot cada 60 segundos por símbolo
last_db_write = {}

def process_market_data(message):
    """Procesa mensajes del canal market_data."""
    try:
        data = json.loads(message['data'])
        symbol = data['symbol']
        
        # Lógica de Throttling para Snapshots de Mercado
        now = time.time()
        if now - last_db_write.get(symbol, 0) > WRITE_INTERVAL:
            session = SessionLocal()
            try:
                snapshot = MarketSnapshot(
                    symbol=symbol,
                    price=float(data['price']),
                    volume_24h=float(data.get('volume', 0)),
                    change_24h=float(data.get('change', 0)),
                    timestamp=datetime.utcnow()
                )
                session.add(snapshot)
                session.commit()
                last_db_write[symbol] = now
                logger.info(f"💾 Snapshot guardado en SQLite para {symbol}")
            except Exception as e:
                logger.error(f"❌ Error escribiendo Snapshot DB: {e}")
            finally:
                session.close()
            
    except Exception as e:
        logger.error(f"Error procesando mensaje de mercado: {e}")

def process_signal(message):
    """Procesa señales de trading y las guarda en BD."""
    try:
        data = json.loads(message['data'])
        session = SessionLocal()
        try:
            signal = Signal(
                symbol=data.get('symbol'),
                signal_type=data.get('type'),
                price=float(data.get('price', 0)),
                reason=data.get('reason', 'N/A'),
                strategy=data.get('source', 'Unknown'),
                timestamp=datetime.utcnow()
            )
            session.add(signal)
            session.commit()
            logger.info(f"💾 Señal persistida: {data.get('type')} {data.get('symbol')}")
        except Exception as e:
            logger.error(f"❌ Error escribiendo Señal DB: {e}")
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error procesando señal: {e}")

def main():
    logger.info("💾 Persistence Worker v16.0 (Local Sovereignty) INICIADO")
    
    redis_conn = memory.get_client()
    if not redis_conn:
        logger.critical("🔥 Fallo conectando a Redis")
        return

    pubsub = redis_conn.pubsub()
    # Nos suscribimos a TODO lo que necesite guardarse
    pubsub.subscribe('market_data', 'signals')
    
    logger.info("✅ Suscrito a canales: market_data, signals. Esperando datos...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel']
            if channel == 'market_data':
                process_market_data(message)
            elif channel == 'signals':
                process_signal(message)

if __name__ == '__main__':
    time.sleep(5)
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"❌ Crash en loop principal: {e}")
            time.sleep(5)
