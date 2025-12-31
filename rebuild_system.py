import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content.strip())
    print(f"✅ Creado: {path}")

# 1. PAIRS TRADING ENGINE
create_file('pairs_trading_engine/main.py', """
import os
from flask import Flask, jsonify
app = Flask(__name__)
@app.route('/api/correlation')
def correlation():
    return jsonify({"status": "active", "pairs": [{"pair": "BTC/ETH", "corr": 0.92}, {"pair": "SOL/ETH", "corr": 0.78}]})
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
""")
create_file('pairs_trading_engine/requirements.txt', "flask\ngunicorn")
create_file('pairs_trading_engine/Procfile', "web: gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app")

# 2. BACKTESTING SIMULATOR
create_file('backtesting_simulator/main.py', """
import os
from flask import Flask, jsonify, request
app = Flask(__name__)
@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    return jsonify({"status": "complete", "pnl": 24.5, "win_rate": 62.3, "trades": 145})
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
""")
create_file('backtesting_simulator/requirements.txt', "flask\ngunicorn")
create_file('backtesting_simulator/Procfile', "web: gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app")

print("\n🚀 Sistema reconstruido localmente. Listo para el siguiente paso.")
