import sys
import os

# FIX V14.2: Asegurar que Python vea los submódulos locales
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import asyncio
import json
import time
import aiohttp
from websockets import connect
from aiohttp import web
from src.shared.memory import memory # <--- NEW SHARED CLIENT
from src.shared.utils import get_logger

# --- IMPORTACIÓN DEL NUEVO CEREBRO FINANCIERO ---
from analyzer.selection_logic import MarketSelector

# Configuración de Logs V17
logger = get_logger("MarketDataHub")

# --- CONFIGURACIÓN DINÁMICA ---
# Lista inicial por defecto (backup si falla el análisis)
DEFAULT_SYMBOLS = ['btcusdt', 'ethusdt', 'bnbusdt', 'solusdt', 'xrpusdt']
current_symbols = DEFAULT_SYMBOLS.copy()

MARKET_SCAN_INTERVAL = 3600  # Escanear el mercado cada 1 hora (3600s)
selector = MarketSelector() # Instancia del cerebro

async def health_check(request):
    """Endpoint de salud para Cloud Run."""
    status = "✅ Connected" if memory.connect() else "❌ Redis Fail"

    return web.Response(
        text=f"Market Data Hub v15.0 (Redis Enterprise) | Redis: {status} | Monitoreando: {current_symbols}",
        content_type="text/plain"
    )

async def fetch_binance_ticker_24hr():
    """Obtiene el resumen de 24h de todos los pares de Binance para el análisis."""
    url = "https://api.binance.com/api/v3/ticker/24hr"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # Convertir lista a diccionario para el selector
                return {item['symbol']: item for item in data}
            else:
                logger.error(f"Error obteniendo tickers de Binance: {response.status}")
                return {}

async def fetch_latest_kline(symbol: str) -> dict:
    """
    V21 EAGLE EYE: Obtiene la última vela cerrada de 1 minuto desde Binance.
    
    Endpoint: GET /api/v3/klines
    Params: symbol=BTCUSDT, interval=1m, limit=1
    
    Returns:
        {
            "symbol": "BTC",
            "timestamp": 1709...,
            "open": 75000.0,
            "high": 75500.0,
            "low": 74900.0,
            "close": 75200.0,
            "volume": 120.5
        }
    """
    url = "https://api.binance.com/api/v3/klines"
    
    # Normalizar símbolo: si viene "btcusdt" -> "BTCUSDT", si viene "btc" -> "BTCUSDT"
    symbol_clean = symbol.replace('usdt', '').replace('USDT', '').upper()
    binance_symbol = f"{symbol_clean}USDT"
    
    params = {
        "symbol": binance_symbol,
        "interval": "1m",
        "limit": 1
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and len(data) > 0:
                        kline = data[0]
                        
                        # Binance kline format: [OpenTime, Open, High, Low, Close, Volume, ...]
                        return {
                            "symbol": symbol_clean,  # Ya normalizado arriba
                            "timestamp": int(kline[0]) / 1000,  # Convert to seconds
                            "open": float(kline[1]),
                            "high": float(kline[2]),
                            "low": float(kline[3]),
                            "close": float(kline[4]),
                            "volume": float(kline[5])
                        }
                else:
                    logger.error(f"Error fetching kline for {symbol}: HTTP {response.status}")
                    
    except Exception as e:
        logger.error(f"Exception fetching kline for {symbol}: {e}")
    
    return None

async def update_top_coins():
    """
    Función periódica que usa el MarketSelector para encontrar las mejores monedas.
    """
    global current_symbols
    logger.info("🕵️‍♂️ Iniciando escaneo de mercado para actualizar Top 5...")
    
    tickers = await fetch_binance_ticker_24hr()
    if tickers:
        new_top = selector.filter_candidates(tickers)
        # Convertir a minúsculas para el stream
        new_top_lower = [s.lower() for s in new_top]
        
        # Si la lista cambió, actualizamos
        if set(new_top_lower) != set(current_symbols):
            logger.info(f"🔄 CAMBIO DE ESTRATEGIA: {current_symbols} -> {new_top_lower}")
            current_symbols = new_top_lower
            
            # --- V15 ENTERPRISE: Notificar cambio a Redis ---
            try:
                memory.set("active_symbols", current_symbols)
                logger.info(f"💾 Active Symbols guardados en Redis: {current_symbols}")
            except Exception as e:
                logger.error(f"❌ Error guardando active_symbols: {e}")
                
            return True # Indica que hay que reiniciar el stream
        else:
            # Aunque no cambie, refrescamos el TTL/valor en Redis
            memory.set("active_symbols", current_symbols)
            logger.info("✅ El Top 5 se mantiene estable. Sin cambios.")
            return False
    return False

async def ohlcv_update_cycle():
    """
    V21 EAGLE EYE: Ciclo de actualización OHLCV cada 60 segundos.
    
    Flujo:
    1. Cada 60s, fetch última vela cerrada (1m) de cada símbolo activo
    2. Publica OHLCV completo en Redis
    3. Actualiza cache de precios para Dashboard
    """
    retry_delay = 5
    last_scan_time = time.time()
    
    # Asegurar que tenemos símbolos activos
    await update_top_coins()
    
    logger.info("🦅 V21 EAGLE EYE: OHLCV Update Cycle iniciado (60s interval)")
    
    while True:
        try:
            # 1. Fetch OHLCV de cada símbolo activo
            for symbol in current_symbols:
                kline_data = await fetch_latest_kline(symbol)
                
                if kline_data:
                    # 2. Publicar en Redis Pub/Sub para Brain
                    memory.publish('market_data', kline_data)
                    
                    # 3. Cache en Redis para Dashboard (mantener compatibilidad)
                    memory.set(f"price:{kline_data['symbol']}", kline_data)
                    
                    logger.info(f"📊 OHLCV: {kline_data['symbol']} | O:{kline_data['open']:.2f} H:{kline_data['high']:.2f} L:{kline_data['low']:.2f} C:{kline_data['close']:.2f}")
                else:
                    logger.warning(f"⚠️ No se pudo obtener OHLCV para {symbol}")
            
            # 4. Verificar si toca re-escanear mercado (cada hora)
            if time.time() - last_scan_time > MARKET_SCAN_INTERVAL:
                logger.info("⏰ Re-evaluando mercado...")
                await update_top_coins()
                last_scan_time = time.time()
            
            # 5. Esperar 60 segundos (sincronizado con cierre de velas)
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"❌ Error en OHLCV cycle: {e}")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

async def main():
    # Servidor HTTP Health Check
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🚀 Market Data Hub V21 EAGLE EYE (OHLCV) iniciado en puerto {port}")
    
    # V21: Iniciar motor OHLCV
    await ohlcv_update_cycle()

if __name__ == '__main__':
    asyncio.run(main())
