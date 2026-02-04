"""
Advanced Regime Detector - V19
===============================
Sistema de detección de régimen de mercado usando ADX + EMA(200) + Volatilidad.

Referencias:
- Welles Wilder Jr. (1978): "New Concepts in Technical Trading Systems" (ADX)
- Perry Kaufman (2005): "Trading Systems and Methods" (Regime Detection)
"""

import numpy as np
from enum import Enum
from typing import List, Tuple, Dict, Any
from datetime import datetime
from src.shared.utils import get_logger

logger = get_logger("RegimeDetector")


class MarketRegime(Enum):
    """Régimen de mercado con estrategias recomendadas"""
    BULL_TREND = "bull_trend"          # Alcista con tendencia: Trend Following
    BEAR_TREND = "bear_trend"          # Bajista con tendencia: Shorting/Cash
    SIDEWAYS_RANGE = "sideways_range"  # Lateral: Mean Reversion
    HIGH_VOLATILITY = "high_volatility" # Alta volatilidad: Reducir tamaño
    UNKNOWN = "unknown"                # Sin datos suficientes


class RegimeDetector:
    """
    Detecta el régimen de mercado actual usando indicadores técnicos avanzados.
    
    Algoritmo:
    1. Calcula EMA(200) para tendencia macro
    2. Calcula ADX para fuerza de tendencia
    3. Clasifica según la matriz de decisión
    
    Reglas de Clasificación:
    - BULL_TREND: Precio > EMA(200) AND ADX > 25
    - BEAR_TREND: Precio < EMA(200) AND ADX > 25  
    - SIDEWAYS: ADX < 20 (sin importar EMA)
    - HIGH_VOLATILITY: ATR > 8% del precio medio
    """
    
    def __init__(self, ema_period: int = 200, adx_period: int = 14):
        self.ema_period = ema_period
        self.adx_period = adx_period
        
        # Thresholds
        self.adx_trend_threshold = 25    # ADX > 25 = Tendencia fuerte
        self.adx_sideways_threshold = 20  # ADX < 20 = Lateral
        self.volatility_threshold = 8.0   # ATR > 8% = Alta volatilidad
        
    def calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA (Exponential Moving Average) con precisión"""
        if len(prices) < period:
            return np.mean(prices)  # Fallback a SMA
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """
        Calcula ATR (Average True Range).
        
        ATR mide volatilidad promedio. Usado para:
        - Detectar alta volatilidad
        - Ajustar stop-loss dinámicos
        """
        if len(highs) < period + 1:
            return 0.0
        
        # True Range = max(H-L, |H-Cp|, |L-Cp|)
        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)
        
        # ATR = EMA de True Ranges
        if len(true_ranges) < period:
            return np.mean(true_ranges)
        
        return self.calculate_ema(np.array(true_ranges[-period:]), period)
    
    def calculate_adx(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> Tuple[float, float, float]:
        """
        Calcula ADX (Average Directional Index).
        
        ADX mide la FUERZA de una tendencia (0-100):
        - ADX < 20: Sin tendencia (Lateral/Choppy)
        - ADX 20-25: Tendencia débil
        - ADX > 25: Tendencia fuerte
        - ADX > 50: Tendencia muy fuerte
        
        Returns:
            Tuple[adx, di_plus, di_minus]
        """
        if len(highs) < period + 1:
            return 0.0, 0.0, 0.0
        
        # 1. Calcular +DM y -DM
        dm_plus = []
        dm_minus = []
        
        for i in range(1, len(highs)):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            # +DM: Movimiento alcista
            if up_move > down_move and up_move > 0:
                dm_plus.append(up_move)
            else:
                dm_plus.append(0)
            
            # -DM: Movimiento bajista
            if down_move > up_move and down_move > 0:
                dm_minus.append(down_move)
            else:
                dm_minus.append(0)
        
        # 2. Calcular ATR (True Range smoothed)
        atr = self.calculate_atr(highs, lows, closes, period)
        
        if atr == 0:
            return 0.0, 0.0, 0.0
        
        # 3. Calcular DI+ y DI-
        dm_plus_smooth = self.calculate_ema(np.array(dm_plus[-period:]), period)
        dm_minus_smooth = self.calculate_ema(np.array(dm_minus[-period:]), period)
        
        di_plus = (dm_plus_smooth / atr) * 100
        di_minus = (dm_minus_smooth / atr) * 100
        
        # 4. Calcular DX (Directional Index)
        if di_plus + di_minus == 0:
            return 0.0, di_plus, di_minus
        
        dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100
        
        # 5. ADX = Smooth de DX
        # Simplificado: Para cálculo en tiempo real, usamos último DX
        adx = dx
        
        return adx, di_plus, di_minus
    
    def detect(
        self,
        price_history: List[float],
        high_history: List[float] = None,
        low_history: List[float] = None
    ) -> Tuple[MarketRegime, Dict[str, Any]]:
        """
        Detecta el régimen de mercado actual.
        
        Args:
            price_history: Lista de precios de cierre (últimos N datos)
            high_history: Lista de máximos (opcional, para ADX preciso)
            low_history: Lista de mínimos (opcional, para ADX preciso)
        
        Returns:
            Tuple[MarketRegime, indicators_dict]
        """
        if len(price_history) < self.ema_period:
            logger.warning(f"Historial insuficiente para régimen: {len(price_history)} < {self.ema_period}")
            return MarketRegime.UNKNOWN, {}
        
        prices = np.array(price_history)
        current_price = prices[-1]
        
        # 1. Calcular EMA(200) para tendencia macro
        ema_200 = self.calculate_ema(prices[-self.ema_period:], self.ema_period)
        
        # 2. Calcular ADX para fuerza de tendencia
        if high_history and low_history and len(high_history) >= self.adx_period:
            highs = np.array(high_history[-self.adx_period-1:])
            lows = np.array(low_history[-self.adx_period-1:])
            closes = prices[-self.adx_period-1:]
            
            adx, di_plus, di_minus = self.calculate_adx(highs, lows, closes, self.adx_period)
            
            # Calcular ATR para volatilidad
            atr = self.calculate_atr(highs, lows, closes, self.adx_period)
            atr_percent = (atr / np.mean(closes)) * 100
        else:
            # Fallback: Estimación simplificada de ADX usando volatilidad
            # Necesita al menos adx_period + 1 para calcular returns
            if len(prices) < self.adx_period + 1:
                adx, di_plus, di_minus = 0.0, 0.0, 0.0
                atr_percent = 0.0
            else:
                # Calcular returns con dimensiones correctas
                price_segment = prices[-(self.adx_period + 1):]
                returns = np.diff(price_segment) / price_segment[:-1]
                volatility = np.std(returns) * 100
                
                # ADX estimado: Alta volatilidad con dirección = tendencia
                mean_return = np.mean(returns)
                adx = min(abs(mean_return) * 1000, 50)  # Estimación burda
                di_plus = max(0, mean_return * 1000)
                di_minus = max(0, -mean_return * 1000)
                
                atr = volatility * np.mean(price_segment) / 100
                atr_percent = volatility
        
        # 3. Clasificar Régimen según Matriz de Decisión
        indicators = {
            'current_price': float(current_price),
            'ema_200': float(ema_200),
            'adx': float(adx),
            'di_plus': float(di_plus),
            'di_minus': float(di_minus),
            'atr_percent': float(atr_percent),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Regla 1: Alta Volatilidad = Reducir exposición
        if atr_percent > self.volatility_threshold:
            regime = MarketRegime.HIGH_VOLATILITY
            logger.info(f"🔥 HIGH VOLATILITY detected: ATR={atr_percent:.2f}% > {self.volatility_threshold}%")
        
        # Regla 2: Lateral/Choppy = Sin tendencia clara
        elif adx < self.adx_sideways_threshold:
            regime = MarketRegime.SIDEWAYS_RANGE
            logger.info(f"↔️ SIDEWAYS market: ADX={adx:.1f} < {self.adx_sideways_threshold}")
        
        # Regla 3: Tendencia Alcista = Precio > EMA(200) + ADX > 25
        elif current_price > ema_200 and adx >= self.adx_trend_threshold:
            regime = MarketRegime.BULL_TREND
            logger.info(f"📈 BULL TREND: Price={current_price:.2f} > EMA200={ema_200:.2f}, ADX={adx:.1f}")
        
        # Regla 4: Tendencia Bajista = Precio < EMA(200) + ADX > 25
        elif current_price < ema_200 and adx >= self.adx_trend_threshold:
            regime = MarketRegime.BEAR_TREND
            logger.info(f"📉 BEAR TREND: Price={current_price:.2f} < EMA200={ema_200:.2f}, ADX={adx:.1f}")
        
        # Regla 5: Transición (ADX entre 20-25)
        else:
            regime = MarketRegime.SIDEWAYS_RANGE
            logger.info(f"⚖️ TRANSITIONAL market (weak trend): ADX={adx:.1f}")
        
        return regime, indicators
    
    def get_recommended_strategies(self, regime: MarketRegime) -> List[str]:
        """
        Devuelve las estrategias recomendadas para cada régimen.
        
        Matriz de Compatibilidad:
        - BULL_TREND: Trend Following (SMA, EMA, Ichimoku, MACD)
        - BEAR_TREND: Cash/Shorting (RSI inverso, ADX filter)
        - SIDEWAYS: Mean Reversion (RSI, Bollinger, Keltner)
        - HIGH_VOLATILITY: Reducir operaciones, stop-loss amplios
        """
        strategy_matrix = {
            MarketRegime.BULL_TREND: [
                'SmaCrossover',
                'EmaTripleCross',
                'IchimokuCloud',
                'MacdStrategy',
                'AdxTrendStrategy'
            ],
            MarketRegime.BEAR_TREND: [
                'AdxTrendStrategy',  # Con filtro para no operar
                'RsiMeanReversion',  # Esperar sobreventa extrema
            ],
            MarketRegime.SIDEWAYS_RANGE: [
                'RsiMeanReversion',
                'BollingerBreakout',
                'KeltnerChannels',
                'VolumeProfileStrategy'
            ],
            MarketRegime.HIGH_VOLATILITY: [
                'AdxTrendStrategy',  # Solo tendencias muy claras
            ],
            MarketRegime.UNKNOWN: [
                'RsiMeanReversion'  # Estrategia conservadora por defecto
            ]
        }
        
        return strategy_matrix.get(regime, ['RsiMeanReversion'])
