#!/usr/bin/env python3
"""
Brain Status Diagnostic Tool - V19
===================================
Script para monitorear el estado del sistema de trading.

Uso:
    python check_brain_status.py
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List
from src.shared.memory import memory
from src.shared.utils import get_logger

logger = get_logger("BrainDiagnostic")


class BrainStatusChecker:
    """
    Herramienta de diagnóstico para el Brain V19.
    """
    
    def __init__(self):
        self.redis_client = memory.get_client()
        
        if not self.redis_client:
            print("❌ ERROR: No se pudo conectar a Redis")
            sys.exit(1)
    
    def check_market_regimes(self) -> Dict[str, any]:
        """
        Verifica el régimen de mercado actual de cada símbolo activo.
        """
        regimes = {}
        
        # Buscar todas las keys de régimen
        regime_keys = self.redis_client.keys("market_regime:*")
        
        if not regime_keys:
            return {}
        
        for key in regime_keys:
            try:
                regime_json = self.redis_client.get(key)
                if regime_json:
                    regime_data = json.loads(regime_json)
                    symbol = regime_data['symbol']
                    regimes[symbol] = regime_data
            except Exception as e:
                logger.error(f"Error leyendo régimen {key}: {e}")
        
        return regimes
    
    def check_active_strategies(self) -> Dict[str, any]:
        """
        Verifica las estrategias activas (campeonas) para cada símbolo.
        """
        strategies = {}
        
        # Buscar todas las keys de configuración
        strategy_keys = self.redis_client.keys("strategy_config:*")
        
        if not strategy_keys:
            return {}
        
        for key in strategy_keys:
            try:
                strategy_json = self.redis_client.get(key)
                if strategy_json:
                    strategy_data = json.loads(strategy_json)
                    symbol = key.decode('utf-8').split(':')[1]
                    strategies[symbol] = strategy_data
            except Exception as e:
                logger.error(f"Error leyendo estrategia {key}: {e}")
        
        return strategies
    
    def check_next_optimization(self) -> dict:
        """
        Estima cuándo será la próxima optimización.
        """
        # Buscar key de última optimización
        last_opt_key = "last_optimization_timestamp"
        last_opt = self.redis_client.get(last_opt_key)
        
        if not last_opt:
            return {
                'next_optimization': 'Desconocido (aún no ha corrido)',
                'last_optimization': 'Nunca'
            }
        
        try:
            last_opt_data = json.loads(last_opt)
            last_timestamp = datetime.fromisoformat(last_opt_data['timestamp'])
            
            # Intervalo es 12 horas (43200 segundos)
            next_timestamp = last_timestamp + timedelta(hours=12)
            time_until_next = next_timestamp - datetime.utcnow()
            
            if time_until_next.total_seconds() < 0:
                status = "⏰ DEBERÍA ESTAR CORRIENDO AHORA"
            else:
                hours = int(time_until_next.total_seconds() // 3600)
                minutes = int((time_until_next.total_seconds() % 3600) // 60)
                status = f"En {hours}h {minutes}min"
            
            return {
                'next_optimization': status,
                'next_timestamp': next_timestamp.isoformat(),
                'last_optimization': last_timestamp.isoformat()
            }
        
        except Exception as e:
            return {
                'next_optimization': f'Error: {e}',
                'last_optimization': 'Error parseando'
            }
    
    def print_report(self):
        """
        Imprime reporte completo del estado del Brain.
        """
        print("\n" + "="*70)
        print("🧠 BRAIN V19 - STATUS REPORT")
        print("="*70)
        
        # 1. MARKET REGIMES
        print("\n📊 MARKET REGIMES (Régimen de Mercado Actual)")
        print("-"*70)
        
        regimes = self.check_market_regimes()
        
        if not regimes:
            print("⚠️  No hay datos de régimen (esperando acumulación de historial)")
        else:
            regime_emojis = {
                'bull_trend': '📈',
                'bear_trend': '📉',
                'sideways_range': '↔️',
                'high_volatility': '🔥',
                'unknown': '❓'
            }
            
            for symbol, data in regimes.items():
                regime_value = data['regime']
                emoji = regime_emojis.get(regime_value, '❓')
                indicators = data['indicators']
                
                print(f"\n  {symbol}:")
                print(f"    Regime:  {emoji} {regime_value.upper().replace('_', ' ')}")
                print(f"    Price:   ${indicators['current_price']:.2f}")
                print(f"    EMA(200): ${indicators['ema_200']:.2f}")
                print(f"    ADX:     {indicators['adx']:.1f} ({'Strong' if indicators['adx'] > 25 else 'Weak'} trend)")
                print(f"    ATR:     {indicators['atr_percent']:.2f}% ({'High' if indicators['atr_percent'] > 5 else 'Normal'} volatility)")
        
        # 2. ACTIVE STRATEGIES
        print("\n\n🏆 ACTIVE STRATEGIES (Estrategias Campeonas)")
        print("-"*70)
        
        strategies = self.check_active_strategies()
        
        if not strategies:
            print("⚠️  No hay estrategias configuradas")
        else:
            for symbol, data in strategies.items():
                strategy_name = data['strategy_name']
                params = data['params']
                metrics = data.get('metrics', {})
                
                print(f"\n  {symbol}:")
                print(f"    Strategy:  {strategy_name}")
                print(f"    Params:    {params}")
                
                if metrics:
                    print(f"    Return:    {metrics.get('total_return', 0):.2f}%")
                    print(f"    Sharpe:    {metrics.get('sharpe_ratio', 0):.2f}")
                    print(f"    Win Rate:  {metrics.get('win_rate', 0):.1f}%")
                    print(f"    Score:     {metrics.get('score', 0):.3f}")
        
        # 3. REGIME-STRATEGY COMPATIBILITY CHECK
        print("\n\n✅ COMPATIBILITY CHECK (Régimen vs Estrategia)")
        print("-"*70)
        
        if regimes and strategies:
            from src.services.brain.strategies.regime_detector import RegimeDetector, MarketRegime
            
            detector = RegimeDetector()
            
            for symbol in regimes.keys():
                if symbol in strategies:
                    regime_value = regimes[symbol]['regime']
                    try:
                        regime_enum = MarketRegime(regime_value)
                        recommended = detector.get_recommended_strategies(regime_enum)
                        current_strategy = strategies[symbol]['strategy_name']
                        
                        is_compatible = current_strategy in recommended
                        
                        status = "✅ COMPATIBLE" if is_compatible else "⚠️  SUBOPTIMAL"
                        
                        print(f"\n  {symbol}: {status}")
                        print(f"    Current:     {current_strategy}")
                        print(f"    Recommended: {', '.join(recommended[:3])}")
                    except Exception as e:
                        print(f"  {symbol}: Error - {e}")
        
        # 4. OPTIMIZATION SCHEDULE
        print("\n\n⏰ OPTIMIZATION SCHEDULE")
        print("-"*70)
        
        opt_info = self.check_next_optimization()
        
        print(f"\n  Last Optimization:  {opt_info['last_optimization']}")
        print(f"  Next Optimization:  {opt_info['next_optimization']}")
        print(f"  Interval:          Every 12 hours")
        
        # 5. SYSTEM HEALTH
        print("\n\n💊 SYSTEM HEALTH")
        print("-"*70)
        
        # Verificar conexión Redis
        try:
            self.redis_client.ping()
            print("  Redis:              ✅ Connected")
        except:
            print("  Redis:              ❌ Disconnected")
        
        # Verificar símbolos activos
        active_symbols_json = self.redis_client.get('active_symbols')
        if active_symbols_json:
            active_symbols = json.loads(active_symbols_json)
            print(f"  Active Symbols:     {len(active_symbols)} ({', '.join(active_symbols)})")
        else:
            print("  Active Symbols:     ⚠️  None")
        
        # Verificar señales recientes
        recent_signals = self.redis_client.lrange('recent_signals', 0, 9)
        print(f"  Recent Signals:     {len(recent_signals)} in cache")
        
        if recent_signals:
            last_signal = json.loads(recent_signals[0])
            last_timestamp = datetime.fromisoformat(last_signal['timestamp'])
            time_since = datetime.now(last_timestamp.tzinfo) - last_timestamp
            
            minutes_ago = int(time_since.total_seconds() // 60)
            print(f"  Last Signal:        {minutes_ago} minutes ago ({last_signal['symbol']} {last_signal['type']})")
        
        print("\n" + "="*70)
        print("✅ Diagnostic complete!")
        print("="*70 + "\n")


def main():
    """
    Punto de entrada del script.
    """
    try:
        checker = BrainStatusChecker()
        checker.print_report()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
