"""
MACD Strategy - V18.5
=====================
Moving Average Convergence Divergence - Estrategia de momentum.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any
from .base import StrategyInterface, StrategyResult


class MacdStrategy(StrategyInterface):
    """
    Estrategia MACD (Moving Average Convergence Divergence).
    
    Señales:
    - BUY: MACD cruza por encima de Signal Line (bullish crossover)
    - SELL: MACD cruza por debajo de Signal Line (bearish crossover)
    
    Funciona bien en: Mercados con momentum claro
    Falla en: Mercados muy laterales (muchas señales falsas)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {
                'fast': int (típicamente 12),
                'slow': int (típicamente 26),
                'signal': int (típicamente 9)
            }
        """
        super().__init__(params)
        self.fast_period = params.get('fast', 12)
        self.slow_period = params.get('slow', 26)
        self.signal_period = params.get('signal', 9)
    
    def calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA (Exponential Moving Average)"""
        multiplier = 2 / (period + 1)
        ema = prices[0]  # Seed con primer valor
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_macd(self, prices: np.ndarray):
        """
        Calcula MACD y Signal Line.
        
        Returns:
            tuple: (macd_line, signal_line, histogram)
        """
        # EMA rápida y lenta
        ema_fast = self.calculate_ema(prices[-self.fast_period:], self.fast_period)
        ema_slow = self.calculate_ema(prices[-self.slow_period:], self.slow_period)
        
        # MACD Line
        macd_line = ema_fast - ema_slow
        
        # Para Signal Line, necesitamos historial de MACD
        # Simplificado: calculamos MACD para varios puntos y luego EMA
        macd_history = []
        window_size = self.signal_period + 5
        
        for i in range(len(prices) - window_size, len(prices)):
            if i >= self.slow_period:
                segment = prices[:i+1]
                fast = self.calculate_ema(segment[-self.fast_period:], self.fast_period)
                slow = self.calculate_ema(segment[-self.slow_period:], self.slow_period)
                macd_history.append(fast - slow)
        
        if len(macd_history) >= self.signal_period:
            signal_line = self.calculate_ema(
                np.array(macd_history[-self.signal_period:]), 
                self.signal_period
            )
        else:
            signal_line = macd_line
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa cruces de MACD.
        """
        prices = np.array(price_history + [current_price])
        
        required = self.slow_period + self.signal_period + 5
        if len(prices) < required:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente para MACD",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # Calcular MACD actual y previo
        macd_current, signal_current, hist_current = self.calculate_macd(prices)
        macd_prev, signal_prev, hist_prev = self.calculate_macd(prices[:-1])
        
        signal = None
        confidence = 0.0
        reason = "Sin cruce"
        
        # Bullish Crossover: MACD cruza hacia arriba sobre Signal
        if macd_prev <= signal_prev and macd_current > signal_current:
            signal = "BUY"
            # Confianza basada en el tamaño del histograma
            histogram_strength = abs(hist_current) / current_price * 1000
            confidence = min(0.9, 0.5 + histogram_strength)
            reason = f"MACD Bullish Cross (Hist: {hist_current:.4f})"
        
        # Bearish Crossover: MACD cruza hacia abajo bajo Signal
        elif macd_prev >= signal_prev and macd_current < signal_current:
            signal = "SELL"
            histogram_strength = abs(hist_current) / current_price * 1000
            confidence = min(0.9, 0.5 + histogram_strength)
            reason = f"MACD Bearish Cross (Hist: {hist_current:.4f})"
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'macd': round(macd_current, 4),
                'signal': round(signal_current, 4),
                'histogram': round(hist_current, 4)
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita slow + signal + buffer para cálculo preciso"""
        return self.slow_period + self.signal_period + 10
    
    def get_parameter_space(self) -> Dict[str, list]:
        """
        Espacio de búsqueda para optimización.
        """
        return {
            'fast': [8, 12, 16],
            'slow': [20, 26, 30],
            'signal': [7, 9, 11]
        }
