import asyncio
import json
import os
from websockets import connect
from google.cloud import firestore, pubsub_v1
from aiohttp import web

# Configuración
PROJECT_ID = "mi-proyecto-trading-12345"
db = firestore.Client(project=PROJECT_ID )
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "market-updates")
SYMBOLS = ['btcusdt', 'ethusdt', 'solusdt', 'bnbusdt', 'xrpusdt']

# 1. Servidor de Salud (Async)
async def health_check(request):
    return web.Response(text="OK")

# 2. Lógica de WebSockets
async def binance_stream(symbol):
    uri = f"wss://stream.binance.com:443/ws/{symbol}@ticker"
    while True:
        try:
            async with connect(uri) as websocket:
                while True:
                    data = json.loads(await websocket.recv())
                    price_data = {"symbol": symbol, "price": data['c'], "timestamp": str(data['E'])}
                    # Guardar y Publicar
                    db.collection(f"market_data_{symbol}").document("latest").set({
                        "symbol": symbol, "price": data['c'], "timestamp": firestore.SERVER_TIMESTAMP
                    })
                    publisher.publish(topic_path, json.dumps(price_data).encode("utf-8"))
        except Exception as e:
            print(f"Error en {symbol}: {e}")
            await asyncio.sleep(5)

# 3. Orquestador Principal
async def main():
    # Configurar servidor web de salud
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    
    # Arrancar todo en paralelo
    print("🚀 Iniciando Market Data Hub v5.1.2...")
    await asyncio.gather(
        site.start(),
        *[binance_stream(s) for s in SYMBOLS]
    )

if __name__ == "__main__":
    asyncio.run(main())
