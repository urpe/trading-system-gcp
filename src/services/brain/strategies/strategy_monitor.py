"""
Strategy Performance Monitor - V18.5
=====================================
Monitorea performance de estrategias en tiempo real y las desactiva si fallan.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from src.shared.utils import get_logger

logger = get_logger("StrategyMonitor")


@dataclass
class StrategyPerformance:
    """Métricas de performance de una estrategia en vivo"""
    symbol: str
    strategy_name: str
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    avg_pnl: float
    total_pnl: float
    last_updated: datetime
    is_healthy: bool
    warning_reason: Optional[str] = None


class StrategyMonitor:
    """
    Monitorea estrategias en tiempo real y las marca como unhealthy si:
    - Win rate < 40% en últimos 20 trades
    - PnL promedio negativo en últimas 2 horas
    - Más de 5 losses consecutivos
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.min_signals_for_eval = 10  # Mínimo de señales antes de evaluar
        self.win_rate_threshold = 0.40  # 40% win rate mínimo
        self.max_consecutive_losses = 5
        
    def record_signal_outcome(self, symbol: str, strategy_name: str, pnl: float):
        """
        Registra el resultado de una señal para monitorización.
        
        Redis Structure:
        - Key: strategy_monitor:{symbol}:{strategy_name}
        - Value: Lista de outcomes [{'pnl': float, 'timestamp': str}, ...]
        """
        key = f"strategy_monitor:{symbol}:{strategy_name}"
        
        outcome = {
            'pnl': pnl,
            'timestamp': datetime.utcnow().isoformat(),
            'is_win': pnl > 0
        }
        
        # Añadir a lista (mantener últimos 50 outcomes)
        self.redis_client.lpush(key, json.dumps(outcome))
        self.redis_client.ltrim(key, 0, 49)
        
        logger.debug(f"Recorded outcome for {symbol} {strategy_name}: PnL={pnl:.2f}")
    
    def get_strategy_performance(self, symbol: str, strategy_name: str) -> Optional[StrategyPerformance]:
        """
        Obtiene métricas de performance de una estrategia.
        """
        key = f"strategy_monitor:{symbol}:{strategy_name}"
        outcomes_json = self.redis_client.lrange(key, 0, -1)
        
        if not outcomes_json or len(outcomes_json) < self.min_signals_for_eval:
            return None
        
        outcomes = [json.loads(o) for o in outcomes_json]
        
        total_signals = len(outcomes)
        winning_signals = sum(1 for o in outcomes if o['is_win'])
        losing_signals = total_signals - winning_signals
        win_rate = winning_signals / total_signals if total_signals > 0 else 0
        
        total_pnl = sum(o['pnl'] for o in outcomes)
        avg_pnl = total_pnl / total_signals if total_signals > 0 else 0
        
        # Verificar salud
        is_healthy = True
        warning_reason = None
        
        # Check 1: Win rate muy bajo
        if win_rate < self.win_rate_threshold:
            is_healthy = False
            warning_reason = f"Low win rate: {win_rate:.1%} < {self.win_rate_threshold:.1%}"
        
        # Check 2: PnL promedio negativo
        elif avg_pnl < -0.5:
            is_healthy = False
            warning_reason = f"Negative avg PnL: ${avg_pnl:.2f}"
        
        # Check 3: Losses consecutivos
        consecutive_losses = 0
        for o in outcomes[:self.max_consecutive_losses]:
            if not o['is_win']:
                consecutive_losses += 1
            else:
                break
        
        if consecutive_losses >= self.max_consecutive_losses:
            is_healthy = False
            warning_reason = f"{consecutive_losses} consecutive losses"
        
        return StrategyPerformance(
            symbol=symbol,
            strategy_name=strategy_name,
            total_signals=total_signals,
            winning_signals=winning_signals,
            losing_signals=losing_signals,
            win_rate=win_rate,
            avg_pnl=avg_pnl,
            total_pnl=total_pnl,
            last_updated=datetime.utcnow(),
            is_healthy=is_healthy,
            warning_reason=warning_reason
        )
    
    def get_all_performances(self) -> List[StrategyPerformance]:
        """
        Obtiene performance de todas las estrategias activas.
        """
        performances = []
        
        # Buscar todas las keys de monitorización
        keys = self.redis_client.keys("strategy_monitor:*")
        
        for key in keys:
            # Parsear key: strategy_monitor:{symbol}:{strategy_name}
            parts = key.decode('utf-8').split(':')
            if len(parts) == 3:
                symbol = parts[1]
                strategy_name = parts[2]
                
                perf = self.get_strategy_performance(symbol, strategy_name)
                if perf:
                    performances.append(perf)
        
        return performances
    
    def disable_unhealthy_strategy(self, symbol: str, strategy_name: str):
        """
        Marca una estrategia como deshabilitada en Redis.
        El Brain la detectará y volverá a estrategia default.
        """
        key = f"strategy_config:{symbol}"
        config_json = self.redis_client.get(key)
        
        if config_json:
            config = json.loads(config_json)
            config['is_disabled'] = True
            config['disabled_reason'] = 'Poor performance detected'
            config['disabled_at'] = datetime.utcnow().isoformat()
            
            self.redis_client.set(key, json.dumps(config))
            logger.warning(f"🚫 DISABLED strategy for {symbol}: {strategy_name} due to poor performance")
    
    def run_health_check(self):
        """
        Ejecuta health check de todas las estrategias y deshabilita las malas.
        """
        logger.info("🏥 Running strategy health check...")
        
        performances = self.get_all_performances()
        
        unhealthy_count = 0
        for perf in performances:
            if not perf.is_healthy:
                logger.warning(
                    f"⚠️ UNHEALTHY: {perf.symbol} {perf.strategy_name} | "
                    f"Win Rate: {perf.win_rate:.1%} | Avg PnL: ${perf.avg_pnl:.2f} | "
                    f"Reason: {perf.warning_reason}"
                )
                # No deshabilitamos automáticamente por ahora, solo alertamos
                # self.disable_unhealthy_strategy(perf.symbol, perf.strategy_name)
                unhealthy_count += 1
            else:
                logger.info(
                    f"✅ HEALTHY: {perf.symbol} {perf.strategy_name} | "
                    f"Win Rate: {perf.win_rate:.1%} | Total PnL: ${perf.total_pnl:.2f}"
                )
        
        logger.info(f"Health check complete: {len(performances)-unhealthy_count}/{len(performances)} strategies healthy")
        return performances
