import os
import requests
from flask import Flask, render_template, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client(project="mi-proyecto-trading-12345")

ASSETS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']

# URLs CORREGIDAS - usando el ID correcto del proyecto
SIMULATOR_URL = os.environ.get('SIMULATOR_URL', 'https://backtesting-simulator-347366802960.us-central1.run.app')
PAIRS_URL = os.environ.get('PAIRS_URL', 'https://pairs-trading-engine-347366802960.us-central1.run.app')

@app.route('/')
def index():
    data = {}
    for asset in ASSETS:
        try:
            doc = db.collection('market_data').document(asset).get()
            if doc.exists:
                data[asset] = doc.to_dict()
            else:
                data[asset] = {"price": 0, "change": 0, "volume": 0, "high": 0, "low": 0}
        except Exception as e:
            print(f"Error leyendo {asset}: {e}")
            data[asset] = {"price": 0, "change": 0, "volume": 0, "high": 0, "low": 0}
    
    # Calcular resumen solo con activos que tienen datos
    active_assets = [d for d in data.values() if d.get('price', 0) > 0]
    if active_assets:
        total_change = sum(d.get('change', 0) for d in active_assets) / len(active_assets)
    else:
        total_change = 0
    
    summary = {
        "total_assets": len(ASSETS),
        "active_assets": len(active_assets),
        "avg_change": round(total_change, 2),
        "market_status": "Alcista" if total_change > 0 else "Bajista" if total_change < 0 else "Neutral"
    }
    
    # Obtener últimas señales
    signals = []
    try:
        signal_docs = db.collection('signals').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        signals = [s.to_dict() for s in signal_docs]
    except Exception as e:
        print(f"Error leyendo señales: {e}")
    
    return render_template('index.html', data=data, assets=ASSETS, summary=summary, signals=signals)

@app.route('/asset/<symbol>')
def asset_view(symbol):
    symbol = symbol.upper()
    doc = db.collection('market_data').document(symbol).get()
    asset_data = doc.to_dict() if doc.exists else {"price": 0, "change": 0, "volume": 0}
    
    # Obtener señales del activo
    signals = []
    try:
        signal_docs = db.collection('signals').where('symbol', '==', symbol).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()
        signals = [s.to_dict() for s in signal_docs]
    except Exception as e:
        print(f"Error leyendo señales de {symbol}: {e}")
    
    return render_template('asset.html', symbol=symbol, data=asset_data, signals=signals)

@app.route('/pairs')
def pairs_view():
    return render_template('pairs.html', assets=ASSETS)

@app.route('/simulator')
def simulator_view():
    return render_template('simulator.html', assets=ASSETS)

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
    try:
        resp = requests.post(f"{SIMULATOR_URL}/run", json=request.json, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"Error conectando al simulador: {str(e)}"}), 500

@app.route('/api/pairs-analysis', methods=['POST'])
def pairs_analysis():
    try:
        resp = requests.post(f"{PAIRS_URL}/analyze", json=request.json, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"Error conectando al motor de pares: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
