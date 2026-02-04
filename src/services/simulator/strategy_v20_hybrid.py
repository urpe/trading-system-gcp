"""
Strategy V20 Hybrid - Best of Both Worlds
==========================================
Combina la entrada probada de V19.1 (54.5% WR) con los Smart Exits de V20.

Filosofía:
- Mantener lógica de entrada simple y efectiva de V19.1
- Aplicar Smart Exits para mejorar ratio R:R
- Objetivo: Win Rate 50%+ con R:R 2:1+
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
import logging

from .smart_exits import SmartExitManager, ExitConfig, PositionState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StrategyV20Hybrid")


class RsiMeanReversionV20Hybrid:
    """
    V20 Hybrid: Entrada V19.1 + Exits V20.
    
    Entry (V19.1 probado - 54.5% WR):
    - RSI < 20 (conservador)
    - EMA20 > EMA50 (uptrend)
    - Precio cerca de EMA20
    
    Exit (V20 Smart):
    - Trailing Stop dinámico
    - ATR Take Profit (3x ATR)
    - Breakeven Stop
    - Control estricto de pérdidas
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 20,
        overbought: float = 85,
        ema_fast: int = 20,
        ema_slow: int = 50,
        exit_config: ExitConfig = None
    ):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        
        # Smart Exit Manager con parámetros agresivos
        if exit_config is None:
            exit_config = ExitConfig(
                trailing_stop_pct=0.4,  # Trailing más ajustado
                trailing_activation_pct=0.6,  # Activar temprano
                atr_multiplier_tp=3.5,  # TP más ambicioso
                breakeven_activation_pct=0.3,
                partial_profit_pct=0,  # Desactivar partial (mantener posición completa)
                partial_profit_target_multiplier=0
            )
        
        self.smart_exit_manager = SmartExitManager(exit_config)
        self.position_states: Dict[str, PositionState] = {}
        
        logger.info(f"RsiMeanReversionV20Hybrid initialized: Entry=V19.1, Exits=SmartV20")
    
    def evaluate(
        self,
        symbol: str,
        current_price: float,
        ohlc_data: List[Dict],
        timestamp: datetime,
        open_position: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Evalúa señal con lógica híbrida"""
        if len(ohlc_data) < max(self.rsi_period + 1, self.ema_slow + 1):
            return None
        
        prices = np.array([candle['close'] for candle in ohlc_data])
        rsi = self._calculate_rsi(prices)
        current_atr = self.smart_exit_manager.calculate_atr(ohlc_data, period=14)
        
        # Si tenemos posición abierta, usar SMART EXITS
        if open_position:
            if symbol not in self.position_states:
                self.position_states[symbol] = PositionState(
                    symbol=symbol,
                    entry_price=open_position['entry_price'],
                    entry_timestamp=open_position.get('timestamp', timestamp),
                    amount=open_position.get('amount', 1.0),
                    highest_price_reached=open_position.get('entry_price')
                )
            
            position_state = self.position_states[symbol]
            
            # Evaluar Smart Exits
            exit_signal = self.smart_exit_manager.evaluate_exit(
                position=position_state,
                current_price=current_price,
                current_atr=current_atr,
                ohlc_current=ohlc_data[-1]
            )
            
            if exit_signal:
                if symbol in self.position_states:
                    del self.position_states[symbol]
                
                return {
                    'type': 'SELL',
                    'reason': exit_signal.reason,
                    'exit_type': exit_signal.exit_type,
                    'rsi': rsi,
                    'atr': current_atr
                }
            
            # Backup: RSI overbought
            if rsi > self.overbought:
                if symbol in self.position_states:
                    del self.position_states[symbol]
                
                return {
                    'type': 'SELL',
                    'reason': f'RSI Overbought ({rsi:.1f})',
                    'exit_type': 'RSI_OVERBOUGHT',
                    'rsi': rsi
                }
            
            return None
        
        # Entrada: Lógica V19.1 (simple y probada)
        if rsi > self.oversold:
            return None
        
        # Filtro de tendencia (solo uptrend)
        ema_fast = self._calculate_ema(prices, self.ema_fast)
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        
        if ema_fast <= ema_slow:
            return None
        
        # Precio debe estar cerca de EMA fast (no más del 2% abajo)
        price_distance = ((current_price - ema_fast) / ema_fast) * 100
        if price_distance < -2:
            return None
        
        # ✅ GENERAR SEÑAL BUY
        atr_tp = current_price + (3.5 * current_atr)
        
        return {
            'type': 'BUY',
            'reason': f'RSI Oversold V19.1 ({rsi:.1f})',
            'rsi': rsi,
            'atr': current_atr,
            'take_profit_target': atr_tp,
            'ema_trend': 'up'
        }
    
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
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA"""
        if len(prices) < period:
            return np.mean(prices)
        
        series = pd.Series(prices)
        ema = series.ewm(span=period, adjust=False).mean().iloc[-1]
        
        return ema
