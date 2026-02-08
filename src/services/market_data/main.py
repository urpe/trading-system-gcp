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
from src.shared.utils import get_logger, normalize_symbol  # Keep for backward compat
from src.domain import TradingSymbol, parse_symbol_list  # V21.3: Value Object
from src.config.symbols import DEFAULT_SYMBOLS_LOWER, ACTIVE_SYMBOLS

# --- IMPORTACIÓN DEL NUEVO CEREBRO FINANCIERO ---
from analyzer.selection_logic import MarketSelector

# Configuración de Logs V17
logger = get_logger("MarketDataHubV21.3")

# --- CONFIGURACIÓN DINÁMICA ---
# V21.3: Parse to TradingSymbol list (type-safe)
DEFAULT_SYMBOLS_STR = DEFAULT_SYMBOLS_LOWER  # ['btcusdt', 'ethusdt', ...]
current_symbols = parse_symbol_list(DEFAULT_SYMBOLS_STR)  # List[TradingSymbol]

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

async def fetch_latest_kline(symbol: TradingSymbol) -> dict:
    """
    V21.3: Obtiene la última vela cerrada de 1 minuto desde Binance (Value Object).
    
    Args:
        symbol: TradingSymbol (type-safe, ya validado)
    
    Returns:
        {
            "symbol": "BTC",  # Formato corto consistente
            "timestamp": 1709...,
            "open": 75000.0,
            "high": 75500.0,
            "low": 74900.0,
            "close": 75200.0,
            "volume": 120.5
        }
    """
    url = "https://api.binance.com/api/v3/klines"
    
    params = {
        "symbol": symbol.to_binance_api(),  # V21.3: Type-safe "BTCUSDT"
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
                            "symbol": symbol.to_short(),  # V21.3: Type-safe "BTC"
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
    V21.3: Función periódica que usa el MarketSelector (Value Object Pattern).
    """
    global current_symbols
    logger.info("🕵️‍♂️ Iniciando escaneo de mercado para actualizar Top 5...")
    
    tickers = await fetch_binance_ticker_24hr()
    if tickers:
        new_top = selector.filter_candidates(tickers)  # Retorna ["BTCUSDT", "ETHUSDT", ...]
        
        # V21.3: Parse to List[TradingSymbol]
        try:
            new_top_symbols = parse_symbol_list(new_top)  # List[TradingSymbol]
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Error parsing new top symbols: {e}")
            return False
        
        # Comparar bases (formato corto para comparación)
        current_bases = {s.to_short() for s in current_symbols}
        new_bases = {s.to_short() for s in new_top_symbols}
        
        # Si la lista cambió, actualizamos
        if new_bases != current_bases:
            logger.info(f"🔄 CAMBIO DE ESTRATEGIA: {[str(s) for s in current_symbols]} -> {[str(s) for s in new_top_symbols]}")
            current_symbols = new_top_symbols
            
            # --- V21.3: Guardar en Redis (formato corto para consistency) ---
            try:
                symbols_to_store = [s.to_short() for s in current_symbols]  # ["BTC", "ETH", ...]
                memory.set("active_symbols", symbols_to_store)
                logger.info(f"💾 Active Symbols guardados en Redis: {symbols_to_store}")
            except Exception as e:
                logger.error(f"❌ Error guardando active_symbols: {e}")
                
            return True  # Indica que hay que reiniciar el stream
        else:
            # Aunque no cambie, refrescamos el TTL/valor en Redis
            symbols_to_store = [s.to_short() for s in current_symbols]
            memory.set("active_symbols", symbols_to_store)
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
            for symbol in current_symbols:  # symbol is TradingSymbol
                kline_data = await fetch_latest_kline(symbol)
                
                if kline_data:
                    # 2. Publicar en Redis Pub/Sub para Brain
                    memory.publish('market_data', kline_data)
                    
                    # 3. Cache en Redis para Dashboard (V21.3: usando Value Object)
                    redis_key = symbol.to_redis_key("price")  # "price:BTC"
                    memory.set(redis_key, kline_data, ttl=300)
                    
                    logger.info(f"📊 OHLCV: {symbol} | O:{kline_data['open']:.2f} H:{kline_data['high']:.2f} L:{kline_data['low']:.2f} C:{kline_data['close']:.2f}")
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
