"""
V21.3 "CANONICAL CORE" - DOMAIN LAYER
======================================
Capa de dominio con Value Objects y lógica de negocio pura.

Exports:
    - TradingSymbol: Value Object para símbolos
    - QuoteCurrency: Enum de monedas de cotización
    - TradingPair: Enum de pares válidos
"""

from src.domain.trading_symbol import (
    TradingSymbol,
    QuoteCurrency,
    TradingPair,
    normalize_symbol_v21_3,
    is_valid_trading_symbol,
    parse_symbol_list,
    get_redis_keys_for_symbols
)

__all__ = [
    'TradingSymbol',
    'QuoteCurrency',
    'TradingPair',
    'normalize_symbol_v21_3',
    'is_valid_trading_symbol',
    'parse_symbol_list',
    'get_redis_keys_for_symbols',
]
