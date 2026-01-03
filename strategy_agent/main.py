import os
import json
import threading
from collections import defaultdict
from flask import Flask, jsonify
from google.cloud import pubsub_v1, firestore

app = Flask(__name__)
db = firestore.Client(project="mi-proyecto-trading-12345")

# Almacén de precios históricos para calcular SMA
price_history = defaultdict(list)
signal_count = defaultdict(int)
SMA_SHORT = 5
SMA_LONG = 20

def calculate_sma(prices, period):
    """Calcula la Media Móvil Simple"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def generate_signal(symbol, price):
    """Genera señales de trading basadas en cruce de SMAs"""
    price_history[symbol].append(price)
    
    # Mantener solo los últimos 50 precios
    if len(price_history[symbol]) > 50:
        price_history[symbol] = price_history[symbol][-50:]
    
    sma_short = calculate_sma(price_history[symbol], SMA_SHORT)
    sma_long = calculate_sma(price_history[symbol], SMA_LONG)
    
    if sma_short is None or sma_long is None:
        return "HOLD", f"Acumulando datos ({len(price_history[symbol])}/20)"
    
    # Señal de compra: SMA corta cruza por encima de SMA larga (1% margen)
    if sma_short > sma_long * 1.01:
        return "BUY", f"SMA{SMA_SHORT}={sma_short:.2f} > SMA{SMA_LONG}={sma_long:.2f}"
    # Señal de venta: SMA corta cruza por debajo de SMA larga (1% margen)
    elif sma_short < sma_long * 0.99:
        return "SELL", f"SMA{SMA_SHORT}={sma_short:.2f} < SMA{SMA_LONG}={sma_long:.2f}"
    else:
        return "HOLD", "SMAs convergentes"

def callback(message):
    """Procesa mensajes de Pub/Sub y genera señales"""
    try:
        data = json.loads(message.data.decode('utf-8'))
        symbol = data.get('symbol', '')
        price = float(data.get('price', 0))
        
        if not symbol or price <= 0:
            message.ack()
            return
        
        signal, reason = generate_signal(symbol, price)
        signal_count[symbol] += 1
        
        # Guardar señal en Firestore
        db.collection('signals').add({
            'symbol': symbol,
            'price': price,
            'signal': signal,
            'reason': reason,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        # Log sin caracteres de escape problemáticos
        print(f"[{symbol}] {signal} @ ${price:.2f} - {reason}")
        message.ack()
        
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        message.ack()

def start_subscriber():
    """Inicia el suscriptor de Pub/Sub"""
    try:
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path("mi-proyecto-trading-12345", "market-updates-sub")
        streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
        print(f"Escuchando mensajes en {subscription_path}...")
        streaming_pull_future.result()
    except Exception as e:
        print(f"Error en suscriptor: {e}")

@app.route('/')
def health():
    return "Strategy Agent Alive", 200

@app.route('/status')
def status():
    """Endpoint para ver el estado del agente"""
    return jsonify({
        "status": "running",
        "symbols_tracked": list(price_history.keys()),
        "data_points": {k: len(v) for k, v in price_history.items()},
        "signals_generated": dict(signal_count)
    })

if __name__ == '__main__':
    # Iniciar suscriptor en hilo separado
    threading.Thread(target=start_subscriber, daemon=True).start()
    
    # Servidor web principal
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
