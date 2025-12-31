#!/usr/bin/env python3
import os, json, logging, pandas as pd, pandas_ta as ta, threading
from datetime import datetime
from flask import Flask, jsonify
from google.cloud import pubsub_v1, firestore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)

PROJECT_ID = os.environ.get('PROJECT_ID', 'mi-proyecto-trading-12345')
SUBSCRIPTION_ID = os.environ.get('SUBSCRIPTION_ID', 'datos-crudos-sub')
TOPIC_ID_SIGNALS = os.environ.get('TOPIC_ID_SIGNALS', 'senales-trading')
TRADING_PAIR = os.environ.get('TRADING_PAIR', 'btcusdt').upper()

db = firestore.Client(project=PROJECT_ID)
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
topic_path_signals = publisher.topic_path(PROJECT_ID, TOPIC_ID_SIGNALS)

price_history = pd.DataFrame(columns=['price'])

def process_message(message):
    global price_history
    try:
        data = json.loads(message.data.decode('utf-8'))
        symbol = data.get('symbol')
        if symbol != TRADING_PAIR:
            message.ack()
            return
        
        price = float(data.get('price'))
        new_row = pd.DataFrame([{'price': price}])
        price_history = pd.concat([price_history, new_row], ignore_index=True)
        
        if len(price_history) > 100:
            price_history = price_history.iloc[-100:]
        
        if len(price_history) >= 50:
            df = price_history.copy()
            df['price'] = pd.to_numeric(df['price'])
            df['SMA_20'] = ta.sma(df['price'], length=20)
            df['SMA_50'] = ta.sma(df['price'], length=50)
            df['RSI_14'] = ta.rsi(df['price'], length=14)
            
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            action = None
            reason = ""
            
            if prev_row['SMA_20'] <= prev_row['SMA_50'] and last_row['SMA_20'] > last_row['SMA_50']:
                if last_row['RSI_14'] < 70:
                    action = "BUY"
                    reason = f"Golden Cross en {symbol} con RSI {round(last_row['RSI_14'], 2)}"
            elif prev_row['SMA_20'] >= prev_row['SMA_50'] and last_row['SMA_20'] < last_row['SMA_50']:
                if last_row['RSI_14'] > 30:
                    action = "SELL"
                    reason = f"Death Cross en {symbol} con RSI {round(last_row['RSI_14'], 2)}"
            
            if action:
                signal_payload = {"symbol": symbol, "action": action, "price": price, "quantity": 0.001, "reason": reason, "timestamp": datetime.utcnow().isoformat()}
                db.collection('signals').add(signal_payload)
                data_str = json.dumps(signal_payload).encode("utf-8")
                publisher.publish(topic_path_signals, data_str)
                logger.info(f"🚀 SEÑAL: {action} {symbol} a {price}")
        
        message.ack()
    except Exception as e:
        logger.error(f"Error: {e}")
        message.nack()

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "pair": TRADING_PAIR}), 200

def start_subscriber():
    logger.info(f"Iniciando suscriptor para {TRADING_PAIR}")
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=process_message)
    try:
        streaming_pull_future.result()
    except Exception as e:
        logger.error(f"Error: {e}")
        streaming_pull_future.cancel()

if __name__ == "__main__":
    t = threading.Thread(target=start_subscriber)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
