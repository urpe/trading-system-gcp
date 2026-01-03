import os
from flask import Flask, jsonify, request
from google.cloud import firestore
from datetime import datetime

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# Activos FIJOS (Horizonte: 1-10 años)
FIXED_ASSETS = ['BTC', 'ETH', 'SOL', 'BNB']

# Universo de 50 monedas
UNIVERSE = [
    'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC',
    'LINK', 'LTC', 'ATOM', 'UNI', 'ETC', 'XLM', 'NEAR', 'APT', 'FIL', 'ARB',
    'OP', 'INJ', 'SUI', 'SEI', 'TIA', 'RUNE', 'FTM', 'AAVE', 'MKR', 'SNX',
    'LDO', 'RNDR', 'GRT', 'IMX', 'SAND', 'MANA', 'AXS', 'APE', 'GMT', 'GALA',
    'CHZ', 'ENJ', 'FLOW', 'KAVA', 'ALGO', 'VET', 'ICP', 'HBAR', 'QNT', 'EGLD'
]

@app.route('/')
def health():
    return "Portfolio Manager v7.0 Running"

@app.route('/portfolio', methods=['GET'])
def get_portfolio():
    market_data = {}
    for symbol in UNIVERSE:
        doc = db.collection('market_data').document(symbol).get()
        if doc.exists:
            market_data[symbol] = doc.to_dict()
    
    candidates = {k: v for k, v in market_data.items() if k not in FIXED_ASSETS}
    sorted_by_change = sorted(candidates.items(), key=lambda x: x[1].get('change', 0), reverse=True)
    variable_assets = [item[0] for item in sorted_by_change[:2]]
    
    portfolio = {
        "timestamp": datetime.now().isoformat(),
        "fixed_assets": {
            "symbols": FIXED_ASSETS,
            "allocation_pct": 60,
            "strategy": "Buy & Hold",
            "horizon": "1-10 años",
            "data": {s: market_data.get(s, {}) for s in FIXED_ASSETS}
        },
        "variable_assets": {
            "symbols": variable_assets,
            "allocation_pct": 40,
            "strategy": "Active Trading",
            "horizon": "días-semanas",
            "data": {s: market_data.get(s, {}) for s in variable_assets}
        },
        "universe_size": len(UNIVERSE),
        "active_monitoring": len(market_data)
    }
    return jsonify(portfolio)

@app.route('/rankings', methods=['GET'])
def get_rankings():
    market_data = {}
    for symbol in UNIVERSE:
        doc = db.collection('market_data').document(symbol).get()
        if doc.exists:
            market_data[symbol] = doc.to_dict()
    
    gainers = sorted(market_data.items(), key=lambda x: x[1].get('change', 0), reverse=True)[:10]
    losers = sorted(market_data.items(), key=lambda x: x[1].get('change', 0))[:10]
    by_volume = sorted(market_data.items(), key=lambda x: x[1].get('volume', 0), reverse=True)[:10]
    
    return jsonify({
        "top_gainers": [{"symbol": s, **d} for s, d in gainers],
        "top_losers": [{"symbol": s, **d} for s, d in losers],
        "top_volume": [{"symbol": s, **d} for s, d in by_volume]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
