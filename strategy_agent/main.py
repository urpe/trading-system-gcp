import os
import json
import threading
from collections import defaultdict
from flask import Flask
from google.cloud import pubsub_v1, firestore

app = Flask(__name__)
db = firestore.Client(project="mi-proyecto-trading-12345")

price_history = defaultdict(list)
SMA_SHORT = 5
SMA_LONG = 20

def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def generate_signal(symbol, price):
    price_history[symbol].append(price)
    if len(price_history[symbol]) > 50:
        price_history[symbol] = price_history[symbol][-50:]
    
    sma_short = calculate_sma(price_history[symbol], SMA_SHORT)
    sma_long = calculate_sma(price_history[symbol], SMA_LONG)
    
    if sma_short is None or sma_long is None:
        return "HOLD", f"Acumulando datos ({len(price_history[symbol])}/20)"
    
    if sma_short > sma_long * 1.01:
        return "BUY", f"SMA{SMA_SHORT}={sma_short:.2f} > SMA{SMA_LONG}={sma_long:.2f}"
    elif sma_short < sma_long * 0.99:
        return "SELL", f"SMA{SMA_SHORT}={sma_short:.2f} < SMA{SMA_LONG}={sma_long:.2f}"
    else:
        return "HOLD", "SMAs convergentes"

def callback(message):
    try:
        data = json.loads(message.data.decode('utf-8'))
        symbol = data.get('symbol', '')
        price = float(data.get('price', 0))
        
        if not symbol or price <= 0:
            message.ack()
            return
        
        signal, reason = generate_signal(symbol, price)
        
        db.collection('signals').add({
            'symbol': symbol,
            'price': price,
            'signal': signal,
            'reason': reason,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        print(f"[{symbol}] {signal} @ \${price:.2f} - {reason}")
        message.ack()
    except Exception as e:
        print(f"Error: {e}")
        message.ack()

def start_subscriber():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path("mi-proyecto-trading-12345", "market-updates-sub")
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Escuchando en {subscription_path}...")
    try:
        streaming_pull_future.result()
    except Exception as e:
        print(f"Error: {e}")

@app.route('/')
def health():
    return "Agent Alive", 200

if __name__ == '__main__':
    threading.Thread(target=start_subscriber, daemon=True).start()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
