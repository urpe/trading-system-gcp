import os
import logging
from flask import Flask, jsonify, request
from google.cloud import firestore

# Configuración de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")

try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    logger.error(f"Error conectando a Firestore: {e}")
    db = None

@app.route('/')
def health():
    return jsonify({"status": "online", "service": "simulator-v9.1-RSI-SL-TP"})

# --- FUNCIONES MATEMÁTICAS ---
def calculate_rsi(prices, period=14):
    """Calcula el RSI manualmente sin librerías pesadas"""
    if len(prices) < period + 1:
        return [50] * len(prices) # Retorno neutro si faltan datos
    
    gains = []
    losses = []
    
    # Calcular cambios
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    
    # Primera media
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    rsi_list = [50] * period # Rellenar hueco inicial
    
    # RSI Suavizado
    for i in range(period, len(prices) - 1):
        change = prices[i+1] - prices[i]
        gain = max(change, 0)
        loss = max(-change, 0)
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        rsi_list.append(rsi)
        
    return rsi_list + [50] # Ajuste final

@app.route('/run', methods=['POST'])
def run_backtest():
    try:
        data = request.json or {}
        symbol = data.get('symbol', 'BTC').upper()
        capital = float(data.get('capital', 10000))
        strategy_name = data.get('strategy', 'SMA_RSI_PRO')
        
        # Parámetros Estrategia Avanzada
        sma_fast = int(data.get('sma_fast', 14))
        sma_slow = int(data.get('sma_slow', 50))
        stop_loss_pct = 0.03  # Cerrar si pierde 3%
        take_profit_pct = 0.06 # Cerrar si gana 6%
        rsi_threshold = 70    # No comprar si RSI > 70 (Sobrecompra)

        if not db:
            return jsonify({"status": "error", "message": "DB desconectada"}), 500

        # Obtener Datos
        docs = db.collection('historical_data').document(symbol).collection('1h')\
            .order_by('timestamp').limit(1000).stream()
        
        candles = [doc.to_dict() for doc in docs]
        
        if len(candles) < sma_slow + 20:
            return jsonify({"status": "error", "message": f"Datos insuficientes para {symbol}"}), 400

        closes = [float(c['close']) for c in candles]
        timestamps = [c['timestamp'] for c in candles]
        
        # Calcular Indicadores
        rsi_values = calculate_rsi(closes)
        
        def get_sma(idx, period):
            if idx < period: return 0
            return sum(closes[idx-period:idx]) / period

        # --- MOTOR DE SIMULACIÓN AVANZADO ---
        trades = []
        current_capital = capital
        position = None # None, 'long'
        entry_price = 0.0
        
        wins = []
        losses = []

        for i in range(sma_slow, len(closes)):
            price = closes[i]
            ts = timestamps[i]
            
            # Indicadores actuales
            sma_f = get_sma(i, sma_fast)
            sma_s = get_sma(i, sma_slow)
            sma_f_prev = get_sma(i-1, sma_fast)
            sma_s_prev = get_sma(i-1, sma_slow)
            rsi = rsi_values[i] if i < len(rsi_values) else 50

            # 1. GESTIÓN DE POSICIÓN ABIERTA (Venta por SL/TP o Cruce)
            if position == 'long':
                profit_pct = (price - entry_price) / entry_price
                
                reason = None
                if profit_pct <= -stop_loss_pct:
                    reason = "Stop Loss 🛑"
                elif profit_pct >= take_profit_pct:
                    reason = "Take Profit 💰"
                elif sma_f < sma_s: # Cruce de la muerte
                    reason = "Cruce Bajista 📉"
                
                if reason:
                    profit_usd = current_capital * profit_pct
                    current_capital += profit_usd
                    trades.append({
                        'type': 'SELL', 'price': price, 'timestamp': ts,
                        'profit_usd': round(profit_usd, 2),
                        'profit_pct': round(profit_pct * 100, 2),
                        'capital': round(current_capital, 2),
                        'reason': reason
                    })
                    if profit_usd > 0: wins.append(profit_usd)
                    else: losses.append(profit_usd)
                    position = None
                    continue # Esperar siguiente vela para operar

            # 2. BÚSQUEDA DE ENTRADA (Compra con Filtros)
            if position is None:
                # Cruce Dorado (Fast cruza hacia arriba Slow)
                golden_cross = sma_f_prev <= sma_s_prev and sma_f > sma_s
                
                # FILTRO: Solo comprar si RSI < 70 (No comprar caro)
                safe_rsi = rsi < rsi_threshold
                
                if golden_cross and safe_rsi:
                    position = 'long'
                    entry_price = price
                    trades.append({
                        'type': 'BUY', 'price': price, 'timestamp': ts,
                        'capital': round(current_capital, 2),
                        'reason': f'Golden Cross + RSI {round(rsi,1)}'
                    })

        # Estadísticas Finales
        total_return = ((current_capital - capital) / capital) * 100
        win_rate = (len(wins) / len(wins + losses) * 100) if (wins or losses) else 0

        result_payload = {
            "status": "success",
            "symbol": symbol,
            "strategy": f"SMA({sma_fast}/{sma_slow}) + RSI + TP/SL",
            "results": {
                "capital_inicial": capital,
                "capital_final": round(current_capital, 2),
                "retorno_total_pct": round(total_return, 2),
                "total_operaciones": len(trades),
                "win_rate_pct": round(win_rate, 2),
                "operaciones_ganadoras": len(wins),
                "operaciones_perdedoras": len(losses)
            },
            "trades": trades[-20:], # Últimos 20
            "explanation": {
                "que_significa": f"Estrategia Avanzada: Se protege capital con Stop Loss del 3% y busca ganancias del 6%.",
                "advertencia": "El RSI evita comprar en precios inflados.",
                "siguiente_paso": "Si el resultado es positivo, podemos llevar esto al bot real."
            }
        }
        
        return jsonify(result_payload)

    except Exception as e:
        logger.exception("Error simulador")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)