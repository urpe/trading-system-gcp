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
    uri = f"wss://stream.binance.com:443/ws/{symbol}@ticker"
    while True:
        try:
            async with connect(uri) as websocket:
                while True:
                    data = json.loads(await websocket.recv())
                    symbol_upper = symbol.replace('usdt', '').upper()
                    
                    price_data = {
                        "symbol": symbol_upper,
                        "price": float(data['c']),
                        "change": float(data['P']),
                        "high": float(data['h']),
                        "low": float(data['l']),
                        "volume": float(data['v'])
                    }
                    
                    db.collection('market_data').document(symbol_upper).set({
                        **price_data,
                        "timestamp": firestore.SERVER_TIMESTAMP
                    })
                    
                    publisher.publish(topic_path, json.dumps(price_data).encode("utf-8"))
                    
        except Exception as e:
            print(f"Error en {symbol}: {e}")
            await asyncio.sleep(5)

async def main():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    print("Hub iniciado en puerto 8080")
    
    tasks = [binance_stream(s) for s in SYMBOLS]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
