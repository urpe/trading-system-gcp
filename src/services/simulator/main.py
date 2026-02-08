import os
import logging
import pandas as pd
import pandas_ta as ta
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from src.shared.utils import get_logger, normalize_symbol

# Configuración
logger = get_logger("SimulatorV21.2.1")
app = Flask(__name__)

# Binance API URL
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

def fetch_binance_data(symbol, interval, start_str=None):
    """
    V21.2.1: Obtiene datos históricos de Binance API con normalización.
    """
    # V21.2.1: NORMALIZACIÓN
    try:
        symbol_normalized = normalize_symbol(symbol, format='long')  # "BTCUSDT"
    except (ValueError, TypeError) as e:
        logger.error(f"❌ Invalid symbol '{symbol}': {e}")
        return []
    
    params = {
        'symbol': symbol_normalized,  # V21.2.1: Usar símbolo normalizado
        'interval': interval,
        'limit': 1000
    }
    # Binance accepts start time in milliseconds
    if start_str:
        # Convert simple strings like '7d' to milliseconds ago not supported directly
        # For simplicity, we stick to limits or calculate timestamps if needed
        pass

    try:
        response = requests.get(BINANCE_API_URL, params=params, timeout=10)
        data = response.json()
        
        # Check for API error
        if isinstance(data, dict) and 'code' in data:
            logger.error(f"Binance API Error: {data}")
            return []

        # Convert to DataFrame
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Clean Data
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)
        df = df[['timestamp', 'close']]
        return df
        
    except Exception as e:
        logger.error(f"Error fetching Binance data: {e}")
        return pd.DataFrame()

def get_historical_data(symbol, interval):
    """
    Obtiene datos históricos directamente de Binance API.
    V17: Sin dependencias de Firestore.
    """
    logger.info(f"📊 Fetching {symbol} data (interval: {interval}) from Binance API")
    df = fetch_binance_data(symbol, interval)
    
    if df.empty:
        logger.error(f"❌ No data available for {symbol} from Binance")
    else:
        logger.info(f"✅ Loaded {len(df)} candles for simulation")
    
    return df

@app.route('/health')
def health():
    return "Simulator OK", 200

@app.route('/run', methods=['POST'])
def run_simulation():
    try:
        req = request.json
        symbol = req.get('symbol', 'BTC')
        capital = float(req.get('capital', 10000))
        strategy_name = req.get('strategy', 'SMA_CROSSOVER')
        timeframe = req.get('timeframe', '1d')  # 1d, 7d, 15d, 1mo

        # Mapeo de Timeframe a Intervalo Binance
        # Para simular "1 mes" usamos velas de 1h o 4h para tener granularidad
        # Para "1 dia" usamos velas de 5m o 15m
        # Pero simplificaremos: timeframe dicta la DURACION de la simulación
        
        # Mapeo: 
        # Si timeframe='1d' -> Usamos últimos 1440 mins (velas 5m)
        # Si timeframe='7d' -> Usamos últimos 7 dias (velas 1h)
        # Por ahora usaremos el intervalo de velas fijo '1h' y filtraremos la cantidad
        
        interval_map = {
            '1d': '5m',
            '7d': '1h',
            '15d': '1h', 
            '1mo': '4h'
        }
        binance_interval = interval_map.get(timeframe, '1h')
        
        logger.info(f"Iniciando simulación: {symbol} - {strategy_name} - {timeframe} ({binance_interval})")

        # 1. Obtener Datos
        df = get_historical_data(symbol, binance_interval)
        
        if df.empty:
            return jsonify({"status": "error", "message": "No historical data available"}), 404
            
        # 2. Aplicar Estrategia (SMA Crossover)
        if strategy_name == 'SMA_CROSSOVER':
            sma_fast = int(req.get('sma_fast', 10))
            sma_slow = int(req.get('sma_slow', 30))
            
            df['SMA_Fast'] = ta.sma(df['close'], length=sma_fast)
            df['SMA_Slow'] = ta.sma(df['close'], length=sma_slow)
            
            # Generar Señales
            df['Signal'] = 0
            # Compra: Fast > Slow
            df.loc[df['SMA_Fast'] > df['SMA_Slow'], 'Signal'] = 1 
            # Venta: Fast < Slow
            df.loc[df['SMA_Fast'] < df['SMA_Slow'], 'Signal'] = -1
            
            # Detectar cambios (Crossover)
            df['Position'] = df['Signal'].diff()
            
        # 3. Ejecutar Backtest
        balance = capital
        position = 0 # Cantidad de activo
        trades = []
        wins = 0
        
        for i, row in df.iterrows():
            if pd.isna(row['Position']): continue
            
            price = row['close']
            
            # Compra (Cruce hacia arriba: Position = 2 o 1)
            if row['Position'] > 0 and balance > 0:
                amount = (balance * 0.99) / price # Usar 99% del capital + fee simulado
                position = amount
                balance = 0
                trades.append({'type': 'BUY', 'price': price, 'time': row['timestamp']})
                
            # Venta (Cruce hacia abajo: Position = -2 o -1)
            elif row['Position'] < 0 and position > 0:
                new_balance = position * price
                profit = new_balance - capital # Profit vs Capital Inicial (simple)
                
                # Check win based on last buy
                last_buy = next((t for t in reversed(trades) if t['type'] == 'BUY'), None)
                if last_buy and price > last_buy['price']:
                    wins += 1
                    
                balance = new_balance
                position = 0
                trades.append({'type': 'SELL', 'price': price, 'time': row['timestamp']})

        # Cierre final al precio actual si quedó abierto
        if position > 0:
            final_price = df.iloc[-1]['close']
            balance = position * final_price
            
        # 4. Resultados
        total_return = ((balance - capital) / capital) * 100
        total_ops = len([t for t in trades if t['type'] == 'SELL'])
        win_rate = (wins / total_ops * 100) if total_ops > 0 else 0
        
        return jsonify({
            "status": "success",
            "results": {
                "capital_final": round(balance, 2),
                "retorno_total_pct": round(total_return, 2),
                "win_rate_pct": round(win_rate, 2),
                "total_operaciones": total_ops,
                "operaciones_ganadoras": wins
            },
            "explanation": {
                "que_significa": f"Simulación V17 basada en {len(df)} velas de {binance_interval} desde Binance API."
            }
        })
        
    except Exception as e:
        logger.error(f"Error en simulación: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
