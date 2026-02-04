"""
Ichimoku Cloud Strategy - V19
==============================
Sistema de Ichimoku Kinko Hyo ("One glance equilibrium chart").

Desarrollado por Goichi Hosoda (1968) - Japón.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from .base import StrategyInterface, StrategyResult


class IchimokuCloud(StrategyInterface):
    """
    Estrategia de Ichimoku Cloud - Sistema japonés de análisis de tendencia.
    
    Componentes:
    - Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    - Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    - Senkou Span A: (Tenkan + Kijun) / 2, displaced 26 periods ahead
    - Senkou Span B: (52-period high + 52-period low) / 2, displaced 26 ahead
    - Kumo (Cloud): Área entre Senkou A y Senkou B
    
    Señales:
    - BUY: Precio rompe Kumo al alza (bullish breakout)
    - SELL: Precio rompe Kumo a la baja (bearish breakdown)
    
    Funciona bien en: Tendencias fuertes con momentum
    Falla en: Mercados muy laterales (señales tardías)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: {
                'tenkan_period': int (default 9),
                'kijun_period': int (default 26),
                'senkou_b_period': int (default 52)
            }
        """
        super().__init__(params)
        self.tenkan_period = params.get('tenkan_period', 9)
        self.kijun_period = params.get('kijun_period', 26)
        self.senkou_b_period = params.get('senkou_b_period', 52)
    
    def calculate_donchian(self, prices: np.ndarray, period: int) -> float:
        """
        Calcula Donchian Midpoint: (Max + Min) / 2
        """
        if len(prices) < period:
            return np.mean(prices)
        
        window = prices[-period:]
        return (np.max(window) + np.min(window)) / 2
    
    def calculate_ichimoku_components(self, price_history: List[float]) -> Dict[str, float]:
        """
        Calcula todos los componentes de Ichimoku.
        
        Returns:
            Dict con tenkan, kijun, senkou_a, senkou_b
        """
        prices = np.array(price_history)
        
        # Tenkan-sen (Conversion Line) - 9 períodos
        tenkan = self.calculate_donchian(prices, self.tenkan_period)
        
        # Kijun-sen (Base Line) - 26 períodos
        kijun = self.calculate_donchian(prices, self.kijun_period)
        
        # Senkou Span A: (Tenkan + Kijun) / 2
        senkou_a = (tenkan + kijun) / 2
        
        # Senkou Span B: 52-period Donchian
        senkou_b = self.calculate_donchian(prices, self.senkou_b_period)
        
        return {
            'tenkan': tenkan,
            'kijun': kijun,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b,
            'kumo_top': max(senkou_a, senkou_b),
            'kumo_bottom': min(senkou_a, senkou_b)
        }
    
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa señales de Ichimoku Cloud.
        """
        if len(price_history) < self.senkou_b_period:
            return StrategyResult(
                signal=None,
                confidence=0.0,
                reason="Historial insuficiente para Ichimoku",
                indicators={},
                timestamp=datetime.utcnow()
            )
        
        # Calcular componentes actuales y previos
        current_components = self.calculate_ichimoku_components(price_history + [current_price])
        prev_components = self.calculate_ichimoku_components(price_history)
        
        signal = None
        confidence = 0.0
        reason = "Sin señal clara"
        
        kumo_top = current_components['kumo_top']
        kumo_bottom = current_components['kumo_bottom']
        
        prev_price = price_history[-1]
        
        # Señal BULLISH: Precio rompe Kumo al alza
        if prev_price <= prev_components['kumo_top'] and current_price > kumo_top:
            signal = "BUY"
            
            # Confianza basada en:
            # 1. Tenkan > Kijun (confirmación de momentum alcista)
            # 2. Distancia del precio sobre la nube
            
            tenkan_kijun_bullish = current_components['tenkan'] > current_components['kijun']
            cloud_distance = ((current_price - kumo_top) / kumo_top) * 100
            
            base_confidence = 0.65
            if tenkan_kijun_bullish:
                base_confidence += 0.15
            if cloud_distance > 1:  # Breakout fuerte (>1%)
                base_confidence += min(cloud_distance / 5, 0.15)
            
            confidence = min(base_confidence, 0.95)
            reason = f"Ichimoku Bullish Breakout (Kumo penetration: {cloud_distance:.2f}%)"
        
        # Señal BEARISH: Precio rompe Kumo a la baja
        elif prev_price >= prev_components['kumo_bottom'] and current_price < kumo_bottom:
            signal = "SELL"
            
            tenkan_kijun_bearish = current_components['tenkan'] < current_components['kijun']
            cloud_distance = ((kumo_bottom - current_price) / kumo_bottom) * 100
            
            base_confidence = 0.65
            if tenkan_kijun_bearish:
                base_confidence += 0.15
            if cloud_distance > 1:
                base_confidence += min(cloud_distance / 5, 0.15)
            
            confidence = min(base_confidence, 0.95)
            reason = f"Ichimoku Bearish Breakdown (Kumo penetration: {cloud_distance:.2f}%)"
        
        # Señal de CONFIRMACIÓN: Precio ya está sobre/bajo nube y Tenkan cruza Kijun
        else:
            # TK Cross (Tenkan-Kijun Cross) - Señal secundaria
            tenkan_prev = prev_components['tenkan']
            kijun_prev = prev_components['kijun']
            tenkan_curr = current_components['tenkan']
            kijun_curr = current_components['kijun']
            
            # Golden Cross (encima de la nube)
            if (tenkan_prev <= kijun_prev and tenkan_curr > kijun_curr and 
                current_price > kumo_top):
                signal = "BUY"
                confidence = 0.55
                reason = "Ichimoku TK Golden Cross (above cloud)"
            
            # Death Cross (debajo de la nube)
            elif (tenkan_prev >= kijun_prev and tenkan_curr < kijun_curr and 
                  current_price < kumo_bottom):
                signal = "SELL"
                confidence = 0.55
                reason = "Ichimoku TK Death Cross (below cloud)"
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                'tenkan': round(current_components['tenkan'], 2),
                'kijun': round(current_components['kijun'], 2),
                'senkou_a': round(current_components['senkou_a'], 2),
                'senkou_b': round(current_components['senkou_b'], 2),
                'kumo_top': round(kumo_top, 2),
                'kumo_bottom': round(kumo_bottom, 2),
                'price_vs_cloud': 'above' if current_price > kumo_top else 'below' if current_price < kumo_bottom else 'inside'
            },
            timestamp=datetime.utcnow()
        )
    
    def get_required_history(self) -> int:
        """Necesita senkou_b_period + buffer"""
        return self.senkou_b_period + 5
    
    def get_parameter_space(self) -> Dict[str, list]:
        """
        Espacio de búsqueda para optimización.
        """
        return {
            'tenkan_period': [7, 9, 12],
            'kijun_period': [20, 26, 30],
            'senkou_b_period': [44, 52, 60]
        }
