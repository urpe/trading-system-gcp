"""
Keltner Channels Strategy - V19
================================
Bandas basadas en ATR (más robustas que Bollinger para volatilidad).

Desarrollado por Chester W. Keltner (1960), modernizado por Linda Bradford Raschke (1980s).
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any
from .base import StrategyInterface, StrategyResult


class KeltnerChannels(StrategyInterface):
    """
    Estrategia de Keltner Channels - Similar a Bollinger pero usando ATR.
    
    Cálculo:
    - Middle Line: EMA del precio
    - Upper Band: EMA + (ATR * multiplier)
    - Lower Band: EMA - (ATR * multiplier)
    
    Señales:
    - BUY: Precio toca/rebota en banda inferior
    - SELL: Precio toca/rebota en banda superior
    
    Funciona bien en: Mercados laterales con volatilidad moderada
    Falla en: Tendencias fuertes (genera señales contrarias prematuras)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {
                'ema_period': int (default 20),
                'atr_period': int (default 10),
                'atr_multiplier': float (default 2.0)
            }
        """
        super().__init__(params)
        self.ema_period = params.get('ema_period', 20)
        self.atr_period = params.get('atr_period', 10)
        self.atr_multiplier = params.get('atr_multiplier', 2.0)
    
    def calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_atr_simple(self, prices: np.ndarray, period: int) -> float:
        """
        Calcula ATR simplificado usando solo precios de cierre.
        (Versión completa requiere high/low/close)
        """
        if len(prices) < period + 1:
            return 0.0
        
        # True Range simplificado: |precio_actual - precio_anterior|
        true_ranges = np.abs(np.diff(prices[-period-1:]))
        
        return np.mean(true_ranges)
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa señales de Keltner Channels.
        """
        prices = np.array(price_history + [current_price])
        
        required = max(self.ema_period, self.atr_period) + 2
        if len(prices) < required:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # 1. Calcular línea media (EMA)
        middle_line = self.calculate_ema(prices[-self.ema_period:], self.ema_period)
        
        # 2. Calcular ATR
        atr = self.calculate_atr_simple(prices, self.atr_period)
        
        # 3. Calcular bandas
        upper_band = middle_line + (atr * self.atr_multiplier)
        lower_band = middle_line - (atr * self.atr_multiplier)
        
        # 4. Determinar posición del precio
        band_width = upper_band - lower_band
        if band_width == 0:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Bandas colapsadas (volatilidad = 0)",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # Posición normalizada: -1 (banda inferior) a +1 (banda superior)
        position_in_bands = (current_price - middle_line) / (band_width / 2)
        
        signal = None
        confidence = 0.0
        reason = "Precio en rango medio"
        
        # Precio previo para detectar rebotes
        prev_price = prices[-2]
        prev_middle = self.calculate_ema(prices[-self.ema_period-1:-1], self.ema_period)
        prev_atr = self.calculate_atr_simple(prices[:-1], self.atr_period)
        prev_upper = prev_middle + (prev_atr * self.atr_multiplier)
        prev_lower = prev_middle - (prev_atr * self.atr_multiplier)
        
        # SEÑAL BUY: Rebote en banda inferior
        # Condición: Precio tocó/perforó banda inferior y ahora rebota hacia arriba
        if prev_price <= prev_lower and current_price > lower_band:
            signal = "BUY"
            
            # Confianza basada en:
            # 1. Qué tan cerca está de la banda inferior
            # 2. Fuerza del rebote
            
            distance_from_lower = abs(position_in_bands + 1) / 2  # 0 = en banda, 1 = lejos
            bounce_strength = (current_price - prev_price) / prev_price * 100
            
            base_confidence = 0.60
            if distance_from_lower < 0.2:  # Muy cerca de banda
                base_confidence += 0.15
            if bounce_strength > 0.5:  # Rebote fuerte
                base_confidence += 0.15
            
            confidence = min(base_confidence, 0.90)
            reason = f"Keltner Bounce from Lower Band (position: {position_in_bands:.2f})"
        
        # SEÑAL SELL: Rechazo en banda superior
        elif prev_price >= prev_upper and current_price < upper_band:
            signal = "SELL"
            
            distance_from_upper = abs(position_in_bands - 1) / 2
            rejection_strength = abs(current_price - prev_price) / prev_price * 100
            
            base_confidence = 0.60
            if distance_from_upper < 0.2:
                base_confidence += 0.15
            if rejection_strength > 0.5:
                base_confidence += 0.15
            
            confidence = min(base_confidence, 0.90)
            reason = f"Keltner Rejection from Upper Band (position: {position_in_bands:.2f})"
        
        # SEÑAL ADICIONAL: Breakout (precio sale de bandas con fuerza)
        elif current_price > upper_band and position_in_bands > 1.2:
            signal = "BUY"
            confidence = 0.50
            reason = f"Keltner Bullish Breakout (above upper band)"
        
        elif current_price < lower_band and position_in_bands < -1.2:
            signal = "SELL"
            confidence = 0.50
            reason = f"Keltner Bearish Breakdown (below lower band)"
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'middle_line': round(middle_line, 2),
                'upper_band': round(upper_band, 2),
                'lower_band': round(lower_band, 2),
                'atr': round(atr, 4),
                'position': round(position_in_bands, 2),  # -1 a +1
                'band_width_pct': round((band_width / middle_line) * 100, 2)
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita max(ema, atr) + buffer"""
        return max(self.ema_period, self.atr_period) + 5
    
    def get_parameter_space(self) -> Dict[str, list]:
        """Espacio de búsqueda"""
        return {
            'ema_period': [15, 20, 25],
            'atr_period': [10, 14, 20],
            'atr_multiplier': [1.5, 2.0, 2.5]
        }
