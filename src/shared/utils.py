import logging
import sys
import time
import random
import requests
from src.config.settings import config
from src.domain import TradingSymbol  # V21.3: Use Value Object

def get_logger(service_name: str) -> logging.Logger:
    """Genera un logger estandarizado para todo el sistema"""
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(config.LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(config.LOG_LEVEL)
    return logger

def normalize_symbol(symbol: str, format: str = 'short') -> str:
    """
    V21.3: NORMALIZACIÓN UNIFICADA DE SÍMBOLOS (Canonical Core)
    ============================================================
    Usa TradingSymbol Value Object internamente para garantizar type safety.
    
    DEPRECATION NOTICE: 
    Esta función existe para backward compatibility.
    Código nuevo debe usar TradingSymbol directamente:
    
        from src.domain import TradingSymbol
        symbol = TradingSymbol.from_str("BTC")
        key = symbol.to_redis_key("price")  # "price:BTC"
    
    Args:
        symbol: El símbolo a normalizar (puede venir como "BTC", "btc", "BTCUSDT", "btcusdt")
        format: 'short' (default) -> "BTC" | 'long' -> "BTCUSDT" | 'lower' -> "btcusdt"
    
    Returns:
        str: Símbolo normalizado según el formato solicitado
    
    Raises:
        TypeError: Si symbol no es un string
        ValueError: Si symbol está vacío o es inválido
    
    Ejemplos:
        normalize_symbol("btcusdt")           -> "BTC"
        normalize_symbol("BTCUSDT")           -> "BTC"
        normalize_symbol("BTC")               -> "BTC"
        normalize_symbol("eth", format="long") -> "ETHUSDT"
        normalize_symbol("SOL", format="lower") -> "solusdt"
    
    CRITICAL: Esta función DEBE ser usada por TODOS los servicios antes de:
    - Escribir claves en Redis (price:{symbol}, market_regime:{symbol})
    - Leer claves desde Redis
    - Consultar APIs externas (Binance)
    """
    # V21.3: Delegate to TradingSymbol Value Object
    ts = TradingSymbol.from_str(symbol)
    
    if format == 'short':
        return ts.to_short()
    elif format == 'long':
        return ts.to_long()
    elif format == 'lower':
        return ts.to_lower()
    else:
        raise ValueError(f"Invalid format: {format}. Use 'short', 'long', or 'lower'")

def fetch_binance_klines(symbol: str, interval: str = '1m', limit: int = 200) -> list:
    """
    V21.2: WARM-UP HELPER - Descarga velas históricas de Binance
    ==============================================================
    Usado por Brain/Market Data para llenar historial inicial sin esperar 3+ horas.
    
    Args:
        symbol: Símbolo base (ej: "BTC", no "BTCUSDT")
        interval: Intervalo de velas (1m, 5m, 1h, etc.)
        limit: Cantidad de velas (max 1000 por Binance API)
    
    Returns:
        Lista de diccionarios OHLCV: [{"open": float, "high": float, "low": float, "close": float, "volume": float}, ...]
    """
    logger = get_logger("BinanceKlinesFetcher")
    
    # Normalizar símbolo al formato largo de Binance
    binance_symbol = normalize_symbol(symbol, format='long')
    
    url = "https://api.binance.com/api/v3/klines"
    params = {
        'symbol': binance_symbol,
        'interval': interval,
        'limit': limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        klines = response.json()
        
        # Validar respuesta
        if isinstance(klines, dict) and 'code' in klines:
            logger.error(f"❌ Binance API error: {klines}")
            return []
        
        # Convertir a formato OHLCV estándar
        ohlcv_data = []
        for k in klines:
            ohlcv_data.append({
                'timestamp': int(k[0]) / 1000,  # OpenTime en segundos
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            })
        
        logger.info(f"✅ Descargadas {len(ohlcv_data)} velas de {binance_symbol} ({interval})")
        return ohlcv_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching klines for {binance_symbol}: {e}")
        return []

def robust_http_request(method: str, url: str, json_data: dict = None, max_retries: int = 3):
    """Realiza peticiones HTTP con Exponential Backoff (Circuit Breaker Light)"""
    logger = get_logger("SharedNetwork")
    for i in range(max_retries):
        try:
            if method == 'POST':
                resp = requests.post(url, json=json_data, timeout=5)
            else:
                resp = requests.get(url, timeout=5)
            return resp
        except requests.RequestException as e:
            wait = (0.5 * (2 ** i)) + random.uniform(0, 0.1)
            if i == max_retries - 1:
                logger.error(f"❌ Network fail after {max_retries} tries: {url} | {e}")
                raise e
            time.sleep(wait)
