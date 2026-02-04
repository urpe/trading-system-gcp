"""
Brain Service V19 - Regime Switching Intelligence
==================================================
Motor de trading adaptativo con detección de régimen de mercado.

Características V19:
- Regime Detection (Bull/Bear/Sideways) usando ADX + EMA(200)
- 9 estrategias avanzadas (Ichimoku, Keltner, Volume Profile, etc.)
- Filtrado automático de estrategias según régimen
- Hot-swap de parámetros sin restart
- Monitorización de compatibilidad estrategia-régimen
"""

import time
import json
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Optional
from src.config.settings import config
from src.shared.utils import get_logger
from src.shared.memory import memory
from src.services.brain.strategies import AVAILABLE_STRATEGIES
from src.services.brain.strategies.base import StrategyInterface
from src.services.brain.strategies.regime_detector import RegimeDetector, MarketRegime

logger = get_logger("BrainV19")


class RegimeSwitchingBrain:
    """
    Brain V19 con Regime Detection y selección adaptativa de estrategias.
    """
    
    def __init__(self):
        self.redis_client = memory.get_client()
        
        # V21: Cachés OHLCV completos
        self.price_history: Dict[str, deque] = {}   # Close prices
        self.high_history: Dict[str, deque] = {}     # High prices (V21 NUEVO)
        self.low_history: Dict[str, deque] = {}      # Low prices (V21 NUEVO)
        self.max_history_size = 200
        
        # Estrategias activas por símbolo (cargadas desde Redis)
        self.active_strategies: Dict[str, StrategyInterface] = {}
        
        # Timestamp de última actualización de estrategias
        self.last_strategy_update = None
        
        # V19: Regime Detector
        self.regime_detector = RegimeDetector(ema_period=200, adx_period=14)
        self.current_regimes: Dict[str, MarketRegime] = {}
        
        # V19.1: Cooldown tracking para evitar overtrading
        self.last_signal_time: Dict[str, datetime] = {}  # {symbol: last_signal_timestamp}
        self.cooldown_minutes = 10  # 10 minutos cooldown por símbolo
        
        logger.info("🦅 Brain V21 EAGLE EYE - OHLCV Intelligence + Cooldown Initialized")
        logger.info(f"📊 {len(AVAILABLE_STRATEGIES)} estrategias disponibles")
        logger.info(f"⏳ Cooldown: {self.cooldown_minutes} minutos por símbolo")
    
    def load_strategy_for_symbol(self, symbol: str) -> Optional[StrategyInterface]:
        """
        Carga la estrategia óptima para un símbolo desde Redis.
        
        Redis Key: strategy_config:{symbol}
        Value: {
            'strategy_name': 'SmaCrossover',
            'params': {'fast': 10, 'slow': 30},
            'metrics': {...}
        }
        """
        try:
            key = f"strategy_config:{symbol}"
            config_json = self.redis_client.get(key)
            
            if not config_json:
                logger.warning(f"⚠️ No hay configuración para {symbol}, usando RSI por defecto")
                # Estrategia por defecto
                return AVAILABLE_STRATEGIES['RsiMeanReversion']({
                    'period': 14,
                    'oversold': 30,
                    'overbought': 70
                })
            
            config_data = json.loads(config_json)
            strategy_name = config_data['strategy_name']
            params = config_data['params']
            
            # Buscar clase de estrategia
            if strategy_name in AVAILABLE_STRATEGIES:
                strategy = AVAILABLE_STRATEGIES[strategy_name](params)
                logger.info(f"✅ Cargada estrategia para {symbol}: {strategy}")
                return strategy
            
            logger.error(f"❌ Estrategia desconocida: {strategy_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error cargando estrategia para {symbol}: {e}")
            return None
    
    def update_ohlcv_history(self, symbol: str, ohlcv_data: dict):
        """
        V21: Actualiza el historial OHLCV completo para un símbolo.
        
        Args:
            symbol: Símbolo de la moneda (ej: "BTC")
            ohlcv_data: {
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float,
                "timestamp": float
            }
        """
        # Inicializar deques si no existen
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.max_history_size)
            self.high_history[symbol] = deque(maxlen=self.max_history_size)
            self.low_history[symbol] = deque(maxlen=self.max_history_size)
        
        # Agregar datos OHLCV
        self.price_history[symbol].append(ohlcv_data['close'])
        self.high_history[symbol].append(ohlcv_data['high'])
        self.low_history[symbol].append(ohlcv_data['low'])
    
    def detect_market_regime(self, symbol: str) -> Optional[MarketRegime]:
        """
        Detecta el régimen de mercado actual para un símbolo.
        
        Returns:
            MarketRegime o None si no hay suficientes datos
        """
        if symbol not in self.price_history:
            return None
        
        price_hist = list(self.price_history[symbol])
        
        if len(price_hist) < 200:  # Necesita EMA(200)
            return None
        
        try:
            # V21: Pasar High/Low para cálculo correcto de ADX
            high_hist = list(self.high_history[symbol]) if symbol in self.high_history else None
            low_hist = list(self.low_history[symbol]) if symbol in self.low_history else None
            
            regime, indicators = self.regime_detector.detect(
                price_history=price_hist,
                high_history=high_hist,
                low_history=low_hist
            )
            
            # Guardar régimen detectado
            self.current_regimes[symbol] = regime
            
            # Guardar en Redis para dashboard/diagnóstico
            regime_data = {
                'symbol': symbol,
                'regime': regime.value,
                'indicators': indicators,
                'timestamp': datetime.utcnow().isoformat()
            }
            self.redis_client.setex(
                f"market_regime:{symbol}",
                300,  # 5 minutos TTL
                json.dumps(regime_data)
            )
            
            return regime
        
        except Exception as e:
            logger.error(f"Error detectando régimen para {symbol}: {e}")
            return None
    
    def process_market_update(self, message):
        """
        Procesa actualización de precio y genera señales con estrategia dinámica + regime awareness.
        """
        try:
            data = json.loads(message['data'])
            
            # Manejar arrays de datos o data simple
            if isinstance(data, list):
                coin_list = data
            else:
                coin_list = [data]
            
            for coin_data in coin_list:
                symbol = coin_data.get('symbol')
                
                # V21: Validar estructura OHLCV
                required_keys = ['open', 'high', 'low', 'close']
                if not all(k in coin_data for k in required_keys):
                    logger.warning(f"⚠️ Datos OHLCV incompletos para {symbol}: {coin_data}")
                    continue
                
                # Validar precios positivos
                if any(float(coin_data.get(k, 0)) <= 0 for k in required_keys):
                    continue
                
                # V21: Actualizar historial OHLCV completo
                self.update_ohlcv_history(symbol, coin_data)
                
                # Para compatibilidad con estrategias que usan solo 'price'
                price = float(coin_data['close'])
                
                # V19: Detectar régimen de mercado (cada 10 actualizaciones para no sobrecargar)
                regime = None
                if len(self.price_history[symbol]) % 10 == 0:
                    regime = self.detect_market_regime(symbol)
                else:
                    regime = self.current_regimes.get(symbol)
                
                # Cargar estrategia si no existe o recargar periódicamente
                if symbol not in self.active_strategies or self._should_reload_strategy():
                    self.active_strategies[symbol] = self.load_strategy_for_symbol(symbol)
                
                strategy = self.active_strategies.get(symbol)
                
                if not strategy:
                    continue
                
                # V19: Verificar compatibilidad estrategia-régimen
                if regime and regime != MarketRegime.UNKNOWN:
                    recommended = self.regime_detector.get_recommended_strategies(regime)
                    
                    if strategy.name not in recommended:
                        logger.warning(
                            f"⚠️ {symbol}: Estrategia {strategy.name} NO óptima para {regime.value}. "
                            f"Recomendadas: {', '.join(recommended[:3])}"
                        )
                        # Continuar pero con advertencia (no bloqueamos)
                
                # Verificar si tenemos suficiente historia
                history = list(self.price_history[symbol])
                if len(history) < strategy.get_required_history():
                    continue
                
                # Evaluar estrategia (sin incluir precio actual en historia)
                result = strategy.evaluate(price, history[:-1])
                
                if result.signal:
                    # Mapeo de emojis por régimen
                    regime_emoji = {
                        'bull_trend': '📈',
                        'bear_trend': '📉',
                        'sideways_range': '↔️',
                        'high_volatility': '🔥',
                        'unknown': '❓'
                    }.get(regime.value if regime else 'unknown', '❓')
                    
                    # Generar señal de trading
                    signal = {
                        "symbol": symbol,
                        "type": result.signal,
                        "price": price,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "BrainV19_RegimeSwitching",
                        "strategy": strategy.name,
                        "params": strategy.params,
                        "confidence": result.confidence,
                        "reason": result.reason,
                        "indicators": result.indicators,
                        "market_regime": regime.value if regime else 'unknown'  # V19
                    }
                    
                    # V19.1: Verificar cooldown antes de publicar señal
                    current_time = datetime.now(timezone.utc)
                    
                    if symbol in self.last_signal_time:
                        time_since_last = (current_time - self.last_signal_time[symbol]).total_seconds() / 60
                        
                        if time_since_last < self.cooldown_minutes:
                            logger.info(
                                f"⏳ Cooldown activo para {symbol}: {time_since_last:.1f} < {self.cooldown_minutes} min - Señal rechazada"
                            )
                            continue  # Rechazar señal y continuar con siguiente símbolo
                    
                    # Actualizar timestamp de última señal
                    self.last_signal_time[symbol] = current_time
                    
                    # Publicar en Redis
                    try:
                        memory.publish('signals', signal)
                        
                        # Cache para Dashboard
                        self.redis_client.lpush('recent_signals', json.dumps(signal))
                        self.redis_client.ltrim('recent_signals', 0, 49)
                        
                        logger.info(
                            f"🧠 SIGNAL: {result.signal} {symbol} @ ${price:.2f} | "
                            f"Regime: {regime_emoji} {regime.value if regime else 'unknown'} | "
                            f"{strategy.name}{strategy.params} | "
                            f"Conf: {result.confidence:.0%} | {result.reason}"
                        )
                        
                    except Exception as e:
                        logger.error(f"❌ Redis Publish Error: {e}")
        
        except Exception as e:
            logger.error(f"Error procesando update: {e}", exc_info=True)
    
    def _should_reload_strategy(self) -> bool:
        """
        Verifica si debe recargar estrategias (cada 30 min para hot-swap)
        """
        if not self.last_strategy_update:
            self.last_strategy_update = time.time()
            return True
        
        # Recargar cada 30 minutos
        if time.time() - self.last_strategy_update > 1800:
            self.last_strategy_update = time.time()
            logger.info("🔄 Hot-swap: Recargando estrategias desde Redis...")
            self.active_strategies.clear()
            return True
        
        return False
    
    def run(self):
        """
        Loop principal del Brain.
        """
        logger.info("🧠 Brain V19 (Regime Switching Intelligence) Started...")
        logger.info(f"   📊 Estrategias: {', '.join(AVAILABLE_STRATEGIES.keys())}")
        logger.info(f"   🎯 Regime Detection: ADX + EMA(200)")
        
        if not self.redis_client:
            logger.critical("🔥 No se pudo conectar a Redis. Reintentando...")
            time.sleep(5)
            return
        
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe('market_data')
        
        logger.info("✅ Brain escuchando mercado en tiempo real...")
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                self.process_market_update(message)


def main():
    brain = RegimeSwitchingBrain()
    brain.run()


if __name__ == '__main__':
    # Espera inicial para servicios
    time.sleep(5)
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"❌ Crash en Brain: {e}", exc_info=True)
            time.sleep(5)
