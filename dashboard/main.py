import os
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Configuración de servicios
SERVICES = {
    "PAIRS_URL": os.environ.get("PAIRS_TRADING_ENGINE_URL", "#"),
    "BACKTEST_URL": os.environ.get("BACKTESTING_SIMULATOR_URL", "#"),
}

@app.route('/')
def index():
    # Datos por defecto para evitar que la página se rompa
    context = {
        "signals": [],
        "orders": [],
        "win_rate": 0,
        "pnl": 0,
        "buys": 0,
        "sells": 0,
        "volume": 0,
        "services": SERVICES
    }
    return render_template('index.html', **context)

@app.route('/api/status')
def status():
    return jsonify({"status": "ok", "version": "v3.1.4", "message": "Dashboard Operativo"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
