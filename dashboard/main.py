import os
import requests
from flask import Flask, render_template, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# URLs de los servicios (actualizadas para v7.0)
SIMULATOR_URL = os.environ.get("SIMULATOR_URL", "http://simulator:5000")
PAIRS_URL = os.environ.get("PAIRS_URL", "http://pairs-trading:5000")
HISTORICAL_URL = os.environ.get("HISTORICAL_URL", "http://historical-data:5000")

# Lista expandida de activos (50 monedas)
ASSETS = [
    'BTC', 'ETH', 'BNB', 'SOL', 'XRP',
    'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC',
    'LINK', 'LTC', 'ATOM', 'UNI', 'ETC',
    'XLM', 'NEAR', 'APT', 'FIL', 'ARB',
    'OP', 'INJ', 'SUI', 'SEI', 'TIA',
    'RUNE', 'FTM', 'AAVE', 'MKR', 'SNX',
    'LDO', 'RNDR', 'GRT', 'IMX', 'SAND',
    'MANA', 'AXS', 'APE', 'GMT', 'GALA',
    'CHZ', 'ENJ', 'FLOW', 'KAVA', 'ALGO',
    'VET', 'ICP', 'HBAR', 'QNT', 'EGLD'
]

@app.route('/')
def index():
    # Obtener datos de mercado
    data = {}
    total_change = 0
    active_count = 0
    
    for asset in ASSETS:
        doc = db.collection('market_data').document(asset).get()
        if doc.exists:
            asset_data = doc.to_dict()
            data[asset] = asset_data
            total_change += asset_data.get('change', 0)
            active_count += 1
        else:
            data[asset] = {"price": 0, "change": 0, "volume": 0, "high": 0, "low": 0}
    
    # Calcular resumen
    summary = {
        "total_assets": len(ASSETS),
        "active_assets": active_count,
        "avg_change": total_change / active_count if active_count > 0 else 0
    }
    
    # Obtener últimas señales
    signals_ref = db.collection('signals').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20)
    signals = [s.to_dict() for s in signals_ref.stream()]
    
    return render_template('index.html', data=data, summary=summary, signals=signals, assets=ASSETS)

@app.route('/asset/<symbol>')
def asset_view(symbol):
    doc = db.collection('market_data').document(symbol.upper()).get()
    data = doc.to_dict() if doc.exists else {}
    
    signals_ref = db.collection('signals')\
        .where('symbol', '==', symbol.upper())\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(20)
    signals = [s.to_dict() for s in signals_ref.stream()]
    
    return render_template('asset.html', symbol=symbol.upper(), data=data, signals=signals)

@app.route('/simulator')
def simulator_view():
    return render_template('simulator.html', assets=ASSETS)

@app.route('/pairs')
def pairs_view():
    return render_template('pairs.html', assets=ASSETS)

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
    try:
        resp = requests.post(f"{SIMULATOR_URL}/run", json=request.json, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/pairs-analysis', methods=['POST'])
def pairs_analysis():
    try:
        resp = requests.post(f"{PAIRS_URL}/analyze", json=request.json, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/load-historical/<symbol>', methods=['POST'])
def load_historical(symbol):
    """Endpoint para cargar datos históricos de un símbolo"""
    try:
        days = request.args.get('days', 30)
        resp = requests.post(f"{HISTORICAL_URL}/load/{symbol}?days={days}", timeout=60)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run(host='0.0.0.0', port=port)
