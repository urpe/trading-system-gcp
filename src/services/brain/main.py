import time
import random
import os
import logging
from datetime import datetime, timezone
from google.cloud import firestore
# FIX: Usar la configuración centralizada V13
from src.config.settings import config
from src.shared.utils import get_logger

# Configuración logger V13
logger = get_logger("BrainSvc")

try:
    db = firestore.Client(project=config.PROJECT_ID)
except Exception as e:
    logger.critical(f"DB Error: {e}")
    db = None

def analyze_market():
    if not db: return
    try:
        # Lógica V14: Generar señal simulada basada en "Market Data" (Simulado por ahora)
        # En el futuro, aquí leerás de la colección 'market_data'
        simulated_assets = [
            {"symbol": "BTC", "price": 91000.0},
            {"symbol": "ETH", "price": 3050.0},
            {"symbol": "SOL", "price": 132.0},
            {"symbol": "XRP", "price": 2.10}
        ]
        
        asset = random.choice(simulated_assets)
        rsi = random.uniform(20, 80)
        
        signal_type = None
        if rsi < 30: signal_type = "BUY"
        elif rsi > 70: signal_type = "SELL"
            
        if signal_type:
            signal = {
                "symbol": asset['symbol'],
                "type": signal_type,
                "price": asset['price'],
                "timestamp": datetime.now(timezone.utc),
                "source": "BrainV14",
                "reason": f"RSI Strategy ({rsi:.1f})"
            }
            db.collection('signals').add(signal)
            logger.info(f"🧠 SIGNAL: {signal_type} {asset['symbol']} (RSI: {rsi:.1f})")
            
    except Exception as e:
        logger.error(f"Error en ciclo de cerebro: {e}")

if __name__ == '__main__':
    logger.info("🧠 Brain V14 (Resurrected) Started...")
    while True:
        analyze_market()
        time.sleep(10)
