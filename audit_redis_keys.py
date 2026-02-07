#!/usr/bin/env python3
"""
V21.2 SYNCHRONIZED ARCHITECTURE: Redis Keys Audit Script
==========================================================
Verifica la integridad de las claves Redis y detecta inconsistencias
en la normalización de símbolos entre servicios.

PROBLEMA ORIGINAL (V21.1):
--------------------------
- Market Data escribía: price:BTC
- Dashboard buscaba: price:BTCUSDT
- Resultado: Dashboard mostraba $0.00 (key miss silencioso)

SOLUCIÓN (V21.2):
----------------
- normalize_symbol() unificada en shared/utils.py
- Todos los servicios usan formato 'short' (BTC, ETH, SOL)
- Este script valida que la arquitectura esté sincronizada

USO:
----
    # Dentro del contenedor Dashboard:
    docker compose exec dashboard python audit_redis_keys.py
    
    # O con Redis expuesto:
    python audit_redis_keys.py

ENTREGABLE:
-----------
- Lista de keys en Redis
- Verificación de active_symbols vs price:* keys
- Detección de discrepancias (ej: price:BTCUSDT vs active_symbols=["btc"])
"""

import sys
import os
import json
from typing import List, Set, Dict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.shared.memory import memory
from src.shared.utils import get_logger, normalize_symbol

logger = get_logger("RedisAudit")


class RedisKeysAuditor:
    """
    Audita las claves de Redis para detectar inconsistencias en normalización.
    """
    
    def __init__(self):
        self.redis_client = memory.get_client()
        
        if not self.redis_client:
            logger.critical("🔥 No se pudo conectar a Redis")
            sys.exit(1)
        
        logger.info("✅ Conectado a Redis")
    
    def get_all_keys(self, pattern: str = "*") -> List[str]:
        """Obtiene todas las keys que coinciden con el patrón."""
        try:
            keys = self.redis_client.keys(pattern)
            return [k.decode() if isinstance(k, bytes) else k for k in keys]
        except Exception as e:
            logger.error(f"Error obteniendo keys: {e}")
            return []
    
    def get_active_symbols(self) -> List[str]:
        """Obtiene los símbolos activos guardados por Market Data."""
        try:
            active_symbols_raw = memory.get("active_symbols")
            
            if not active_symbols_raw:
                logger.warning("⚠️ active_symbols no encontrado en Redis")
                return []
            
            if isinstance(active_symbols_raw, list):
                # Normalizar cada símbolo
                normalized = []
                for s in active_symbols_raw:
                    try:
                        normalized.append(normalize_symbol(s, format='short'))
                    except ValueError as e:
                        logger.error(f"❌ Error normalizando '{s}': {e}")
                return normalized
            else:
                logger.error(f"❌ active_symbols tiene tipo incorrecto: {type(active_symbols_raw)}")
                return []
        
        except Exception as e:
            logger.error(f"Error obteniendo active_symbols: {e}")
            return []
    
    def get_price_symbols(self) -> Set[str]:
        """Extrae símbolos de las keys price:*"""
        price_keys = self.get_all_keys("price:*")
        
        symbols = set()
        for key in price_keys:
            # Extraer símbolo de "price:BTC" -> "BTC"
            symbol = key.split(':', 1)[1] if ':' in key else None
            if symbol:
                symbols.add(symbol)
        
        return symbols
    
    def get_regime_symbols(self) -> Set[str]:
        """Extrae símbolos de las keys market_regime:*"""
        regime_keys = self.get_all_keys("market_regime:*")
        
        symbols = set()
        for key in regime_keys:
            symbol = key.split(':', 1)[1] if ':' in key else None
            if symbol:
                symbols.add(symbol)
        
        return symbols
    
    def run_audit(self):
        """Ejecuta la auditoría completa."""
        logger.info("=" * 80)
        logger.info("🔍 AUDITORÍA DE CLAVES REDIS - V21.2 SYNCHRONIZED ARCHITECTURE")
        logger.info("=" * 80)
        logger.info("")
        
        # 1. Lista de todas las keys
        all_keys = self.get_all_keys()
        logger.info(f"📊 Total de keys en Redis: {len(all_keys)}")
        logger.info("")
        
        # 2. Keys por categoría
        price_keys = [k for k in all_keys if k.startswith('price:')]
        regime_keys = [k for k in all_keys if k.startswith('market_regime:')]
        strategy_keys = [k for k in all_keys if k.startswith('strategy_config:')]
        
        logger.info("📋 KEYS POR CATEGORÍA:")
        logger.info(f"   - price:* (Market Data)      : {len(price_keys)} keys")
        logger.info(f"   - market_regime:* (Brain)    : {len(regime_keys)} keys")
        logger.info(f"   - strategy_config:* (Optimizer): {len(strategy_keys)} keys")
        logger.info(f"   - active_symbols (Market Data): {'✅ Existe' if 'active_symbols' in all_keys else '❌ No existe'}")
        logger.info("")
        
        # 3. Obtener símbolos activos
        active_symbols = self.get_active_symbols()
        logger.info(f"🎯 ACTIVE SYMBOLS (de Market Data):")
        logger.info(f"   {active_symbols}")
        logger.info("")
        
        # 4. Símbolos en price:*
        price_symbols = self.get_price_symbols()
        logger.info(f"💰 SÍMBOLOS EN PRICE:* KEYS:")
        logger.info(f"   {sorted(price_symbols)}")
        logger.info("")
        
        # 5. Símbolos en market_regime:*
        regime_symbols = self.get_regime_symbols()
        logger.info(f"📈 SÍMBOLOS EN MARKET_REGIME:* KEYS:")
        logger.info(f"   {sorted(regime_symbols)}")
        logger.info("")
        
        # 6. VERIFICACIÓN DE INTEGRIDAD
        logger.info("=" * 80)
        logger.info("🔬 VERIFICACIÓN DE INTEGRIDAD (V21.2 FIX)")
        logger.info("=" * 80)
        logger.info("")
        
        # 6.1 Verificar que active_symbols coincida con price:*
        active_set = set(active_symbols)
        
        missing_in_price = active_set - price_symbols
        extra_in_price = price_symbols - active_set
        
        if not missing_in_price and not extra_in_price:
            logger.info("✅ PERFECT SYNC: active_symbols coincide 100% con price:* keys")
        else:
            if missing_in_price:
                logger.warning(f"⚠️ DISCREPANCIA: Símbolos en active_symbols pero SIN price:* key:")
                for s in missing_in_price:
                    logger.warning(f"   - {s} (Market Data NO está publicando datos)")
            
            if extra_in_price:
                logger.warning(f"⚠️ DISCREPANCIA: Keys price:* sin active_symbols correspondiente:")
                for s in extra_in_price:
                    logger.warning(f"   - price:{s} (posiblemente obsoleto)")
        
        logger.info("")
        
        # 6.2 Verificar que Brain esté generando regímenes
        missing_regimes = active_set - regime_symbols
        
        if not missing_regimes:
            logger.info("✅ BRAIN OK: Todos los active_symbols tienen market_regime:* key")
        else:
            logger.warning(f"⚠️ BRAIN ISSUE: Símbolos sin régimen detectado:")
            for s in missing_regimes:
                logger.warning(f"   - {s} (Brain NO está procesando o faltan 200 velas)")
        
        logger.info("")
        
        # 7. PRUEBA DE NORMALIZACIÓN
        logger.info("=" * 80)
        logger.info("🧪 PRUEBA DE NORMALIZACIÓN normalize_symbol()")
        logger.info("=" * 80)
        logger.info("")
        
        test_cases = [
            ("btcusdt", "short", "BTC"),
            ("BTCUSDT", "short", "BTC"),
            ("BTC", "short", "BTC"),
            ("eth", "long", "ETHUSDT"),
            ("SOL", "lower", "solusdt")
        ]
        
        all_pass = True
        for input_val, format_val, expected in test_cases:
            try:
                result = normalize_symbol(input_val, format=format_val)
                status = "✅" if result == expected else "❌"
                if result != expected:
                    all_pass = False
                logger.info(f"{status} normalize_symbol('{input_val}', '{format_val}') = '{result}' (esperado: '{expected}')")
            except Exception as e:
                logger.error(f"❌ normalize_symbol('{input_val}', '{format_val}') ERROR: {e}")
                all_pass = False
        
        logger.info("")
        
        if all_pass:
            logger.info("✅ Todas las pruebas de normalización PASARON")
        else:
            logger.error("❌ Algunas pruebas de normalización FALLARON")
        
        logger.info("")
        
        # 8. MUESTRA DE DATOS
        logger.info("=" * 80)
        logger.info("📦 MUESTRA DE DATOS (Primeras 3 keys de cada tipo)")
        logger.info("=" * 80)
        logger.info("")
        
        for key in price_keys[:3]:
            data = memory.get(key)
            logger.info(f"🔑 {key}:")
            if data and isinstance(data, dict):
                logger.info(f"   Close: ${data.get('close', 0):.2f} | High: ${data.get('high', 0):.2f} | Low: ${data.get('low', 0):.2f}")
            else:
                logger.info(f"   ⚠️ Tipo: {type(data)} | Valor: {data}")
            logger.info("")
        
        # RESUMEN FINAL
        logger.info("=" * 80)
        logger.info("📊 RESUMEN DE AUDITORÍA")
        logger.info("=" * 80)
        logger.info("")
        
        issues_count = len(missing_in_price) + len(extra_in_price) + len(missing_regimes) + (0 if all_pass else 1)
        
        if issues_count == 0:
            logger.info("🎉 ¡SISTEMA PERFECTO! Arquitectura V21.2 sincronizada correctamente")
            logger.info("")
            logger.info("   ✅ active_symbols → price:* keys: SYNC")
            logger.info("   ✅ active_symbols → market_regime:* keys: SYNC")
            logger.info("   ✅ normalize_symbol(): FUNCIONA")
        else:
            logger.warning(f"⚠️ SE ENCONTRARON {issues_count} ISSUES - Revisar arriba")
        
        logger.info("")
        logger.info("=" * 80)


def main():
    auditor = RedisKeysAuditor()
    auditor.run_audit()


if __name__ == '__main__':
    main()
