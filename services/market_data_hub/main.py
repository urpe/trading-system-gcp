import asyncio
import json
import os
from websockets import connect
from google.cloud import firestore, pubsub_v1
from aiohttp import web

PROJECT_ID = "mi-proyecto-trading-12345"
db = firestore.Client(project=PROJECT_ID)
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "market-updates")
SYMBOLS = ['btcusdt', 'ethusdt', 'solusdt', 'bnbusdt', 'xrpusdt']

async def health_check(request):
    return web.Response(text="OK")

async def binance_stream(symbol):
    """Stream de datos con reconexión robusta y timeout extendido"""
    uri = f"wss://stream.binance.com:443/ws/{symbol}@ticker"
    retry_delay = 5
    max_retry_delay = 60
    
    while True:
        try:
            # Aumentar timeout de conexión a 30 segundos
            async with connect(uri, ping_interval=20, ping_timeout=20, close_timeout=10, open_timeout=30) as websocket:
                print(f"✅ Conectado a {symbol}")
                retry_delay = 5  # Reset delay on successful connection
                
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=60)
                        data = json.loads(message)
                        symbol_upper = symbol.replace('usdt', '').upper()
                        
                        price_data = {
                            "symbol": symbol_upper,
                            "price": float(data['c']),
                            "change": float(data['P']),
                            "high": float(data['h']),
                            "low": float(data['l']),
                            "volume": float(data['v'])
                        }
                        
                        # Guardar en Firestore
                        db.collection('market_data').document(symbol_upper).set({
                            **price_data,
                            "timestamp": firestore.SERVER_TIMESTAMP
                        })
                        
                        # Publicar en Pub/Sub para el Strategy Agent
                        publisher.publish(topic_path, json.dumps(price_data).encode("utf-8"))
                        
                    except asyncio.TimeoutError:
                        print(f"⏱️ Timeout recibiendo datos de {symbol}, reconectando...")
                        break
                        
        except Exception as e:
            print(f"❌ Error en {symbol}: {e}")
            print(f"🔄 Reintentando en {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)

async def start_streams_sequentially():
    """Iniciar streams uno por uno para evitar sobrecarga"""
    tasks = []
    for symbol in SYMBOLS:
        print(f"🚀 Iniciando stream para {symbol}...")
        task = asyncio.create_task(binance_stream(symbol))
        tasks.append(task)
        await asyncio.sleep(2)  # Esperar 2 segundos entre cada conexión
    return tasks

async def main():
    # Servidor web para health checks
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    print("🌐 Hub iniciado en puerto 8080")
    
    # Iniciar streams secuencialmente
    tasks = await start_streams_sequentially()
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
