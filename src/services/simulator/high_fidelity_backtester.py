"""
High Fidelity Backtester - V19.1
=================================
Simulador de alta fidelidad que replica EXACTAMENTE las restricciones del sistema real.

Características:
- Multi-symbol support
- 1-minute granularity
- Comisiones y slippage reales
- Cooldowns entre trades
- Max positions limit
- Global throttling
- Stop loss automático
- Trend filters
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HighFidelityBacktester")


@dataclass
class SimulationConfig:
    """Configuración de la simulación"""
    initial_capital: float = 1000.0
    trade_amount: float = 50.0  # Cantidad por trade
    max_positions: int = 2  # Max posiciones simultáneas
    cooldown_minutes: int = 10  # Minutos entre trades del mismo símbolo
    global_throttle_seconds: int = 60  # Segundos entre trades globales
    stop_loss_pct: Optional[float] = 2.0  # Stop loss en %
    take_profit_pct: Optional[float] = None  # Take profit en %
    commission: float = 0.001  # 0.1% por operación
    slippage: float = 0.0005  # 0.05% slippage
    
    # V20: Smart Exits configuration
    enable_trailing_stop: bool = False
    trailing_activation_pct: float = 1.0  # Activar trailing cuando profit > 1%
    trailing_distance_pct: float = 0.5  # Distancia del trailing en %
    enable_atr_tp: bool = False
    atr_multiplier: float = 2.0  # Multiplicador ATR para TP
    

@dataclass
class Trade:
    """Registro de un trade"""
    timestamp: datetime
    symbol: str
    side: str  # 'BUY' or 'SELL'
    price: float
    amount: float
    cost: float  # Costo total incluyendo comisión
    commission_paid: float
    reason: str  # Razón de la señal


@dataclass
class Position:
    """Posición abierta"""
    symbol: str
    entry_timestamp: datetime
    entry_price: float
    amount: float
    cost: float  # Costo total pagado
    
    # V20: Tracking para Smart Exits
    highest_price_reached: float = None
    trailing_stop_price: Optional[float] = None
    trailing_stop_active: bool = False
    breakeven_active: bool = False
    partial_executed: bool = False
    remaining_amount: float = None
    
    def __post_init__(self):
        if self.highest_price_reached is None:
            self.highest_price_reached = self.entry_price
        if self.remaining_amount is None:
            self.remaining_amount = self.amount


@dataclass
class SimulationResult:
    """Resultado de la simulación"""
    config: SimulationConfig
    
    # Métricas financieras
    initial_capital: float
    final_capital: float
    total_pnl: float
    total_return_pct: float
    
    # Métricas de trading
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Métricas de profit/loss
    avg_win: float
    avg_loss: float
    max_win: float
    max_loss: float
    
    # Costos
    total_commissions: float
    commission_pct_of_pnl: float
    
    # Risk metrics
    max_drawdown: float
    sharpe_ratio: float
    
    # Trade frequency
    trades_per_hour: float
    trades_per_day: float
    
    # Detalles
    trades_history: List[Trade]
    equity_curve: List[float]
    
    # Restricciones aplicadas
    cooldown_rejections: int
    position_limit_rejections: int
    throttle_rejections: int
    balance_rejections: int
    stop_loss_triggered: int
    
    def summary(self) -> str:
        """Genera resumen legible"""
        return f"""
=== SIMULATION RESULTS ===
Capital: ${self.initial_capital:.2f} → ${self.final_capital:.2f}
PnL: ${self.total_pnl:.2f} ({self.total_return_pct:+.1f}%)
Trades: {self.total_trades} ({self.trades_per_day:.0f}/día)
Win Rate: {self.win_rate:.1f}% ({self.winning_trades}W / {self.losing_trades}L)
Avg Win: ${self.avg_win:.2f} | Avg Loss: ${self.avg_loss:.2f}
Commissions: ${self.total_commissions:.2f} ({self.commission_pct_of_pnl:.1f}% of PnL)
Max Drawdown: {self.max_drawdown:.1f}%
Sharpe: {self.sharpe_ratio:.2f}

RESTRICTIONS APPLIED:
- Cooldown rejections: {self.cooldown_rejections}
- Position limit rejections: {self.position_limit_rejections}
- Throttle rejections: {self.throttle_rejections}
- Balance rejections: {self.balance_rejections}
- Stop loss triggered: {self.stop_loss_triggered}
"""


class HighFidelityBacktester:
    """
    Backtester de alta fidelidad que replica el comportamiento exacto del sistema.
    """
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.balance = config.initial_capital
        self.open_positions: Dict[str, Position] = {}
        self.last_trade_time: Dict[str, datetime] = {}
        self.last_global_trade: Optional[datetime] = None
        self.trades_history: List[Trade] = []
        self.equity_curve: List[float] = [config.initial_capital]
        
        # Contadores de restricciones
        self.cooldown_rejections = 0
        self.position_limit_rejections = 0
        self.throttle_rejections = 0
        self.balance_rejections = 0
        self.stop_loss_triggered = 0
        
    def run(self, market_data: Dict[str, pd.DataFrame], strategy) -> SimulationResult:
        """
        Ejecuta la simulación minuto a minuto.
        
        Args:
            market_data: {symbol: DataFrame(timestamp, open, high, low, close, volume)}
            strategy: Instancia de estrategia con método evaluate()
        
        Returns:
            SimulationResult con métricas completas
        """
        # Preparar datos - alinear timestamps
        aligned_data = self._align_data(market_data)
        total_minutes = len(aligned_data)
        
        logger.info(f"🚀 Iniciando simulación de {total_minutes} minutos...")
        logger.info(f"📊 Config: {self.config}")
        
        # Procesar minuto a minuto
        for i, (timestamp, prices) in enumerate(aligned_data.items()):
            if i % 500 == 0:
                logger.info(f"   Procesando minuto {i}/{total_minutes} ({i/total_minutes*100:.0f}%)")
            
            # 1. Verificar stop loss para posiciones abiertas
            self._check_stop_loss(timestamp, prices)
            
            # 1.5. V20: Actualizar trailing stops
            self._update_trailing_stops(timestamp, prices)
            
            # 2. Evaluar estrategia para cada símbolo
            for symbol, price in prices.items():
                if pd.isna(price):
                    continue
                
                # V20: Obtener historia OHLC completa (si estrategia lo soporta)
                # Intentar primero con OHLC, si falla usar solo prices
                try:
                    ohlc_history = self._get_ohlc_history(market_data[symbol], timestamp)
                    
                    if len(ohlc_history) < 50:
                        continue
                    
                    # Pasar posición abierta si existe
                    open_pos = None
                    if symbol in self.open_positions:
                        pos = self.open_positions[symbol]
                        open_pos = {
                            'entry_price': pos.entry_price,
                            'amount': pos.remaining_amount,
                            'timestamp': pos.entry_timestamp
                        }
                    
                    # Evaluar estrategia con OHLC
                    signal = strategy.evaluate(symbol, price, ohlc_history, timestamp, open_pos)
                    
                except (AttributeError, TypeError):
                    # Fallback: estrategia antigua que solo usa price_history
                    price_history = self._get_price_history(market_data[symbol], timestamp)
                    
                    if len(price_history) < 50:
                        continue
                    
                    signal = strategy.evaluate(symbol, price, price_history, timestamp)
                
                if signal:
                    if signal['type'] == 'BUY':
                        self._execute_buy(timestamp, symbol, price, signal.get('reason', 'Strategy'))
                    elif signal['type'] == 'SELL':
                        self._execute_sell(timestamp, symbol, price, signal.get('reason', 'Strategy'))
            
            # 3. Actualizar equity curve
            current_equity = self._calculate_equity(prices)
            self.equity_curve.append(current_equity)
        
        # Cerrar posiciones abiertas al final
        final_prices = list(aligned_data.values())[-1]
        for symbol in list(self.open_positions.keys()):
            if symbol in final_prices:
                self._execute_sell(
                    list(aligned_data.keys())[-1],
                    symbol,
                    final_prices[symbol],
                    "End of simulation"
                )
        
        return self._generate_result()
    
    def _align_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[datetime, Dict[str, float]]:
        """Alinea datos de múltiples símbolos por timestamp"""
        # Crear un índice común de timestamps
        all_timestamps = set()
        for df in market_data.values():
            all_timestamps.update(df['timestamp'].tolist())
        
        sorted_timestamps = sorted(list(all_timestamps))
        
        # Crear diccionario {timestamp: {symbol: close_price}}
        aligned = {}
        for ts in sorted_timestamps:
            aligned[ts] = {}
            for symbol, df in market_data.items():
                # Buscar precio en este timestamp
                row = df[df['timestamp'] == ts]
                if not row.empty:
                    aligned[ts][symbol] = row.iloc[0]['close']
                else:
                    # Forward fill si falta dato
                    prev_data = df[df['timestamp'] < ts]
                    if not prev_data.empty:
                        aligned[ts][symbol] = prev_data.iloc[-1]['close']
        
        return aligned
    
    def _get_price_history(self, df: pd.DataFrame, until_timestamp: datetime) -> List[float]:
        """Obtiene historia de precios hasta un timestamp"""
        historical = df[df['timestamp'] < until_timestamp]
        return historical['close'].tolist()
    
    def _get_ohlc_history(self, df: pd.DataFrame, until_timestamp: datetime) -> List[Dict]:
        """
        Obtiene historia OHLC completa hasta un timestamp.
        V20: Necesario para filtros de velas y cálculo de ATR.
        """
        historical = df[df['timestamp'] < until_timestamp]
        if historical.empty:
            return []
        
        return historical[['open', 'high', 'low', 'close', 'volume']].to_dict('records')
    
    def _check_stop_loss(self, timestamp: datetime, current_prices: Dict[str, float]):
        """Verifica stop loss para posiciones abiertas"""
        if not self.config.stop_loss_pct:
            return
        
        for symbol in list(self.open_positions.keys()):
            if symbol not in current_prices:
                continue
            
            position = self.open_positions[symbol]
            current_price = current_prices[symbol]
            
            # V20: Si trailing stop está activo, verificar primero
            if position.trailing_stop_active and position.trailing_stop_price:
                if current_price <= position.trailing_stop_price:
                    logger.warning(f"   🛑 TRAILING STOP: {symbol} @ ${current_price:.2f}")
                    self._execute_sell(timestamp, symbol, current_price, "Trailing Stop")
                    self.stop_loss_triggered += 1
                    continue
            
            # Calcular pérdida actual
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            
            if pnl_pct <= -self.config.stop_loss_pct:
                logger.warning(f"   🛑 STOP LOSS: {symbol} @ ${current_price:.2f} (PnL: {pnl_pct:.1f}%)")
                self._execute_sell(timestamp, symbol, current_price, f"Stop Loss ({pnl_pct:.1f}%)")
                self.stop_loss_triggered += 1
    
    def _update_trailing_stops(self, timestamp: datetime, current_prices: Dict[str, float]):
        """
        V20: Actualiza trailing stops dinámicos.
        
        Lógica:
        - Cuando profit > 1%, activa trailing stop
        - Trailing stop = precio_máximo * (1 - 0.5%)
        - Se actualiza solo al alza (nunca baja)
        """
        for symbol, position in self.open_positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # Actualizar precio máximo
            if current_price > position.highest_price_reached:
                position.highest_price_reached = current_price
            
            # Calcular profit actual
            profit_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            
            # Activar trailing stop si no está activo y profit > threshold
            if not position.trailing_stop_active:
                trailing_activation = getattr(self.config, 'trailing_activation_pct', 1.0)
                
                if profit_pct >= trailing_activation:
                    position.trailing_stop_active = True
                    trailing_distance = getattr(self.config, 'trailing_distance_pct', 0.5)
                    position.trailing_stop_price = position.highest_price_reached * (1 - trailing_distance / 100)
                    logger.debug(f"   📈 {symbol}: Trailing stop activated @ ${position.trailing_stop_price:.2f}")
            
            # Actualizar trailing stop si está activo
            elif position.trailing_stop_price:
                trailing_distance = getattr(self.config, 'trailing_distance_pct', 0.5)
                new_trailing = position.highest_price_reached * (1 - trailing_distance / 100)
                
                # Solo actualizar al alza
                if new_trailing > position.trailing_stop_price:
                    position.trailing_stop_price = new_trailing
    
    def _execute_buy(self, timestamp: datetime, symbol: str, price: float, reason: str):
        """Ejecuta orden de compra con todas las restricciones"""
        # CHECK 1: Ya tenemos posición en este símbolo?
        if symbol in self.open_positions:
            return
        
        # CHECK 2: Cooldown period
        if symbol in self.last_trade_time:
            time_since_last = (timestamp - self.last_trade_time[symbol]).total_seconds() / 60
            if time_since_last < self.config.cooldown_minutes:
                self.cooldown_rejections += 1
                return
        
        # CHECK 3: Global throttle
        if self.last_global_trade:
            time_since_global = (timestamp - self.last_global_trade).total_seconds()
            if time_since_global < self.config.global_throttle_seconds:
                self.throttle_rejections += 1
                return
        
        # CHECK 4: Max positions
        if len(self.open_positions) >= self.config.max_positions:
            self.position_limit_rejections += 1
            return
        
        # CHECK 5: Balance suficiente
        if self.balance < self.config.trade_amount:
            self.balance_rejections += 1
            return
        
        # EJECUTAR COMPRA
        # Aplicar slippage (precio peor)
        execution_price = price * (1 + self.config.slippage)
        
        # Calcular comisión
        gross_amount = self.config.trade_amount
        commission = gross_amount * self.config.commission
        net_amount = gross_amount - commission
        
        # Cantidad de activo comprado
        amount = net_amount / execution_price
        
        # Crear posición
        position = Position(
            symbol=symbol,
            entry_timestamp=timestamp,
            entry_price=execution_price,
            amount=amount,
            cost=gross_amount
        )
        
        self.open_positions[symbol] = position
        self.balance -= gross_amount
        self.last_trade_time[symbol] = timestamp
        self.last_global_trade = timestamp
        
        # Registrar trade
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side='BUY',
            price=execution_price,
            amount=amount,
            cost=gross_amount,
            commission_paid=commission,
            reason=reason
        )
        self.trades_history.append(trade)
    
    def _execute_sell(self, timestamp: datetime, symbol: str, price: float, reason: str):
        """Ejecuta orden de venta"""
        if symbol not in self.open_positions:
            return
        
        position = self.open_positions[symbol]
        
        # Aplicar slippage
        execution_price = price * (1 - self.config.slippage)
        
        # Calcular valor bruto
        gross_value = position.amount * execution_price
        
        # Aplicar comisión
        commission = gross_value * self.config.commission
        net_value = gross_value - commission
        
        # Actualizar balance
        self.balance += net_value
        
        # Registrar trade
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side='SELL',
            price=execution_price,
            amount=position.amount,
            cost=net_value,
            commission_paid=commission,
            reason=reason
        )
        self.trades_history.append(trade)
        
        # Cerrar posición
        del self.open_positions[symbol]
        self.last_trade_time[symbol] = timestamp
        self.last_global_trade = timestamp
    
    def _calculate_equity(self, current_prices: Dict[str, float]) -> float:
        """Calcula equity total (balance + valor de posiciones)"""
        equity = self.balance
        
        for symbol, position in self.open_positions.items():
            if symbol in current_prices:
                equity += position.amount * current_prices[symbol]
        
        return equity
    
    def _generate_result(self) -> SimulationResult:
        """Genera resultado final con métricas"""
        final_capital = self.equity_curve[-1]
        total_pnl = final_capital - self.config.initial_capital
        total_return_pct = (total_pnl / self.config.initial_capital) * 100
        
        # Analizar trades cerrados (pares BUY/SELL)
        closed_trades = []
        buy_trades = [t for t in self.trades_history if t.side == 'BUY']
        
        for buy in buy_trades:
            # Buscar SELL correspondiente
            sell = next((t for t in self.trades_history 
                        if t.side == 'SELL' and t.symbol == buy.symbol and t.timestamp > buy.timestamp),
                       None)
            if sell:
                pnl = sell.cost - buy.cost
                closed_trades.append({
                    'symbol': buy.symbol,
                    'entry_price': buy.price,
                    'exit_price': sell.price,
                    'pnl': pnl,
                    'duration': (sell.timestamp - buy.timestamp).total_seconds() / 60
                })
        
        # Métricas de trades
        winning = [t for t in closed_trades if t['pnl'] > 0]
        losing = [t for t in closed_trades if t['pnl'] < 0]
        
        win_rate = (len(winning) / len(closed_trades) * 100) if closed_trades else 0
        avg_win = np.mean([t['pnl'] for t in winning]) if winning else 0
        avg_loss = np.mean([t['pnl'] for t in losing]) if losing else 0
        max_win = max([t['pnl'] for t in winning]) if winning else 0
        max_loss = min([t['pnl'] for t in losing]) if losing else 0
        
        # Comisiones totales
        total_commissions = sum(t.commission_paid for t in self.trades_history)
        commission_pct = (total_commissions / abs(total_pnl) * 100) if total_pnl != 0 else 0
        
        # Max drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max * 100
        max_drawdown = abs(np.min(drawdown))
        
        # Sharpe ratio
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(365 * 24 * 60)) if np.std(returns) > 0 else 0
        else:
            sharpe = 0
        
        # Frecuencia de trades
        duration_hours = len(self.equity_curve) / 60
        trades_per_hour = len(closed_trades) / duration_hours if duration_hours > 0 else 0
        trades_per_day = trades_per_hour * 24
        
        return SimulationResult(
            config=self.config,
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            total_trades=len(closed_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_win=max_win,
            max_loss=max_loss,
            total_commissions=total_commissions,
            commission_pct_of_pnl=commission_pct,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            trades_per_hour=trades_per_hour,
            trades_per_day=trades_per_day,
            trades_history=self.trades_history,
            equity_curve=self.equity_curve,
            cooldown_rejections=self.cooldown_rejections,
            position_limit_rejections=self.position_limit_rejections,
            throttle_rejections=self.throttle_rejections,
            balance_rejections=self.balance_rejections,
            stop_loss_triggered=self.stop_loss_triggered
        )
