"""
HFT Trading Bot V19 - Regime Switching Intelligence
====================================================
Sistema adaptativo con detección de régimen de mercado y 9 estrategias avanzadas.
"""

from .base import StrategyInterface, StrategyResult
from .sma_crossover import SmaCrossover
from .rsi_mean_reversion import RsiMeanReversion
from .bollinger_breakout import BollingerBreakout
from .macd_strategy import MacdStrategy
from .ema_triple_cross import EmaTripleCross
from .ichimoku_cloud import IchimokuCloud
from .keltner_channels import KeltnerChannels
from .adx_trend_filter import AdxTrendFilter
from .volume_profile import VolumeProfileStrategy

# Registry de estrategias disponibles (9 total)
AVAILABLE_STRATEGIES = {
    # Trend Following Strategies
    'SmaCrossover': SmaCrossover,
    'EmaTripleCross': EmaTripleCross,
    'IchimokuCloud': IchimokuCloud,
    'MacdStrategy': MacdStrategy,
    'AdxTrendFilter': AdxTrendFilter,
    
    # Mean Reversion Strategies
    'RsiMeanReversion': RsiMeanReversion,
    'BollingerBreakout': BollingerBreakout,
    'KeltnerChannels': KeltnerChannels,
    'VolumeProfileStrategy': VolumeProfileStrategy
}

__all__ = [
    'StrategyInterface',
    'StrategyResult',
    'SmaCrossover',
    'RsiMeanReversion',
    'BollingerBreakout',
    'MacdStrategy',
    'EmaTripleCross',
    'IchimokuCloud',
    'KeltnerChannels',
    'AdxTrendFilter',
    'VolumeProfileStrategy',
    'AVAILABLE_STRATEGIES'
]
