import os
import redis
import json
import logging
from src.config.settings import config

logger = logging.getLogger("RedisClient")

class RedisClient:
    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance

    def connect(self):
        """Establece conexión con Redis (Singleton)"""
        if self._connection:
            try:
                self._connection.ping()
                return self._connection
            except redis.ConnectionError:
                logger.warning("⚠️ Conexión Redis perdida, reconectando...")
                self._connection = None

        redis_host = config.REDIS_HOST
        redis_port = config.REDIS_PORT
        
        try:
            # V17: socket_timeout=None for blocking Pub/Sub listeners
            # para evitar que los workers (Brain/Persistence) crashean esperando mensajes.
            self._connection = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=0, 
                decode_responses=True,
                socket_timeout=None,
                socket_connect_timeout=10
            )
            self._connection.ping()
            logger.info(f"✅ Conectado a Redis en {redis_host}:{redis_port}")
            return self._connection
        except Exception as e:
            logger.critical(f"🔥 Fallo conectando a Redis: {e}")
            return None

    def get_client(self):
        """Retorna el cliente crudo para operaciones avanzadas (PubSub, etc)"""
        return self.connect()

    def publish(self, channel: str, message: dict):
        """Publica un mensaje JSON en un canal"""
        try:
            r = self.connect()
            if r:
                r.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Error publicando en {channel}: {e}")

    def set(self, key: str, value: any, ttl: int = None):
        """Guarda un valor (serializa dicts a JSON automáticamente)"""
        try:
            r = self.connect()
            if r:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                r.set(key, value, ex=ttl)
        except Exception as e:
            logger.error(f"Error escribiendo key {key}: {e}")

    def get(self, key: str):
        """Obtiene un valor (intenta deserializar JSON)"""
        try:
            r = self.connect()
            if r:
                val = r.get(key)
                if val:
                    try:
                        return json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        return val
        except Exception as e:
            logger.error(f"Error leyendo key {key}: {e}")
        return None

# Instancia global para importar
memory = RedisClient()
