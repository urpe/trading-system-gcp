"""
Tournament Optimizer - V18
==========================
Motor de optimización que compite estrategias para encontrar la mejor configuración.
"""

import itertools
import json
from typing import Dict, List, Tuple, Any
from datetime import datetime
from src.shared.utils import get_logger
from .base import StrategyInterface
from ..backtesting.fast_backtester import FastBacktester, BacktestResult

logger = get_logger("TournamentOptimizer")


class TournamentOptimizer:
    """
    Optimizador basado en "Torneo de Estrategias".
    
    Proceso:
    1. Toma todas las estrategias disponibles (SMA, RSI, Bollinger, etc.)
    2. Para cada estrategia, prueba múltiples combinaciones de parámetros
    3. Ejecuta backtest rápido para cada combinación
    4. Retorna la estrategia ganadora (mayor score)
    
    El "torneo" se ejecuta cada 4 horas para adaptarse al mercado.
    """
    
    def __init__(self, strategy_classes: Dict[str, type]):
        """
        Args:
            strategy_classes: Diccionario {nombre: clase} de estrategias disponibles
                              Ej: {'sma': SmaCrossover, 'rsi': RsiMeanReversion}
        """
        self.strategy_classes = strategy_classes
        self.backtester = FastBacktester(initial_capital=10000.0)
    
    def optimize_for_symbol(
        self, 
        symbol: str, 
        price_history: List[float],
        max_combinations: int = 50,
        strategies_to_test: Dict[str, type] = None
    ) -> Tuple[StrategyInterface, BacktestResult]:
        """
        Ejecuta el "torneo" para un símbolo específico.
        
        Args:
            symbol: Símbolo del activo (ej: 'BTC')
            price_history: Datos históricos de precio [más antiguo -> más reciente]
            max_combinations: Máximo de combinaciones a probar (para limitar tiempo)
            strategies_to_test: (V19) Diccionario de estrategias a probar. Si None, usa todas.
        
        Returns:
            Tupla (estrategia_ganadora, resultado_backtest)
        """
        # V19: Permitir filtrado de estrategias por régimen
        strategies = strategies_to_test if strategies_to_test is not None else self.strategy_classes
        
        logger.info(f"🏆 Iniciando Torneo de Estrategias para {symbol} ({len(price_history)} precios)")
        logger.info(f"   🎯 Probando {len(strategies)} estrategias")
        
        all_results = []
        combinations_tested = 0
        
        # Probar cada tipo de estrategia
        for strategy_name, strategy_class in strategies.items():
            logger.info(f"  🔍 Probando {strategy_name}...")
            
            # Obtener espacio de parámetros
            temp_strategy = strategy_class({})
            param_space = temp_strategy.get_parameter_space()
            
            # Generar todas las combinaciones posibles
            param_names = list(param_space.keys())
            param_values = [param_space[name] for name in param_names]
            
            for combination in itertools.product(*param_values):
                if combinations_tested >= max_combinations:
                    break
                
                # Crear diccionario de parámetros
                params = dict(zip(param_names, combination))
                
                try:
                    # Crear instancia de estrategia con estos parámetros
                    strategy = strategy_class(params)
                    
                    # Ejecutar backtest
                    result = self.backtester.run(strategy, price_history)
                    
                    all_results.append((strategy, result))
                    combinations_tested += 1
                    
                except Exception as e:
                    logger.warning(f"    ⚠️ Error con params {params}: {e}")
                    continue
        
        if not all_results:
            logger.error(f"❌ No se pudo probar ninguna estrategia para {symbol}")
            raise ValueError("No valid strategies tested")
        
        # Ordenar por score y seleccionar la mejor
        all_results.sort(key=lambda x: x[1].score, reverse=True)
        
        best_strategy, best_result = all_results[0]
        
        logger.info(f"✅ Ganador para {symbol}: {best_result}")
        logger.info(f"   Total combinaciones probadas: {combinations_tested}")
        
        # Mostrar top 3
        if len(all_results) > 1:
            logger.info(f"   🥈 Runner-up: {all_results[1][1]}")
        if len(all_results) > 2:
            logger.info(f"   🥉 Third: {all_results[2][1]}")
        
        return best_strategy, best_result
    
    def optimize_all_symbols(
        self, 
        symbols_data: Dict[str, List[float]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Ejecuta el torneo para múltiples símbolos en paralelo.
        
        Args:
            symbols_data: Diccionario {símbolo: [precios históricos]}
        
        Returns:
            Diccionario con resultados para cada símbolo:
            {
                'BTC': {
                    'strategy_name': 'SmaCrossover',
                    'params': {'fast': 10, 'slow': 30},
                    'metrics': {...}
                },
                ...
            }
        """
        logger.info(f"🎯 Optimizando estrategias para {len(symbols_data)} símbolos...")
        
        results = {}
        
        for symbol, price_history in symbols_data.items():
            try:
                best_strategy, backtest_result = self.optimize_for_symbol(
                    symbol, 
                    price_history
                )
                
                results[symbol] = {
                    'strategy_name': best_strategy.name,
                    'params': best_strategy.params,
                    'metrics': {
                        'total_return': backtest_result.total_return,
                        'sharpe_ratio': backtest_result.sharpe_ratio,
                        'win_rate': backtest_result.win_rate,
                        'max_drawdown': backtest_result.max_drawdown,
                        'total_trades': backtest_result.total_trades,
                        'score': backtest_result.score
                    },
                    'last_updated': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Error optimizando {symbol}: {e}")
                # Estrategia por defecto en caso de error
                results[symbol] = {
                    'strategy_name': 'RsiMeanReversion',
                    'params': {'period': 14, 'oversold': 30, 'overbought': 70},
                    'metrics': {},
                    'last_updated': datetime.utcnow().isoformat(),
                    'error': str(e)
                }
        
        logger.info(f"✅ Optimización completada para {len(results)} símbolos")
        return results
    
    def save_to_redis(self, redis_client, results: Dict[str, Dict[str, Any]]):
        """
        Guarda los resultados del torneo en Redis para acceso en vivo.
        
        Redis Structure:
        - Key: strategy_config:{symbol}
        - Value: JSON con estrategia ganadora y parámetros
        """
        for symbol, config in results.items():
            key = f"strategy_config:{symbol}"
            redis_client.set(key, json.dumps(config))
            logger.info(f"💾 Guardado: {key} -> {config['strategy_name']}{config['params']}")
        
        # Guardar timestamp de última optimización
        redis_client.set('strategy_optimization:last_run', datetime.utcnow().isoformat())
        
        logger.info("✅ Configuraciones guardadas en Redis")
