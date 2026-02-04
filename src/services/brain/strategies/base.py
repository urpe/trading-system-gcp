"""
Base Strategy Interface - V18
=============================
Interfaz abstracta para todas las estrategias de trading.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class StrategyResult:
    """Resultado de evaluación de una estrategia"""
    signal: Optional[str]  # 'BUY', 'SELL', or None
    confidence: float  # 0.0 - 1.0
    reason: str
    indicators: Dict[str, float]  # Valores de indicadores usados
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para Redis"""
        return {
            'signal': self.signal,
            'confidence': self.confidence,
            'reason': self.reason,
            'indicators': self.indicators,
            'timestamp': self.timestamp.isoformat()
        }


class StrategyInterface(ABC):
    """
    Interfaz base para todas las estrategias.
    
    Cada estrategia debe implementar:
    1. evaluate() - Evalúa precio actual y genera señal
    2. get_required_history() - Cuántos períodos necesita
    3. get_parameter_space() - Espacio de búsqueda para optimización
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: Parámetros de la estrategia (ej: {'fast': 10, 'slow': 30})
        """
        self.params = params
        self.name = self.__class__.__name__
    
    @abstractmethod
    def evaluate(self, current_price: float, price_history: list) -> StrategyResult:
        """
        Evalúa si debe generar señal de compra/venta.
        
        Args:
            current_price: Precio actual del activo
            price_history: Lista de precios históricos [más antiguo -> más reciente]
        
        Returns:
            StrategyResult con señal y metadatos
        """
        pass
    
    @abstractmethod
    def get_required_history(self) -> int:
        """
        Retorna cuántos períodos históricos necesita la estrategia.
        Ej: SMA(50) necesita 50 períodos.
        """
        pass
    
    @abstractmethod
    def get_parameter_space(self) -> Dict[str, list]:
        """
        Retorna el espacio de búsqueda para optimización.
        
        Ejemplo:
        {
            'fast': [5, 10, 15, 20],
            'slow': [20, 30, 40, 50]
        }
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.name}({self.params})"
