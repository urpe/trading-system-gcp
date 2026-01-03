import asyncio
import json
import os
import time
from websockets import connect
from google.cloud import firestore, pubsub_v1
from aiohttp import web

PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "market-updates")

# ============================================================
# CONFIGURACIÓN PRO - OPTIMIZADA PARA COSTOS Y ESCALABILIDAD
# ============================================================
# Lista de 50 monedas para monitoreo completo del mercado
SYMBOLS = [
    'btcusdt', 'ethusdt', 'bnbusdt', 'solusdt', 'xrpusdt',
    'adausdt', 'dogeusdt', 'avaxusdt', 'dotusdt', 'maticusdt',
    'linkusdt', 'ltcusdt', 'atomusdt', 'uniusdt', 'etcusdt',
    'xlmusdt', 'nearusdt', 'aptusdt', 'filusdt', 'arbusdt',
    'opusdt', 'injusdt', 'suiusdt', 'seiusdt', 'tiausdt',
    'runeusdt', 'ftmusdt', 'aaveusdt', 'mkrusdt', 'snxusdt',
    'ldousdt', 'rndrusdt', 'grtusdt', 'imxusdt', 'sandusdt',
    'manausdt', 'axsusdt', 'apeusdt', 'gmtusdt', 'galausdt',
    'chzusdt', 'enjusdt', 'flowusdt', 'kavausdt', 'algousdt',
    'vetusdt', 'icpusdt', 'hbarusdt', 'qntusdt', 'egldusdt'
]

# Throttling: Escribir en Firestore solo cada 15 segundos (ahorro masivo)
DB_WRITE_INTERVAL = 15
last_db_write = {}

async def health_check(request):
    """
    Endpoint de salud para Google Cloud Run.
    Cloud Run verifica este endpoint para saber si el servicio está vivo.
    """
    active_symbols = len(last_db_write)
    return web.Response(
        text=f"Market Data Hub v7.0 PRO | Monitoreando {active_symbols}/{len(SYMBOLS)} activos",
        content_type="text/plain"
    )

async def binance_multiplex_stream():
    """
    CONEXIÓN MULTIPLEXADA PRO
    -------------------------
    ¿Qué es Multiplexing?
    En lugar de abrir 50 conexiones separadas (una por moneda),
    abrimos UNA SOLA conexión que recibe datos de todas las monedas.
    
    Beneficios:
    1. Evita bloqueos de IP por exceso de conexiones
    2. Menor latencia (menos handshakes)
    3. Más eficiente en recursos
    
    Binance soporta hasta 1024 streams en una conexión multiplex.
    """
    streams = "/".join([f"{s}@ticker" for s in SYMBOLS])
    uri = f"wss://stream.binance.com:443/stream?streams={streams}"
    
    retry_delay = 5
    
    while True:
        try:
            print(f"🔌 Conectando a Binance Multiplex Stream ({len(SYMBOLS)} activos)...")
            async with connect(uri, ping_interval=20, ping_timeout=10, close_timeout=10) as websocket:
                print("✅ Conexión multiplex establecida exitosamente.")
                retry_delay = 5
                
                while True:
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    
                    # Estructura del mensaje multiplex: {"stream": "btcusdt@ticker", "data": {...}}
                    ticker = data['data']
                    symbol_raw = ticker['s']  # Ej: BTCUSDT
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
                    
                    # =========================================================
                    # ESTRATEGIA DE ESCRITURA DUAL (Tiempo Real vs Económico)
                    # =========================================================
                    
                    # 1. PUB/SUB: Tiempo real para el Strategy Agent (cada tick)
                    #    El bot necesita cada movimiento para operar rápido
                    #    Pub/Sub es muy económico para alto volumen
                    publisher.publish(topic_path, json.dumps(price_data).encode("utf-8"))
                    
                    # 2. FIRESTORE: Throttled para el Dashboard (cada 15 segundos)
                    #    Los humanos no necesitan ver cambios cada milisegundo
                    #    Esto reduce las escrituras de ~86,400/día a ~5,760/día por moneda
                    now = time.time()
                    if now - last_db_write.get(symbol_clean, 0) > DB_WRITE_INTERVAL:
                        db.collection('market_data').document(symbol_clean).set({
                            **price_data,
                            "timestamp": firestore.SERVER_TIMESTAMP
                        })
                        last_db_write[symbol_clean] = now

        except Exception as e:
            print(f"❌ Error en Websocket: {e}")
            print(f"🔄 Reintentando en {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Backoff exponencial, máximo 60s

async def main():
    # Servidor HTTP para Health Check de Cloud Run
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"🚀 Hub Pro v7.0 iniciado en puerto {port}")
    print(f"📊 Monitoreando {len(SYMBOLS)} activos")
    
    # Iniciar el Stream Multiplexado
    await binance_multiplex_stream()

if __name__ == '__main__':
    asyncio.run(main())
