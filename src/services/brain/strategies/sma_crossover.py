"""
SMA Crossover Strategy - V18
============================
Estrategia clásica de cruce de medias móviles.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
from .base import StrategyInterface, StrategyResult


class SmaCrossover(StrategyInterface):
    """
    Estrategia de Cruce de Medias Móviles Simples (SMA).
    
    Señales:
    - BUY: Cuando SMA rápida cruza por encima de SMA lenta (Golden Cross)
    - SELL: Cuando SMA rápida cruza por debajo de SMA lenta (Death Cross)
    
    Funciona bien en: Mercados con tendencia clara
    Falla en: Mercados laterales (whipsaw)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {'fast': int, 'slow': int}
                    Ej: {'fast': 10, 'slow': 30}
        """
        super().__init__(params)
        self.fast_period = params.get('fast', 10)
        self.slow_period = params.get('slow', 30)
        
        if self.fast_period >= self.slow_period:
            raise ValueError(f"Fast period ({self.fast_period}) debe ser menor que slow period ({self.slow_period})")
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa cruce de SMAs.
        
        Necesita al menos slow_period + 1 precios para detectar cruces.
        """
        prices = np.array(price_history + [current_price])
        
        if len(prices) < self.slow_period + 1:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # Calcular SMAs
        sma_fast = np.mean(prices[-self.fast_period:])
        sma_slow = np.mean(prices[-self.slow_period:])
        
        # SMAs del período anterior (para detectar cruce)
        sma_fast_prev = np.mean(prices[-(self.fast_period+1):-1])
        sma_slow_prev = np.mean(prices[-(self.slow_period+1):-1])
        
        # Detectar cruce
        signal = None
        confidence = 0.0
        reason = "Sin cruce"
        
        # Golden Cross: SMA rápida cruza hacia arriba
        if sma_fast_prev <= sma_slow_prev and sma_fast > sma_slow:
            signal = "BUY"
            # Confianza proporcional a la separación de las SMAs
            separation = (sma_fast - sma_slow) / sma_slow * 100
            confidence = min(0.9, 0.5 + abs(separation) / 2)
            reason = f"Golden Cross (SMA{self.fast_period} > SMA{self.slow_period})"
        
        # Death Cross: SMA rápida cruza hacia abajo
        elif sma_fast_prev >= sma_slow_prev and sma_fast < sma_slow:
            signal = "SELL"
            separation = (sma_slow - sma_fast) / sma_slow * 100
            confidence = min(0.9, 0.5 + abs(separation) / 2)
            reason = f"Death Cross (SMA{self.fast_period} < SMA{self.slow_period})"
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'sma_fast': round(sma_fast, 2),
                'sma_slow': round(sma_slow, 2),
                'separation_%': round((sma_fast - sma_slow) / sma_slow * 100, 3)
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita slow_period + 1 para detectar cruces"""
        return self.slow_period + 1
    
    def get_parameter_space(self) -> Dict[str, list]:
        """
        Espacio de búsqueda común para SMAs.
        Fast: 5-20, Slow: 20-50
        """
        return {
            'fast': [5, 10, 15, 20],
            'slow': [20, 30, 40, 50]
        }
