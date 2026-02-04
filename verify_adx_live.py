#!/usr/bin/env python3
"""
V21 EAGLE EYE - Verificación de ADX en Vivo
============================================
Script de diagnóstico que se suscribe a Redis y verifica que el ADX
ya no es 0.0 después de la implementación de OHLCV.

Uso:
    python3 verify_adx_live.py
    
Criterio de Éxito:
    Ver log: "🌡️ Régimen actualizado para SOL: BEAR_TREND (ADX: 35.4)"
    en lugar de "SIDEWAYS (ADX: 0.2)"
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import time
import json
from collections import deque
from src.shared.memory import memory
from src.services.brain.strategies.regime_detector import RegimeDetector

# Configuración
SYMBOLS_TO_MONITOR = ['BTC', 'ETH', 'SOL']
UPDATES_PER_SYMBOL = 5  # Verificar después de 5 actualizaciones

def main():
    print("=" * 80)
    print("🦅 V21 EAGLE EYE - Verificación de ADX en Vivo")
    print("=" * 80)
    print()
    print("Suscribiéndose al canal 'market_data' de Redis...")
    print(f"Monitoreando: {SYMBOLS_TO_MONITOR}")
    print(f"Recolectando {UPDATES_PER_SYMBOL} actualizaciones por símbolo...")
    print()
    
    # Inicializar detector
    detector = RegimeDetector(ema_period=200, adx_period=14)
    
    # Cachés de datos
    ohlcv_cache = {symbol: {
        'close': deque(maxlen=250),
        'high': deque(maxlen=250),
        'low': deque(maxlen=250)
    } for symbol in SYMBOLS_TO_MONITOR}
    
    update_counts = {symbol: 0 for symbol in SYMBOLS_TO_MONITOR}
    
    # Suscribirse a Redis
    pubsub = memory.get_client().pubsub()
    pubsub.subscribe('market_data')
    
    print("✅ Suscripción activa. Esperando datos OHLCV...\n")
    
    for message in pubsub.listen():
        if message['type'] != 'message':
            continue
        
        try:
            data = json.loads(message['data'])
            symbol = data.get('symbol')
            
            if symbol not in SYMBOLS_TO_MONITOR:
                continue
            
            # Validar estructura OHLCV
            if not all(k in data for k in ['open', 'high', 'low', 'close']):
                print(f"⚠️ {symbol}: Estructura OHLCV incompleta - {data}")
                continue
            
            # Agregar a cache
            ohlcv_cache[symbol]['close'].append(data['close'])
            ohlcv_cache[symbol]['high'].append(data['high'])
            ohlcv_cache[symbol]['low'].append(data['low'])
            
            update_counts[symbol] += 1
            
            print(f"📊 {symbol} Update #{update_counts[symbol]}: O={data['open']:.2f} H={data['high']:.2f} L={data['low']:.2f} C={data['close']:.2f}")
            
            # Verificar después de N actualizaciones
            if update_counts[symbol] == UPDATES_PER_SYMBOL:
                print(f"\n🔬 VERIFICACIÓN PARA {symbol}:")
                print("-" * 80)
                
                closes = list(ohlcv_cache[symbol]['close'])
                highs = list(ohlcv_cache[symbol]['high'])
                lows = list(ohlcv_cache[symbol]['low'])
                
                if len(closes) >= 200:
                    # TEST 1: Detección con OHLCV (modo V21)
                    regime, indicators = detector.detect(
                        price_history=closes,
                        high_history=highs,
                        low_history=lows
                    )
                    
                    adx_v21 = indicators.get('adx', 0)
                    di_plus = indicators.get('di_plus', 0)
                    di_minus = indicators.get('di_minus', 0)
                    
                    print(f"V21 (OHLCV): Régimen={regime.value}, ADX={adx_v21:.2f}, DI+={di_plus:.2f}, DI-={di_minus:.2f}")
                    
                    # TEST 2: Verificación con pandas_ta (ground truth)
                    try:
                        import pandas as pd
                        import pandas_ta as ta
                        
                        df = pd.DataFrame({
                            'high': highs,
                            'low': lows,
                            'close': closes
                        })
                        
                        adx_pandas = df.ta.adx(length=14)
                        if adx_pandas is not None and len(adx_pandas) > 0:
                            adx_pandas_val = adx_pandas['ADX_14'].iloc[-1]
                            print(f"pandas_ta (Ground Truth): ADX={adx_pandas_val:.2f}")
                            
                            # Comparar
                            diff = abs(adx_v21 - adx_pandas_val)
                            if diff < 5:
                                print(f"✅ VALIDACIÓN OK: Diferencia={diff:.2f} (< 5 puntos)")
                            else:
                                print(f"⚠️ DISCREPANCIA: Diferencia={diff:.2f} puntos")
                    except ImportError:
                        print("⚠️ pandas_ta no disponible, saltando verificación ground truth")
                    except Exception as e:
                        print(f"⚠️ Error en verificación pandas_ta: {e}")
                    
                    # VEREDICTO FINAL
                    print()
                    if adx_v21 > 5:
                        regime_emoji = {
                            'bull_trend': '📈',
                            'bear_trend': '📉',
                            'sideways_range': '↔️',
                            'high_volatility': '🔥',
                            'unknown': '❓'
                        }.get(regime.value, '❓')
                        
                        print(f"🎯 {regime_emoji} Régimen actualizado para {symbol}: {regime.value.upper()} (ADX: {adx_v21:.2f})")
                        print("✅ ÉXITO: ADX ya no es 0.0, el sistema tiene visión!")
                    else:
                        print(f"❌ FALLO: ADX aún es ~0 ({adx_v21:.2f}). El bug persiste.")
                    
                    print("-" * 80)
                    print()
                else:
                    print(f"⏳ Acumulando datos: {len(closes)}/200 velas necesarias")
                    print()
            
            # Terminar cuando todos los símbolos estén verificados
            if all(count >= UPDATES_PER_SYMBOL for count in update_counts.values()):
                print("=" * 80)
                print("✅ VERIFICACIÓN COMPLETADA PARA TODOS LOS SÍMBOLOS")
                print("=" * 80)
                break
                
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
            import traceback
            traceback.print_exc()
    
    pubsub.close()
    print("\n🦅 Script de verificación finalizado.")

if __name__ == "__main__":
    main()
