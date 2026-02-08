"""
Strategy Optimizer Worker - V18
================================
Servicio background que ejecuta el "Torneo de Estrategias" cada 4 horas.

Proceso:
1. Obtiene símbolos activos desde Redis
2. Descarga datos históricos recientes (últimas 1000 velas de 1h)
3. Ejecuta TournamentOptimizer para cada símbolo
4. Guarda configuración ganadora en Redis para que Brain la use
"""

import time
import requests
import logging
from datetime import datetime
from typing import Dict, List
from src.shared.memory import memory
from src.shared.utils import get_logger, normalize_symbol
from src.config.symbols import ACTIVE_SYMBOLS, FALLBACK_SYMBOLS
from src.services.brain.strategies import AVAILABLE_STRATEGIES
from src.services.brain.strategies.optimizer import TournamentOptimizer
from src.services.strategy_optimizer.rolling_validator import RollingValidator

logger = get_logger("StrategyOptimizerV19")

# Configuración
OPTIMIZATION_INTERVAL = 4 * 3600  # 4 horas en segundos
BINANCE_API = "https://api.binance.com/api/v3/klines"
HISTORICAL_CANDLES = 1000  # Últimas 1000 velas de 1h (~42 días)


class StrategyOptimizerWorker:
    """
    Worker que ejecuta optimización de estrategias en background.
    """
    
    def __init__(self):
        self.redis_client = memory.get_client()
        self.optimizer = TournamentOptimizer(AVAILABLE_STRATEGIES)
        self.rolling_validator = RollingValidator()
        
        # V19: Importar regime detector para filtrado inteligente
        from src.services.brain.strategies.regime_detector import RegimeDetector
        self.regime_detector = RegimeDetector()
        
        logger.info("🎯 Strategy Optimizer Worker V19 - Regime-Aware Initialized")
        logger.info(f"⏰ Intervalo de optimización: {OPTIMIZATION_INTERVAL//3600}h")
        
        # V19: Ejecutar torneo inmediato si Redis está vacío (post-reset)
        if not self.redis_client.exists('strategy_config:BTC'):
            logger.info("🚨 Redis vacío detectado, ejecutando torneo INMEDIATO...")
            self.run_optimization_cycle()
        else:
            logger.info("✅ Estrategias ya cargadas en Redis")
    
    def get_active_symbols(self) -> List[str]:
        """
        V21.2.1: Obtiene lista de símbolos activos desde Redis con normalización.
        Key: active_symbols
        """
        try:
            symbols_json = self.redis_client.lrange('active_symbols', 0, -1)
            if not symbols_json:
                logger.warning("⚠️ No hay símbolos activos, usando canonical fallback")
                return FALLBACK_SYMBOLS  # V21.2.1: Canonical source
            
            symbols_raw = [s.decode('utf-8') if isinstance(s, bytes) else s for s in symbols_json]
            
            # V21.2.1: NORMALIZACIÓN - Asegurar formato corto consistente
            try:
                symbols = [normalize_symbol(s, format='short') for s in symbols_raw]
                logger.info(f"📊 Símbolos activos (normalizados): {symbols}")
                return symbols
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Error normalizando símbolos: {e}")
                return FALLBACK_SYMBOLS  # V21.2.1: Canonical source
            
        except Exception as e:
            logger.error(f"Error obteniendo símbolos: {e}")
            return FALLBACK_SYMBOLS  # V21.2.1: Canonical source
    
    def fetch_historical_data(self, symbol: str) -> List[float]:
        """
        V21.2.1: Descarga datos históricos de Binance para backtesting con normalización.
        
        Returns:
            Lista de precios de cierre [más antiguo -> más reciente]
        """
        try:
            # V21.2.1: NORMALIZACIÓN
            symbol_normalized = normalize_symbol(symbol, format='long')  # "BTCUSDT"
            
            logger.info(f"📥 Descargando {HISTORICAL_CANDLES} velas para {symbol}...")
            
            params = {
                'symbol': symbol_normalized,  # V21.2.1: Usar símbolo normalizado
                'interval': '1h',
                'limit': HISTORICAL_CANDLES
            }
            
            response = requests.get(BINANCE_API, params=params, timeout=30)
            response.raise_for_status()
            
            klines = response.json()
            
            if isinstance(klines, dict) and 'code' in klines:
                logger.error(f"❌ Binance API error: {klines}")
                return []
            
            # Extraer precios de cierre (índice 4)
            prices = [float(k[4]) for k in klines]
            
            logger.info(f"✅ Descargados {len(prices)} precios para {symbol}")
            return prices
            
        except Exception as e:
            logger.error(f"❌ Error descargando datos de {symbol}: {e}")
            return []
    
    def run_optimization_cycle(self):
        """
        Ejecuta un ciclo completo de optimización.
        """
        logger.info("=" * 80)
        logger.info("🏆 INICIANDO TORNEO DE ESTRATEGIAS")
        logger.info(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # 1. Obtener símbolos activos
        symbols = self.get_active_symbols()
        
        # 2. Descargar datos históricos para cada símbolo
        symbols_data = {}
        for symbol in symbols:
            price_data = self.fetch_historical_data(symbol)
            if price_data:
                symbols_data[symbol] = price_data
            else:
                logger.warning(f"⚠️ Saltando {symbol} por falta de datos")
        
        if not symbols_data:
            logger.error("❌ No hay datos para optimizar, abortando ciclo")
            return
        
        # 3. Ejecutar torneo con ROLLING VALIDATION para todos los símbolos
        logger.info(f"\n🎯 Ejecutando torneo CON VALIDACIÓN ROLLING para {len(symbols_data)} símbolos...")
        logger.info("   📊 Validación: 50% peso últimos 7d, 30% últimos 15d, 20% últimos 30d")
        
        results = {}
        for symbol, price_data in symbols_data.items():
            try:
                logger.info(f"\n🏆 Torneo para {symbol}:")
                
                # V19: Detectar régimen de mercado para filtrar estrategias
                regime, regime_indicators = self.regime_detector.detect(price_data)
                recommended_strategy_names = self.regime_detector.get_recommended_strategies(regime)
                
                logger.info(f"   📊 Régimen detectado: {regime.value}")
                logger.info(f"   🎯 Estrategias compatibles: {', '.join(recommended_strategy_names)}")
                
                # Filtrar AVAILABLE_STRATEGIES por régimen
                filtered_strategies = {
                    name: cls for name, cls in AVAILABLE_STRATEGIES.items()
                    if name in recommended_strategy_names
                }
                
                if not filtered_strategies:
                    logger.warning(f"   ⚠️ No hay estrategias compatibles para {symbol} en {regime.value}, usando todas")
                    filtered_strategies = AVAILABLE_STRATEGIES
                
                # Generar candidatos con optimizer (solo estrategias filtradas)
                best_strategy, backtest_result = self.optimizer.optimize_for_symbol(
                    symbol,
                    price_data,
                    max_combinations=50,
                    strategies_to_test=filtered_strategies
                )
                
                # VALIDACIÓN ROLLING: Verificar con datos recientes
                logger.info(f"   🔄 Aplicando Rolling Validation...")
                validation = self.rolling_validator.validate_strategy(best_strategy, price_data)
                
                if validation['is_approved']:
                    logger.info(f"   ✅ Estrategia APROBADA (Weighted Score: {validation['weighted_score']:.3f})")
                    
                    # Usar métricas de ventana más reciente (7d) como principales
                    recent_metrics = validation['results_by_window'].get('recent_7d', {})
                    
                    results[symbol] = {
                        'strategy_name': best_strategy.name,
                        'params': best_strategy.params,
                        'metrics': {
                            'total_return': recent_metrics.get('total_return', backtest_result.total_return),
                            'sharpe_ratio': recent_metrics.get('sharpe_ratio', backtest_result.sharpe_ratio),
                            'win_rate': recent_metrics.get('win_rate', backtest_result.win_rate),
                            'max_drawdown': recent_metrics.get('max_drawdown', backtest_result.max_drawdown),
                            'total_trades': recent_metrics.get('total_trades', backtest_result.total_trades),
                            'score': validation['weighted_score']
                        },
                        'validation': {
                            'weighted_score': validation['weighted_score'],
                            'valid_windows': validation['valid_windows'],
                            'by_window': validation['results_by_window']
                        },
                        'last_updated': datetime.utcnow().isoformat()
                    }
                else:
                    logger.warning(f"   ⚠️ Estrategia RECHAZADA en rolling validation, usando RSI default")
                    # Fallback a RSI conservador
                    results[symbol] = {
                        'strategy_name': 'RsiMeanReversion',
                        'params': {'period': 14, 'oversold': 25, 'overbought': 75},
                        'metrics': {},
                        'last_updated': datetime.utcnow().isoformat(),
                        'note': 'Fallback strategy due to validation failure'
                    }
                
            except Exception as e:
                logger.error(f"❌ Error optimizando {symbol}: {e}")
                results[symbol] = {
                    'strategy_name': 'RsiMeanReversion',
                    'params': {'period': 14, 'oversold': 30, 'overbought': 70},
                    'metrics': {},
                    'last_updated': datetime.utcnow().isoformat(),
                    'error': str(e)
                }
        
        # 4. Guardar resultados en Redis
        self.optimizer.save_to_redis(self.redis_client, results)
        
        # 5. Estadísticas finales
        elapsed = time.time() - start_time
        logger.info("\n" + "=" * 80)
        logger.info("✅ TORNEO COMPLETADO")
        logger.info(f"   Tiempo total: {elapsed:.1f}s")
        logger.info(f"   Símbolos optimizados: {len(results)}")
        
        # Mostrar resumen por símbolo
        logger.info("\n📊 RESUMEN DE ESTRATEGIAS GANADORAS:")
        for symbol, config in results.items():
            metrics = config.get('metrics', {})
            logger.info(
                f"   {symbol}: {config['strategy_name']}{config['params']} | "
                f"Return: {metrics.get('total_return', 0):.2f}% | "
                f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f} | "
                f"Score: {metrics.get('score', 0):.2f}"
            )
        
        logger.info("=" * 80 + "\n")
    
    def run(self):
        """
        Loop principal del worker.
        Ejecuta optimización cada OPTIMIZATION_INTERVAL segundos.
        """
        logger.info(f"🚀 Strategy Optimizer Worker iniciado")
        logger.info(f"⏱️  Intervalo de optimización: {OPTIMIZATION_INTERVAL/3600:.1f} horas")
        logger.info(f"📊 Estrategias disponibles: {list(AVAILABLE_STRATEGIES.keys())}")
        
        # Ejecutar primer ciclo inmediatamente
        logger.info("\n🎬 Ejecutando primer ciclo de optimización...")
        self.run_optimization_cycle()
        
        # Loop continuo
        while True:
            logger.info(f"\n⏳ Próxima optimización en {OPTIMIZATION_INTERVAL/3600:.1f} horas...")
            logger.info(f"   Hora actual: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            time.sleep(OPTIMIZATION_INTERVAL)
            
            try:
                self.run_optimization_cycle()
            except Exception as e:
                logger.error(f"❌ Error en ciclo de optimización: {e}")
                logger.exception(e)


def main():
    # Espera inicial para que Redis esté listo
    time.sleep(10)
    
    if not memory.connect():
        logger.critical("🔥 No se pudo conectar a Redis")
        return
    
    worker = StrategyOptimizerWorker()
    worker.run()


if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"❌ Crash en Strategy Optimizer: {e}")
            logger.exception(e)
            time.sleep(60)
