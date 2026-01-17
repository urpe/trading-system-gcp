import os
from flask import Flask, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client(project="mi-proyecto-trading-12345")

@app.route('/')
def health():
    return "Pairs Engine Alive", 200

@app.route('/analyze', methods=['POST'])
def analyze_pairs():
    try:
        data = request.json or {}
        pair1 = data.get('pair1', 'BTC')
        pair2 = data.get('pair2', 'ETH')
        
        doc1 = db.collection('market_data').document(pair1).get()
        doc2 = db.collection('market_data').document(pair2).get()
        
        if not doc1.exists or not doc2.exists:
            return jsonify({"status": "error", "message": f"No hay datos para {pair1} o {pair2}"}), 400
        
        price1 = doc1.to_dict().get('price', 0)
        price2 = doc2.to_dict().get('price', 0)
        
        ratio = price1 / price2 if price2 > 0 else 0
        correlation = 0.85
        spread = ratio - 28.5
        
        if spread > 2:
            signal = "SHORT_SPREAD"
            recommendation = f"Vender {pair1}, Comprar {pair2}"
        elif spread < -2:
            signal = "LONG_SPREAD"
            recommendation = f"Comprar {pair1}, Vender {pair2}"
        else:
            signal = "NEUTRAL"
            recommendation = "Mantener posición"
        
        return jsonify({
            "status": "success",
            "pair1": {"symbol": pair1, "price": price1},
            "pair2": {"symbol": pair2, "price": price2},
            "analysis": {
                "ratio": round(ratio, 4),
                "correlation": correlation,
                "spread": round(spread, 4),
                "signal": signal,
                "recommendation": recommendation
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
