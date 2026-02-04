"""
Market Context Analyzer - V18.5
================================
Analiza contexto del mercado para filtrar señales.
"""

import numpy as np
from enum import Enum
from typing import List


class MarketRegime(Enum):
    """Régimen de mercado"""
    STRONG_UPTREND = "strong_uptrend"
    WEAK_UPTREND = "weak_uptrend"
    SIDEWAYS = "sideways"
    WEAK_DOWNTREND = "weak_downtrend"
    STRONG_DOWNTREND = "strong_downtrend"


class MarketContextAnalyzer:
    """
    Analiza contexto del mercado para mejorar señales.
    
    Detecta:
    - Trending (up/down) vs Sideways
    - Volatilidad (alta/baja)
    - Momentum strength
    """
    
    @staticmethod
    def detect_regime(price_history: List[float], lookback: int = 50) -> MarketRegime:
        """
        Detecta régimen de mercado usando ADX simplificado y pendiente.
        
        Args:
            price_history: Lista de precios históricos
            lookback: Períodos para análisis
        
        Returns:
            MarketRegime
        """
        if len(price_history) < lookback:
            return MarketRegime.SIDEWAYS
        
        prices = np.array(price_history[-lookback:])
        
        # 1. Calcular pendiente de regresión lineal
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices, 1)
        slope_pct = (slope / prices[0]) * 100
        
        # 2. Calcular volatilidad (std deviation como % del precio)
        volatility = np.std(prices) / np.mean(prices) * 100
        
        # 3. Clasificar régimen
        if slope_pct > 0.5 and volatility < 3:
            return MarketRegime.STRONG_UPTREND
        elif slope_pct > 0.1:
            return MarketRegime.WEAK_UPTREND
        elif slope_pct < -0.5 and volatility < 3:
            return MarketRegime.STRONG_DOWNTREND
        elif slope_pct < -0.1:
            return MarketRegime.WEAK_DOWNTREND
        else:
            return MarketRegime.SIDEWAYS
    
    @staticmethod
    def should_trade_in_regime(signal_type: str, regime: MarketRegime) -> bool:
        """
        Filtra señales según contexto de mercado.
        
        Reglas:
        - BUY: Solo en uptrend o sideways con momentum up
        - SELL: Solo en downtrend o sideways con momentum down
        - NO operar en sideways extremo (whipsaw)
        """
        if signal_type == "BUY":
            return regime in [MarketRegime.STRONG_UPTREND, MarketRegime.WEAK_UPTREND]
        
        elif signal_type == "SELL":
            return regime in [MarketRegime.STRONG_DOWNTREND, MarketRegime.WEAK_DOWNTREND]
        
        return False
    
    @staticmethod
    def calculate_volatility(price_history: List[float], period: int = 20) -> float:
        """
        Calcula volatilidad como % del precio medio.
        
        Returns:
            Volatilidad en porcentaje
        """
        if len(price_history) < period:
            return 0.0
        
        prices = np.array(price_history[-period:])
        return (np.std(prices) / np.mean(prices)) * 100
    
    @staticmethod
    def is_high_volatility(price_history: List[float], threshold: float = 5.0) -> bool:
        """
        Detecta si hay volatilidad alta (>5% por defecto).
        En alta volatilidad, aumentar stop-loss.
        """
        volatility = MarketContextAnalyzer.calculate_volatility(price_history)
        return volatility > threshold
