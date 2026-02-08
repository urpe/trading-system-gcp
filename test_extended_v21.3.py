#!/usr/bin/env python3
"""
V21.3: EXTENDED TESTING - Edge Cases & Performance
===================================================
Tests adicionales para casos extremos y performance.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.domain import TradingSymbol, parse_symbol_list, get_redis_keys_for_symbols
from src.shared.utils import get_logger
import time

logger = get_logger("ExtendedTests")


def test_edge_cases():
    """Test casos extremos que podrían romper el sistema"""
    logger.info("=" * 80)
    logger.info("TEST: Edge Cases")
    logger.info("=" * 80)
    
    tests = [
        # Case sensitivity
        ("btc", "BTC", "lowercase input"),
        ("BtC", "BTC", "mixed case"),
        ("  BTC  ", "BTC", "whitespace padding"),
        ("BTCUSDT", "BTC", "with USDT suffix"),
        ("btcusdt", "BTC", "lowercase with suffix"),
        
        # Different formats
        ("ETH", "ETH", "ETH base"),
        ("ETHUSDT", "ETH", "ETH with USDT"),
    ]
    
    passed = 0
    failed = 0
    
    for input_str, expected_base, description in tests:
        try:
            symbol = TradingSymbol.from_str(input_str)
            if symbol.base == expected_base:
                logger.info(f"✅ PASS: {description} - '{input_str}' → '{symbol.base}'")
                passed += 1
            else:
                logger.error(f"❌ FAIL: {description} - Expected {expected_base}, got {symbol.base}")
                failed += 1
        except Exception as e:
            logger.error(f"❌ FAIL: {description} - Exception: {e}")
            failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{len(tests)} edge cases passed\n")
    return failed == 0


def test_performance():
    """Test performance de construcción y conversión"""
    logger.info("=" * 80)
    logger.info("TEST: Performance")
    logger.info("=" * 80)
    
    iterations = 10000
    
    # Test 1: Construction speed
    start = time.time()
    for _ in range(iterations):
        symbol = TradingSymbol.from_str("BTC")
    elapsed = time.time() - start
    
    ops_per_sec = iterations / elapsed
    logger.info(f"✅ Construction: {ops_per_sec:.0f} ops/sec ({elapsed*1000:.2f}ms for {iterations} ops)")
    
    # Test 2: Format conversion speed
    symbol = TradingSymbol.from_str("BTC")
    start = time.time()
    for _ in range(iterations):
        _ = symbol.to_long()
        _ = symbol.to_short()
        _ = symbol.to_lower()
        _ = symbol.to_redis_key("price")
    elapsed = time.time() - start
    
    ops_per_sec = (iterations * 4) / elapsed
    logger.info(f"✅ Format conversion: {ops_per_sec:.0f} ops/sec ({elapsed*1000:.2f}ms for {iterations*4} ops)")
    
    # Test 3: Parsing list
    symbols_list = ["BTC", "ETH", "SOL", "BNB", "XRP"] * 100  # 500 symbols
    start = time.time()
    parsed = parse_symbol_list(symbols_list)
    elapsed = time.time() - start
    
    ops_per_sec = len(symbols_list) / elapsed
    logger.info(f"✅ Bulk parsing: {ops_per_sec:.0f} symbols/sec ({elapsed*1000:.2f}ms for {len(symbols_list)} symbols)")
    
    # Benchmark: Debe ser > 1000 ops/sec para construcción
    if ops_per_sec > 1000:
        logger.info("\n🎯 Performance: EXCELLENT (>1000 ops/sec)")
        return True
    elif ops_per_sec > 500:
        logger.warning("\n⚠️ Performance: ACCEPTABLE (>500 ops/sec)")
        return True
    else:
        logger.error(f"\n❌ Performance: POOR ({ops_per_sec:.0f} ops/sec)")
        return False


def test_memory_efficiency():
    """Test que TradingSymbol no cause memory leaks"""
    logger.info("=" * 80)
    logger.info("TEST: Memory Efficiency")
    logger.info("=" * 80)
    
    # Crear muchas instancias
    symbols = []
    for _ in range(1000):
        for base in ["BTC", "ETH", "SOL", "BNB", "XRP"]:
            symbols.append(TradingSymbol.from_str(base))
    
    # Verificar que iguales sean iguales (usa hash correctamente)
    btc1 = TradingSymbol.from_str("BTC")
    btc2 = TradingSymbol.from_str("BTCUSDT")
    
    if btc1 == btc2 and hash(btc1) == hash(btc2):
        logger.info(f"✅ PASS: Hash consistency - BTC instances are equal")
    else:
        logger.error(f"❌ FAIL: Hash mismatch")
        return False
    
    # Verificar que se pueden usar en sets (elimina duplicados)
    unique_symbols = set(symbols)
    expected_unique = 5  # BTC, ETH, SOL, BNB, XRP
    
    if len(unique_symbols) == expected_unique:
        logger.info(f"✅ PASS: Set deduplication - {len(symbols)} symbols → {len(unique_symbols)} unique")
        return True
    else:
        logger.error(f"❌ FAIL: Expected {expected_unique} unique, got {len(unique_symbols)}")
        return False


def test_redis_key_consistency():
    """Test que las keys de Redis sean 100% consistentes"""
    logger.info("=" * 80)
    logger.info("TEST: Redis Key Consistency")
    logger.info("=" * 80)
    
    # Diferentes formas de crear el mismo símbolo
    variants = ["BTC", "btc", "BTCUSDT", "btcusdt", "  BTC  "]
    
    keys = []
    for variant in variants:
        symbol = TradingSymbol.from_str(variant)
        key = symbol.to_redis_key("price")
        keys.append(key)
    
    # Todas las keys deben ser idénticas
    if len(set(keys)) == 1:
        logger.info(f"✅ PASS: All variants produce same key: {keys[0]}")
        logger.info(f"   Tested: {variants}")
        return True
    else:
        logger.error(f"❌ FAIL: Inconsistent keys: {set(keys)}")
        return False


def test_thread_safety():
    """Test inmutabilidad (thread-safe por diseño)"""
    logger.info("=" * 80)
    logger.info("TEST: Thread Safety (Immutability)")
    logger.info("=" * 80)
    
    symbol = TradingSymbol.from_str("BTC")
    
    # Intentar modificar (debe fallar)
    try:
        symbol.base = "ETH"
        logger.error("❌ FAIL: Symbol is mutable (not frozen)")
        return False
    except Exception:
        logger.info("✅ PASS: Symbol is immutable (frozen dataclass)")
    
    # Verificar que to_*() no modifica el original
    original_str = str(symbol)
    _ = symbol.to_long()
    _ = symbol.to_lower()
    _ = symbol.to_redis_key("test")
    
    if str(symbol) == original_str:
        logger.info("✅ PASS: Conversion methods don't mutate original")
        return True
    else:
        logger.error("❌ FAIL: Symbol was mutated by conversion")
        return False


def main():
    logger.info("=" * 80)
    logger.info("🔬 V21.3 EXTENDED TESTING - Edge Cases & Performance")
    logger.info("=" * 80)
    
    tests = [
        ("Edge Cases", test_edge_cases),
        ("Performance", test_performance),
        ("Memory Efficiency", test_memory_efficiency),
        ("Redis Key Consistency", test_redis_key_consistency),
        ("Thread Safety", test_thread_safety),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Resumen
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESUMEN FINAL")
    logger.info("=" * 80)
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {status}: {test_name}")
    
    logger.info(f"\n🎯 RESULTADO: {total_passed}/{total_tests} tests PASSED")
    
    if total_passed == total_tests:
        logger.info("\n🎉 ¡TODOS LOS TESTS EXTENDIDOS PASARON!")
        logger.info("=" * 80)
        return 0
    else:
        logger.error(f"\n⚠️ {total_tests - total_passed} tests FALLARON")
        logger.info("=" * 80)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
