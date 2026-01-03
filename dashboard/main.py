import os
import requests
from flask import Flask, render_template, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client()

# URLs de los Microservicios (Detectadas en tu auditoría)
SIMULATOR_URL = "https://backtesting-simulator-rtez5nojkq-uc.a.run.app"
ORDER_AGENT_URL = "https://order-agent-rtez5nojkq-uc.a.run.app"

ASSETS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']

@app.route('/' )
def index():
    data = {}
    for asset in ASSETS:
        docs = db.collection('market_data').document(asset).get()
        data[asset] = docs.to_dict() if docs.exists else {"price": 0, "change": 0}
    
    signals = db.collection('signals').order_by('timestamp', direction='DESCENDING').limit(10).stream()
    recent_signals = [s.to_dict() for s in signals]
    
    return render_template('index.html', assets=ASSETS, market_data=data, signals=recent_signals)

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
    # El Dashboard ahora SI habla con el Simulador
    try:
        resp = requests.post(f"{SIMULATOR_URL}/run", json=request.json, timeout=5)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pairs')
def pairs_view():
    return render_template('pairs.html', assets=ASSETS)

@app.route('/simulator')
def simulator_view():
    return render_template('simulator.html', assets=ASSETS)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))