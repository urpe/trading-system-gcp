import os
import requests
from flask import Flask, render_template, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client(project="mi-proyecto-trading-12345")

ASSETS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']
SIMULATOR_URL = os.environ.get('SIMULATOR_URL', 'https://backtesting-simulator-rtez5nojkq-uc.a.run.app')
PAIRS_URL = os.environ.get('PAIRS_URL', 'https://pairs-trading-engine-rtez5nojkq-uc.a.run.app')

@app.route('/')
def index():
    data = {}
    for asset in ASSETS:
        try:
            doc = db.collection('market_data').document(asset).get()
            if doc.exists:
                data[asset] = doc.to_dict()
            else:
                data[asset] = {"price": 0, "change": 0, "volume": 0}
        except Exception as e:
            print(f"Error leyendo {asset}: {e}")
            data[asset] = {"price": 0, "change": 0, "volume": 0}
    
    total_change = sum(d.get('change', 0) for d in data.values()) / len(data) if data else 0
    summary = {
        "total_assets": len(ASSETS),
        "avg_change": round(total_change, 2),
        "market_status": "Alcista" if total_change > 0 else "Bajista" if total_change < 0 else "Neutral"
    }
    
    signals = []
    try:
        signal_docs = db.collection('signals').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        signals = [s.to_dict() for s in signal_docs]
    except Exception as e:
        print(f"Error leyendo señales: {e}")
    
    return render_template('index.html', data=data, assets=ASSETS, summary=summary, signals=signals)

@app.route('/asset/<symbol>')
def asset_view(symbol):
    doc = db.collection('market_data').document(symbol.upper()).get()
    asset_data = doc.to_dict() if doc.exists else {}
    signals = []
    return render_template('asset.html', symbol=symbol.upper(), data=asset_data, signals=signals)

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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pairs-analysis', methods=['POST'])
def pairs_analysis():
    try:
        resp = requests.post(f"{PAIRS_URL}/analyze", json=request.json, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
