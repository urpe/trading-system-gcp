import sys
import traceback
import time
import logging
import os
import threading
import numpy as np
import pandas as pd
from flask import Flask, jsonify
from google.cloud import firestore

# Configuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PairsTrading')

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# Parámetros de la Estrategia
WINDOW_SIZE = 24       # Horas para calcular correlación
Z_THRESHOLD = 2.0      # Cuánto debe estirarse la liga para operar
CORRELATION_MIN = 0.8  # Mínima similitud para considerarlos "pareja"

def get_historical_prices():
    """Descarga precios de las últimas 24h para todas las monedas activas"""
    try:
        # 1. Ver qué monedas están activas en Market Data
        active_docs = db.collection('market_data').stream()
        symbols = [d.id for d in active_docs]
        
        price_data = {}
        
        # 2. Bajar historial reciente para cada una
        for sym in symbols:
            docs = db.collection('historical_data').document(sym).collection('1h')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING).limit(WINDOW_SIZE).stream()
            
            prices = [d.to_dict()['close'] for d in docs]
            if len(prices) >= WINDOW_SIZE:
                price_data[sym] = list(reversed(prices)) # Ordenar cronológicamente
                
        return pd.DataFrame(price_data)
    except Exception as e:
        logger.error(f"Error bajando datos: {e}")
        return pd.DataFrame()

def analyze_pairs():
    """Busca oportunidades de arbitraje"""
    while True:
        try:
            logger.info("🔍 Buscando pares correlacionados...")
            df = get_historical_prices()
            
            if df.empty or len(df.columns) < 2:
                logger.warning("Datos insuficientes. Esperando...")
                time.sleep(60)
                continue

            # 1. Matriz de Correlación
            corr_matrix = df.corr()
            
            # 2. Buscar pares con alta correlación (> 0.8)
            opportunities = []
            checked = set()
            
            for asset_a in df.columns:
                for asset_b in df.columns:
                    if asset_a == asset_b: continue
                    pair_key = tuple(sorted([asset_a, asset_b]))
                    if pair_key in checked: continue
                    checked.add(pair_key)
                    
                    score = corr_matrix.loc[asset_a, asset_b]
                    
                    if score > CORRELATION_MIN:
                        # Son pareja! Calculemos el Spread (Diferencia)
                        # Normalizamos precios para compararlos
                        series_a = df[asset_a] / df[asset_a].iloc[0]
                        series_b = df[asset_b] / df[asset_b].iloc[0]
                        
                        spread = series_a - series_b
                        z_score = (spread.iloc[-1] - spread.mean()) / spread.std()
                        
                        signal = "NEUTRAL"
                        if z_score > Z_THRESHOLD:
                            # A está muy caro respecto a B -> Vender A, Comprar B
                            signal = f"SHORT {asset_a} / LONG {asset_b}"
                        elif z_score < -Z_THRESHOLD:
                            # A está muy barato respecto a B -> Comprar A, Vender B
                            signal = f"LONG {asset_a} / SHORT {asset_b}"
                        
                        if signal != "NEUTRAL":
                            logger.info(f"⚡ OPORTUNIDAD: {signal} (Corr: {round(score,2)}, Z: {round(z_score,2)})")
                            
                            # Guardar señal especial
                            db.collection('signals').add({
                                'type': 'PAIR_TRADE', # Tipo especial
                                'symbol': f"{asset_a}-{asset_b}",
                                'signal': signal,
                                'z_score': round(z_score, 2),
                                'correlation': round(score, 2),
                                'timestamp': firestore.SERVER_TIMESTAMP
                            })

            logger.info("✅ Análisis de pares completado. Durmiendo 5 min.")
            time.sleep(300) # Revisar cada 5 minutos

        except Exception as e:
            logger.error(f"Error en loop de pares: {e}")
            time.sleep(60)

@app.route('/')
def health():
    return jsonify({"status": "online", "service": "pairs-trading-v9.3"})

if __name__ == '__main__':
    # Iniciar cerebro en segundo plano
    thread = threading.Thread(target=analyze_pairs)
    thread.daemon = True
    thread.start()
    
    app.run(host='0.0.0.0', port=5000)