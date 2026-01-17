import os
import requests
from flask import Flask, jsonify, request
from google.cloud import firestore
from datetime import datetime, timedelta

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# ============================================================
# SERVICIO DE DATOS HISTÓRICOS
# ============================================================
# Este servicio obtiene datos históricos de Binance para:
# 1. Alimentar el simulador de backtesting
# 2. Calcular indicadores técnicos con más contexto
# 3. Entrenar modelos de ML en el futuro

BINANCE_API = "https://api.binance.com/api/v3/klines"

@app.route('/')
def health():
    return "Historical Data Service v7.0 Running"

@app.route('/load/<symbol>', methods=['POST'])
def load_historical(symbol):
    """
    Carga datos históricos de un símbolo desde Binance.
    
    ¿Qué son los Klines/Candlesticks?
    ---------------------------------
    Son "velas" que resumen el precio en un período:
    - Open: Precio de apertura
    - High: Precio más alto
    - Low: Precio más bajo
    - Close: Precio de cierre
    - Volume: Cantidad transaccionada
    
    Uso: POST /load/BTC?days=365&interval=1h
    """
    days = int(request.args.get('days', 30))
    interval = request.args.get('interval', '1h')
    
    symbol_pair = f"{symbol.upper()}USDT"
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    all_data = []
    current_start = start_time
    
    while current_start < end_time:
        params = {
            'symbol': symbol_pair,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_time,
            'limit': 1000
        }
        
        response = requests.get(BINANCE_API, params=params)
        if response.status_code != 200:
            return jsonify({"error": f"Binance API error: {response.text}"}), 500
        
        klines = response.json()
        if not klines:
            break
            
        for k in klines:
            all_data.append({
                'timestamp': k[0],
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
                'close_time': k[6]
            })
        
        current_start = klines[-1][6] + 1
    
    # Guardar en Firestore (colección historical_data)
    batch = db.batch()
    collection_ref = db.collection('historical_data').document(symbol.upper()).collection(interval)
    
    for i, candle in enumerate(all_data):
        doc_ref = collection_ref.document(str(candle['timestamp']))
        batch.set(doc_ref, candle)
        
        # Firestore permite máximo 500 operaciones por batch
        if (i + 1) % 500 == 0:
            batch.commit()
            batch = db.batch()
    
    batch.commit()
    
    return jsonify({
        "status": "success",
        "symbol": symbol.upper(),
        "interval": interval,
        "candles_loaded": len(all_data),
        "date_range": f"{datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}"
    })

@app.route('/get/<symbol>', methods=['GET'])
def get_historical(symbol):
    """
    Obtiene datos históricos almacenados para un símbolo.
    
    Uso: GET /get/BTC?interval=1h&limit=100
    """
    interval = request.args.get('interval', '1h')
    limit = int(request.args.get('limit', 100))
    
    docs = db.collection('historical_data').document(symbol.upper()).collection(interval)\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(limit).stream()
    
    data = [doc.to_dict() for doc in docs]
    data.reverse()  # Ordenar de más antiguo a más reciente
    
    return jsonify({
        "symbol": symbol.upper(),
        "interval": interval,
        "count": len(data),
        "data": data
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


