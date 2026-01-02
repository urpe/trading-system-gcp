import os
from flask import Flask, render_template, jsonify
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client(project="mi-proyecto-trading-12345")

ASSETS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']

@app.route('/')
def index():
    # Resumen: Intentar traer el último precio de cada moneda
    summary = []
    for asset in ASSETS:
        col_name = f"market_data_{asset.lower()}usdt"
        docs = list(db.collection(col_name).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).stream())
        price = docs[0].to_dict().get('price', 'N/A') if docs else 'N/A'
        summary.append({'symbol': asset, 'price': price})
    return render_template('index.html', assets=ASSETS, summary=summary)

@app.route('/asset/<symbol>')
def asset_detail(symbol):
    symbol = symbol.upper()
    col_name = f"market_data_{symbol.lower()}usdt"
    # Traer los últimos 20 registros de esa moneda específica
    docs = db.collection(col_name).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()
    data = [doc.to_dict() for doc in docs]
    return render_template('asset.html', symbol=symbol, signals=data, assets=ASSETS)

@app.route('/pairs')
def pairs_view(): return render_template('pairs.html', assets=ASSETS)

@app.route('/simulator')
def simulator_view(): return render_template('simulator.html', assets=ASSETS)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
