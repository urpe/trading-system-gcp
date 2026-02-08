"""
V21.3 "CANONICAL CORE" - DOMAIN MODEL
======================================
Value Object Pattern para Trading Symbols.

Filosofía:
- "Make illegal states unrepresentable" (Scott Wlaschin)
- Si un TradingSymbol existe, es VÁLIDO por construcción
- Imposible crear instancias inválidas

Uso:
    from src.domain.trading_symbol import TradingSymbol
    
    # Construcción
    symbol = TradingSymbol.from_str("BTC")       # ✅ OK
    symbol = TradingSymbol.from_str("BTCUSDT")   # ✅ OK (auto-parse)
    symbol = TradingSymbol.from_str("banana")    # ❌ ValueError
    
    # Formatos
    symbol.to_short()      # "BTC"
    symbol.to_long()       # "BTCUSDT"
    symbol.to_lower()      # "btcusdt"
    symbol.to_redis_key("price")  # "price:BTC"
    
    # Inmutabilidad
    symbol.base = "ETH"    # ❌ AttributeError (frozen dataclass)
    
    # Comparación
    btc1 = TradingSymbol.from_str("BTC")
    btc2 = TradingSymbol.from_str("BTCUSDT")
    btc1 == btc2  # True (mismo símbolo base)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Literal, Dict


class QuoteCurrency(Enum):
    """
    Monedas de cotización soportadas.
    
    Por ahora solo USDT, pero preparado para expansión futura.
    """
    USDT = "USDT"
    BUSD = "BUSD"  # Para futuro
    EUR = "EUR"    # Para futuro
    

class TradingPair(Enum):
    """
    Pares de trading válidos en el sistema.
    
    Si un símbolo no está aquí, NO es válido.
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
    SHIB = "SHIB"
    LTC = "LTC"
    UNI = "UNI"
    PAXG = "PAXG"  # V21.3.1: PAX Gold
    
    @classmethod
    def is_valid(cls, symbol: str) -> bool:
        """Verifica si un símbolo está en el enum"""
        return symbol.upper() in cls._value2member_map_


@dataclass(frozen=True)  # Inmutable
class TradingSymbol:
    """
    Value Object para símbolos de trading.
    
    Garantías:
    - Inmutable (frozen=True)
    - Siempre válido (validación en construcción)
    - Type-safe (no es un string suelto)
    - Auto-normalización
    
    Attributes:
        base: Símbolo base (ej: "BTC")
        quote: Moneda de cotización (default: USDT)
    
    Examples:
        >>> symbol = TradingSymbol.from_str("BTC")
        >>> symbol.to_long()
        'BTCUSDT'
        
        >>> symbol.to_redis_key("price")
        'price:BTC'
        
        >>> TradingSymbol.from_str("banana")
        ValueError: Invalid trading pair: banana
    """
    
    base: str
    quote: QuoteCurrency = QuoteCurrency.USDT
    
    def __post_init__(self):
        """
        Validación post-construcción.
        
        Se ejecuta DESPUÉS de __init__, pero ANTES de devolver la instancia.
        """
        # Validar que base sea un par válido
        if not TradingPair.is_valid(self.base):
            valid_pairs = [p.value for p in TradingPair]
            raise ValueError(
                f"Invalid trading pair: {self.base}. "
                f"Valid pairs: {', '.join(valid_pairs)}"
            )
        
        # Validar que base sea uppercase
        if self.base != self.base.upper():
            # Corregir silenciosamente (Value Objects pueden auto-normalizarse)
            object.__setattr__(self, 'base', self.base.upper())
    
    @classmethod
    def from_str(
        cls,
        symbol: str,
        default_quote: QuoteCurrency = QuoteCurrency.USDT
    ) -> 'TradingSymbol':
        """
        Constructor principal: parsea un string a TradingSymbol.
        
        Soporta múltiples formatos:
        - "BTC" → TradingSymbol(base="BTC", quote=USDT)
        - "btc" → TradingSymbol(base="BTC", quote=USDT)
        - "BTCUSDT" → TradingSymbol(base="BTC", quote=USDT)
        - "btcusdt" → TradingSymbol(base="BTC", quote=USDT)
        - "BTCBUSD" → TradingSymbol(base="BTC", quote=BUSD)
        
        Args:
            symbol: String a parsear
            default_quote: Quote currency por defecto si no se especifica
        
        Returns:
            TradingSymbol validado e inmutable
        
        Raises:
            TypeError: Si symbol no es string
            ValueError: Si symbol es vacío o inválido
        """
        # Validación de tipo (V21.2.1 type safety)
        if symbol is None:
            raise TypeError("Symbol cannot be None (expected str)")
        
        if not isinstance(symbol, str):
            raise TypeError(f"Symbol must be str, not {type(symbol).__name__}")
        
        # Validación de contenido
        symbol_clean = symbol.strip().upper()
        
        if not symbol_clean:
            raise ValueError("Symbol cannot be empty")
        
        # Parsear: detectar si tiene sufijo de quote currency
        base = symbol_clean
        quote = default_quote
        
        # Intentar remover sufijos conocidos
        for qc in QuoteCurrency:
            if symbol_clean.endswith(qc.value):
                base = symbol_clean[:-len(qc.value)]
                quote = qc
                break
        
        # Validar que base no quedó vacío después de remover quote
        if not base:
            raise ValueError(f"Invalid symbol after parsing: {symbol}")
        
        # Crear instancia (post_init validará que base sea válido)
        return cls(base=base, quote=quote)
    
    @classmethod
    def from_config(cls, pair: TradingPair, quote: QuoteCurrency = QuoteCurrency.USDT) -> 'TradingSymbol':
        """
        Constructor desde TradingPair enum (type-safe).
        
        Uso:
            symbol = TradingSymbol.from_config(TradingPair.BTC)
        """
        return cls(base=pair.value, quote=quote)
    
    # ==========================================================================
    # MÉTODOS DE FORMATO (Output Representations)
    # ==========================================================================
    
    def to_short(self) -> str:
        """
        Formato corto: solo base.
        
        Returns:
            "BTC"
        """
        return self.base
    
    def to_long(self) -> str:
        """
        Formato largo: base + quote.
        
        Returns:
            "BTCUSDT"
        """
        return f"{self.base}{self.quote.value}"
    
    def to_lower(self) -> str:
        """
        Formato lowercase (para WebSocket streams).
        
        Returns:
            "btcusdt"
        """
        return self.to_long().lower()
    
    def to_redis_key(self, prefix: str) -> str:
        """
        Formato para Redis keys.
        
        Args:
            prefix: Prefijo de la key (ej: "price", "market_regime")
        
        Returns:
            "price:BTC"
        
        Examples:
            >>> symbol.to_redis_key("price")
            'price:BTC'
            
            >>> symbol.to_redis_key("market_regime")
            'market_regime:BTC'
        """
        return f"{prefix}:{self.base}"
    
    def to_binance_api(self) -> str:
        """
        Formato para Binance API (largo, uppercase).
        
        Returns:
            "BTCUSDT"
        """
        return self.to_long()
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert to dictionary (useful for JSON serialization).
        
        Returns:
            Dict representation with base, quote, and full symbol
        
        Examples:
            >>> symbol.to_dict()
            {'base': 'BTC', 'quote': 'USDT', 'full': 'BTCUSDT'}
            
            >>> import json
            >>> json.dumps(symbol.to_dict())
            '{"base": "BTC", "quote": "USDT", "full": "BTCUSDT"}'
        """
        return {
            'base': self.base,
            'quote': self.quote.value,
            'full': self.to_long()
        }
    
    # ==========================================================================
    # MÉTODOS ESPECIALES (Dunder Methods)
    # ==========================================================================
    
    def __str__(self) -> str:
        """
        String representation (formato corto por defecto).
        
        Returns:
            "BTC"
        """
        return self.to_short()
    
    def __repr__(self) -> str:
        """
        Developer-friendly representation.
        
        Returns:
            "TradingSymbol(base='BTC', quote=QuoteCurrency.USDT)"
        """
        return f"TradingSymbol(base='{self.base}', quote={self.quote})"
    
    def __repr_html__(self) -> str:
        """
        HTML representation para Jupyter Notebooks.
        
        Returns:
            HTML string con formato visual
        
        Examples:
            En Jupyter Notebook, el símbolo se mostrará con un formato visual:
            
            [TradingSymbol]
            Base: BTC
            Quote: USDT
            Full: BTCUSDT
        """
        return f'''
        <div style="padding: 10px; border: 2px solid #2196F3; border-radius: 6px; display: inline-block; font-family: monospace; background-color: #f5f5f5;">
            <div style="color: #2196F3; font-weight: bold; margin-bottom: 6px; font-size: 14px;">📊 TradingSymbol</div>
            <div style="margin: 4px 0;"><span style="color: #666; font-weight: bold;">Base:</span> <code style="background: white; padding: 2px 6px; border-radius: 3px; color: #d32f2f;">{self.base}</code></div>
            <div style="margin: 4px 0;"><span style="color: #666; font-weight: bold;">Quote:</span> <code style="background: white; padding: 2px 6px; border-radius: 3px; color: #388e3c;">{self.quote.value}</code></div>
            <div style="margin: 4px 0;"><span style="color: #666; font-weight: bold;">Full:</span> <code style="background: white; padding: 2px 6px; border-radius: 3px; color: #1976d2;">{self.to_long()}</code></div>
        </div>
        '''
    
    def __hash__(self) -> int:
        """
        Hash para usar en sets/dicts.
        
        Basado en base + quote (dos símbolos con mismo base y quote son iguales).
        """
        return hash((self.base, self.quote))
    
    def __eq__(self, other) -> bool:
        """
        Igualdad: dos TradingSymbol son iguales si tienen mismo base y quote.
        
        Examples:
            >>> TradingSymbol.from_str("BTC") == TradingSymbol.from_str("BTCUSDT")
            True
            
            >>> TradingSymbol.from_str("BTC") == TradingSymbol.from_str("ETH")
            False
        """
        if not isinstance(other, TradingSymbol):
            return False
        return self.base == other.base and self.quote == other.quote
    
    def __lt__(self, other: 'TradingSymbol') -> bool:
        """
        Comparación (para sorting).
        
        Ordena alfabéticamente por base, luego por quote.
        """
        if not isinstance(other, TradingSymbol):
            return NotImplemented
        return (self.base, self.quote.value) < (other.base, other.quote.value)


# ==========================================================================
# HELPER FUNCTIONS (Backward Compatibility)
# ==========================================================================

def normalize_symbol_v21_3(
    symbol: str, 
    format: Literal['short', 'long', 'lower'] = 'short'
) -> str:
    """
    V21.3: Wrapper de backward compatibility para normalize_symbol().
    
    DEPRECATION NOTICE: Esta función existe solo para compatibilidad.
    Código nuevo debe usar TradingSymbol directamente.
    
    Args:
        symbol: String a normalizar
        format: Literal type - must be 'short', 'long', or 'lower'
    
    Returns:
        String normalizado
    
    Examples:
        >>> normalize_symbol_v21_3("btcusdt", "short")
        'BTC'
        
        >>> normalize_symbol_v21_3("BTC", "long")
        'BTCUSDT'
    """
    ts = TradingSymbol.from_str(symbol)
    
    if format == 'short':
        return ts.to_short()
    elif format == 'long':
        return ts.to_long()
    elif format == 'lower':
        return ts.to_lower()
    else:
        raise ValueError(f"Invalid format: {format}. Use 'short', 'long', or 'lower'")


# ==========================================================================
# VALIDATION HELPERS
# ==========================================================================

def is_valid_trading_symbol(symbol: str) -> bool:
    """
    Verifica si un string puede ser parseado a TradingSymbol válido.
    
    Args:
        symbol: String a validar
    
    Returns:
        True si es válido, False si no
    
    Examples:
        >>> is_valid_trading_symbol("BTC")
        True
        
        >>> is_valid_trading_symbol("banana")
        False
    """
    try:
        TradingSymbol.from_str(symbol)
        return True
    except (TypeError, ValueError):
        return False


# ==========================================================================
# BULK OPERATIONS
# ==========================================================================

def parse_symbol_list(symbols: list[str]) -> list[TradingSymbol]:
    """
    Parsea una lista de strings a lista de TradingSymbol.
    
    Útil para procesar active_symbols de Redis.
    
    Args:
        symbols: Lista de strings
    
    Returns:
        Lista de TradingSymbol validados
    
    Raises:
        ValueError: Si algún símbolo es inválido
    
    Examples:
        >>> parse_symbol_list(["BTC", "ETH", "SOL"])
        [TradingSymbol(base='BTC', ...), TradingSymbol(base='ETH', ...), ...]
    """
    return [TradingSymbol.from_str(s) for s in symbols]


def get_redis_keys_for_symbols(
    symbols: list[TradingSymbol],
    prefix: str
) -> list[str]:
    """
    Genera lista de Redis keys para múltiples símbolos.
    
    Args:
        symbols: Lista de TradingSymbol
        prefix: Prefijo (ej: "price", "market_regime")
    
    Returns:
        Lista de keys (ej: ["price:BTC", "price:ETH", ...])
    
    Examples:
        >>> symbols = [TradingSymbol.from_str("BTC"), TradingSymbol.from_str("ETH")]
        >>> get_redis_keys_for_symbols(symbols, "price")
        ['price:BTC', 'price:ETH']
    """
    return [symbol.to_redis_key(prefix) for symbol in symbols]
