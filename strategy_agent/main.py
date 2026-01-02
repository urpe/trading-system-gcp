import os
import json
import pandas as pd
import numpy as np
from collections import deque
from google.cloud import pubsub_v1, firestore

# 1. CONFIGURACIÓN PROFESIONAL
PROJECT_ID = "mi-proyecto-trading-12345"
db = firestore.Client(project=PROJECT_ID)
SYMBOLS = ['btcusdt', 'ethusdt', 'solusdt', 'bnbusdt', 'xrpusdt']

# Memoria ultra-rápida para evitar la "Amnesia" y el lag de Pandas
# Guardamos los últimos 100 precios de cada moneda
history = {s: deque(maxlen=100) for s in SYMBOLS}

def calculate_indicators(prices):
    """Calcula indicadores sobre una lista de precios"""
    df = pd.DataFrame(prices, columns=['close'])
    # Ejemplo: Media Móvil Simple (SMA)
    df['sma'] = df['close'].rolling(window=14).mean()
    return df

def process_message(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        symbol = data['symbol'].lower()
        price = float(data['price'])
        
        # 1. Actualizar memoria del activo correspondiente
        if symbol in history:
            history[symbol].append(price)
            
            # 2. Lógica de Estrategia (Solo si hay datos suficientes)
            if len(history[symbol]) >= 20:
                df = calculate_indicators(list(history[symbol]))
                last_price = df['close'].iloc[-1]
                sma = df['sma'].iloc[-1]
                
                # Ejemplo de Estrategia: Cruce de precio con SMA
                action = None
                if last_price > sma: action = "BUY"
                elif last_price < sma: action = "SELL"
                
                if action:
                    print(f"🚀 SEÑAL {action} para {symbol.upper()} a ${price}")
                    # Guardar señal en Firestore para el Dashboard
                    db.collection("signals").add({
                        "symbol": symbol,
                        "action": action,
                        "price": price,
                        "timestamp": firestore.SERVER_TIMESTAMP
                    })
        
        message.ack() # Confirmar recepción a Pub/Sub
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        message.nack() # Reintentar si hay error

# 3. INICIO DEL SUSCRIPTOR (SISTEMA NERVIOSO)
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, "market-updates-sub")

print(f"✅ Strategy Agent v5.1.0 activo. Escuchando {SYMBOLS}...")

with subscriber:
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=process_message)
    try:
        streaming_pull_future.result()
    except Exception as e:
        print(f"⚠️ Suspensión de flujo: {e}")
        streaming_pull_future.cancel()
