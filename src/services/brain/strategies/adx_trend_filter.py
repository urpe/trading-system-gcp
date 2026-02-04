"""
ADX Trend Filter Strategy - V19
================================
Filtro puro de tendencia - Solo opera cuando ADX > threshold.

Basado en el trabajo de Welles Wilder Jr. (1978).
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any
from .base import StrategyInterface, StrategyResult


class AdxTrendFilter(StrategyInterface):
    """
    Estrategia ADX Trend Filter - Opera SOLO cuando hay tendencia fuerte.
    
    ADX (Average Directional Index) mide la FUERZA de una tendencia:
    - ADX > 30: Tendencia MUY fuerte → Operar agresivamente
    - ADX 25-30: Tendencia fuerte → Operar
    - ADX 20-25: Tendencia débil → Precaución
    - ADX < 20: Sin tendencia → NO operar
    
    Señales:
    - BUY: DI+ > DI- AND ADX > threshold (tendencia alcista fuerte)
    - SELL: DI- > DI+ AND ADX > threshold (tendencia bajista fuerte)
    - NO SIGNAL: ADX < threshold (mercado lateral)
    
    Funciona bien en: Cualquier condición (es un filtro)
    Falla en: No genera señales en mercados laterales (diseño intencional)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {
                'adx_period': int (default 14),
                'adx_threshold': int (default 25)
            }
        """
        super().__init__(params)
        self.adx_period = params.get('adx_period', 14)
        self.adx_threshold = params.get('adx_threshold', 25)
    
    def calculate_ema(self, values: np.ndarray, period: int) -> float:
        """Calcula EMA para smoothing"""
        if len(values) < period:
            return np.mean(values)
        
        multiplier = 2 / (period + 1)
        ema = values[0]
        
        for value in values[1:]:
            ema = (value - ema) * multiplier + ema
        
        return ema
    
    def calculate_adx_from_prices(self, prices: np.ndarray, period: int = 14) -> tuple:
        """
        Calcula ADX, DI+, DI- usando solo precios de cierre.
        (Versión simplificada sin high/low)
        
        Returns:
            Tuple[adx, di_plus, di_minus]
        """
        if len(prices) < period + 1:
            return 0.0, 0.0, 0.0
        
        # 1. Calcular movimientos direccionales
        price_changes = np.diff(prices)
        
        # +DM: Movimientos alcistas
        dm_plus = np.where(price_changes > 0, price_changes, 0)
        
        # -DM: Movimientos bajistas (valor absoluto)
        dm_minus = np.where(price_changes < 0, -price_changes, 0)
        
        # 2. Calcular True Range simplificado
        tr = np.abs(price_changes)
        
        # 3. Smooth +DM, -DM y TR
        smoothed_dm_plus = self.calculate_ema(dm_plus[-period:], period)
        smoothed_dm_minus = self.calculate_ema(dm_minus[-period:], period)
        smoothed_tr = self.calculate_ema(tr[-period:], period)
        
        if smoothed_tr == 0:
            return 0.0, 0.0, 0.0
        
        # 4. Calcular DI+ y DI-
        di_plus = (smoothed_dm_plus / smoothed_tr) * 100
        di_minus = (smoothed_dm_minus / smoothed_tr) * 100
        
        # 5. Calcular DX (Directional Index)
        di_sum = di_plus + di_minus
        if di_sum == 0:
            return 0.0, di_plus, di_minus
        
        dx = abs(di_plus - di_minus) / di_sum * 100
        
        # 6. ADX = Smooth de DX
        # Para simplificar en tiempo real, usamos directamente DX
        # (Idealmente se debería promediar múltiples DX)
        adx = dx
        
        return adx, di_plus, di_minus
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa si hay tendencia fuerte (ADX filter).
        """
        prices = np.array(price_history + [current_price])
        
        if len(prices) < self.adx_period + 2:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente para ADX",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # Calcular ADX y Directional Indicators
        adx, di_plus, di_minus = self.calculate_adx_from_prices(
            prices[-self.adx_period-1:], 
            self.adx_period
        )
        
        signal = None
        confidence = 0.0
        reason = f"ADX={adx:.1f} < {self.adx_threshold} (sin tendencia)"
        
        # FILTRO: Solo opera si ADX > threshold
        if adx >= self.adx_threshold:
            
            # Tendencia ALCISTA: DI+ > DI-
            if di_plus > di_minus:
                signal = "BUY"
                
                # Confianza basada en:
                # 1. Nivel de ADX (más alto = más confianza)
                # 2. Separación entre DI+ y DI-
                
                adx_strength = min((adx - self.adx_threshold) / 30, 1.0)  # 0-1
                di_separation = abs(di_plus - di_minus) / 100  # 0-1
                
                confidence = 0.50 + (adx_strength * 0.25) + (di_separation * 0.20)
                confidence = min(confidence, 0.95)
                
                reason = f"Strong Uptrend (ADX={adx:.1f}, DI+={di_plus:.1f} > DI-={di_minus:.1f})"
            
            # Tendencia BAJISTA: DI- > DI+
            elif di_minus > di_plus:
                signal = "SELL"
                
                adx_strength = min((adx - self.adx_threshold) / 30, 1.0)
                di_separation = abs(di_plus - di_minus) / 100
                
                confidence = 0.50 + (adx_strength * 0.25) + (di_separation * 0.20)
                confidence = min(confidence, 0.95)
                
                reason = f"Strong Downtrend (ADX={adx:.1f}, DI-={di_minus:.1f} > DI+={di_plus:.1f})"
            
            else:
                reason = f"ADX high ({adx:.1f}) but DI inconclusive"
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'adx': round(adx, 2),
                'di_plus': round(di_plus, 2),
                'di_minus': round(di_minus, 2),
                'trend_strength': 'very_strong' if adx > 40 else 'strong' if adx > 30 else 'moderate' if adx > 20 else 'weak'
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita adx_period + 2"""
        return self.adx_period + 3
    
    def get_parameter_space(self) -> Dict[str, list]:
        """Espacio de búsqueda"""
        return {
            'adx_period': [10, 14, 20],
            'adx_threshold': [20, 25, 30]
        }
