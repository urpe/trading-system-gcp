#!/usr/bin/env python3
"""
V21.3 "CANONICAL CORE" - UNIT TESTS
====================================
Tests exhaustivos para TradingSymbol Value Object.

Ejecutar:
    python3 test_trading_symbol.py
"""

import sys
import os

# Añadir src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.domain.trading_symbol import (
    TradingSymbol,
    QuoteCurrency,
    TradingPair,
    normalize_symbol_v21_3,
    is_valid_trading_symbol,
    parse_symbol_list,
    get_redis_keys_for_symbols
)
from src.shared.utils import get_logger

logger = get_logger("TestTradingSymbol")


def test_construction_from_str():
    """Test 1: Construcción desde string"""
    logger.info("=" * 80)
    logger.info("TEST 1: Construction from String")
    logger.info("=" * 80)
    
    tests = [
        ("BTC", "BTC", QuoteCurrency.USDT),
        ("btc", "BTC", QuoteCurrency.USDT),
        ("BTCUSDT", "BTC", QuoteCurrency.USDT),
        ("btcusdt", "BTC", QuoteCurrency.USDT),
        ("ETH", "ETH", QuoteCurrency.USDT),
        ("ETHUSDT", "ETH", QuoteCurrency.USDT),
        ("SOL", "SOL", QuoteCurrency.USDT),
    ]
    
    passed = 0
    failed = 0
    
    for input_str, expected_base, expected_quote in tests:
        try:
            symbol = TradingSymbol.from_str(input_str)
            if symbol.base == expected_base and symbol.quote == expected_quote:
                logger.info(f"✅ PASS: TradingSymbol.from_str('{input_str}') → {symbol.base}/{symbol.quote.value}")
                passed += 1
            else:
                logger.error(f"❌ FAIL: Expected {expected_base}/{expected_quote.value}, got {symbol.base}/{symbol.quote.value}")
                failed += 1
        except Exception as e:
            logger.error(f"❌ FAIL: TradingSymbol.from_str('{input_str}') raised {type(e).__name__}: {e}")
            failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{len(tests)} tests passed\n")
    return failed == 0


def test_type_safety():
    """Test 2: Type Safety (rechazar tipos inválidos)"""
    logger.info("=" * 80)
    logger.info("TEST 2: Type Safety")
    logger.info("=" * 80)
    
    tests = [
        (None, TypeError, "None input"),
        (123, TypeError, "Integer input"),
        ([], TypeError, "List input"),
        ("", ValueError, "Empty string"),
        ("   ", ValueError, "Whitespace only"),
        ("banana", ValueError, "Invalid trading pair"),
    ]
    
    passed = 0
    failed = 0
    
    for input_val, expected_exception, description in tests:
        try:
            symbol = TradingSymbol.from_str(input_val)
            logger.error(f"❌ FAIL: {description} - Should raise {expected_exception.__name__} but got: {symbol}")
            failed += 1
        except expected_exception:
            logger.info(f"✅ PASS: {description} - Correctly raised {expected_exception.__name__}")
            passed += 1
        except Exception as e:
            logger.error(f"❌ FAIL: {description} - Wrong exception: {type(e).__name__}: {e}")
            failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{len(tests)} tests passed\n")
    return failed == 0


def test_format_outputs():
    """Test 3: Métodos de formato"""
    logger.info("=" * 80)
    logger.info("TEST 3: Format Outputs")
    logger.info("=" * 80)
    
    symbol = TradingSymbol.from_str("BTC")
    
    tests = [
        (symbol.to_short(), "BTC", "to_short()"),
        (symbol.to_long(), "BTCUSDT", "to_long()"),
        (symbol.to_lower(), "btcusdt", "to_lower()"),
        (symbol.to_redis_key("price"), "price:BTC", "to_redis_key('price')"),
        (symbol.to_redis_key("market_regime"), "market_regime:BTC", "to_redis_key('market_regime')"),
        (symbol.to_binance_api(), "BTCUSDT", "to_binance_api()"),
        (str(symbol), "BTC", "__str__()"),
    ]
    
    passed = 0
    failed = 0
    
    for result, expected, method_name in tests:
        if result == expected:
            logger.info(f"✅ PASS: {method_name} = '{result}'")
            passed += 1
        else:
            logger.error(f"❌ FAIL: {method_name} = '{result}' (expected: '{expected}')")
            failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{len(tests)} tests passed\n")
    return failed == 0


def test_immutability():
    """Test 4: Inmutabilidad (frozen dataclass)"""
    logger.info("=" * 80)
    logger.info("TEST 4: Immutability")
    logger.info("=" * 80)
    
    symbol = TradingSymbol.from_str("BTC")
    
    try:
        symbol.base = "ETH"  # ❌ Debe fallar (frozen)
        logger.error("❌ FAIL: Debería ser inmutable pero permitió modificar .base")
        return False
    except Exception:
        logger.info("✅ PASS: TradingSymbol es inmutable (frozen dataclass)")
        return True


def test_equality():
    """Test 5: Igualdad y Hash"""
    logger.info("=" * 80)
    logger.info("TEST 5: Equality & Hashing")
    logger.info("=" * 80)
    
    btc1 = TradingSymbol.from_str("BTC")
    btc2 = TradingSymbol.from_str("BTCUSDT")
    eth = TradingSymbol.from_str("ETH")
    
    tests = [
        (btc1 == btc2, True, "BTC == BTCUSDT (mismo base)"),
        (btc1 == eth, False, "BTC != ETH"),
        (hash(btc1) == hash(btc2), True, "hash(BTC) == hash(BTCUSDT)"),
        (hash(btc1) == hash(eth), False, "hash(BTC) != hash(ETH)"),
    ]
    
    passed = 0
    failed = 0
    
    for result, expected, description in tests:
        if result == expected:
            logger.info(f"✅ PASS: {description}")
            passed += 1
        else:
            logger.error(f"❌ FAIL: {description} - Got {result}, expected {expected}")
            failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{len(tests)} tests passed\n")
    return failed == 0


def test_sorting():
    """Test 6: Sorting (para usar en listas ordenadas)"""
    logger.info("=" * 80)
    logger.info("TEST 6: Sorting")
    logger.info("=" * 80)
    
    symbols = [
        TradingSymbol.from_str("XRP"),
        TradingSymbol.from_str("BTC"),
        TradingSymbol.from_str("ETH"),
        TradingSymbol.from_str("ADA"),
    ]
    
    sorted_symbols = sorted(symbols)
    expected_order = ["ADA", "BTC", "ETH", "XRP"]
    actual_order = [s.to_short() for s in sorted_symbols]
    
    if actual_order == expected_order:
        logger.info(f"✅ PASS: Sorting works - {actual_order}")
        return True
    else:
        logger.error(f"❌ FAIL: Expected {expected_order}, got {actual_order}")
        return False


def test_backward_compatibility():
    """Test 7: Backward compatibility con normalize_symbol()"""
    logger.info("=" * 80)
    logger.info("TEST 7: Backward Compatibility")
    logger.info("=" * 80)
    
    tests = [
        ("btcusdt", "short", "BTC"),
        ("BTCUSDT", "short", "BTC"),
        ("BTC", "short", "BTC"),
        ("eth", "long", "ETHUSDT"),
        ("SOL", "lower", "solusdt"),
    ]
    
    passed = 0
    failed = 0
    
    for input_str, format_type, expected in tests:
        try:
            result = normalize_symbol_v21_3(input_str, format_type)
            if result == expected:
                logger.info(f"✅ PASS: normalize_symbol_v21_3('{input_str}', '{format_type}') = '{result}'")
                passed += 1
            else:
                logger.error(f"❌ FAIL: Expected '{expected}', got '{result}'")
                failed += 1
        except Exception as e:
            logger.error(f"❌ FAIL: Raised {type(e).__name__}: {e}")
            failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{len(tests)} tests passed\n")
    return failed == 0


def test_validation_helpers():
    """Test 8: Helper functions"""
    logger.info("=" * 80)
    logger.info("TEST 8: Validation Helpers")
    logger.info("=" * 80)
    
    passed = 0
    failed = 0
    
    # Test is_valid_trading_symbol()
    if is_valid_trading_symbol("BTC"):
        logger.info("✅ PASS: is_valid_trading_symbol('BTC') = True")
        passed += 1
    else:
        logger.error("❌ FAIL: is_valid_trading_symbol('BTC') should be True")
        failed += 1
    
    if not is_valid_trading_symbol("banana"):
        logger.info("✅ PASS: is_valid_trading_symbol('banana') = False")
        passed += 1
    else:
        logger.error("❌ FAIL: is_valid_trading_symbol('banana') should be False")
        failed += 1
    
    # Test parse_symbol_list()
    try:
        symbols = parse_symbol_list(["BTC", "ETH", "SOL"])
        if len(symbols) == 3 and all(isinstance(s, TradingSymbol) for s in symbols):
            logger.info(f"✅ PASS: parse_symbol_list() returned {len(symbols)} TradingSymbol objects")
            passed += 1
        else:
            logger.error("❌ FAIL: parse_symbol_list() returned invalid objects")
            failed += 1
    except Exception as e:
        logger.error(f"❌ FAIL: parse_symbol_list() raised {type(e).__name__}: {e}")
        failed += 1
    
    # Test get_redis_keys_for_symbols()
    try:
        symbols = parse_symbol_list(["BTC", "ETH"])
        keys = get_redis_keys_for_symbols(symbols, "price")
        if keys == ["price:BTC", "price:ETH"]:
            logger.info(f"✅ PASS: get_redis_keys_for_symbols() = {keys}")
            passed += 1
        else:
            logger.error(f"❌ FAIL: Expected ['price:BTC', 'price:ETH'], got {keys}")
            failed += 1
    except Exception as e:
        logger.error(f"❌ FAIL: get_redis_keys_for_symbols() raised {type(e).__name__}: {e}")
        failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{passed+failed} tests passed\n")
    return failed == 0


def test_from_config():
    """Test 9: Constructor desde TradingPair enum"""
    logger.info("=" * 80)
    logger.info("TEST 9: Construction from TradingPair Enum")
    logger.info("=" * 80)
    
    try:
        symbol = TradingSymbol.from_config(TradingPair.BTC)
        if symbol.base == "BTC" and symbol.quote == QuoteCurrency.USDT:
            logger.info(f"✅ PASS: TradingSymbol.from_config(TradingPair.BTC) = {symbol}")
            return True
        else:
            logger.error(f"❌ FAIL: Unexpected result: {symbol}")
            return False
    except Exception as e:
        logger.error(f"❌ FAIL: Raised {type(e).__name__}: {e}")
        return False


def main():
    logger.info("=" * 80)
    logger.info("🧪 V21.3 TRADING SYMBOL - UNIT TESTS")
    logger.info("=" * 80)
    
    tests = [
        ("Construction from String", test_construction_from_str),
        ("Type Safety", test_type_safety),
        ("Format Outputs", test_format_outputs),
        ("Immutability", test_immutability),
        ("Equality & Hashing", test_equality),
        ("Sorting", test_sorting),
        ("Backward Compatibility", test_backward_compatibility),
        ("Validation Helpers", test_validation_helpers),
        ("Construction from Enum", test_from_config),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Resumen final
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESUMEN FINAL DE TESTS")
    logger.info("=" * 80)
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {status}: {test_name}")
    
    logger.info(f"\n🎯 RESULTADO: {total_passed}/{total_tests} tests PASSED")
    
    if total_passed == total_tests:
        logger.info("\n🎉 ¡TODOS LOS TESTS PASARON! TradingSymbol Value Object is READY")
        logger.info("=" * 80)
        return 0
    else:
        logger.error(f"\n⚠️ {total_tests - total_passed} tests FALLARON - Revisar arriba")
        logger.info("=" * 80)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
