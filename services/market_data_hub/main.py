import asyncio
import json
import os
from websockets import connect
from google.cloud import firestore

db = firestore.Client(project="mi-proyecto-trading-12345")
SYMBOLS = ['btcusdt', 'ethusdt', 'solusdt', 'bnbusdt', 'xrpusdt']

async def binance_stream(symbol):
    uri = f"wss://stream.binance.com:9443/ws/{symbol}@ticker"
    async with connect(uri) as websocket:
        while True:
            data = json.loads(await websocket.recv())
            price_data = {
                "symbol": symbol,
                "price": data['c'],
                "timestamp": firestore.SERVER_TIMESTAMP
            }
            # Guardar en Firestore (y en el futuro en Redis)
            db.collection(f"market_data_{symbol}").document("latest").set(price_data)
            print(f"Updated {symbol}: {data['c']}")

async def main():
    tasks = [binance_stream(s) for s in SYMBOLS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
