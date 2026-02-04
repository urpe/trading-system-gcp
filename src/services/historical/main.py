import os
import requests
import logging
from flask import Flask, jsonify, request
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('HistoricalDataSvc')

# ============================================================
# SERVICIO DE DATOS HISTÓRICOS V17
# ============================================================
# Este servicio obtiene datos históricos de Binance para:
# 1. Alimentar el simulador de backtesting
# 2. Calcular indicadores técnicos con más contexto
# 3. Entrenar modelos de ML en el futuro
#
# V17: Sin Firestore, datos servidos directamente desde Binance API

BINANCE_API = "https://api.binance.com/api/v3/klines"

@app.route('/')
def health():
    return jsonify({
        "status": "online",
        "service": "historical-data-v17",
        "description": "Historical data from Binance API (no cache)"
    })

@app.route('/load/<symbol>', methods=['POST'])
def load_historical(symbol):
    """
    Carga datos históricos de un símbolo desde Binance.
    V17: Retorna datos sin persistirlos en base de datos.
    
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
    
    logger.info(f"📊 Fetching {symbol} historical data: {days}d, interval={interval}")
    
    all_data = []
    current_start = start_time
    
    try:
        while current_start < end_time:
            params = {
                'symbol': symbol_pair,
                'interval': interval,
                'startTime': current_start,
                'endTime': end_time,
                'limit': 1000
            }
            
            response = requests.get(BINANCE_API, params=params, timeout=10)
            if response.status_code != 200:
                logger.error(f"Binance API error: {response.text}")
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
        
        logger.info(f"✅ Loaded {len(all_data)} candles for {symbol}")
        
        return jsonify({
            "status": "success",
            "symbol": symbol.upper(),
            "interval": interval,
            "candles_loaded": len(all_data),
            "date_range": f"{datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}",
            "data": all_data  # V17: Return data directly
        })
        
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get/<symbol>', methods=['GET'])
def get_historical(symbol):
    """
    Obtiene datos históricos desde Binance API.
    V17: Sin caché, consulta directa a Binance.
    
    Uso: GET /get/BTC?interval=1h&limit=100
    """
    interval = request.args.get('interval', '1h')
    limit = int(request.args.get('limit', 100))
    
    logger.info(f"📊 Fetching {symbol} data: interval={interval}, limit={limit}")
    
    try:
        symbol_pair = f"{symbol.upper()}USDT"
        params = {
            'symbol': symbol_pair,
            'interval': interval,
            'limit': limit
        }
        
        response = requests.get(BINANCE_API, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"Binance API error: {response.text}")
            return jsonify({"error": f"Binance API error: {response.text}"}), 500
        
        klines = response.json()
        data = []
        
        for k in klines:
            data.append({
                'timestamp': k[0],
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
                'close_time': k[6]
            })
        
        logger.info(f"✅ Returned {len(data)} candles for {symbol}")
        
        return jsonify({
            "status": "success",
            "symbol": symbol.upper(),
            "interval": interval,
            "count": len(data),
            "data": data
        })
        
    except Exception as e:
        logger.error(f"Error getting historical data: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Historical Data Service V19 starting on port {port}")
    app.run(host='0.0.0.0', port=port)
