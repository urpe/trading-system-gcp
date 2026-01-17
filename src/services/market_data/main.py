import asyncio
import json
import os
import time
import logging
import aiohttp
from websockets import connect
from google.cloud import firestore, pubsub_v1
from aiohttp import web

# --- IMPORTACIÓN DEL NUEVO CEREBRO FINANCIERO ---
from analyzer.selection_logic import MarketSelector

# Configuración de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MarketDataHub')

PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "market-updates")

# --- CONFIGURACIÓN DINÁMICA ---
# Lista inicial por defecto (backup si falla el análisis)
DEFAULT_SYMBOLS = ['btcusdt', 'ethusdt', 'bnbusdt', 'solusdt', 'xrpusdt']
current_symbols = DEFAULT_SYMBOLS.copy()

# Intervalos
DB_WRITE_INTERVAL = 15
MARKET_SCAN_INTERVAL = 3600  # Escanear el mercado cada 1 hora (3600s)

last_db_write = {}
selector = MarketSelector() # Instancia del cerebro

async def health_check(request):
    """Endpoint de salud para Cloud Run."""
    active_symbols = len(last_db_write)
    return web.Response(
        text=f"Market Data Hub v9.0 (Dynamic) | Monitoreando {len(current_symbols)} activos: {current_symbols}",
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
            return True # Indica que hay que reiniciar el stream
        else:
            logger.info("✅ El Top 5 se mantiene estable. Sin cambios.")
            return False
    return False

async def binance_multiplex_stream():
    """
    CONEXIÓN MULTIPLEXADA DINÁMICA
    Se reconecta automáticamente si cambia la lista de monedas.
    """
    retry_delay = 5
    
    while True:
        try:
            # 1. Antes de conectar, aseguramos tener el Top actualizado
            await update_top_coins()
            
            streams = "/".join([f"{s}@ticker" for s in current_symbols])
            uri = f"wss://stream.binance.com:443/stream?streams={streams}"
            
            logger.info(f"🔌 Conectando a Binance Stream para: {current_symbols}")
            
            async with connect(uri, ping_interval=20, ping_timeout=10, close_timeout=10) as websocket:
                logger.info("✅ Conexión establecida.")
                retry_delay = 5
                
                # Bucle de lectura de mensajes
                last_scan_time = time.time()
                
                while True:
                    # A. Recibir Datos
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=25)
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Timeout en Websocket, reconectando...")
                        break # Rompe el bucle interno para reconectar

                    data = json.loads(msg)
                    
                    # Procesar datos (igual que antes)
                    if 'data' in data:
                        ticker = data['data']
                        symbol_raw = ticker['s']
                        symbol_clean = symbol_raw.replace('USDT', '')
                        
                        price_data = {
                            "symbol": symbol_clean,
                            "price": float(ticker['c']),
                            "change": float(ticker['P']),
                            "high": float(ticker['h']),
                            "low": float(ticker['l']),
                            "volume": float(ticker['v']),
                            "timestamp": time.time()
                        }
                        
                        # 1. Pub/Sub (Tiempo Real)
                        publisher.publish(topic_path, json.dumps(price_data).encode("utf-8"))
                        
                        # 2. Firestore (Throttled)
                        now = time.time()
                        if now - last_db_write.get(symbol_clean, 0) > DB_WRITE_INTERVAL:
                            db.collection('market_data').document(symbol_clean).set({
                                **price_data,
                                "timestamp": firestore.SERVER_TIMESTAMP
                            })
                            last_db_write[symbol_clean] = now

                    # B. Verificar si toca re-escanear el mercado (cada hora)
                    if time.time() - last_scan_time > MARKET_SCAN_INTERVAL:
                        logger.info("⏰ Hora de re-evaluar el mercado...")
                        changed = await update_top_coins()
                        if changed:
                            logger.info("♻️ Reiniciando conexión para aplicar nuevos símbolos...")
                            break # Rompe el bucle para reconectar con nueva URI
                        last_scan_time = time.time()

        except Exception as e:
            logger.error(f"❌ Error en Loop Principal: {e}")
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
    
    logger.info(f"🚀 Market Data Hub v9.0 (Dynamic) iniciado en puerto {port}")
    
    # Iniciar el motor
    await binance_multiplex_stream()

if __name__ == '__main__':
    asyncio.run(main())