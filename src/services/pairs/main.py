import sys
import traceback
import time
import logging
import os
import threading
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request
from google.cloud import firestore
from datetime import datetime, timedelta

# Configuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PairsTrading')

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# Parámetros de la Estrategia (Live)
WINDOW_SIZE = 24       # Horas para calcular correlación
Z_THRESHOLD = 2.0      # Cuánto debe estirarse la liga para operar
CORRELATION_MIN = 0.8  # Mínima similitud para considerarlos "pareja"
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

def fetch_binance_data(symbol, interval, limit=1000):
    """Obtiene datos históricos de Binance API para backtesting"""
    params = {
        'symbol': f"{symbol}USDT",
        'interval': interval,
        'limit': limit
    }
    try:
        response = requests.get(BINANCE_API_URL, params=params, timeout=10)
        data = response.json()
        if isinstance(data, dict) and 'code' in data:
            logger.error(f"Binance API Error: {data}")
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)
        return df[['timestamp', 'close']]
    except Exception as e:
        logger.error(f"Error fetching Binance data: {e}")
        return pd.DataFrame()

def get_historical_prices():
    """Descarga precios de las últimas 24h para todas las monedas activas (LIVE)"""
    try:
        active_docs = db.collection('market_data').stream()
        symbols = [d.id for d in active_docs]
        price_data = {}
        for sym in symbols:
            docs = db.collection('historical_data').document(sym).collection('1h')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING).limit(WINDOW_SIZE).stream()
            prices = [d.to_dict()['close'] for d in docs]
            if len(prices) >= WINDOW_SIZE:
                price_data[sym] = list(reversed(prices))
        return pd.DataFrame(price_data)
    except Exception as e:
        logger.error(f"Error bajando datos: {e}")
        return pd.DataFrame()

def analyze_pairs():
    """Busca oportunidades de arbitraje (Loop Infinito)"""
    while True:
        try:
            logger.info("🔍 Buscando pares correlacionados...")
            df = get_historical_prices()
            if df.empty or len(df.columns) < 2:
                logger.warning("Datos insuficientes. Esperando...")
                time.sleep(60)
                continue

            corr_matrix = df.corr()
            checked = set()
            
            for asset_a in df.columns:
                for asset_b in df.columns:
                    if asset_a == asset_b: continue
                    pair_key = tuple(sorted([asset_a, asset_b]))
                    if pair_key in checked: continue
                    checked.add(pair_key)
                    
                    score = corr_matrix.loc[asset_a, asset_b]
                    if score > CORRELATION_MIN:
                        series_a = df[asset_a] / df[asset_a].iloc[0]
                        series_b = df[asset_b] / df[asset_b].iloc[0]
                        spread = series_a - series_b
                        z_score = (spread.iloc[-1] - spread.mean()) / spread.std()
                        
                        signal = "NEUTRAL"
                        if z_score > Z_THRESHOLD:
                            signal = f"SHORT {asset_a} / LONG {asset_b}"
                        elif z_score < -Z_THRESHOLD:
                            signal = f"LONG {asset_a} / SHORT {asset_b}"
                        
                        if signal != "NEUTRAL":
                            logger.info(f"⚡ OPORTUNIDAD: {signal} (Corr: {round(score,2)}, Z: {round(z_score,2)})")
                            db.collection('signals').add({
                                'type': 'PAIR_TRADE',
                                'symbol': f"{asset_a}-{asset_b}",
                                'signal': signal,
                                'z_score': round(z_score, 2),
                                'correlation': round(score, 2),
                                'source': 'pairs_trading',
                                'timestamp': firestore.SERVER_TIMESTAMP
                            })
            logger.info("✅ Análisis de pares completado. Durmiendo 5 min.")
            time.sleep(300)
        except Exception as e:
            logger.error(f"Error en loop de pares: {e}")
            time.sleep(60)

@app.route('/')
def health():
    return jsonify({"status": "online", "service": "pairs-trading-v14-pro"})

@app.route('/backtest', methods=['POST'])
def run_backtest():
    """Ejecuta una simulación de Pairs Trading con datos históricos"""
    try:
        req = request.json
        asset_a = req.get('asset_a', 'BTC')
        asset_b = req.get('asset_b', 'ETH')
        timeframe = req.get('timeframe', '1mo') # 1mo, 3mo, 6mo
        capital = float(req.get('capital', 10000))
        z_threshold = float(req.get('z_threshold', 2.0))
        
        # Mapeo de duración a límite de velas (aprox) para intervalo 1h
        # 1 mes = 30 * 24 = 720 velas
        limit_map = {
            '1mo': 720,
            '3mo': 2160,
            '6mo': 4320
        }
        limit = limit_map.get(timeframe, 720)
        
        # 1. Obtener Datos Históricos de Binance
        logger.info(f"Bajando datos para backtest {asset_a}-{asset_b}, limit={limit}")
        df_a = fetch_binance_data(asset_a, '1h', limit)
        df_b = fetch_binance_data(asset_b, '1h', limit)
        
        if df_a.empty or df_b.empty:
            return jsonify({"status": "error", "message": "No data from Binance"}), 404
            
        # 2. Alinear Datos
        df = pd.merge(df_a, df_b, on='timestamp', suffixes=('_a', '_b'))
        df.set_index('timestamp', inplace=True)
        
        # 3. Lógica de Backtest Vectorizada
        # Normalizar precios
        df['norm_a'] = df['close_a'] / df['close_a'].iloc[0]
        df['norm_b'] = df['close_b'] / df['close_b'].iloc[0]
        df['spread'] = df['norm_a'] - df['norm_b']
        
        # Z-Score Rolling (Ventana dinámica)
        roll_window = 24
        df['spread_mean'] = df['spread'].rolling(window=roll_window).mean()
        df['spread_std'] = df['spread'].rolling(window=roll_window).std()
        df['z_score'] = (df['spread'] - df['spread_mean']) / df['spread_std']
        
        # Simulación de Operaciones
        balance = capital
        positions = {'a': 0, 'b': 0} # Amounts
        entry_equity = 0
        trades = []
        status = "NEUTRAL" # NEUTRAL, LONG_SPREAD (Long A, Short B), SHORT_SPREAD (Short A, Long B)
        # Nota: LONG_SPREAD es comprar spread -> Comprar A, Vender B (si spread está bajo)
        # Aquí: Spread = A - B.
        # Si Z < -2 (Spread muy bajo, A barato vs B): Comprar A, Vender B (LONG SPREAD)
        # Si Z > 2 (Spread muy alto, A caro vs B): Vender A, Comprar B (SHORT SPREAD)
        
        equity_curve = []

        for ts, row in df.iterrows():
            z = row['z_score']
            price_a = row['close_a']
            price_b = row['close_b']
            
            if pd.isna(z): continue
            
            # Entry Conditions
            if status == "NEUTRAL":
                if z > z_threshold:
                    # Short A, Long B
                    size = (balance / 2) 
                    positions['a'] = -size / price_a # Short
                    positions['b'] = size / price_b  # Long
                    entry_equity = balance
                    status = "SHORT_SPREAD"
                    trades.append({'type': 'OPEN_SHORT_SPREAD', 'price_a': price_a, 'price_b': price_b, 'ts': ts, 'z': z})
                    
                elif z < -z_threshold:
                    # Long A, Short B
                    size = (balance / 2)
                    positions['a'] = size / price_a # Long
                    positions['b'] = -size / price_b # Short
                    entry_equity = balance
                    status = "LONG_SPREAD"
                    trades.append({'type': 'OPEN_LONG_SPREAD', 'price_a': price_a, 'price_b': price_b, 'ts': ts, 'z': z})

            # Exit Conditions (Mean Reversion: Z crosses 0 or stop loss)
            elif status == "SHORT_SPREAD":
                if z <= 0: # Reversion to mean
                    # Close Positions
                    # PnL A (Short): (Entry - Current) * Size
                    # PnL B (Long): (Current - Entry) * Size
                    # Simplified: Equity = Balance + PnL
                    # Actually: New Balance = (PosA * PriceA) + (PosB * PriceB) ... wait, for Short PosA is negative.
                    # Equity = Cash + AssetValue.
                    # Cash part was used to buy B. Short A generates cash but is a liability.
                    # Let's simplify: PnL = size_a * (price_a_diff) + size_b * (price_b_diff)
                    
                    # Cierre
                    # Value A: positions['a'] * price_a (Negative value for short liability)
                    # Value B: positions['b'] * price_b (Positive value)
                    # PnL = (Value A + Value B) - (Initial Cost which is 0 for net market neutral? No.)
                    
                    # Simplified Simulation PnL:
                    # Previous Equity was 'balance'.
                    # Current Equity = entry_equity + (positions['a'] * (price_a - entry_price_a))?? No.
                    # Let's use simple % return approach for speed
                    
                    # Re-calculate correct PnL
                    last_trade = trades[-1]
                    pnl_a = positions['a'] * (price_a - last_trade['price_a'])
                    pnl_b = positions['b'] * (price_b - last_trade['price_b'])
                    
                    balance = entry_equity + pnl_a + pnl_b
                    status = "NEUTRAL"
                    trades.append({'type': 'CLOSE', 'pnl': pnl_a + pnl_b, 'ts': ts, 'z': z})

            elif status == "LONG_SPREAD":
                if z >= 0:
                    last_trade = trades[-1]
                    pnl_a = positions['a'] * (price_a - last_trade['price_a'])
                    pnl_b = positions['b'] * (price_b - last_trade['price_b'])
                    
                    balance = entry_equity + pnl_a + pnl_b
                    status = "NEUTRAL"
                    trades.append({'type': 'CLOSE', 'pnl': pnl_a + pnl_b, 'ts': ts, 'z': z})
            
            equity_curve.append(balance)
            
        # Metrics
        total_return = ((balance - capital) / capital) * 100
        closed_trades = [t for t in trades if t['type'] == 'CLOSE']
        win_trades = [t for t in closed_trades if t['pnl'] > 0]
        win_rate = (len(win_trades) / len(closed_trades) * 100) if closed_trades else 0
        
        return jsonify({
            "status": "success",
            "results": {
                "capital_final": round(balance, 2),
                "retorno_total_pct": round(total_return, 2),
                "win_rate_pct": round(win_rate, 2),
                "total_trades": len(closed_trades),
                "correlation_mean": round(df['close_a'].corr(df['close_b']), 2)
            }
        })

    except Exception as e:
        logger.error(f"Backtest error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    thread = threading.Thread(target=analyze_pairs)
    thread.daemon = True
    thread.start()
    app.run(host='0.0.0.0', port=5000)
