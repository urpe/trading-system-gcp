# TIME MACHINE - EVENT-DRIVEN SIMULATION ARCHITECTURE

**Concepto:** "Digital Twin" del trading system  
**Fecha Diseño:** 2026-02-08  
**Inspiración:** HFT Institutional Backtesting (Event-Driven)  
**Objetivo:** Simular sistema completo con datos históricos a velocidad acelerada

---

## 🎯 CONCEPTO: ¿QUÉ ES EL TIME MACHINE?

### **NO es:**
- ❌ Un simple script de backtest
- ❌ Una estrategia evaluando datos del pasado
- ❌ Un test unitario

### **SÍ es:**
- ✅ **Digital Twin:** Réplica completa del sistema (Brain, Orders, Redis, DB)
- ✅ **Event-Driven:** Inyecta eventos históricos (velas OHLCV) como si fueran en tiempo real
- ✅ **Time-Compressed:** 1 día de datos en 5 minutos de simulación
- ✅ **Ecosystem Simulation:** Incluye latencia, spreads, slippage, comisiones

**Pregunta que responde:**
> "Si este código hubiera estado corriendo ayer, ¿cuánto habría ganado/perdido?"

---

## 🏗️ ARQUITECTURA

### **Componentes del Time Machine:**

```
┌─────────────────────────────────────────────────────────────────┐
│  TIME MACHINE CONTROLLER (run_time_machine.py)                  │
│                                                                  │
│  1. Load historical data (Binance API)                          │
│  2. Create ephemeral environment (Redis, SQLite)                │
│  3. Inject events at accelerated speed                          │
│  4. Capture results (signals, trades, PnL)                      │
│  5. Generate report                                             │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  SIMULATED REDIS (Ephemeral)                                    │
│                                                                  │
│  - market_data channel (injected events)                        │
│  - signals channel (Brain output)                               │
│  - active_symbols key                                           │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  SIMULATED BRAIN (In-Process or Dockerized)                     │
│                                                                  │
│  - Subscribes to market_data                                    │
│  - Processes OHLCV candles                                      │
│  - Publishes signals                                            │
│  - Uses simulated clock (not real time)                         │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  SIMULATED ORDERS (In-Process or Dockerized)                    │
│                                                                  │
│  - Executes trades based on signals                             │
│  - Writes to ephemeral SQLite DB                                │
│  - Tracks wallet balance                                        │
│  - Applies slippage + commissions                               │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  SIMULATION REPORT                                               │
│                                                                  │
│  - Total PnL                                                     │
│  - Win rate                                                      │
│  - Max drawdown                                                  │
│  - Sharpe ratio                                                  │
│  - Trade list (CSV)                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 IMPLEMENTATION PLAN

### **Phase 1: Data Loader (1 día)**

**Archivo:** `src/time_machine/data_loader.py` (NUEVO)

```python
import requests
from datetime import datetime, timedelta
from typing import List, Dict

class BinanceHistoricalLoader:
    """
    Carga datos históricos de Binance.
    
    Ejemplo:
        loader = BinanceHistoricalLoader()
        klines = loader.fetch_klines(
            symbol="BTCUSDT",
            interval="1m",
            start_time=datetime(2026, 2, 7, 0, 0, 0),
            end_time=datetime(2026, 2, 8, 0, 0, 0)
        )
        # Returns: 1440 klines (24h * 60m)
    """
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
    
    def fetch_klines(
        self,
        symbol: str,
        interval: str = "1m",
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Fetch historical klines from Binance.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Candle interval (1m, 5m, 1h, etc.)
            start_time: Start datetime (UTC)
            end_time: End datetime (UTC)
            limit: Max candles per request (1000 max)
        
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
        
        response = requests.get(url, params=params)
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
                "symbol": symbol.replace("USDT", "")  # "BTCUSDT" -> "BTC"
            })
        
        return result
    
    def fetch_multiple_symbols(
        self,
        symbols: List[str],
        interval: str = "1m",
        start_time: datetime = None,
        end_time: datetime = None
    ) -> Dict[str, List[Dict]]:
        """
        Fetch data for multiple symbols.
        
        Returns:
            {
                "BTC": [kline1, kline2, ...],
                "ETH": [kline1, kline2, ...],
                ...
            }
        """
        result = {}
        
        for symbol in symbols:
            symbol_pair = f"{symbol}USDT" if not symbol.endswith("USDT") else symbol
            
            try:
                klines = self.fetch_klines(
                    symbol=symbol_pair,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time
                )
                result[symbol.replace("USDT", "")] = klines
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                result[symbol] = []
        
        return result
```

---

### **Phase 2: Event Injector (1 día)**

**Archivo:** `src/time_machine/event_injector.py` (NUEVO)

```python
import redis
import json
import time
from typing import List, Dict
from datetime import datetime

class EventInjector:
    """
    Inyecta eventos históricos en Redis a velocidad acelerada.
    
    Ejemplo:
        injector = EventInjector(redis_client, speed_multiplier=60)
        
        # 1 minuto de datos históricos se inyecta en 1 segundo
        injector.inject_events(klines, channel="market_data")
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        speed_multiplier: int = 60,  # 60x real-time = 1 hora en 1 minuto
        simulated_clock: 'SimulatedClock' = None
    ):
        self.redis = redis_client
        self.speed_multiplier = speed_multiplier
        self.clock = simulated_clock
    
    def inject_events(
        self,
        klines: List[Dict],
        channel: str = "market_data",
        delay_between_events: float = None
    ):
        """
        Inject historical klines as real-time events.
        
        Args:
            klines: List of OHLCV dicts
            channel: Redis Pub/Sub channel
            delay_between_events: Seconds between events (calculated if None)
        """
        if not klines:
            return
        
        # Calculate delay
        if delay_between_events is None:
            # Assuming 1m candles
            real_interval = 60  # seconds
            delay_between_events = real_interval / self.speed_multiplier
        
        print(f"Injecting {len(klines)} events at {self.speed_multiplier}x speed")
        print(f"Delay between events: {delay_between_events:.3f}s")
        print(f"Total simulation time: {len(klines) * delay_between_events:.1f}s")
        
        for i, kline in enumerate(klines):
            # Publish event
            self.redis.publish(channel, json.dumps(kline))
            
            # Update simulated clock
            if self.clock:
                self.clock.set_time(kline["timestamp"])
            
            # Progress
            if (i + 1) % 100 == 0:
                print(f"  Injected {i+1}/{len(klines)} events...")
            
            # Wait
            if i < len(klines) - 1:  # Don't wait after last event
                time.sleep(delay_between_events)
        
        print(f"✅ Injection complete: {len(klines)} events")
    
    def inject_multiple_symbols(
        self,
        symbols_data: Dict[str, List[Dict]],
        channel: str = "market_data"
    ):
        """
        Inject data for multiple symbols (interleaved by timestamp).
        
        Args:
            symbols_data: {"BTC": [klines], "ETH": [klines], ...}
            channel: Redis channel
        """
        # Merge and sort all klines by timestamp
        all_klines = []
        
        for symbol, klines in symbols_data.items():
            all_klines.extend(klines)
        
        # Sort by timestamp
        all_klines.sort(key=lambda k: k["timestamp"])
        
        # Inject
        self.inject_events(all_klines, channel)
```

---

### **Phase 3: Simulated Clock (0.5 días)**

**Archivo:** `src/time_machine/simulated_clock.py` (NUEVO)

```python
from datetime import datetime
from typing import Optional

class SimulatedClock:
    """
    Reloj simulado para Time Machine.
    
    Permite que servicios usen "tiempo simulado" en lugar de tiempo real.
    
    Uso:
        clock = SimulatedClock()
        clock.set_time(1707350400000)  # Set to specific timestamp
        
        # En servicios:
        if simulated_clock:
            current_time = simulated_clock.now()
        else:
            current_time = datetime.now()
    """
    
    def __init__(self, initial_time: Optional[int] = None):
        """
        Args:
            initial_time: Timestamp in milliseconds (optional)
        """
        self._current_time_ms = initial_time or int(datetime.now().timestamp() * 1000)
    
    def set_time(self, timestamp_ms: int):
        """Set current simulated time."""
        self._current_time_ms = timestamp_ms
    
    def now(self) -> datetime:
        """Get current simulated time as datetime."""
        return datetime.fromtimestamp(self._current_time_ms / 1000)
    
    def now_ms(self) -> int:
        """Get current simulated time as milliseconds."""
        return self._current_time_ms
    
    def advance(self, seconds: float):
        """Advance clock by N seconds."""
        self._current_time_ms += int(seconds * 1000)
```

---

### **Phase 4: Simulation Controller (2 días)**

**Archivo:** `run_time_machine.py` (NUEVO, root level)

```python
#!/usr/bin/env python3
"""
TIME MACHINE - Event-Driven System Simulator
=============================================
Simula el sistema completo con datos históricos a velocidad acelerada.

Uso:
    # Simular últimas 24h a 60x speed (24h en 24 minutos)
    python3 run_time_machine.py --period 24h --speed 60x
    
    # Simular fecha específica
    python3 run_time_machine.py --date 2026-02-07 --speed 120x
    
    # Simular con símbolos específicos
    python3 run_time_machine.py --symbols BTC,ETH,SOL --period 12h
"""

import argparse
import redis
from datetime import datetime, timedelta
from src.time_machine.data_loader import BinanceHistoricalLoader
from src.time_machine.event_injector import EventInjector
from src.time_machine.simulated_clock import SimulatedClock
from src.time_machine.results_analyzer import ResultsAnalyzer

def parse_period(period_str: str) -> timedelta:
    """Convert '24h', '7d', '1w' to timedelta."""
    unit = period_str[-1]
    value = int(period_str[:-1])
    
    if unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    else:
        raise ValueError(f"Invalid period: {period_str}")

def main():
    parser = argparse.ArgumentParser(description='Time Machine Simulator')
    parser.add_argument('--period', default='24h', help='Simulation period (24h, 7d, 1w)')
    parser.add_argument('--date', help='Specific date (YYYY-MM-DD)')
    parser.add_argument('--speed', type=int, default=60, help='Speed multiplier (60x = 1h in 1min)')
    parser.add_argument('--symbols', default='BTC,ETH,SOL', help='Comma-separated symbols')
    parser.add_argument('--output', default='simulation_report.json', help='Output report file')
    
    args = parser.parse_args()
    
    # Parse parameters
    symbols = args.symbols.split(',')
    speed_multiplier = args.speed
    
    if args.date:
        end_time = datetime.strptime(args.date, '%Y-%m-%d')
        period = parse_period(args.period)
        start_time = end_time - period
    else:
        end_time = datetime.now()
        period = parse_period(args.period)
        start_time = end_time - period
    
    print("=" * 80)
    print("TIME MACHINE - Event-Driven Simulation")
    print("=" * 80)
    print(f"Period:        {start_time} → {end_time}")
    print(f"Duration:      {period}")
    print(f"Speed:         {speed_multiplier}x real-time")
    print(f"Symbols:       {symbols}")
    print(f"Output:        {args.output}")
    print("=" * 80)
    
    # Step 1: Load historical data
    print("\n[1/5] Loading historical data from Binance...")
    loader = BinanceHistoricalLoader()
    symbols_data = loader.fetch_multiple_symbols(
        symbols=symbols,
        interval="1m",
        start_time=start_time,
        end_time=end_time
    )
    
    total_candles = sum(len(klines) for klines in symbols_data.values())
    print(f"✅ Loaded {total_candles} candles for {len(symbols)} symbols")
    
    # Step 2: Create ephemeral Redis connection
    print("\n[2/5] Connecting to Redis (simulation mode)...")
    redis_client = redis.Redis(host='localhost', port=6379, db=15)  # Use DB 15 for simulation
    redis_client.flushdb()  # Clear simulation DB
    print("✅ Redis simulation DB ready (DB 15)")
    
    # Step 3: Initialize simulated clock
    print("\n[3/5] Initializing simulated clock...")
    clock = SimulatedClock(initial_time=int(start_time.timestamp() * 1000))
    print(f"✅ Clock initialized at {clock.now()}")
    
    # Step 4: Set up active_symbols in Redis
    print("\n[4/5] Setting up environment...")
    redis_client.set("active_symbols", json.dumps(symbols))
    print(f"✅ active_symbols set: {symbols}")
    
    # Step 5: Inject events
    print("\n[5/5] Injecting events (simulation running)...")
    print(f"⏱️  Estimated time: {total_candles / speed_multiplier / 60:.1f} minutes")
    
    injector = EventInjector(
        redis_client=redis_client,
        speed_multiplier=speed_multiplier,
        simulated_clock=clock
    )
    
    injector.inject_multiple_symbols(symbols_data, channel="market_data")
    
    # Step 6: Analyze results
    print("\n[6/6] Analyzing results...")
    analyzer = ResultsAnalyzer(redis_client=redis_client)
    report = analyzer.generate_report()
    
    # Save report
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Report saved: {args.output}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SIMULATION SUMMARY")
    print("=" * 80)
    print(f"Total Signals: {report['total_signals']}")
    print(f"Total Trades:  {report['total_trades']}")
    print(f"Final PnL:     ${report['pnl']:.2f}")
    print(f"Win Rate:      {report['win_rate']:.1f}%")
    print("=" * 80)

if __name__ == '__main__':
    main()
```

---

## 🧪 USAGE EXAMPLES

### **Example 1: Simulate Yesterday**
```bash
# Simulate what would have happened yesterday at 60x speed
python3 run_time_machine.py --period 24h --speed 60

# Expected output:
# - Simulation completes in ~24 minutes (24h / 60x)
# - Report shows: signals, trades, PnL
```

### **Example 2: Simulate Specific Date**
```bash
# Test code against specific market event
python3 run_time_machine.py --date 2026-02-07 --speed 120

# Use case: "The crash of Feb 7" - would system have survived?
```

### **Example 3: Fast Stress Test**
```bash
# Simulate 7 days at 240x speed (7 days in 42 minutes)
python3 run_time_machine.py --period 7d --speed 240

# Use case: Longevity test, find memory leaks
```

---

## 📊 OUTPUT REPORT FORMAT

```json
{
  "simulation_config": {
    "start_time": "2026-02-07T00:00:00",
    "end_time": "2026-02-08T00:00:00",
    "duration_hours": 24,
    "speed_multiplier": 60,
    "symbols": ["BTC", "ETH", "SOL"]
  },
  "results": {
    "total_signals": 45,
    "signals_by_type": {
      "BUY": 23,
      "SELL": 22
    },
    "total_trades": 12,
    "winning_trades": 7,
    "losing_trades": 5,
    "win_rate": 58.3,
    "pnl": 245.67,
    "pnl_percentage": 2.45,
    "max_drawdown": -120.50,
    "sharpe_ratio": 1.85
  },
  "trades": [
    {
      "symbol": "BTC",
      "side": "BUY",
      "entry_price": 75000.0,
      "exit_price": 75500.0,
      "pnl": 50.0,
      "entry_time": "2026-02-07T03:15:00",
      "exit_time": "2026-02-07T04:30:00"
    },
    ...
  ]
}
```

---

## ✅ NEXT STEPS

1. **Implementar Phase 1** (Data Loader) - 1 día
2. **Implementar Phase 2** (Event Injector) - 1 día
3. **Implementar Phase 3** (Simulated Clock) - 0.5 días
4. **Implementar Phase 4** (Controller) - 2 días
5. **Testing** - 0.5 días

**TOTAL:** ~5 días para Time Machine completo

---

**Status:** 📋 DESIGN COMPLETE - Ready for implementation  
**Próximo paso:** Aprobar diseño → Implementar Phase 1 (Data Loader)

---

**Documento generado:** 2026-02-08  
**Autor:** HFT Trading Bot Team  
**Inspiración:** Institutional HFT Backtesting Systems
