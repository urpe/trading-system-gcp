import sys
import traceback
import time
import logging
import os
import threading
import json
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
from src.shared.memory import memory # <--- SHARED CLIENT
from src.shared.database import init_db, SessionLocal, PairsSignal # <--- V17 SQLite

# Configuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PairsTrading')

app = Flask(__name__)

# Inicializar BD Local
init_db()
logger.info("💾 Pairs Trading usando SQLite (V17)")

# Cache de Precios en Memoria
LATEST_PRICES = {}

# Parámetros de la Estrategia (Live)
WINDOW_SIZE = 24       # Horas para calcular correlación
Z_THRESHOLD = 2.0      # Cuánto debe estirarse la liga para operar
CORRELATION_MIN = 0.8  # Mínima similitud para considerarlos "pareja"
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

def redis_listener():
    """Hilo background para escuchar precios en tiempo real"""
    logger.info("🎧 Pairs Service escuchando Redis...")
    
    redis_conn = memory.get_client()
    if not redis_conn:
        logger.error("❌ No hay conexión Redis para Pairs Listener")
        return

    pubsub = redis_conn.pubsub()
    pubsub.subscribe('market_data')
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                symbol = data['symbol']
                price = data['price']
                LATEST_PRICES[symbol] = price
            except Exception as e:
                pass

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

def get_historical_prices(symbols=['BTC', 'ETH', 'BNB', 'SOL', 'XRP']):
    """
    Obtiene precios históricos desde Binance API para análisis de pares.
    V17: Sin Firestore, usa Binance directamente.
    """
    logger.info(f"📊 Fetching historical data for {len(symbols)} symbols from Binance")
    
    try:
        price_data = {}
        
        for symbol in symbols:
            df = fetch_binance_data(symbol, '1h', WINDOW_SIZE)
            if not df.empty and len(df) >= WINDOW_SIZE:
                price_data[symbol] = df['close'].tolist()
        
        if len(price_data) >= 2:
            logger.info(f"✅ Loaded {len(price_data)} symbols with {WINDOW_SIZE}h data")
            return pd.DataFrame(price_data)
        else:
            logger.warning(f"⚠️ Insufficient data: only {len(price_data)} symbols loaded")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error fetching historical prices: {e}")
        return pd.DataFrame()

def store_signal(asset_a, asset_b, correlation, z_score, signal):
    """Guarda señal de pairs trading en SQLite V17"""
    try:
        session = SessionLocal()
        
        ps = PairsSignal(
            timestamp=datetime.utcnow(),
            asset_a=asset_a,
            asset_b=asset_b,
            correlation=correlation,
            z_score=z_score,
            signal=signal,
            status='OPEN'
        )
        session.add(ps)
        session.commit()
        logger.info(f"💾 Pairs signal stored: {asset_a}-{asset_b}")
        session.close()
    except Exception as e:
        logger.error(f"Error storing pairs signal: {e}")
        if 'session' in locals():
            session.close()

def analyze_pairs():
    """Busca oportunidades de arbitraje (Loop Infinito)"""
    # Monedas a analizar (podría obtenerse de Redis active_symbols en el futuro)
    SYMBOLS_TO_ANALYZE = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']
    
    while True:
        try:
            logger.info("🔍 Buscando pares correlacionados...")
            df = get_historical_prices(SYMBOLS_TO_ANALYZE)
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
                            store_signal(asset_a, asset_b, round(score, 2), round(z_score, 2), signal)
            logger.info("✅ Análisis de pares completado. Durmiendo 5 min.")
            time.sleep(300)
        except Exception as e:
            logger.error(f"Error en loop de pares: {e}")
            time.sleep(60)

@app.route('/')
def health():
    return jsonify({
        "status": "online", 
        "service": "pairs-trading-v15-redis",
        "redis_prices_tracked": len(LATEST_PRICES)
    })

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
        
        limit_map = {'1mo': 720, '3mo': 2160, '6mo': 4320}
        limit = limit_map.get(timeframe, 720)
        
        logger.info(f"Bajando datos para backtest {asset_a}-{asset_b}, limit={limit}")
        df_a = fetch_binance_data(asset_a, '1h', limit)
        df_b = fetch_binance_data(asset_b, '1h', limit)
        
        if df_a.empty or df_b.empty:
            return jsonify({"status": "error", "message": "No data from Binance"}), 404
            
        df = pd.merge(df_a, df_b, on='timestamp', suffixes=('_a', '_b'))
        df.set_index('timestamp', inplace=True)
        
        df['norm_a'] = df['close_a'] / df['close_a'].iloc[0]
        df['norm_b'] = df['close_b'] / df['close_b'].iloc[0]
        df['spread'] = df['norm_a'] - df['norm_b']
        
        roll_window = 24
        df['spread_mean'] = df['spread'].rolling(window=roll_window).mean()
        df['spread_std'] = df['spread'].rolling(window=roll_window).std()
        df['z_score'] = (df['spread'] - df['spread_mean']) / df['spread_std']
        
        balance = capital
        positions = {'a': 0, 'b': 0} 
        entry_equity = 0
        trades = []
        status = "NEUTRAL"
        
        for ts, row in df.iterrows():
            z = row['z_score']
            price_a = row['close_a']
            price_b = row['close_b']
            
            if pd.isna(z): continue
            
            if status == "NEUTRAL":
                if z > z_threshold:
                    size = (balance / 2) 
                    positions['a'] = -size / price_a 
                    positions['b'] = size / price_b
                    entry_equity = balance
                    status = "SHORT_SPREAD"
                    trades.append({'type': 'OPEN_SHORT_SPREAD', 'price_a': price_a, 'price_b': price_b, 'ts': ts, 'z': z})
                    
                elif z < -z_threshold:
                    size = (balance / 2)
                    positions['a'] = size / price_a 
                    positions['b'] = -size / price_b 
                    entry_equity = balance
                    status = "LONG_SPREAD"
                    trades.append({'type': 'OPEN_LONG_SPREAD', 'price_a': price_a, 'price_b': price_b, 'ts': ts, 'z': z})

            elif status == "SHORT_SPREAD":
                if z <= 0: 
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
    # Thread Redis
    redis_thread = threading.Thread(target=redis_listener, daemon=True)
    redis_thread.start()
    
    # Thread Análisis
    analysis_thread = threading.Thread(target=analyze_pairs, daemon=True)
    analysis_thread.start()
    
    app.run(host='0.0.0.0', port=5000)
