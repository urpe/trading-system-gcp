import os
from flask import Flask, render_template, jsonify

app = Flask(__name__)

SERVICES = {
    "PAIRS_URL": os.environ.get("PAIRS_TRADING_ENGINE_URL", "https://pairs-trading-engine-347366802960.us-central1.run.app" ),
    "BACKTEST_URL": os.environ.get("BACKTESTING_SIMULATOR_URL", "https://backtesting-simulator-347366802960.us-central1.run.app" ),
}

@app.route('/')
def index():
    # Datos iniciales seguros para evitar pantalla en blanco
    data = {
        "signals": [], "orders": [], "buys": 0, "sells": 0,
        "win_rate": 0, "pnl": 0, "volume": 0, "services": SERVICES
    }
    return render_template('index.html', **data)

@app.route('/api/status')
def status():
    return jsonify({"status": "ok", "version": "v3.1.1"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
