import os
from flask import Flask, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client(project="mi-proyecto-trading-12345")

@app.route('/')
def health():
    return "Simulator Alive", 200

@app.route('/run', methods=['POST'])
def run_backtest():
    try:
        data = request.json or {}
        symbol = data.get('symbol', 'BTC')
        initial_capital = float(data.get('capital', 10000))
        
        signals = []
        try:
            signal_docs = db.collection('signals').where('symbol', '==', symbol).order_by('timestamp').limit(100).stream()
            signals = [s.to_dict() for s in signal_docs]
        except:
            pass
        
        if not signals:
            return jsonify({
                "status": "warning",
                "message": f"No hay señales para {symbol}",
                "result": {"profit": 0, "trades": 0, "initial_capital": initial_capital, "final_capital": initial_capital, "profit_pct": 0, "signals_analyzed": 0}
            })
        
        capital = initial_capital
        position = 0
        trades = 0
        buy_price = 0
        
        for signal in signals:
            price = signal.get('price', 0)
            action = signal.get('signal', 'HOLD')
            
            if action == 'BUY' and position == 0:
                position = capital / price
                buy_price = price
                capital = 0
                trades += 1
            elif action == 'SELL' and position > 0:
                capital = position * price
                position = 0
                trades += 1
        
        if position > 0 and signals:
            capital = position * signals[-1].get('price', buy_price)
        
        profit = capital - initial_capital
        profit_pct = (profit / initial_capital) * 100
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "result": {
                "initial_capital": initial_capital,
                "final_capital": round(capital, 2),
                "profit": round(profit, 2),
                "profit_pct": round(profit_pct, 2),
                "total_trades": trades,
                "signals_analyzed": len(signals)
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
