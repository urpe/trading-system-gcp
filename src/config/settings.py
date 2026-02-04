import os

class Settings:
    """
    Configuración Global V19.
    Todas las variables de entorno se centralizan aquí.
    """
    # Identidad del Proyecto
    PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
    
    # Configuración de Trading
    INITIAL_CAPITAL = float(os.environ.get("INITIAL_CAPITAL", "1000.0"))  # $1000 para prueba de fuego
    TRADE_AMOUNT = float(os.environ.get("TRADE_AMOUNT", "50.0"))  # V19.1: 5% del capital (conservador)
    MAX_OPEN_POSITIONS = int(os.environ.get("MAX_OPEN_POSITIONS", "2"))  # V19.1: Máximo 2 posiciones
    STOP_LOSS_PCT = float(os.environ.get("STOP_LOSS_PCT", "2.0"))  # V19.1: Stop loss -2%
    ALLOW_SHORT = os.environ.get("ALLOW_SHORT", "True").lower() == "true"
    
    # Trading Mode
    PAPER_TRADING = os.environ.get("PAPER_TRADING", "True").lower() == "true"
    COMMISSION_RATE = float(os.environ.get("COMMISSION_RATE", "0.001"))  # 0.1% (Binance fees)
    
    # Endpoints de Servicios (Service Discovery)
    # Usamos nombres de host de Docker (DNS interno)
    SVC_PORTFOLIO = "http://portfolio:8080"
    SVC_ORDERS = "http://orders:8080"
    SVC_SIMULATOR = "http://simulator:5000"
    
    # Configuración Técnica
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s'

    # Infraestructura (Redis)
    REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

config = Settings()
