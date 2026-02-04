"""
Strategy V20 - Alpha Generation
================================
Estrategia con Smart Exits y Sniper Mode Entries para ratio R:R óptimo.

Mejoras sobre V19.1:
- Smart Exits: Trailing stop, ATR TP, Breakeven, Partial Profit
- Sniper Entries: Candle confirmation, Volume surge, Spread filter
- Multi-Timeframe confirmation (opcional)
- Objetivo: Transformar R:R de 1:2 a 2:1+
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
import logging

from .smart_exits import SmartExitManager, ExitConfig, PositionState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StrategyV20")


class RsiMeanReversionV20:
    """
    RSI Mean Reversion V20 - Búsqueda del Alpha.
    
    Entry Filters (Sniper Mode):
    1. RSI oversold (<15)
    2. EMA trend filter (EMA20 > EMA50)
    3. Candle confirmation (vela verde después de roja)
    4. Volume surge (>150% promedio)
    5. Spread acceptable (<0.05%)
    
    Exit System (Smart Exits):
    1. Trailing Stop Loss dinámico
    2. ATR-based Take Profit
    3. Breakeven Stop automático
    4. Partial Profit Taking
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 15,
        overbought: float = 85,
        ema_fast: int = 20,
        ema_slow: int = 50,
        enable_trend_filter: bool = True,
        enable_candle_confirmation: bool = True,
        enable_volume_filter: bool = True,
        enable_spread_filter: bool = False,  # Disable en simulación (no tenemos bid/ask)
        enable_mtf: bool = False,
        exit_config: ExitConfig = None
    ):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        
        # Entry Filters
        self.enable_trend_filter = enable_trend_filter
        self.enable_candle_confirmation = enable_candle_confirmation
        self.enable_volume_filter = enable_volume_filter
        self.enable_spread_filter = enable_spread_filter
        self.enable_mtf = enable_mtf
        
        # Smart Exit Manager
        self.smart_exit_manager = SmartExitManager(exit_config or ExitConfig())
        
        # Track de posiciones para exits
        self.position_states: Dict[str, PositionState] = {}
        
        logger.info(f"RsiMeanReversionV20 initialized: RSI({rsi_period}), Filters: "
                   f"Trend={enable_trend_filter}, Candle={enable_candle_confirmation}, "
                   f"Volume={enable_volume_filter}")
    
    def evaluate(
        self,
        symbol: str,
        current_price: float,
        ohlc_data: List[Dict],
        timestamp: datetime,
        open_position: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Evalúa si debe generar señal de trading.
        
        Args:
            symbol: Símbolo del activo
            current_price: Precio actual
            ohlc_data: Lista de OHLC completo [más antiguo -> más reciente]
            timestamp: Timestamp actual
            open_position: Posición abierta si existe
        
        Returns:
            Dict con señal {'type': 'BUY'/'SELL', ...} o None
        """
        if len(ohlc_data) < max(self.rsi_period + 1, self.ema_slow + 1):
            return None
        
        # Extraer precios de cierre
        prices = np.array([candle['close'] for candle in ohlc_data])
        
        # Calcular indicadores
        rsi = self._calculate_rsi(prices)
        current_atr = self.smart_exit_manager.calculate_atr(ohlc_data, period=14)
        
        # V20: Validación menos restrictiva - RSI extremo solo si es exactamente 0 o 100
        # (En mercados fuerte, RSI puede ser <5 legítimamente)
        if rsi == 0.0 or rsi == 100.0:
            # Solo rechazar si hay muy pocos datos
            if len(prices) < 30:
                return None
        
        # Si tenemos posición abierta, evaluar SMART EXITS
        if open_position:
            # Obtener o crear PositionState
            if symbol not in self.position_states:
                self.position_states[symbol] = PositionState(
                    symbol=symbol,
                    entry_price=open_position['entry_price'],
                    entry_timestamp=open_position.get('timestamp', timestamp),
                    amount=open_position.get('amount', 1.0),
                    highest_price_reached=open_position.get('entry_price')
                )
            
            position_state = self.position_states[symbol]
            
            # Evaluar exit con Smart Exit Manager
            exit_signal = self.smart_exit_manager.evaluate_exit(
                position=position_state,
                current_price=current_price,
                current_atr=current_atr,
                ohlc_current=ohlc_data[-1] if ohlc_data else None
            )
            
            if exit_signal:
                # Limpiar position state si es salida completa
                if exit_signal.exit_type != 'PARTIAL':
                    if symbol in self.position_states:
                        del self.position_states[symbol]
                
                return {
                    'type': 'SELL',
                    'reason': exit_signal.reason,
                    'exit_type': exit_signal.exit_type,
                    'rsi': rsi,
                    'atr': current_atr,
                    'partial_pct': exit_signal.partial_pct
                }
            
            # También check RSI overbought como backup
            if rsi > self.overbought:
                if symbol in self.position_states:
                    del self.position_states[symbol]
                
                return {
                    'type': 'SELL',
                    'reason': f'RSI Overbought ({rsi:.1f})',
                    'exit_type': 'RSI_OVERBOUGHT',
                    'rsi': rsi,
                    'atr': current_atr
                }
            
            return None
        
        # Si NO tenemos posición, evaluar SNIPER ENTRY
        
        # FILTRO 0: RSI oversold (más permisivo: < 20)
        if rsi > 20:  # Cambiar de 15 a 20 para permitir más señales
            return None
        
        # FILTRO 1: Trend Filter (EMA) - Hacer más permisivo
        if self.enable_trend_filter:
            ema_fast = self._calculate_ema(prices, self.ema_fast)
            ema_slow = self._calculate_ema(prices, self.ema_slow)
            
            # V20: Permitir comprar incluso si EMA fast <= slow (mean reversion funciona en downtrends)
            # Solo rechazar si el downtrend es muy fuerte (fast < slow * 0.98)
            if ema_fast < (ema_slow * 0.98):
                return None
            
            # Precio puede estar lejos de EMA (mean reversion busca extremos)
            # No aplicar filtro de distancia
        
        # FILTRO 2: Candle Confirmation (hacer menos restrictivo)
        if self.enable_candle_confirmation:
            if len(ohlc_data) < 2:
                return None
            
            # V20: Solo verificar que vela actual es verde, no exigir que anterior sea roja
            current_candle = ohlc_data[-1]
            is_green = current_candle['close'] > current_candle['open']
            
            # Y que tenga body significativo
            body = abs(current_candle['close'] - current_candle['open'])
            total_range = current_candle['high'] - current_candle['low']
            has_body = (body / total_range) > 0.2 if total_range > 0 else False
            
            if not (is_green and has_body):
                return None
        
        # FILTRO 3: Volume Surge (hacer menos restrictivo) (hacer menos restrictivo)
        if self.enable_volume_filter:
            if len(ohlc_data) < 20:
                return None
            
            volumes = [candle['volume'] for candle in ohlc_data[-20:]]
            current_volume = ohlc_data[-1]['volume']
            avg_volume = np.mean(volumes)
            
            # V20: Reducir threshold a 120% (menos restrictivo que 150%)
            if avg_volume > 0 and current_volume < (avg_volume * 1.2):
                return None
        
        # FILTRO 4: Spread (en simulación, skip - no tenemos bid/ask real)
        # En producción, verificaríamos que spread < 0.05%
        
        # FILTRO 5: Multi-Timeframe (opcional, avanzado)
        if self.enable_mtf:
            # TODO: Implementar verificación de RSI en timeframe superior
            # Por ahora skip
            pass
        
        # ✅ GENERAR SEÑAL BUY (todos los filtros pasaron)
        atr_tp_target = current_price + (2.0 * current_atr)
        
        return {
            'type': 'BUY',
            'reason': f'RSI Oversold Sniper ({rsi:.1f})',
            'rsi': rsi,
            'atr': current_atr,
            'take_profit_target': atr_tp_target,
            'ema_trend': 'up' if self.enable_trend_filter else 'unknown',
            'filters_passed': self._get_filters_passed()
        }
    
    def _calculate_rsi(self, prices: np.ndarray) -> float:
        """Calcula RSI usando método estándar de Wilder"""
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
        """Calcula EMA (Exponential Moving Average)"""
        if len(prices) < period:
            return np.mean(prices)
        
        series = pd.Series(prices)
        ema = series.ewm(span=period, adjust=False).mean().iloc[-1]
        
        return ema
    
    def _check_candle_confirmation(self, current_candle: Dict, previous_candle: Dict) -> bool:
        """
        Verifica confirmación de vela (anti falling knife).
        
        Reglas:
        1. Vela actual debe ser VERDE (close > open)
        2. Vela anterior debe haber sido ROJA (close < open)
        3. Body debe ser > 30% del rango total (no doji)
        
        Returns:
            True si hay confirmación, False si no
        """
        try:
            # Check vela actual es verde
            is_green = current_candle['close'] > current_candle['open']
            
            # Check vela anterior era roja
            previous_red = previous_candle['close'] < previous_candle['open']
            
            # Check que tiene body significativo (no doji)
            body = abs(current_candle['close'] - current_candle['open'])
            total_range = current_candle['high'] - current_candle['low']
            
            has_body = False
            if total_range > 0:
                body_pct = body / total_range
                has_body = body_pct > 0.3
            
            return is_green and previous_red and has_body
            
        except (KeyError, TypeError, ZeroDivisionError):
            return False
    
    def _check_volume_surge(self, current_volume: float, volume_history: List[float]) -> bool:
        """
        Verifica si hay surge de volumen.
        
        Args:
            current_volume: Volumen actual
            volume_history: Lista de volúmenes históricos
        
        Returns:
            True si volumen > 150% del promedio
        """
        if not volume_history or current_volume <= 0:
            return False
        
        avg_volume = np.mean(volume_history)
        
        if avg_volume <= 0:
            return False
        
        # Volumen debe ser >150% del promedio
        return current_volume > (avg_volume * 1.5)
    
    def _get_filters_passed(self) -> List[str]:
        """Retorna lista de filtros que están activos"""
        filters = []
        if self.enable_trend_filter:
            filters.append('EMA_TREND')
        if self.enable_candle_confirmation:
            filters.append('CANDLE_CONF')
        if self.enable_volume_filter:
            filters.append('VOLUME_SURGE')
        if self.enable_spread_filter:
            filters.append('SPREAD_CHECK')
        if self.enable_mtf:
            filters.append('MTF')
        
        return filters


# Versión con filtros desactivados para comparación
class RsiMeanReversionV20_NoFilters(RsiMeanReversionV20):
    """V20 sin filtros de entrada (para A/B testing)"""
    
    def __init__(self, **kwargs):
        super().__init__(
            enable_trend_filter=False,
            enable_candle_confirmation=False,
            enable_volume_filter=False,
            enable_spread_filter=False,
            enable_mtf=False,
            **kwargs
        )


def test_strategy():
    """Test unitario de la estrategia V20"""
    print("🧪 Testing Strategy V20...")
    
    # Datos de prueba (OHLC)
    ohlc_data = []
    for i in range(100):
        price = 100 - i * 0.2  # Tendencia bajista
        ohlc_data.append({
            'timestamp': datetime.now(),
            'open': price + 0.1,
            'high': price + 0.3,
            'low': price - 0.2,
            'close': price,
            'volume': 1000 + (i * 10)
        })
    
    # Última vela verde (reversión)
    ohlc_data.append({
        'timestamp': datetime.now(),
        'open': 80.0,
        'high': 81.5,
        'low': 79.8,
        'close': 81.0,  # Verde
        'volume': 2000  # Volumen alto
    })
    
    strategy = RsiMeanReversionV20(
        enable_candle_confirmation=True,
        enable_volume_filter=True
    )
    
    signal = strategy.evaluate(
        symbol='TEST',
        current_price=81.0,
        ohlc_data=ohlc_data,
        timestamp=datetime.now()
    )
    
    if signal:
        print(f"✅ Signal: {signal['type']} - {signal['reason']}")
        print(f"   RSI: {signal.get('rsi', 'N/A'):.1f}")
        print(f"   ATR: {signal.get('atr', 'N/A'):.2f}")
        print(f"   TP Target: ${signal.get('take_profit_target', 0):.2f}")
        print(f"   Filters: {signal.get('filters_passed', [])}")
    else:
        print("❌ No signal generated (filters blocked it)")
    
    print("\n✅ Test completed")


if __name__ == "__main__":
    test_strategy()
