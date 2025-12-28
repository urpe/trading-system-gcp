# Arquitectura del Sistema

## Flujo de Datos
1. Data Ingestor conecta a Binance WebSocket
2. Publica datos en Pub/Sub (datos-crudos)
3. Strategy Agent consume y analiza con SMA/RSI
4. Genera señales en Pub/Sub (senales-trading)
5. Order Agent ejecuta en Binance Testnet
6. Dashboard lee de Firestore

## URLs de Servicios
- Dashboard: https://dashboard-347366802960.us-central1.run.app
- Data Ingestor: https://data-ingestor-347366802960.us-central1.run.app
- Strategy Agent: https://strategy-agent-347366802960.us-central1.run.app
- Order Agent: https://order-agent-347366802960.us-central1.run.app
- Alert Service: (se mostrará después del despliegue )
