"""
SQLAlchemy Custom Types for Trading System
===========================================
Implementa tipos personalizados para persistencia type-safe de Value Objects.

Author: HFT Trading Bot Team
Version: V22.1
Date: 2026-02-08
"""

from sqlalchemy.types import TypeDecorator, String
from sqlalchemy import JSON
from src.domain import TradingSymbol, QuoteCurrency
import json
from typing import Optional
from src.shared.utils import get_logger

logger = get_logger("DatabaseTypes")


class TradingSymbolType(TypeDecorator):
    """
    SQLAlchemy custom type para TradingSymbol Value Object.
    
    Implementación:
        - Almacena como JSON string en SQLite: '{"base": "BTC", "quote": "USDT"}'
        - Deserializa automáticamente a TradingSymbol al leer
        - Serializa automáticamente desde TradingSymbol al escribir
    
    Ventajas:
        - Type safety en queries: `session.query(Trade).filter(Trade.symbol == TradingSymbol.from_str("BTC"))`
        - No más conversiones manuales: `trade = Trade(symbol=TradingSymbol.from_str("BTC"))`
        - Soporte para Multi-Quote nativo: `{"base": "ETH", "quote": "BTC"}`
        - Backward compatible: Lee strings viejos ("BTC") y los convierte automáticamente
    
    Ejemplo de Uso:
        # Write (INSERT/UPDATE)
        symbol = TradingSymbol.from_str("ETHBTC")
        trade = Trade(symbol=symbol)  # Automatic serialization to JSON
        session.add(trade)
        session.commit()
        
        # Read (SELECT)
        trade = session.query(Trade).first()
        print(trade.symbol.to_long())  # "ETHBTC" - Automatic deserialization
        print(trade.symbol.base)       # "ETH"
        print(trade.symbol.quote.value) # "BTC"
    
    Storage Format:
        SQLite: String column storing JSON
        Example: '{"base": "BTC", "quote": "USDT"}'
        Max length: 100 chars (sufficient for all valid pairs)
    
    Migration Handling:
        - Old format: "BTC" (plain string) → Converted to TradingSymbol("BTC", "USDT")
        - New format: '{"base": "BTC", "quote": "USDT"}' → Parsed as JSON
        - Invalid format: Logs error and returns None (fail-safe)
    """
    
    impl = String(100)  # Max 100 chars para JSON
    cache_ok = True     # Enable SQLAlchemy caching for performance
    
    def process_bind_param(self, value: Optional[TradingSymbol], dialect) -> Optional[str]:
        """
        Serialize TradingSymbol → JSON string (for INSERT/UPDATE).
        
        Called automatically when:
            - session.add(trade) with trade.symbol = TradingSymbol(...)
            - session.query(Trade).filter(Trade.symbol == TradingSymbol(...))
        
        Args:
            value: TradingSymbol instance or None
            dialect: SQLAlchemy dialect (sqlite, postgresql, etc.)
        
        Returns:
            JSON string: '{"base": "BTC", "quote": "USDT"}' or None
        
        Raises:
            TypeError: If value is not TradingSymbol or None
        
        Example:
            >>> symbol = TradingSymbol.from_str("ETHBTC")
            >>> type_handler.process_bind_param(symbol, None)
            '{"base": "ETH", "quote": "BTC"}'
        """
        if value is None:
            return None
        
        if not isinstance(value, TradingSymbol):
            raise TypeError(
                f"TradingSymbolType requires TradingSymbol instance, got {type(value).__name__}. "
                f"Use TradingSymbol.from_str('{value}') to convert."
            )
        
        # Serialize to JSON
        data = {
            "base": value.base,
            "quote": value.quote.value
        }
        
        json_str = json.dumps(data)
        logger.debug(f"Serializing TradingSymbol: {value.to_short()} → {json_str}")
        
        return json_str
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[TradingSymbol]:
        """
        Deserialize JSON string → TradingSymbol (for SELECT).
        
        Called automatically when:
            - trade = session.query(Trade).first()
            - Accessing trade.symbol attribute
        
        Args:
            value: JSON string from database or plain string (backward compat)
            dialect: SQLAlchemy dialect
        
        Returns:
            TradingSymbol instance or None
        
        Handles Migration:
            - New format (JSON): '{"base": "BTC", "quote": "USDT"}' → TradingSymbol("BTC", "USDT")
            - Old format (String): "BTC" → TradingSymbol("BTC", "USDT") with default USDT
            - Invalid format: Logs error and returns None
        
        Example:
            >>> type_handler.process_result_value('{"base": "ETH", "quote": "BTC"}', None)
            TradingSymbol(base='ETH', quote=QuoteCurrency.BTC)
            
            >>> type_handler.process_result_value('BTC', None)  # Old format
            TradingSymbol(base='BTC', quote=QuoteCurrency.USDT)
        """
        if value is None:
            return None
        
        try:
            # Try JSON format first (new format)
            if value.startswith('{'):
                data = json.loads(value)
                quote = QuoteCurrency(data['quote'])
                symbol = TradingSymbol(base=data['base'], quote=quote)
                logger.debug(f"Deserialized JSON: {value} → {symbol.to_short()}")
                return symbol
            
            else:
                # Backward compatibility: Plain string (old format)
                # "BTC" → TradingSymbol("BTC", "USDT")
                symbol = TradingSymbol.from_str(value)
                logger.warning(
                    f"⚠️ Old format detected: '{value}' → Converted to {symbol.to_short()} "
                    f"(Consider running migration script)"
                )
                return symbol
        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(
                f"❌ Failed to deserialize TradingSymbol: '{value}' - Error: {e}. "
                f"Returning None (data integrity issue!)"
            )
            return None
    
    def process_literal_param(self, value: Optional[TradingSymbol], dialect) -> str:
        """
        Process literal parameter for SQL compilation.
        
        Used for:
            - filter() clauses with literal values
            - Debugging SQL queries
        
        Returns:
            String representation for SQL
        """
        if value is None:
            return "NULL"
        return f"'{self.process_bind_param(value, dialect)}'"
    
    @property
    def python_type(self):
        """
        Declare the Python type for type hints and introspection.
        
        Allows SQLAlchemy and IDEs to understand the type:
            trade.symbol  # Type hint: TradingSymbol
        """
        return TradingSymbol


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_trading_symbol_column(session, table_name: str, column_name: str = 'symbol') -> dict:
    """
    Validate TradingSymbol column data integrity.
    
    Checks:
        - All values are valid JSON or convertible strings
        - No NULL values where not expected
        - All deserialized successfully
    
    Args:
        session: SQLAlchemy session
        table_name: Name of table to check (e.g., 'trades')
        column_name: Name of symbol column (default: 'symbol')
    
    Returns:
        {
            'total_rows': int,
            'valid_json': int,
            'old_format': int,
            'invalid': int,
            'null_values': int,
            'errors': [list of error details]
        }
    
    Example:
        >>> from src.shared.database import SessionLocal, Trade
        >>> session = SessionLocal()
        >>> result = validate_trading_symbol_column(session, 'trades')
        >>> print(f"Valid: {result['valid_json']}, Old: {result['old_format']}")
    """
    from sqlalchemy import text
    
    result = {
        'total_rows': 0,
        'valid_json': 0,
        'old_format': 0,
        'invalid': 0,
        'null_values': 0,
        'errors': []
    }
    
    query = text(f"SELECT id, {column_name} FROM {table_name}")
    rows = session.execute(query).fetchall()
    
    result['total_rows'] = len(rows)
    
    for row_id, value in rows:
        if value is None:
            result['null_values'] += 1
            continue
        
        try:
            if value.startswith('{'):
                # New JSON format
                data = json.loads(value)
                QuoteCurrency(data['quote'])  # Validate quote
                result['valid_json'] += 1
            else:
                # Old string format
                TradingSymbol.from_str(value)  # Validate conversion
                result['old_format'] += 1
        except Exception as e:
            result['invalid'] += 1
            result['errors'].append({
                'row_id': row_id,
                'value': value,
                'error': str(e)
            })
    
    return result


def convert_string_to_trading_symbol_json(session, table_name: str, column_name: str = 'symbol') -> int:
    """
    Migrate old string format to new JSON format in-place.
    
    Converts:
        "BTC" → '{"base": "BTC", "quote": "USDT"}'
    
    Args:
        session: SQLAlchemy session (must be writable)
        table_name: Table to migrate
        column_name: Column to migrate
    
    Returns:
        Number of rows migrated
    
    WARNING:
        - This modifies data in-place
        - Always backup before running
        - Run validation after migration
    
    Example:
        >>> session = SessionLocal()
        >>> migrated = convert_string_to_trading_symbol_json(session, 'trades')
        >>> print(f"Migrated {migrated} trades")
        >>> session.commit()
    """
    from sqlalchemy import text
    
    migrated_count = 0
    
    # Get all rows with old format (not starting with '{')
    query = text(f"SELECT id, {column_name} FROM {table_name} WHERE {column_name} NOT LIKE '{{%'")
    rows = session.execute(query).fetchall()
    
    for row_id, old_value in rows:
        if old_value is None:
            continue
        
        try:
            # Convert to TradingSymbol
            symbol = TradingSymbol.from_str(old_value)
            
            # Serialize to JSON
            new_value = json.dumps({
                "base": symbol.base,
                "quote": symbol.quote.value
            })
            
            # Update row
            update_query = text(
                f"UPDATE {table_name} SET {column_name} = :new_value WHERE id = :row_id"
            )
            session.execute(update_query, {'new_value': new_value, 'row_id': row_id})
            
            migrated_count += 1
            
            logger.info(f"✅ Migrated {table_name}.{column_name} row {row_id}: '{old_value}' → '{new_value}'")
        
        except Exception as e:
            logger.error(f"❌ Failed to migrate {table_name} row {row_id}: {e}")
    
    return migrated_count
