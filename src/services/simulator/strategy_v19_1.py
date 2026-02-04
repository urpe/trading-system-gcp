"""
Strategy V19.1 - Conservative RSI with Trend Filter
====================================================
Estrategia conservadora para simulación.

Mejoras sobre V19:
- RSI más conservador (15/85 vs 25/75)
- Filtro de tendencia EMA (20 vs 50)
- No operar en contra de la tendencia
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StrategyV191")


class RsiMeanReversionV191:
    """
    RSI Mean Reversion con filtros conservadores.
    
    Reglas:
    1. BUY: RSI < oversold (15) AND EMA20 > EMA50 (uptrend) AND precio > EMA20
    2. SELL: RSI > overbought (85) OR posición en profit > 1%
    3. NO operar si RSI extremo (<5 o >95) - posible error de datos
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 15,
        overbought: float = 85,
        ema_fast: int = 20,
        ema_slow: int = 50,
        min_profit_target_pct: float = 1.0,
        enable_trend_filter: bool = True
    ):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.min_profit_target = min_profit_target_pct
        self.enable_trend_filter = enable_trend_filter
        
    def evaluate(
        self,
        symbol: str,
        current_price: float,
        price_history: List[float],
        timestamp: datetime,
        open_position: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Evalúa si debe generar señal de trading.
        
        Args:
            symbol: Símbolo del activo
            current_price: Precio actual
            price_history: Lista de precios históricos
            timestamp: Timestamp actual
            open_position: Posición abierta si existe {entry_price, ...}
        
        Returns:
            Dict con señal {'type': 'BUY'/'SELL', 'reason': str} o None
        """
        if len(price_history) < max(self.rsi_period + 1, self.ema_slow + 1):
            return None
        
        prices = np.array(price_history + [current_price])
        
        # Calcular indicadores
        rsi = self._calculate_rsi(prices)
        ema_fast = self._calculate_ema(prices, self.ema_fast)
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        
        # VALIDACIÓN: RSI extremo indica posible error de datos
        if rsi < 5 or rsi > 95:
            return None
        
        # Si tenemos posición abierta, evaluar SELL
        if open_position:
            entry_price = open_position['entry_price']
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            
            # SELL: RSI overbought
            if rsi > self.overbought:
                return {
                    'type': 'SELL',
                    'reason': f'RSI Overbought ({rsi:.1f})',
                    'rsi': rsi,
                    'profit_pct': profit_pct
                }
            
            # SELL: Profit target alcanzado
            if profit_pct >= self.min_profit_target:
                return {
                    'type': 'SELL',
                    'reason': f'Take Profit ({profit_pct:.1f}%)',
                    'rsi': rsi,
                    'profit_pct': profit_pct
                }
            
            return None
        
        # Si NO tenemos posición, evaluar BUY
        # Condición 1: RSI oversold
        if rsi > self.oversold:
            return None
        
        # Condición 2: Trend filter (opcional)
        if self.enable_trend_filter:
            # Solo comprar en uptrend (EMA fast > EMA slow)
            if ema_fast <= ema_slow:
                return None
            
            # Precio debe estar cerca o arriba de EMA fast (no muy alejado)
            price_distance = ((current_price - ema_fast) / ema_fast) * 100
            if price_distance < -2:  # Si está >2% por debajo de EMA, skip
                return None
        
        # ✅ GENERAR SEÑAL BUY
        return {
            'type': 'BUY',
            'reason': f'RSI Oversold ({rsi:.1f})',
            'rsi': rsi,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'trend': 'up' if ema_fast > ema_slow else 'down'
        }
    
    def _calculate_rsi(self, prices: np.ndarray) -> float:
        """
        Calcula RSI usando método estándar de Wilder.
        """
        if len(prices) < self.rsi_period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-self.rsi_period:])
        avg_loss = np.mean(losses[-self.rsi_period:])
        
        if avg_loss == 0:
            return 100.0
        if avg_gain == 0:
            return 0.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """
        Calcula EMA (Exponential Moving Average).
        """
        if len(prices) < period:
            return np.mean(prices)
        
        # Usar pandas para EMA (más eficiente)
        series = pd.Series(prices)
        ema = series.ewm(span=period, adjust=False).mean().iloc[-1]
        
        return ema


class RsiMeanReversionV19:
    """
    RSI Mean Reversion SIN filtros (para simular V19 real).
    
    Reglas agresivas:
    - BUY: RSI < 25
    - SELL: RSI > 75
    - Sin filtro de tendencia
    - Sin validación de RSI extremo
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 25,
        overbought: float = 75
    ):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def evaluate(
        self,
        symbol: str,
        current_price: float,
        price_history: List[float],
        timestamp: datetime,
        open_position: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Evalúa señal (versión agresiva V19)"""
        if len(price_history) < self.rsi_period + 1:
            return None
        
        prices = np.array(price_history + [current_price])
        rsi = self._calculate_rsi(prices)
        
        # Si tenemos posición, evaluar SELL
        if open_position:
            if rsi > self.overbought:
                return {
                    'type': 'SELL',
                    'reason': f'RSI Overbought ({rsi:.1f})',
                    'rsi': rsi
                }
            return None
        
        # Si NO tenemos posición, evaluar BUY
        if rsi < self.oversold:
            return {
                'type': 'BUY',
                'reason': f'RSI Oversold ({rsi:.1f})',
                'rsi': rsi
            }
        
        return None
    
    def _calculate_rsi(self, prices: np.ndarray) -> float:
        """Calcula RSI"""
        if len(prices) < self.rsi_period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-self.rsi_period:])
        avg_loss = np.mean(losses[-self.rsi_period:])
        
        if avg_loss == 0:
            return 100.0
        if avg_gain == 0:
            return 0.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


def test_strategy():
    """Test unitario de la estrategia"""
    print("🧪 Testing Strategy V19.1...")
    
    # Datos de prueba
    prices = [100, 101, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85]
    
    strategy = RsiMeanReversionV191()
    signal = strategy.evaluate(
        symbol='TEST',
        current_price=85,
        price_history=prices[:-1],
        timestamp=datetime.now()
    )
    
    if signal:
        print(f"✅ Signal: {signal['type']} - {signal['reason']}")
        print(f"   RSI: {signal.get('rsi', 'N/A'):.1f}")
    else:
        print("❌ No signal generated")
    
    # Test V19 agresiva
    print("\n🧪 Testing Strategy V19 (Aggressive)...")
    strategy_v19 = RsiMeanReversionV19()
    signal_v19 = strategy_v19.evaluate(
        symbol='TEST',
        current_price=85,
        price_history=prices[:-1],
        timestamp=datetime.now()
    )
    
    if signal_v19:
        print(f"✅ Signal: {signal_v19['type']} - {signal_v19['reason']}")
        print(f"   RSI: {signal_v19.get('rsi', 'N/A'):.1f}")
    else:
        print("❌ No signal generated")


if __name__ == "__main__":
    test_strategy()
