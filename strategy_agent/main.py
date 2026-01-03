import os
import threading
from flask import Flask
from google.cloud import pubsub_v1

app = Flask(__name__)

# Lógica de procesamiento de señales
def callback(message):
    print(f"Recibido mensaje: {message.data}")
    # Aquí va tu lógica de SMA/Estrategia
    message.ack()

def start_subscriber():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path("mi-proyecto-trading-12345", "market-updates-sub")
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Escuchando mensajes en {subscription_path}...")
    try:
        streaming_pull_future.result()
    except Exception as e:
        print(f"Error en suscriptor: {e}")

# Ruta de salud para que Google Cloud no apague el servicio
@app.route('/')
def health():
    return "Agent is Alive", 200

if __name__ == '__main__':
    # Iniciamos el suscriptor en un hilo separado para no bloquear el servidor web
    threading.Thread(target=start_subscriber, daemon=True).start()
    
    # El servidor web principal que Google Cloud necesita
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
