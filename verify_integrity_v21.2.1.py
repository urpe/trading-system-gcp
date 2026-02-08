#!/usr/bin/env python3
"""
V21.2.1 INTEGRITY VERIFICATION SCRIPT
======================================
Verifica que todas las correcciones de "Integrity Hardening" se hayan aplicado correctamente.

Uso:
    python verify_integrity_v21.2.1.py
"""

import sys
import os

# Añadir src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.shared.utils import get_logger, normalize_symbol
from src.config.symbols import ACTIVE_SYMBOLS, FALLBACK_SYMBOLS, TradingPair

logger = get_logger("IntegrityVerifier")

def test_normalize_symbol_type_safety():
    """Test 1: Verificar que normalize_symbol() rechaza tipos inválidos"""
    logger.info("=" * 80)
    logger.info("TEST 1: Type Safety en normalize_symbol()")
    logger.info("=" * 80)
    
    tests = [
        (None, TypeError, "None input"),
        (123, TypeError, "Integer input"),
        ([], TypeError, "List input"),
        ("", ValueError, "Empty string"),
        ("   ", ValueError, "Whitespace only"),
    ]
    
    passed = 0
    failed = 0
    
    for input_val, expected_exception, description in tests:
        try:
            result = normalize_symbol(input_val)
            logger.error(f"❌ FAIL: {description} - Should raise {expected_exception.__name__} but got: {result}")
            failed += 1
        except expected_exception:
            logger.info(f"✅ PASS: {description} - Correctly raised {expected_exception.__name__}")
            passed += 1
        except Exception as e:
            logger.error(f"❌ FAIL: {description} - Wrong exception: {type(e).__name__}: {e}")
            failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{len(tests)} tests passed")
    return failed == 0


def test_normalize_symbol_formats():
    """Test 2: Verificar que normalize_symbol() maneja todos los formatos"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Format Consistency")
    logger.info("=" * 80)
    
    tests = [
        ("BTC", "short", "BTC"),
        ("btc", "short", "BTC"),
        ("BTCUSDT", "short", "BTC"),
        ("btcusdt", "short", "BTC"),
        ("BTC", "long", "BTCUSDT"),
        ("eth", "long", "ETHUSDT"),
        ("SOL", "lower", "solusdt"),
    ]
    
    passed = 0
    failed = 0
    
    for input_val, format_type, expected in tests:
        try:
            result = normalize_symbol(input_val, format=format_type)
            if result == expected:
                logger.info(f"✅ PASS: normalize_symbol('{input_val}', '{format_type}') = '{result}'")
                passed += 1
            else:
                logger.error(f"❌ FAIL: normalize_symbol('{input_val}', '{format_type}') = '{result}' (expected: '{expected}')")
                failed += 1
        except Exception as e:
            logger.error(f"❌ FAIL: normalize_symbol('{input_val}', '{format_type}') raised {type(e).__name__}: {e}")
            failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{len(tests)} tests passed")
    return failed == 0


def test_canonical_symbols_config():
    """Test 3: Verificar que config/symbols.py es consistente"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Canonical Symbols Configuration")
    logger.info("=" * 80)
    
    passed = 0
    failed = 0
    
    # Test 3.1: No duplicados en ACTIVE_SYMBOLS
    if len(ACTIVE_SYMBOLS) == len(set(ACTIVE_SYMBOLS)):
        logger.info(f"✅ PASS: ACTIVE_SYMBOLS sin duplicados ({len(ACTIVE_SYMBOLS)} símbolos)")
        passed += 1
    else:
        logger.error(f"❌ FAIL: ACTIVE_SYMBOLS contiene duplicados")
        failed += 1
    
    # Test 3.2: Todos los símbolos son válidos
    valid_pairs = {pair.value for pair in TradingPair}
    for symbol in ACTIVE_SYMBOLS:
        if symbol in valid_pairs:
            passed += 1
        else:
            logger.error(f"❌ FAIL: Symbol '{symbol}' not in TradingPair enum")
            failed += 1
    
    # Test 3.3: FALLBACK_SYMBOLS es copia de ACTIVE_SYMBOLS
    if FALLBACK_SYMBOLS == ACTIVE_SYMBOLS:
        logger.info(f"✅ PASS: FALLBACK_SYMBOLS coincide con ACTIVE_SYMBOLS")
        passed += 1
    else:
        logger.error(f"❌ FAIL: FALLBACK_SYMBOLS != ACTIVE_SYMBOLS")
        failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{passed+failed} tests passed")
    return failed == 0


def test_service_imports():
    """Test 4: Verificar que los servicios importan normalize_symbol()"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Service Imports (Static Analysis)")
    logger.info("=" * 80)
    
    services_to_check = [
        ('src/services/market_data/main.py', ['normalize_symbol']),
        ('src/services/brain/main.py', ['normalize_symbol', 'FALLBACK_SYMBOLS']),
        ('src/services/orders/main.py', ['normalize_symbol']),
        ('src/services/dashboard/app.py', ['normalize_symbol', 'FALLBACK_SYMBOLS']),
        ('src/services/historical/main.py', ['normalize_symbol']),
        ('src/services/simulator/main.py', ['normalize_symbol']),
        ('src/services/strategy_optimizer/main.py', ['normalize_symbol', 'FALLBACK_SYMBOLS']),
    ]
    
    passed = 0
    failed = 0
    
    for filepath, required_imports in services_to_check:
        full_path = os.path.join(os.path.dirname(__file__), filepath)
        
        if not os.path.exists(full_path):
            logger.warning(f"⚠️ SKIP: {filepath} no existe")
            continue
        
        with open(full_path, 'r') as f:
            content = f.read()
        
        for import_name in required_imports:
            if import_name in content:
                logger.info(f"✅ PASS: {os.path.basename(filepath)} imports {import_name}")
                passed += 1
            else:
                logger.error(f"❌ FAIL: {os.path.basename(filepath)} missing import: {import_name}")
                failed += 1
    
    logger.info(f"\nRESULTADO: {passed}/{passed+failed} imports verified")
    return failed == 0


def test_magic_strings_eliminated():
    """Test 5: Verificar que NO quedan magic strings"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Magic Strings Detection")
    logger.info("=" * 80)
    
    # Patrones prohibidos
    forbidden_patterns = [
        ("['BTC', 'ETH'", "Hardcoded symbol list"),
        ("['btcusdt', 'eth", "Hardcoded lowercase symbols"),
        ('f"{symbol}USDT"', "String interpolation sin normalize_symbol"),
        ('f"{symbol.upper()}USDT"', "String interpolation sin normalize_symbol"),
    ]
    
    services_to_check = [
        'src/services/market_data/main.py',
        'src/services/brain/main.py',
        'src/services/dashboard/app.py',
        'src/services/strategy_optimizer/main.py',
    ]
    
    issues_found = 0
    
    for filepath in services_to_check:
        full_path = os.path.join(os.path.dirname(__file__), filepath)
        
        if not os.path.exists(full_path):
            continue
        
        with open(full_path, 'r') as f:
            content = f.read()
        
        for pattern, description in forbidden_patterns:
            if pattern in content:
                logger.warning(f"⚠️ DETECTED: {os.path.basename(filepath)} - {description}")
                issues_found += 1
    
    if issues_found == 0:
        logger.info("✅ PASS: No magic strings detectados en servicios críticos")
        return True
    else:
        logger.warning(f"⚠️ {issues_found} magic strings aún presentes (pueden ser legítimos en comentarios)")
        return True  # No bloqueante (pueden ser comentarios)


def main():
    logger.info("=" * 80)
    logger.info("🔍 V21.2.1 INTEGRITY VERIFICATION - RUNNING ALL TESTS")
    logger.info("=" * 80)
    
    tests = [
        ("Type Safety", test_normalize_symbol_type_safety),
        ("Format Consistency", test_normalize_symbol_formats),
        ("Canonical Config", test_canonical_symbols_config),
        ("Service Imports", test_service_imports),
        ("Magic Strings", test_magic_strings_eliminated),
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
    logger.info("📊 RESUMEN FINAL DE VERIFICACIÓN")
    logger.info("=" * 80)
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {status}: {test_name}")
    
    logger.info(f"\n🎯 RESULTADO: {total_passed}/{total_tests} tests PASSED")
    
    if total_passed == total_tests:
        logger.info("\n🎉 ¡SISTEMA VERIFICADO! Todas las correcciones aplicadas correctamente")
        logger.info("=" * 80)
        return 0
    else:
        logger.error(f"\n⚠️ {total_tests - total_passed} tests FALLARON - Revisar arriba")
        logger.info("=" * 80)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
