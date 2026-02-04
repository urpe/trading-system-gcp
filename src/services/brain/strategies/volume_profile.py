"""
Volume Profile Strategy (Simplified) - V19
===========================================
Identifica POC (Point of Control) - nivel de precio con mayor volumen.

Basado en Market Profile (J. Peter Steidlmayer, 1985) y Volume Profile.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter
from .base import StrategyInterface, StrategyResult


class VolumeProfileStrategy(StrategyInterface):
    """
    Estrategia basada en Volume Profile (versión simplificada).
    
    Concepto:
    - POC (Point of Control): Nivel de precio donde se negoció MÁS volumen
    - El POC actúa como imán: los precios tienden a volver a él
    
    Lógica Simplificada (sin datos de volumen real):
    - Divide rango de precios en "bins"
    - Cuenta cuántas veces el precio visitó cada bin
    - El bin más visitado = POC estimado
    
    Señales:
    - BUY: Precio rebota en/cerca del POC desde abajo
    - SELL: Precio rechaza POC desde arriba
    
    Funciona bien en: Mercados laterales con niveles claros
    Falla en: Tendencias fuertes (POC queda atrás)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {
                'lookback_period': int (default 100),
                'num_bins': int (default 20),
                'poc_proximity_pct': float (default 0.5)
            }
        """
        super().__init__(params)
        self.lookback_period = params.get('lookback_period', 100)
        self.num_bins = params.get('num_bins', 20)
        self.poc_proximity_pct = params.get('poc_proximity_pct', 0.5)  # 0.5% de cercanía al POC
    
    def calculate_poc(self, price_history: List[float]) -> Dict[str, Any]:
        """
        Calcula el POC (Point of Control) usando histograma de precios.
        
        Returns:
            Dict con poc_price, value_area_high, value_area_low
        """
        if len(price_history) < self.lookback_period:
            prices = price_history
        else:
            prices = price_history[-self.lookback_period:]
        
        prices_array = np.array(prices)
        
        # Crear bins de precios
        min_price = np.min(prices_array)
        max_price = np.max(prices_array)
        
        if min_price == max_price:
            return {
                'poc_price': min_price,
                'value_area_high': min_price,
                'value_area_low': min_price,
                'histogram': {}
            }
        
        # Dividir rango en bins
        bins = np.linspace(min_price, max_price, self.num_bins + 1)
        
        # Contar visitas a cada bin
        histogram, bin_edges = np.histogram(prices_array, bins=bins)
        
        # POC = Bin con más visitas
        poc_bin_index = np.argmax(histogram)
        poc_price = (bin_edges[poc_bin_index] + bin_edges[poc_bin_index + 1]) / 2
        
        # Value Area = 70% del volumen alrededor del POC
        # Simplificado: ±2 bins del POC
        value_area_low_index = max(0, poc_bin_index - 2)
        value_area_high_index = min(len(bin_edges) - 2, poc_bin_index + 2)
        
        value_area_low = bin_edges[value_area_low_index]
        value_area_high = bin_edges[value_area_high_index + 1]
        
        return {
            'poc_price': poc_price,
            'value_area_high': value_area_high,
            'value_area_low': value_area_low,
            'histogram': dict(zip(bin_edges[:-1], histogram))
        }
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa rebotes/rechazos en el POC.
        """
        if len(price_history) < 20:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # Calcular POC
        poc_data = self.calculate_poc(price_history)
        poc_price = poc_data['poc_price']
        va_high = poc_data['value_area_high']
        va_low = poc_data['value_area_low']
        
        # Distancia del precio actual al POC
        distance_to_poc_pct = abs(current_price - poc_price) / poc_price * 100
        
        signal = None
        confidence = 0.0
        reason = "Precio lejos del POC"
        
        prev_price = price_history[-1]
        
        # SEÑAL BUY: Rebote en POC desde abajo
        # Condición: Precio estaba debajo/en POC y ahora rebota hacia arriba
        if distance_to_poc_pct < self.poc_proximity_pct:
            
            # Movimiento hacia arriba cerca del POC
            if current_price > poc_price and prev_price <= poc_price:
                signal = "BUY"
                
                # Confianza basada en:
                # 1. Qué tan cerca está del POC
                # 2. Si está dentro del Value Area
                
                proximity_factor = 1 - (distance_to_poc_pct / self.poc_proximity_pct)
                in_value_area = va_low <= current_price <= va_high
                
                base_confidence = 0.55
                base_confidence += proximity_factor * 0.20
                if in_value_area:
                    base_confidence += 0.15
                
                confidence = min(base_confidence, 0.85)
                reason = f"Volume Profile Bounce at POC (dist: {distance_to_poc_pct:.2f}%)"
            
            # SEÑAL SELL: Rechazo en POC desde arriba
            elif current_price < poc_price and prev_price >= poc_price:
                signal = "SELL"
                
                proximity_factor = 1 - (distance_to_poc_pct / self.poc_proximity_pct)
                in_value_area = va_low <= current_price <= va_high
                
                base_confidence = 0.55
                base_confidence += proximity_factor * 0.20
                if in_value_area:
                    base_confidence += 0.15
                
                confidence = min(base_confidence, 0.85)
                reason = f"Volume Profile Rejection at POC (dist: {distance_to_poc_pct:.2f}%)"
        
        # SEÑAL SECUNDARIA: Breakout del Value Area
        elif current_price > va_high and prev_price <= va_high:
            signal = "BUY"
            confidence = 0.45
            reason = "Breakout above Value Area High"
        
        elif current_price < va_low and prev_price >= va_low:
            signal = "SELL"
            confidence = 0.45
            reason = "Breakdown below Value Area Low"
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'poc_price': round(poc_price, 2),
                'value_area_high': round(va_high, 2),
                'value_area_low': round(va_low, 2),
                'distance_to_poc_pct': round(distance_to_poc_pct, 2),
                'price_position': 'at_poc' if distance_to_poc_pct < 0.5 else 'above_va' if current_price > va_high else 'below_va' if current_price < va_low else 'in_va'
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita lookback_period"""
        return max(20, self.lookback_period)
    
    def get_parameter_space(self) -> Dict[str, list]:
        """Espacio de búsqueda"""
        return {
            'lookback_period': [50, 100, 150],
            'num_bins': [15, 20, 25],
            'poc_proximity_pct': [0.3, 0.5, 0.7]
        }
