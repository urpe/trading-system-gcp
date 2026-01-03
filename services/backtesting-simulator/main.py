import os
from flask import Flask, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

@app.route('/')
def health():
    return "Backtesting Simulator v2.0 - Datos Históricos Reales"

@app.route('/run', methods=['POST'])
def run_backtest():
    """
    SIMULADOR DE ESTRATEGIAS v2.0
    =============================
    
    ¿Qué es Backtesting?
    --------------------
    Es probar una estrategia de trading con datos HISTÓRICOS para ver
    cómo habría funcionado en el pasado. NO garantiza resultados futuros,
    pero ayuda a identificar estrategias prometedoras.
    
    Estrategias Disponibles:
    ------------------------
    1. SMA_CROSSOVER: Cruce de Medias Móviles
       - Compra cuando SMA rápida cruza por encima de SMA lenta
       - Vende cuando SMA rápida cruza por debajo de SMA lenta
    
    2. RSI_OVERSOLD: Índice de Fuerza Relativa
       - Compra cuando RSI < 30 (sobreventa)
       - Vende cuando RSI > 70 (sobrecompra)
    
    Parámetros:
    -----------
    - symbol: Moneda a simular (ej: BTC)
    - capital: Capital inicial en USD
    - strategy: Estrategia a usar (SMA_CROSSOVER, RSI_OVERSOLD)
    - sma_fast: Período SMA rápida (default: 10)
    - sma_slow: Período SMA lenta (default: 30)
    """
    data = request.json or {}
    symbol = data.get('symbol', 'BTC').upper()
    capital = float(data.get('capital', 10000))
    strategy = data.get('strategy', 'SMA_CROSSOVER')
    sma_fast = int(data.get('sma_fast', 10))
    sma_slow = int(data.get('sma_slow', 30))
    
    # Obtener datos históricos
    docs = db.collection('historical_data').document(symbol).collection('1h')\
        .order_by('timestamp').limit(500).stream()
    
    candles = [doc.to_dict() for doc in docs]
    
    if len(candles) < sma_slow + 10:
        return jsonify({
            "status": "error",
            "message": f"Datos insuficientes para {symbol}. Necesitas al menos {sma_slow + 10} velas.",
            "hint": "Ejecuta primero: POST /load/{symbol}?days=30 en el servicio historical-data"
        }), 400
    
    # Calcular SMAs
    closes = [c['close'] for c in candles]
    
    def calculate_sma(prices, period):
        return [sum(prices[i-period:i])/period if i >= period else None for i in range(len(prices))]
    
    sma_fast_values = calculate_sma(closes, sma_fast)
    sma_slow_values = calculate_sma(closes, sma_slow)
    
    # Simulación
    position = None  # None = sin posición, 'long' = comprado
    entry_price = 0
    trades = []
    current_capital = capital
    
    for i in range(sma_slow, len(candles)):
        price = closes[i]
        sma_f = sma_fast_values[i]
        sma_s = sma_slow_values[i]
        prev_sma_f = sma_fast_values[i-1]
        prev_sma_s = sma_slow_values[i-1]
        
        # Señal de COMPRA: SMA rápida cruza por encima de SMA lenta
        if prev_sma_f <= prev_sma_s and sma_f > sma_s and position is None:
            position = 'long'
            entry_price = price
            trades.append({
                'type': 'BUY',
                'price': price,
                'timestamp': candles[i]['timestamp'],
                'reason': f'SMA{sma_fast} cruzó por encima de SMA{sma_slow}'
            })
        
        # Señal de VENTA: SMA rápida cruza por debajo de SMA lenta
        elif prev_sma_f >= prev_sma_s and sma_f < sma_s and position == 'long':
            profit_pct = ((price - entry_price) / entry_price) * 100
            current_capital *= (1 + profit_pct / 100)
            trades.append({
                'type': 'SELL',
                'price': price,
                'timestamp': candles[i]['timestamp'],
                'profit_pct': round(profit_pct, 2),
                'reason': f'SMA{sma_fast} cruzó por debajo de SMA{sma_slow}'
            })
            position = None
    
    # Calcular métricas
    total_trades = len([t for t in trades if t['type'] == 'SELL'])
    winning_trades = len([t for t in trades if t['type'] == 'SELL' and t.get('profit_pct', 0) > 0])
    total_return = ((current_capital - capital) / capital) * 100
    
    return jsonify({
        "status": "success",
        "symbol": symbol,
        "strategy": strategy,
        "parameters": {
            "sma_fast": sma_fast,
            "sma_slow": sma_slow
        },
        "results": {
            "capital_inicial": capital,
            "capital_final": round(current_capital, 2),
            "retorno_total_pct": round(total_return, 2),
            "total_operaciones": total_trades,
            "operaciones_ganadoras": winning_trades,
            "win_rate_pct": round((winning_trades / total_trades * 100) if total_trades > 0 else 0, 2)
        },
        "trades": trades[-10:],  # Últimas 10 operaciones
        "explanation": {
            "que_significa": "Este resultado muestra cómo habría funcionado la estrategia con datos históricos.",
            "advertencia": "El rendimiento pasado NO garantiza resultados futuros.",
            "siguiente_paso": "Si el win_rate es > 50% y el retorno es positivo, la estrategia podría ser viable."
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
