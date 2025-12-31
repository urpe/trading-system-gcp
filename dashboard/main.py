#!/usr/bin/env python3
import os, logging
from flask import Flask, render_template, jsonify
from google.cloud import firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

PROJECT_ID = os.environ.get('PROJECT_ID', 'mi-proyecto-trading-12345')
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
db = firestore.Client(project=PROJECT_ID)

def get_signals_by_symbol(symbol, limit=10):
    try:
        signals_ref = db.collection('signals').where('symbol', '==', symbol).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        return [doc.to_dict() for doc in signals_ref.stream()]
    except:
        return []

def get_orders_by_symbol(symbol, limit=10):
    try:
        orders_ref = db.collection('orders').where('signal_received.symbol', '==', symbol).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        return [doc.to_dict() for doc in orders_ref.stream()]
    except:
        return []

def get_all_signals(limit=50):
    try:
        signals_ref = db.collection('signals').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        return [doc.to_dict() for doc in signals_ref.stream()]
    except:
        return []

def get_all_orders(limit=50):
    try:
        orders_ref = db.collection('orders').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        return [doc.to_dict() for doc in orders_ref.stream()]
    except:
        return []

def calculate_global_metrics():
    try:
        all_signals = get_all_signals(limit=500)
        all_orders = get_all_orders(limit=500)
        
        metrics_by_symbol = {}
        for symbol in SYMBOLS:
            symbol_signals = [s for s in all_signals if s.get('symbol') == symbol]
            symbol_orders = [o for o in all_orders if o.get('signal_received', {}).get('symbol') == symbol]
            buy_signals = [s for s in symbol_signals if s.get('action') == 'BUY']
            sell_signals = [s for s in symbol_signals if s.get('action') == 'SELL']
            successful_orders = sum(1 for o in symbol_orders if o.get('order_status') == 'SUCCESS')
            
            metrics_by_symbol[symbol] = {
                "total_signals": len(symbol_signals),
                "buy_count": len(buy_signals),
                "sell_count": len(sell_signals),
                "successful_orders": successful_orders,
                "total_orders": len(symbol_orders)
            }
        
        total_signals = sum(m['total_signals'] for m in metrics_by_symbol.values())
        total_buy = sum(m['buy_count'] for m in metrics_by_symbol.values())
        total_sell = sum(m['sell_count'] for m in metrics_by_symbol.values())
        total_orders = sum(m['total_orders'] for m in metrics_by_symbol.values())
        successful_orders = sum(m['successful_orders'] for m in metrics_by_symbol.values())
        win_rate = (successful_orders / total_orders * 100) if total_orders > 0 else 0
        
        return {
            "total_signals": total_signals,
            "buy_count": total_buy,
            "sell_count": total_sell,
            "total_orders": total_orders,
            "successful_orders": successful_orders,
            "win_rate": round(win_rate, 2),
            "by_symbol": metrics_by_symbol
        }
    except:
        return {}

@app.route('/')
def index():
    try:
        global_metrics = calculate_global_metrics()
        all_signals = get_all_signals()
        all_orders = get_all_orders()
        return render_template('index.html', symbols=SYMBOLS, global_metrics=global_metrics, all_signals=all_signals, all_orders=all_orders)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/api/symbol/<symbol>')
def get_symbol_data(symbol):
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        return jsonify({"error": "Símbolo no válido"}), 400
    signals = get_signals_by_symbol(symbol)
    orders = get_orders_by_symbol(symbol)
    return jsonify({"symbol": symbol, "signals": signals, "orders": orders})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
