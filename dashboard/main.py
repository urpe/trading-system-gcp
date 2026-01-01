import os
from flask import Flask, render_template, jsonify
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client(project=os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345"))

ASSETS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']

@app.route('/')
def index():
    # Vista General: Resumen de todos los activos
    return render_template('index.html', assets=ASSETS)

@app.route('/asset/<symbol>')
def asset_detail(symbol):
    # Vista Detallada: Datos de una sola moneda
    symbol = symbol.upper()
    signals_ref = db.collection('signals').where('symbol', '==', symbol.lower()+'usdt').limit(20).stream()
    signals = [doc.to_dict() for doc in signals_ref]
    return render_template('asset.html', symbol=symbol, signals=signals, assets=ASSETS)

@app.route('/pairs')
def pairs_view():
    return render_template('pairs.html', assets=ASSETS)

@app.route('/simulator')
def simulator_view():
    return render_template('simulator.html', assets=ASSETS)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
