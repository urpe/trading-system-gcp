"""
Smart Exits Manager - V20
==========================
Sistema de salidas inteligentes para maximizar ganancias y minimizar pérdidas.

Características:
- Trailing Stop Loss dinámico
- Take Profit basado en ATR
- Breakeven Stop automático
- Partial Profit Taking
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartExits")


@dataclass
class ExitConfig:
    """Configuración del sistema de exits"""
    trailing_stop_pct: float = 0.5  # Distancia del trailing stop en %
    trailing_activation_pct: float = 1.0  # Profit % para activar trailing
    atr_multiplier_tp: float = 3.0  # Multiplicador ATR para Take Profit (aumentado de 2.0)
    breakeven_activation_pct: float = 0.5  # Profit % para mover a breakeven
    partial_profit_pct: float = 50.0  # % de posición a cerrar en partial
    partial_profit_target_multiplier: float = 1.5  # Multiplicador ATR para partial (aumentado)


@dataclass
class ExitSignal:
    """Señal de salida"""
    reason: str
    exit_type: str  # 'TRAILING_STOP', 'ATR_TP', 'BREAKEVEN', 'PARTIAL', 'STOP_LOSS'
    target_price: Optional[float] = None
    partial_pct: Optional[float] = None  # Si es partial, qué % cerrar


@dataclass
class PositionState:
    """Estado de una posición para tracking de exits"""
    symbol: str
    entry_price: float
    entry_timestamp: datetime
    amount: float
    
    # Tracking de máximos
    highest_price_reached: float
    
    # Trailing stop
    trailing_stop_active: bool = False
    trailing_stop_price: Optional[float] = None
    
    # Breakeven
    breakeven_active: bool = False
    
    # Partial profit
    partial_executed: bool = False
    remaining_amount: float = None
    
    def __post_init__(self):
        if self.remaining_amount is None:
            self.remaining_amount = self.amount
        if self.highest_price_reached is None:
            self.highest_price_reached = self.entry_price


class SmartExitManager:
    """
    Gestor inteligente de salidas que maximiza el ratio R:R.
    
    Estrategias:
    1. Trailing Stop: Deja correr ganancias mientras protege profits
    2. ATR Take Profit: Objetivos realistas basados en volatilidad
    3. Breakeven Stop: Elimina riesgo cuando hay profit inicial
    4. Partial Profit: Asegura ganancias mientras deja correr winners
    """
    
    def __init__(self, config: ExitConfig = None):
        self.config = config or ExitConfig()
        logger.info(f"SmartExitManager initialized: {self.config}")
    
    def evaluate_exit(
        self,
        position: PositionState,
        current_price: float,
        current_atr: float,
        ohlc_current: Dict = None
    ) -> Optional[ExitSignal]:
        """
        Evalúa si debe generar señal de salida.
        
        Orden de prioridad:
        1. Trailing Stop Loss (si activo)
        2. ATR Take Profit
        3. Partial Profit (si no ejecutado)
        4. Breakeven Stop (si no hay trailing)
        
        Args:
            position: Estado de la posición
            current_price: Precio actual
            current_atr: ATR actual
            ohlc_current: OHLC de la vela actual (opcional)
        
        Returns:
            ExitSignal si debe salir, None si mantener
        """
        # Actualizar precio máximo alcanzado
        if current_price > position.highest_price_reached:
            position.highest_price_reached = current_price
        
        # Calcular profit actual
        profit_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        profit_amount = (current_price - position.entry_price) * position.remaining_amount
        
        # 1. CHECK TRAILING STOP LOSS
        if position.trailing_stop_active and position.trailing_stop_price:
            if current_price <= position.trailing_stop_price:
                return ExitSignal(
                    reason=f"Trailing Stop Hit ({profit_pct:.2f}%)",
                    exit_type='TRAILING_STOP',
                    target_price=position.trailing_stop_price
                )
            
            # Actualizar trailing stop si el precio sigue subiendo
            new_trailing = position.highest_price_reached * (1 - self.config.trailing_stop_pct / 100)
            if new_trailing > position.trailing_stop_price:
                position.trailing_stop_price = new_trailing
                logger.debug(f"Trailing stop updated: ${new_trailing:.2f}")
        
        # 2. CHECK ATR TAKE PROFIT
        atr_tp_price = position.entry_price + (self.config.atr_multiplier_tp * current_atr)
        if current_price >= atr_tp_price:
            return ExitSignal(
                reason=f"ATR Take Profit ({profit_pct:.2f}%)",
                exit_type='ATR_TP',
                target_price=atr_tp_price
            )
        
        # 3. CHECK PARTIAL PROFIT
        if not position.partial_executed:
            partial_target = position.entry_price + (self.config.partial_profit_target_multiplier * current_atr)
            
            if current_price >= partial_target:
                position.partial_executed = True
                return ExitSignal(
                    reason=f"Partial Profit ({profit_pct:.2f}%)",
                    exit_type='PARTIAL',
                    target_price=current_price,
                    partial_pct=self.config.partial_profit_pct
                )
        
        # 4. ACTIVATE TRAILING STOP
        if not position.trailing_stop_active:
            if profit_pct >= self.config.trailing_activation_pct:
                position.trailing_stop_active = True
                position.trailing_stop_price = position.highest_price_reached * (1 - self.config.trailing_stop_pct / 100)
                logger.info(f"{position.symbol}: Trailing stop activated at ${position.trailing_stop_price:.2f}")
        
        # 5. ACTIVATE BREAKEVEN STOP (solo si trailing no está activo)
        if not position.breakeven_active and not position.trailing_stop_active:
            if profit_pct >= self.config.breakeven_activation_pct:
                position.breakeven_active = True
                logger.info(f"{position.symbol}: Breakeven stop activated at ${position.entry_price:.2f}")
                # No generamos señal de salida, solo movemos el stop loss mental
        
        return None
    
    def calculate_atr(self, ohlc_data: list, period: int = 14) -> float:
        """
        Calcula ATR (Average True Range).
        
        Args:
            ohlc_data: Lista de diccionarios con keys: open, high, low, close
            period: Período para el ATR
        
        Returns:
            ATR value
        """
        if len(ohlc_data) < period + 1:
            return 0.0
        
        # Extraer arrays
        highs = np.array([candle['high'] for candle in ohlc_data])
        lows = np.array([candle['low'] for candle in ohlc_data])
        closes = np.array([candle['close'] for candle in ohlc_data])
        
        # Calcular True Range
        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)
        
        # ATR = promedio de True Ranges
        if len(true_ranges) >= period:
            atr = np.mean(true_ranges[-period:])
            return atr
        
        return 0.0
    
    def get_exit_stats(self, position: PositionState) -> Dict:
        """Retorna estadísticas del estado de exits de una posición"""
        return {
            'trailing_active': position.trailing_stop_active,
            'trailing_price': position.trailing_stop_price,
            'breakeven_active': position.breakeven_active,
            'partial_executed': position.partial_executed,
            'highest_reached': position.highest_price_reached,
            'remaining_pct': (position.remaining_amount / position.amount) * 100
        }


class ExitMetrics:
    """Métricas de performance del sistema de exits"""
    
    def __init__(self):
        self.trailing_stops_hit = 0
        self.atr_tps_hit = 0
        self.breakeven_stops_hit = 0
        self.partials_executed = 0
        
        self.total_exits = 0
        self.avg_profit_on_exit = 0.0
        self.max_profit_captured_pct = 0.0
        
    def record_exit(self, exit_signal: ExitSignal, profit_pct: float, profit_amount: float):
        """Registra una salida para métricas"""
        self.total_exits += 1
        
        if exit_signal.exit_type == 'TRAILING_STOP':
            self.trailing_stops_hit += 1
        elif exit_signal.exit_type == 'ATR_TP':
            self.atr_tps_hit += 1
        elif exit_signal.exit_type == 'BREAKEVEN':
            self.breakeven_stops_hit += 1
        elif exit_signal.exit_type == 'PARTIAL':
            self.partials_executed += 1
        
        # Actualizar promedios
        self.avg_profit_on_exit = (
            (self.avg_profit_on_exit * (self.total_exits - 1) + profit_pct) / self.total_exits
        )
        
        if profit_pct > self.max_profit_captured_pct:
            self.max_profit_captured_pct = profit_pct
    
    def get_summary(self) -> Dict:
        """Retorna resumen de métricas"""
        if self.total_exits == 0:
            return {
                'total_exits': 0,
                'trailing_hit_rate': 0,
                'atr_tp_hit_rate': 0,
                'partial_rate': 0,
                'avg_profit': 0,
                'max_profit': 0
            }
        
        return {
            'total_exits': self.total_exits,
            'trailing_stop_hits': self.trailing_stops_hit,
            'atr_tp_hits': self.atr_tps_hit,
            'breakeven_hits': self.breakeven_stops_hit,
            'partials_executed': self.partials_executed,
            'trailing_hit_rate': (self.trailing_stops_hit / self.total_exits * 100),
            'atr_tp_hit_rate': (self.atr_tps_hit / self.total_exits * 100),
            'partial_rate': (self.partials_executed / self.total_exits * 100),
            'avg_profit_on_exit': self.avg_profit_on_exit,
            'max_profit_captured': self.max_profit_captured_pct
        }


if __name__ == "__main__":
    # Test unitario
    print("🧪 Testing SmartExitManager...")
    
    config = ExitConfig()
    manager = SmartExitManager(config)
    
    # Simular posición
    position = PositionState(
        symbol='BTC',
        entry_price=100.0,
        entry_timestamp=datetime.now(),
        amount=1.0,
        highest_price_reached=100.0
    )
    
    # Test 1: Precio sube 1.5%, debe activar trailing
    signal = manager.evaluate_exit(position, 101.5, 1.0)
    print(f"Test 1 (price +1.5%): {signal}")
    print(f"Trailing active: {position.trailing_stop_active}")
    print(f"Trailing price: {position.trailing_stop_price}")
    
    # Test 2: Precio baja a trailing stop
    signal = manager.evaluate_exit(position, 101.0, 1.0)
    print(f"\nTest 2 (hit trailing): {signal}")
    
    print("\n✅ Tests completed")
