"""
Rolling Validation - V18.5
===========================
Valida estrategias con ventanas de tiempo más recientes para evitar overfitting.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from src.services.brain.backtesting.fast_backtester import FastBacktester, BacktestResult

logger = logging.getLogger("RollingValidator")


class RollingValidator:
    """
    Valida estrategias con múltiples ventanas temporales.
    
    En lugar de solo probar con datos históricos completos, valida con:
    - Últimos 7 días (168 velas de 1h) - Mercado MUY reciente
    - Últimos 15 días (360 velas)
    - Últimos 30 días (720 velas) - Balance entre reciente e histórico
    
    Solo aprueba estrategias que funcionen bien en TODAS las ventanas.
    """
    
    def __init__(self, initial_capital: float = 10000.0):
        self.backtester = FastBacktester(initial_capital)
        self.validation_windows = {
            'recent_7d': 168,    # Últimas 7 días (peso: 50%)
            'medium_15d': 360,   # Últimos 15 días (peso: 30%)
            'full_30d': 720      # Últimos 30 días (peso: 20%)
        }
        self.window_weights = {
            'recent_7d': 0.50,
            'medium_15d': 0.30,
            'full_30d': 0.20
        }
    
    def validate_strategy(
        self,
        strategy,
        full_price_data: List[float]
    ) -> Dict[str, Any]:
        """
        Valida estrategia en múltiples ventanas temporales.
        
        Returns:
            Dict con resultados por ventana y score ponderado
        """
        results = {}
        weighted_score = 0.0
        
        for window_name, window_size in self.validation_windows.items():
            # Extraer ventana de datos
            if len(full_price_data) >= window_size:
                window_data = full_price_data[-window_size:]
                
                # Ejecutar backtest en esta ventana
                result = self.backtester.run(strategy, window_data)
                
                results[window_name] = {
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'max_drawdown': result.max_drawdown,
                    'total_trades': result.total_trades,
                    'score': result.score
                }
                
                # Acumular score ponderado
                weight = self.window_weights[window_name]
                weighted_score += result.score * weight
            else:
                logger.warning(
                    f"No hay suficientes datos para ventana {window_name} "
                    f"(necesita {window_size}, tiene {len(full_price_data)})"
                )
                results[window_name] = None
        
        # Calcular score final ponderado
        valid_windows = sum(1 for r in results.values() if r is not None)
        
        return {
            'results_by_window': results,
            'weighted_score': weighted_score,
            'valid_windows': valid_windows,
            'is_approved': weighted_score > 0 and valid_windows >= 2  # Al menos 2 ventanas válidas
        }
    
    def get_best_validated_strategy(
        self,
        strategies_with_data: List[tuple],  # [(strategy_instance, price_data), ...]
        symbol: str
    ):
        """
        Encuentra la mejor estrategia usando validación rolling.
        
        Args:
            strategies_with_data: Lista de tuplas (estrategia, datos_precio)
            symbol: Símbolo para logging
        
        Returns:
            Tupla (mejor_estrategia, validation_result)
        """
        logger.info(f"🔄 Rolling validation para {symbol} con {len(strategies_with_data)} estrategias...")
        
        validated_strategies = []
        
        for strategy, price_data in strategies_with_data:
            validation = self.validate_strategy(strategy, price_data)
            
            if validation['is_approved']:
                validated_strategies.append((strategy, validation))
                
                logger.info(
                    f"   ✅ {strategy}: Weighted Score={validation['weighted_score']:.3f} "
                    f"(Valid windows: {validation['valid_windows']}/3)"
                )
            else:
                logger.warning(
                    f"   ❌ {strategy}: REJECTED (Score={validation['weighted_score']:.3f})"
                )
        
        if not validated_strategies:
            logger.error(f"⚠️ Ninguna estrategia pasó rolling validation para {symbol}")
            return None, None
        
        # Ordenar por score ponderado
        validated_strategies.sort(key=lambda x: x[1]['weighted_score'], reverse=True)
        
        best_strategy, best_validation = validated_strategies[0]
        
        logger.info(
            f"🏆 Mejor estrategia validada: {best_strategy.name}{best_strategy.params} "
            f"(Score: {best_validation['weighted_score']:.3f})"
        )
        
        return best_strategy, best_validation
