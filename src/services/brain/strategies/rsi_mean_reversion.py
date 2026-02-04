"""
RSI Mean Reversion Strategy - V18
==================================
Estrategia de reversión a la media basada en RSI.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any
from .base import StrategyInterface, StrategyResult


class RsiMeanReversion(StrategyInterface):
    """
    Estrategia de Reversión a la Media con RSI.
    
    Señales:
    - BUY: RSI < oversold (típicamente 30) - activo sobrevendido
    - SELL: RSI > overbought (típicamente 70) - activo sobrecomprado
    
    Funciona bien en: Mercados laterales con reversión
    Falla en: Tendencias fuertes (puede quedarse vendido en bull market)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {
                'period': int (típicamente 14),
                'oversold': int (típicamente 30),
                'overbought': int (típicamente 70)
            }
        """
        super().__init__(params)
        self.period = params.get('period', 14)
        self.oversold = params.get('oversold', 30)
        self.overbought = params.get('overbought', 70)
    
    def calculate_rsi(self, prices: np.ndarray) -> float:
        """
        Calcula RSI usando método estándar de Wilder.
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        if len(prices) < self.period + 1:
            return 50.0  # Neutral si no hay suficientes datos
        
        # Calcular cambios de precio
        deltas = np.diff(prices)
        
        # Separar ganancias y pérdidas
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Promedio de ganancias y pérdidas (método EMA de Wilder)
        avg_gain = np.mean(gains[-self.period:])
        avg_loss = np.mean(losses[-self.period:])
        
        if avg_loss == 0:
            return 100.0  # Todas ganancias = RSI máximo
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa condiciones de sobrecompra/sobreventa con RSI.
        """
        prices = np.array(price_history + [current_price])
        
        if len(prices) < self.period + 1:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente para RSI",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        rsi = self.calculate_rsi(prices)
        
        signal = None
        confidence = 0.0
        reason = f"RSI neutral ({rsi:.1f})"
        
        # Señal de compra (sobrevendido)
        if rsi < self.oversold:
            signal = "BUY"
            # Confianza aumenta cuanto más bajo es el RSI
            confidence = min(0.95, (self.oversold - rsi) / self.oversold + 0.5)
            reason = f"RSI Oversold ({rsi:.1f} < {self.oversold})"
        
        # Señal de venta (sobrecomprado)
        elif rsi > self.overbought:
            signal = "SELL"
            # Confianza aumenta cuanto más alto es el RSI
            confidence = min(0.95, (rsi - self.overbought) / (100 - self.overbought) + 0.5)
            reason = f"RSI Overbought ({rsi:.1f} > {self.overbought})"
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'rsi': round(rsi, 2),
                'oversold_level': self.oversold,
                'overbought_level': self.overbought
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita period + 1 para calcular RSI correctamente"""
        return self.period + 1
    
    def get_parameter_space(self) -> Dict[str, list]:
        """
        Espacio de búsqueda para optimización.
        """
        return {
            'period': [7, 14, 21],
            'oversold': [20, 25, 30],
            'overbought': [70, 75, 80]
        }
