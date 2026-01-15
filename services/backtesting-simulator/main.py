import os
import logging
from flask import Flask, jsonify, request
from google.cloud import firestore

# Configuración de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")

# Cliente Firestore
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    logger.error(f"Error conectando a Firestore: {e}")
    db = None

@app.route('/')
def health():
    return jsonify({"status": "online", "service": "backtesting-simulator-v9"})

@app.route('/run', methods=['POST'])
def run_backtest():
    try:
        # 1. Recibir y Validar Datos
        data = request.json or {}
        symbol = data.get('symbol', 'BTC').upper()
        capital = float(data.get('capital', 10000))
        # --- AQUÍ ESTABA EL ERROR: FALTABA DEFINIR STRATEGY ---
        strategy = data.get('strategy', 'SMA_CROSSOVER') 
        # ------------------------------------------------------
        sma_fast = int(data.get('sma_fast', 10))
        sma_slow = int(data.get('sma_slow', 30))
        
        logger.info(f"Iniciando simulación para {symbol} | Capital: {capital} | SMA: {sma_fast}/{sma_slow}")

        if not db:
            return jsonify({"status": "error", "message": "Base de datos no conectada"}), 500

        # 2. Obtener Datos Históricos
        docs = db.collection('historical_data').document(symbol).collection('1h')\
            .order_by('timestamp').limit(1000).stream()
        
        candles = []
        for doc in docs:
            d = doc.to_dict()
            if 'close' in d and 'timestamp' in d:
                candles.append(d)

        if len(candles) < sma_slow + 5:
            msg = f"Datos insuficientes para {symbol}. Se encontraron {len(candles)} velas."
            return jsonify({"status": "error", "message": msg}), 400

        # 3. Preparar Datos
        closes = [float(c['close']) for c in candles]
        
        def safe_sma(data, period, index):
            if index < period: return None
            subset = data[index-period:index]
            return sum(subset) / period

        # 4. Motor de Simulación
        position = None
        entry_price = 0.0
        trades = []
        current_capital = capital
        equity_curve = []

        for i in range(1, len(candles)):
            price = closes[i]
            timestamp = candles[i]['timestamp']
            
            sma_f_curr = safe_sma(closes, sma_fast, i)
            sma_s_curr = safe_sma(closes, sma_slow, i)
            sma_f_prev = safe_sma(closes, sma_fast, i-1)
            sma_s_prev = safe_sma(closes, sma_slow, i-1)

            if None in [sma_f_curr, sma_s_curr, sma_f_prev, sma_s_prev]:
                continue

            # COMPRA (Golden Cross)
            if sma_f_prev <= sma_s_prev and sma_f_curr > sma_s_curr:
                if position is None:
                    position = 'long'
                    entry_price = price
                    trades.append({
                        'type': 'BUY',
                        'price': price,
                        'timestamp': timestamp,
                        'capital': round(current_capital, 2),
                        'reason': f'Cruce SMA {sma_fast}/{sma_slow}'
                    })

            # VENTA (Death Cross)
            elif sma_f_prev >= sma_s_prev and sma_f_curr < sma_s_curr:
                if position == 'long':
                    profit_pct = ((price - entry_price) / entry_price)
                    profit_usd = current_capital * profit_pct
                    current_capital += profit_usd
                    
                    trades.append({
                        'type': 'SELL',
                        'price': price,
                        'timestamp': timestamp,
                        'profit_usd': round(profit_usd, 2),
                        'profit_pct': round(profit_pct * 100, 2),
                        'capital': round(current_capital, 2),
                        'reason': f'Cruce SMA {sma_fast}/{sma_slow}'
                    })
                    position = None

            equity_curve.append(current_capital)

        # 5. Resultados Finales (FORMATO ESPAÑOL PARA EL DASHBOARD)
        wins = [t for t in trades if t['type'] == 'SELL' and t['profit_usd'] > 0]
        losses = [t for t in trades if t['type'] == 'SELL' and t['profit_usd'] <= 0]
        total_trades_count = len([t for t in trades if t['type'] == 'SELL'])
        
        win_rate = (len(wins) / total_trades_count * 100) if total_trades_count > 0 else 0
        total_return = ((current_capital - capital) / capital) * 100

        result_payload = {
            "status": "success",
            "symbol": symbol,
            "strategy": strategy,
            "results": {
                "capital_inicial": capital,
                "capital_final": round(current_capital, 2),
                "retorno_total_pct": round(total_return, 2),
                "total_operaciones": total_trades_count,
                "win_rate_pct": round(win_rate, 2),
                "operaciones_ganadoras": len(wins),
                "operaciones_perdedoras": len(losses)
            },
            "trades": trades[-20:],
            "explanation": {
                "que_significa": f"Simulación de {strategy} en {symbol}.",
                "advertencia": "Rendimientos pasados no garantizan futuros.",
                "siguiente_paso": "Ajusta las medias móviles para optimizar."
            }
        }
        
        return jsonify(result_payload)

    except Exception as e:
        logger.exception("Error crítico")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)