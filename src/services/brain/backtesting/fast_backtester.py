"""
Fast Backtester - V18
=====================
Motor de backtesting optimizado para evaluación rápida de estrategias.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class BacktestResult:
    """Resultado de un backtest"""
    strategy_name: str
    params: Dict[str, Any]
    
    # Métricas de performance
    total_return: float  # Retorno total en %
    sharpe_ratio: float  # Sharpe ratio (risk-adjusted return)
    max_drawdown: float  # Máxima caída en %
    win_rate: float  # % de trades ganadores
    total_trades: int
    
    # Detalles
    final_capital: float
    initial_capital: float
    
    # Puntuación compuesta (para ranking)
    score: float
    
    def __repr__(self) -> str:
        return (f"{self.strategy_name}{self.params}: "
                f"Return={self.total_return:.2f}%, Sharpe={self.sharpe_ratio:.2f}, "
                f"Win Rate={self.win_rate:.1f}%")


class FastBacktester:
    """
    Backtester vectorizado para máxima velocidad.
    
    Ejecuta un backtest completo en < 100ms para períodos de 1000 velas.
    Optimizado para el "Torneo de Estrategias".
    """
    
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        """
        Args:
            initial_capital: Capital inicial para el backtest
            commission: Comisión por operación (0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run(self, strategy, price_data: List[float]) -> BacktestResult:
        """
        Ejecuta backtest de una estrategia sobre datos históricos.
        
        Args:
            strategy: Instancia de StrategyInterface
            price_data: Lista de precios históricos [más antiguo -> más reciente]
        
        Returns:
            BacktestResult con métricas de performance
        """
        if len(price_data) < strategy.get_required_history() + 10:
            # No hay suficientes datos
            return BacktestResult(
                strategy_name=strategy.name,
                params=strategy.params,
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=100.0,
                win_rate=0.0,
                total_trades=0,
                final_capital=self.initial_capital,
                initial_capital=self.initial_capital,
                score=0.0
            )
        
        prices = np.array(price_data)
        capital = self.initial_capital
        position = 0.0  # Cantidad de activo que tenemos
        position_entry_price = 0.0
        
        trades = []
        equity_curve = [capital]
        
        # Iterar sobre cada período (después de tener suficiente historia)
        required = strategy.get_required_history()
        
        for i in range(required, len(prices)):
            current_price = prices[i]
            history = prices[:i].tolist()
            
            # Evaluar estrategia
            result = strategy.evaluate(current_price, history)
            
            # Ejecutar señales
            if result.signal == "BUY" and position == 0:
                # Abrir posición larga
                position = (capital * (1 - self.commission)) / current_price
                position_entry_price = current_price
                capital = 0
            
            elif result.signal == "SELL" and position > 0:
                # Cerrar posición
                capital = position * current_price * (1 - self.commission)
                pnl = capital - self.initial_capital
                
                trades.append({
                    'entry': position_entry_price,
                    'exit': current_price,
                    'pnl': pnl,
                    'return': (current_price - position_entry_price) / position_entry_price
                })
                
                position = 0
                position_entry_price = 0
            
            # Calcular equity actual
            if position > 0:
                current_equity = position * current_price
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
        
        # Cerrar posición final si está abierta
        if position > 0:
            capital = position * prices[-1] * (1 - self.commission)
            pnl = capital - self.initial_capital
            trades.append({
                'entry': position_entry_price,
                'exit': prices[-1],
                'pnl': pnl,
                'return': (prices[-1] - position_entry_price) / position_entry_price
            })
            position = 0
        
        final_capital = capital if position == 0 else position * prices[-1]
        
        # Calcular métricas
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100
        
        # Sharpe Ratio (simplificado, asumiendo 0% risk-free rate)
        if len(equity_curve) > 1:
            returns = np.diff(equity_curve) / equity_curve[:-1]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Max Drawdown
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max * 100
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        # Win Rate
        if trades:
            winning_trades = sum(1 for t in trades if t['pnl'] > 0)
            win_rate = winning_trades / len(trades) * 100
        else:
            win_rate = 0
        
        # Score compuesto para ranking
        # Prioriza: Sharpe Ratio (60%), Total Return (30%), Win Rate (10%)
        # Penaliza drawdown alto
        score = (
            sharpe_ratio * 0.6 +
            total_return / 100 * 0.3 +
            win_rate / 100 * 0.1 -
            max_drawdown / 100 * 0.2
        )
        
        return BacktestResult(
            strategy_name=strategy.name,
            params=strategy.params,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=len(trades),
            final_capital=final_capital,
            initial_capital=self.initial_capital,
            score=score
        )
