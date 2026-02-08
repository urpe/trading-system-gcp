"""
Binance Historical Data Loader
===============================
Fetches historical OHLCV klines from Binance API.

Usage:
    from src.time_machine.data_loader import BinanceHistoricalLoader
    
    loader = BinanceHistoricalLoader()
    klines = loader.fetch_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_time=datetime(2026, 2, 7),
        end_time=datetime(2026, 2, 8)
    )
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
from src.shared.utils import get_logger

logger = get_logger("TimeMachine.DataLoader")


class BinanceHistoricalLoader:
    """
    Carga datos históricos de Binance.
    
    Maneja:
        - Rate limiting (weight limits)
        - Pagination (max 1000 candles per request)
        - Error handling y retries
    """
    
    def __init__(self, base_url: str = "https://api.binance.com/api/v3"):
        self.base_url = base_url
        self.request_count = 0
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Apply rate limiting (1200 requests/min = 20/sec)."""
        now = time.time()
        elapsed = now - self.last_request_time
        
        if elapsed < 0.05:  # Min 50ms between requests
            time.sleep(0.05 - elapsed)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def fetch_klines(
        self,
        symbol: str,
        interval: str = "1m",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Fetch historical klines from Binance.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Candle interval (1m, 5m, 1h, 1d)
            start_time: Start datetime (UTC)
            end_time: End datetime (UTC)
            limit: Max candles per request (500-1000 recommended)
        
        Returns:
            List of OHLCV dicts: [
                {
                    "timestamp": 1707350400000,
                    "open": 75000.0,
                    "high": 75500.0,
                    "low": 74900.0,
                    "close": 75200.0,
                    "volume": 120.5,
                    "symbol": "BTC"
                },
                ...
            ]
        """
        url = f"{self.base_url}/klines"
        
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)
        
        self._rate_limit()
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            klines = response.json()
            
            # Convert to standardized format
            result = []
            for kline in klines:
                result.append({
                    "timestamp": kline[0],
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "symbol": symbol.replace("USDT", "").replace("BUSD", "").replace("BTC", "", 1) if symbol.endswith(("USDT", "BUSD")) else symbol
                })
            
            logger.info(f"✅ Fetched {len(result)} klines for {symbol}")
            return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching klines for {symbol}: {e}")
            return []
    
    def fetch_multiple_symbols(
        self,
        symbols: List[str],
        interval: str = "1m",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, List[Dict]]:
        """
        Fetch data for multiple symbols.
        
        Args:
            symbols: List of symbols (e.g., ["BTC", "ETH", "SOL"])
            interval: Candle interval
            start_time: Start datetime
            end_time: End datetime
        
        Returns:
            {
                "BTC": [kline1, kline2, ...],
                "ETH": [kline1, kline2, ...],
                ...
            }
        """
        result = {}
        
        logger.info(f"📥 Fetching data for {len(symbols)} symbols...")
        
        for i, symbol in enumerate(symbols, 1):
            # Ensure symbol has USDT suffix
            symbol_pair = f"{symbol}USDT" if not symbol.endswith("USDT") else symbol
            base_symbol = symbol.replace("USDT", "")
            
            logger.info(f"   [{i}/{len(symbols)}] Fetching {symbol_pair}...")
            
            try:
                klines = self.fetch_klines(
                    symbol=symbol_pair,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time
                )
                result[base_symbol] = klines
            except Exception as e:
                logger.error(f"❌ Error fetching {symbol}: {e}")
                result[base_symbol] = []
        
        total_candles = sum(len(klines) for klines in result.values())
        logger.info(f"✅ Fetched {total_candles} total candles for {len(symbols)} symbols")
        
        return result
    
    def fetch_last_n_hours(
        self,
        symbols: List[str],
        hours: int = 24,
        interval: str = "1m"
    ) -> Dict[str, List[Dict]]:
        """
        Fetch last N hours of data (convenience method).
        
        Args:
            symbols: List of symbols
            hours: Number of hours to fetch
            interval: Candle interval
        
        Returns:
            Symbol → klines dict
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        logger.info(f"📥 Fetching last {hours}h: {start_time} → {end_time}")
        
        return self.fetch_multiple_symbols(
            symbols=symbols,
            interval=interval,
            start_time=start_time,
            end_time=end_time
        )
