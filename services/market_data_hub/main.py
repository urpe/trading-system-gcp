import asyncio
import json
import os
from websockets import connect
from google.cloud import firestore
from google.cloud import pubsub_v1

# Configuración de Clientes
PROJECT_ID = "mi-proyecto-trading-12345"
db = firestore.Client(project=PROJECT_ID)
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "market-updates")

SYMBOLS = ['btcusdt', 'ethusdt', 'solusdt', 'bnbusdt', 'xrpusdt']

async def binance_stream(symbol):
    uri = f"wss://stream.binance.com:9443/ws/{symbol}@ticker"
    print(f"Conectando WebSocket para {symbol}...")
    
    async with connect(uri) as websocket:
        while True:
            try:
                # Recibir datos de Binance
                message = await websocket.recv()
                data = json.loads(message)
                
                price_data = {
                    "symbol": symbol,
                    "price": data['c'],
                    "timestamp": str(data['E']) # Timestamp de Binance
                }
                
                # 1. Guardar en Firestore (Persistencia para el Dashboard)
                db.collection(f"market_data_{symbol}").document("latest").set({
                    "symbol": symbol,
                    "price": data['c'],
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
                
                # 2. Publicar en Pub/Sub (Evento en tiempo real para Estrategias)
                message_json = json.dumps(price_data)
                publisher.publish(topic_path, message_json.encode("utf-8"))
                
                print(f"✅ {symbol.upper()}: {data['c']} (Firestore + Pub/Sub)")
                
            except Exception as e:
                print(f"❌ Error en stream {symbol}: {e}")
                await asyncio.sleep(5) # Esperar antes de reintentar
                break

async def main():
    # Ejecutar todos los streams en paralelo
    tasks = [binance_stream(s) for s in SYMBOLS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
