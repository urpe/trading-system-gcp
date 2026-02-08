"""
V21.2.1: CANONICAL SYMBOL DEFINITIONS
======================================
Centraliza todos los símbolos hard-coded del sistema en un solo lugar.

Antes (V21.2): 12 ubicaciones con magic strings dispersos
Después (V21.2.1): 1 única fuente de verdad

Uso:
    from src.config.symbols import ACTIVE_SYMBOLS, DEFAULT_SYMBOLS
    
    # En lugar de:
    symbols = ['BTC', 'ETH', 'SOL']  # ❌ Magic string
    
    # Usar:
    symbols = ACTIVE_SYMBOLS  # ✅ Canonical source
"""

from enum import Enum
from typing import List

# ============================================================================
# CANONICAL SYMBOL DEFINITIONS
# ============================================================================

class TradingPair(Enum):
    """
    Pares de trading disponibles en el sistema.
    
    Uso:
        TradingPair.BTC.value -> "BTC"
        TradingPair.BTC.name -> "BTC"
    """
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    BNB = "BNB"
    XRP = "XRP"
    TRX = "TRX"
    LINK = "LINK"
    ADA = "ADA"
    DOGE = "DOGE"
    DOT = "DOT"
    AVAX = "AVAX"
    MATIC = "MATIC"
    PAXG = "PAXG"  # V21.3.1: Added PAX Gold (fix Dashboard errors)


# ============================================================================
# ACTIVE SYMBOLS (Formato Corto)
# ============================================================================

# Lista principal de símbolos activos para trading
ACTIVE_SYMBOLS: List[str] = [
    TradingPair.BTC.value,
    TradingPair.ETH.value,
    TradingPair.SOL.value,
    TradingPair.TRX.value,
    TradingPair.LINK.value,
]

# Alias para compatibilidad con código existente
DEFAULT_SYMBOLS_SHORT = ACTIVE_SYMBOLS


# ============================================================================
# DEFAULT SYMBOLS (Formato Largo - Binance)
# ============================================================================

# Lista de símbolos en formato Binance (para Market Data)
DEFAULT_SYMBOLS_LONG: List[str] = [
    f"{symbol}USDT" for symbol in ACTIVE_SYMBOLS
]

# Lista de símbolos en formato lowercase (para streams WebSocket)
DEFAULT_SYMBOLS_LOWER: List[str] = [
    f"{symbol.lower()}usdt" for symbol in ACTIVE_SYMBOLS
]


# ============================================================================
# FALLBACK SYMBOLS (Si Redis falla)
# ============================================================================

FALLBACK_SYMBOLS: List[str] = ACTIVE_SYMBOLS.copy()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_active_symbols(format: str = 'short') -> List[str]:
    """
    Obtiene la lista de símbolos activos en el formato solicitado.
    
    Args:
        format: 'short' -> ["BTC", "ETH"]
                'long' -> ["BTCUSDT", "ETHUSDT"]
                'lower' -> ["btcusdt", "ethusdt"]
    
    Returns:
        Lista de símbolos en el formato solicitado
    
    Examples:
        >>> get_active_symbols('short')
        ['BTC', 'ETH', 'SOL', 'TRX', 'LINK']
        
        >>> get_active_symbols('long')
        ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'TRXUSDT', 'LINKUSDT']
    """
    if format == 'short':
        return ACTIVE_SYMBOLS
    elif format == 'long':
        return DEFAULT_SYMBOLS_LONG
    elif format == 'lower':
        return DEFAULT_SYMBOLS_LOWER
    else:
        raise ValueError(f"Invalid format: {format}. Use 'short', 'long', or 'lower'")


def is_valid_symbol(symbol: str) -> bool:
    """
    Verifica si un símbolo está en la lista de símbolos activos.
    
    Args:
        symbol: Símbolo a verificar (cualquier formato)
    
    Returns:
        True si el símbolo es válido, False en caso contrario
    
    Examples:
        >>> is_valid_symbol("BTC")
        True
        >>> is_valid_symbol("BTCUSDT")
        True
        >>> is_valid_symbol("banana")
        False
    """
    from src.shared.utils import normalize_symbol
    
    try:
        normalized = normalize_symbol(symbol, format='short')
        return normalized in ACTIVE_SYMBOLS
    except (ValueError, TypeError):
        return False


def get_all_supported_pairs() -> List[str]:
    """
    Retorna TODOS los pares soportados (incluso los no activos).
    Útil para backtesting o análisis histórico.
    
    Returns:
        Lista de todos los símbolos en TradingPair enum
    """
    return [pair.value for pair in TradingPair]


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_symbols_config():
    """
    Valida que la configuración de símbolos sea consistente.
    Se ejecuta al importar este módulo.
    """
    # Verificar que no haya duplicados
    if len(ACTIVE_SYMBOLS) != len(set(ACTIVE_SYMBOLS)):
        raise ValueError("ACTIVE_SYMBOLS contains duplicates")
    
    # Verificar que todos los símbolos estén en TradingPair
    valid_pairs = {pair.value for pair in TradingPair}
    for symbol in ACTIVE_SYMBOLS:
        if symbol not in valid_pairs:
            raise ValueError(f"Symbol '{symbol}' not found in TradingPair enum")
    
    # Verificar que las listas derivadas tengan el mismo tamaño
    if len(DEFAULT_SYMBOLS_LONG) != len(ACTIVE_SYMBOLS):
        raise ValueError("DEFAULT_SYMBOLS_LONG size mismatch")
    
    if len(DEFAULT_SYMBOLS_LOWER) != len(ACTIVE_SYMBOLS):
        raise ValueError("DEFAULT_SYMBOLS_LOWER size mismatch")


# Validar al importar
validate_symbols_config()
