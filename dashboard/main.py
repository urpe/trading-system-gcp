import os
import requests
from flask import Flask, render_template, jsonify, request
from google.cloud import firestore

app = Flask(__name__)

# Inicialización segura de Firestore
try:
    db = firestore.Client()
except Exception as e:
    print(f"Error conectando a Firestore: {e}")
    db = None

SIMULATOR_URL = "https://backtesting-simulator-rtez5nojkq-uc.a.run.app"
ASSETS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']

@app.route('/' )
def index():
    data = {}
    try:
        for asset in ASSETS:
            if db:
                doc = db.collection('market_data').document(asset).get()
                data[asset] = doc.to_dict() if doc.exists else {"price": 0, "change": 0}
            else:
                data[asset] = {"price": "Error DB", "change": 0}
    except Exception as e:
        print(f"Error en index: {e}")
    
    return render_template('index.html', assets=ASSETS, market_data=data, signals=[])

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
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

# Ruta de salud explícita para Google Cloud
@app.route('/_health')
def health():
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)