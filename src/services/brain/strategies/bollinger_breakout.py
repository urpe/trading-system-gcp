"""
Bollinger Bands Breakout Strategy - V18
========================================
Estrategia de ruptura de Bandas de Bollinger.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any
from .base import StrategyInterface, StrategyResult


class BollingerBreakout(StrategyInterface):
    """
    Estrategia de Ruptura de Bandas de Bollinger.
    
    Señales:
    - BUY: Precio rompe banda inferior hacia arriba (rebote desde sobreventa)
    - SELL: Precio rompe banda superior hacia abajo (corrección desde sobrecompra)
    
    Bandas de Bollinger = SMA ± (std_dev * num_std)
    
    Funciona bien en: Mercados con volatilidad moderada
    Falla en: Tendencias fuertes (las bandas se expanden continuamente)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {
                'period': int (típicamente 20),
                'num_std': float (típicamente 2.0)
            }
        """
        super().__init__(params)
        self.period = params.get('period', 20)
        self.num_std = params.get('num_std', 2.0)
    
    def calculate_bollinger_bands(self, prices: np.ndarray):
        """
        Calcula Bandas de Bollinger.
        
        Returns:
            tuple: (middle_band, upper_band, lower_band)
        """
        middle_band = np.mean(prices[-self.period:])
        std_dev = np.std(prices[-self.period:])
        
        upper_band = middle_band + (self.num_std * std_dev)
        lower_band = middle_band - (self.num_std * std_dev)
        
        return middle_band, upper_band, lower_band
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa rupturas de las bandas de Bollinger.
        """
        prices = np.array(price_history + [current_price])
        
        if len(prices) < self.period + 1:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente para Bollinger",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # Calcular bandas actuales
        middle, upper, lower = self.calculate_bollinger_bands(prices)
        
        # Precio anterior
        prev_price = prices[-2]
        
        signal = None
        confidence = 0.0
        reason = "Precio dentro de bandas"
        
        # Distancia del precio a las bandas (en % del ancho de banda)
        band_width = upper - lower
        
        # Señal de compra: Precio rebota desde banda inferior
        if prev_price <= lower and current_price > lower:
            signal = "BUY"
            # Confianza basada en qué tan cerca estuvo de la banda
            distance_ratio = (lower - prev_price) / band_width
            confidence = min(0.9, 0.6 + abs(distance_ratio) * 2)
            reason = f"Breakout Up from Lower Band (${current_price:.2f} > ${lower:.2f})"
        
        # Señal de venta: Precio cae desde banda superior
        elif prev_price >= upper and current_price < upper:
            signal = "SELL"
            distance_ratio = (prev_price - upper) / band_width
            confidence = min(0.9, 0.6 + abs(distance_ratio) * 2)
            reason = f"Breakout Down from Upper Band (${current_price:.2f} < ${upper:.2f})"
        
        # Calcular posición dentro de las bandas (%B indicator)
        percent_b = (current_price - lower) / band_width if band_width > 0 else 0.5
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'middle_band': round(middle, 2),
                'upper_band': round(upper, 2),
                'lower_band': round(lower, 2),
                'percent_b': round(percent_b, 3),  # 0 = en banda inferior, 1 = en banda superior
                'band_width_%': round(band_width / middle * 100, 2)
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita period + 1 para calcular bandas y detectar rupturas"""
        return self.period + 1
    
    def get_parameter_space(self) -> Dict[str, list]:
        """
        Espacio de búsqueda para optimización.
        """
        return {
            'period': [15, 20, 25],
            'num_std': [1.5, 2.0, 2.5, 3.0]
        }
