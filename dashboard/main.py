import os
from flask import Flask, render_template, jsonify

app = Flask(__name__)

SERVICES = {
    "PAIRS_TRADING_ENGINE_URL": os.environ.get("PAIRS_TRADING_ENGINE_URL", "http://pairs-trading-engine-347366802960.us-central1.run.app" ),
    "BACKTESTING_SIMULATOR_URL": os.environ.get("BACKTESTING_SIMULATOR_URL", "http://backtesting-simulator-347366802960.us-central1.run.app" ),
}

@app.route('/')
def index():
    return render_template('index.html', services=SERVICES)

@app.route('/api/status')
def status():
    return jsonify({"status": "ok", "version": "v3.1.0", "message": "Dashboard operativo"})

@app.route('/api/pairs-trading/correlation', methods=['GET'])
def get_correlation():
    return jsonify({"message": "Endpoint de correlación de Pairs Trading"})

@app.route('/api/backtesting/run', methods=['POST'])
def run_backtest():
    return jsonify({"message": "Endpoint de ejecución de Backtesting"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
