"""
EMA Triple Crossover Strategy - V18.5
======================================
Estrategia con 3 EMAs para mejor filtrado de señales.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any
from .base import StrategyInterface, StrategyResult


class EmaTripleCross(StrategyInterface):
    """
    Estrategia de Triple Cruce de EMAs.
    
    Usa 3 EMAs (rápida, media, lenta) para filtrar señales falsas.
    
    Señales:
    - BUY: EMA rápida > EMA media > EMA lenta (alineación bullish)
    - SELL: EMA rápida < EMA media < EMA lenta (alineación bearish)
    
    Funciona bien en: Tendencias fuertes con múltiples timeframes
    Falla en: Mercados muy laterales (entrada tardía)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {
                'fast': int (típicamente 5),
                'medium': int (típicamente 20),
                'slow': int (típicamente 50)
            }
        """
        super().__init__(params)
        self.fast_period = params.get('fast', 5)
        self.medium_period = params.get('medium', 20)
        self.slow_period = params.get('slow', 50)
        
        if not (self.fast_period < self.medium_period < self.slow_period):
            raise ValueError(
                f"Períodos deben ser ascendentes: fast({self.fast_period}) < "
                f"medium({self.medium_period}) < slow({self.slow_period})"
            )
    
    def calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA con precisión"""
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa alineación de 3 EMAs.
        """
        prices = np.array(price_history + [current_price])
        
        if len(prices) < self.slow_period + 2:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # Calcular EMAs actuales
        ema_fast = self.calculate_ema(prices[-self.fast_period:], self.fast_period)
        ema_medium = self.calculate_ema(prices[-self.medium_period:], self.medium_period)
        ema_slow = self.calculate_ema(prices[-self.slow_period:], self.slow_period)
        
        # EMAs previas (para detectar cruces)
        ema_fast_prev = self.calculate_ema(prices[-(self.fast_period+1):-1], self.fast_period)
        ema_medium_prev = self.calculate_ema(prices[-(self.medium_period+1):-1], self.medium_period)
        ema_slow_prev = self.calculate_ema(prices[-(self.slow_period+1):-1], self.slow_period)
        
        signal = None
        confidence = 0.0
        reason = "Sin alineación completa"
        
        # Bullish Alignment: Fast > Medium > Slow (y no estaba así antes)
        is_bullish_now = ema_fast > ema_medium > ema_slow
        was_bullish_before = ema_fast_prev > ema_medium_prev > ema_slow_prev
        
        if is_bullish_now and not was_bullish_before:
            signal = "BUY"
            # Confianza basada en separación de EMAs
            separation = ((ema_fast - ema_slow) / ema_slow * 100)
            confidence = min(0.95, 0.6 + abs(separation) / 5)
            reason = f"Triple EMA Bullish Alignment (Sep: {separation:.2f}%)"
        
        # Bearish Alignment: Fast < Medium < Slow
        is_bearish_now = ema_fast < ema_medium < ema_slow
        was_bearish_before = ema_fast_prev < ema_medium_prev < ema_slow_prev
        
        if is_bearish_now and not was_bearish_before:
            signal = "SELL"
            separation = ((ema_slow - ema_fast) / ema_slow * 100)
            confidence = min(0.95, 0.6 + abs(separation) / 5)
            reason = f"Triple EMA Bearish Alignment (Sep: {separation:.2f}%)"
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'ema_fast': round(ema_fast, 2),
                'ema_medium': round(ema_medium, 2),
                'ema_slow': round(ema_slow, 2),
                'trend': 'bullish' if is_bullish_now else 'bearish' if is_bearish_now else 'neutral'
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita slow + 2 para cruces"""
        return self.slow_period + 2
    
    def get_parameter_space(self) -> Dict[str, list]:
        """
        Espacio de búsqueda para optimización.
        """
        return {
            'fast': [5, 8, 10],
            'medium': [15, 20, 25],
            'slow': [40, 50, 60]
        }
