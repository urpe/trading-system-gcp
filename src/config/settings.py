import os

class Settings:
    """
    Configuración Global V13.
    Todas las variables de entorno se centralizan aquí.
    """
    # Identidad del Proyecto
    PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
    
    # Configuración de Trading
    INITIAL_CAPITAL = 10000.0
    TRADE_AMOUNT = float(os.environ.get("TRADE_AMOUNT", "2000.0"))
    ALLOW_SHORT = os.environ.get("ALLOW_SHORT", "True").lower() == "true"
    
    # Endpoints de Servicios (Service Discovery)
    # Usamos nombres de host de Docker (DNS interno)
    SVC_PORTFOLIO = "http://portfolio:8080"
    SVC_ORDERS = "http://orders:8080"
    
    # Configuración Técnica
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s'

config = Settings()
