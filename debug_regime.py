#!/usr/bin/env python3
"""
Debug Regime Detector - V19.1
==============================
Script de diagnóstico para verificar por qué ADX = 0.0

Analiza:
1. Datos históricos disponibles
2. Cálculo de ADX con datos reales
3. Detección de régimen
4. Comparación con análisis manual
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.simulator.binance_data_fetcher import fetch_1m_data
from src.services.brain.strategies.regime_detector import RegimeDetector, MarketRegime
import numpy as np
from datetime import datetime

def main():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO DE REGIME DETECTOR - V19.1")
    print("=" * 80)
    print()
    
    # FASE 1: Descargar datos históricos
    print("📥 FASE 1: Descargando datos históricos (últimas 48h)...")
    symbols = ['BTC', 'ETH', 'SOL']
    
    try:
        market_data = fetch_1m_data(symbols, hours_back=48)
        print(f"   ✅ {len(market_data)} símbolos descargados")
        print()
    except Exception as e:
        print(f"   ❌ Error descargando datos: {e}")
        return 1
    
    # FASE 2: Inicializar detector
    print("🧠 FASE 2: Inicializando Regime Detector...")
    detector = RegimeDetector(ema_period=200, adx_period=14)
    print(f"   EMA Period: {detector.ema_period}")
    print(f"   ADX Period: {detector.adx_period}")
    print(f"   ADX Trend Threshold: {detector.adx_trend_threshold}")
    print()
    
    # FASE 3: Analizar cada símbolo
    for symbol, df in market_data.items():
        print("-" * 80)
        print(f"📊 ANALIZANDO {symbol}")
        print("-" * 80)
        
        # Extraer arrays
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        
        print(f"Datos disponibles: {len(closes)} velas")
        print(f"Precio inicial: ${closes[0]:.2f}")
        print(f"Precio final: ${closes[-1]:.2f}")
        print(f"Cambio: {((closes[-1] - closes[0]) / closes[0] * 100):+.2f}%")
        print()
        
        # TEST 1: Detección SIN high/low (modo actual - BUGGY)
        print("TEST 1: Detección SIN high/low (modo actual del sistema)")
        regime_no_hl, indicators_no_hl = detector.detect(
            price_history=closes.tolist(),
            high_history=None,  # Force fallback
            low_history=None
        )
        
        print(f"   Régimen detectado: {regime_no_hl.value}")
        print(f"   ADX: {indicators_no_hl.get('adx', 0):.2f}")
        print(f"   EMA200: ${indicators_no_hl.get('ema_200', 0):.2f}")
        print(f"   Precio vs EMA: {indicators_no_hl.get('price_vs_ema', 'N/A')}")
        print()
        
        # TEST 2: Detección CON high/low (modo correcto)
        print("TEST 2: Detección CON high/low (modo correcto)")
        regime_with_hl, indicators_with_hl = detector.detect(
            price_history=closes.tolist(),
            high_history=highs.tolist(),
            low_history=lows.tolist()
        )
        
        print(f"   Régimen detectado: {regime_with_hl.value}")
        print(f"   ADX: {indicators_with_hl.get('adx', 0):.2f}")
        print(f"   DI+: {indicators_with_hl.get('di_plus', 0):.2f}")
        print(f"   DI-: {indicators_with_hl.get('di_minus', 0):.2f}")
        print(f"   EMA200: ${indicators_with_hl.get('ema_200', 0):.2f}")
        print(f"   Precio vs EMA: {indicators_with_hl.get('price_vs_ema', 'N/A')}")
        print(f"   ATR: {indicators_with_hl.get('atr_percent', 0):.2f}%")
        print()
        
        # TEST 3: Análisis manual
        print("TEST 3: Análisis Manual")
        ema_200 = np.mean(closes[-200:]) if len(closes) >= 200 else np.mean(closes)
        current_price = closes[-1]
        trend_direction = "ALCISTA" if current_price > ema_200 else "BAJISTA"
        
        print(f"   Precio actual: ${current_price:.2f}")
        print(f"   EMA(200): ${ema_200:.2f}")
        print(f"   Tendencia: {trend_direction}")
        
        # Calcular cambio de precio (proxy de tendencia)
        lookback_7d = min(len(closes)-1, 7*24*60)
        price_change_7d = ((closes[-1] - closes[-lookback_7d]) / closes[-lookback_7d] * 100)
        print(f"   Cambio 7d: {price_change_7d:+.2f}%")
        print()
        
        # VEREDICTO
        print("🎯 VEREDICTO:")
        if indicators_no_hl.get('adx', 0) == 0.0:
            print("   ❌ BUG CONFIRMADO: ADX = 0.0 en modo sin high/low")
            print("   ⚠️  El sistema está CIEGO a las tendencias")
        else:
            print(f"   ✅ ADX funciona en modo fallback: {indicators_no_hl.get('adx', 0):.2f}")
        
        if regime_with_hl != regime_no_hl:
            print(f"   ⚠️  DISCREPANCIA: {regime_no_hl.value} vs {regime_with_hl.value}")
            print(f"   🔧 SOLUCIÓN: Market Data debe enviar high/low en Redis")
        else:
            print(f"   ✅ Ambos modos detectan mismo régimen: {regime_no_hl.value}")
        
        # Análisis de la diferencia ADX
        adx_diff = indicators_with_hl.get('adx', 0) - indicators_no_hl.get('adx', 0)
        if abs(adx_diff) > 5:
            print(f"   ⚠️  DIFERENCIA ADX SIGNIFICATIVA: {adx_diff:+.2f} puntos")
        
        print()
    
    # FASE 4: Conclusiones
    print("=" * 80)
    print("📋 CONCLUSIONES Y RECOMENDACIONES")
    print("=" * 80)
    print()
    print("PROBLEMA RAÍZ:")
    print("- El servicio market_data solo publica 'close' price en Redis")
    print("- Brain no recibe high/low para cálculo correcto de ADX")
    print("- Fallback usa estimación que retorna ADX muy bajo o 0")
    print()
    print("IMPACTO:")
    print("- Sistema detecta UNKNOWN o SIDEWAYS incorrectamente")
    print("- Mean Reversion se activa en tendencias fuertes (FATAL)")
    print("- V19 operó en mercado bajista -8% como si fuera lateral")
    print()
    print("SOLUCIÓN V21:")
    print("1. Modificar market_data para publicar OHLC completo en Redis")
    print("   - Cambiar: redis.set(f'price:{symbol}', price)")
    print("   - A: redis.hset(f'ohlc:{symbol}', mapping={'open': o, 'high': h, 'low': l, 'close': c})")
    print()
    print("2. Modificar Brain para leer high/low de Redis")
    print("   - Mantener caché de high/low por símbolo")
    print("   - Pasar high_history y low_history al detector")
    print()
    print("3. Re-test detector con datos completos")
    print("   - Ejecutar este script de nuevo")
    print("   - Verificar ADX > 0 en tendencias")
    print()
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
