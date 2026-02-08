#!/usr/bin/env python3
"""
HYPER SIMULATION - Time Machine Execution
==========================================
Simula 24h de trading en minutos usando datos reales de ayer.

Responde la pregunta:
    "¿Cuánto habría ganado/perdido ayer con este código?"

Usage:
    python3 run_hyper_simulation.py                    # Last 24h at 60x speed
    python3 run_hyper_simulation.py --hours 48 --speed 120  # Custom
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List
from src.time_machine.data_loader import BinanceHistoricalLoader
from src.shared.utils import get_logger
from src.domain import TradingSymbol  # V22.1: Type-safe symbols

logger = get_logger("HyperSimulation.V22.1")


def print_header(text: str):
    """Print styled header."""
    print("\n" + "=" * 80)
    print(f"{text:^80}")
    print("=" * 80)


def print_section(text: str):
    """Print section header."""
    print(f"\n>>> {text}")
    print("-" * 80)


def calculate_metrics(signals: List[Dict], trades: List[Dict]) -> Dict:
    """
    Calculate trading metrics from simulation.
    
    Args:
        signals: List of signals generated
        trades: List of trades executed
    
    Returns:
        {
            'total_signals': int,
            'total_trades': int,
            'winning_trades': int,
            'losing_trades': int,
            'win_rate': float,
            'total_pnl': float,
            'avg_pnl_per_trade': float,
            'max_drawdown': float
        }
    """
    if not trades:
        return {
            'total_signals': len(signals),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'avg_pnl_per_trade': 0.0,
            'max_drawdown': 0.0
        }
    
    winning = [t for t in trades if t.get('pnl', 0) > 0]
    losing = [t for t in trades if t.get('pnl', 0) <= 0]
    
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    win_rate = (len(winning) / len(trades)) * 100 if trades else 0
    
    # Max drawdown
    cumulative_pnl = 0
    peak = 0
    max_dd = 0
    
    for trade in trades:
        cumulative_pnl += trade.get('pnl', 0)
        peak = max(peak, cumulative_pnl)
        drawdown = peak - cumulative_pnl
        max_dd = max(max_dd, drawdown)
    
    return {
        'total_signals': len(signals),
        'total_trades': len(trades),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl_per_trade': total_pnl / len(trades) if trades else 0,
        'max_drawdown': max_dd
    }


def simulate_brain_strategy(klines: List[Dict], symbol: TradingSymbol) -> List[Dict]:
    """
    Simulate Brain strategy on historical data.
    
    V22.1: Now uses TradingSymbol objects for type safety.
    
    Simplified version: RSI Mean Reversion.
    
    Args:
        klines: Historical OHLCV data
        symbol: TradingSymbol object (V22.1: type-safe)
    
    Returns:
        List of signals: [
            {'symbol': TradingSymbol(...), 'symbol_str': 'BTC', 'type': 'BUY', ...},
            ...
        ]
    """
    signals = []
    
    # Need at least 14 candles for RSI
    if len(klines) < 20:
        return signals
    
    # Calculate RSI
    prices = [k['close'] for k in klines]
    
    for i in range(14, len(prices)):
        # Simple RSI calculation
        window = prices[i-14:i]
        gains = [max(window[j] - window[j-1], 0) for j in range(1, len(window))]
        losses = [max(window[j-1] - window[j], 0) for j in range(1, len(window))]
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Generate signals (V22.1: Store TradingSymbol object)
        if rsi < 30:  # Oversold - BUY signal
            signals.append({
                'symbol': symbol,  # V22.1: TradingSymbol object
                'symbol_str': symbol.to_short(),  # For display
                'type': 'BUY',
                'price': prices[i],
                'timestamp': klines[i]['timestamp'],
                'rsi': rsi,
                'reason': f"RSI Oversold ({rsi:.1f} < 30)"
            })
        elif rsi > 70:  # Overbought - SELL signal
            signals.append({
                'symbol': symbol,  # V22.1: TradingSymbol object
                'symbol_str': symbol.to_short(),  # For display
                'type': 'SELL',
                'price': prices[i],
                'timestamp': klines[i]['timestamp'],
                'rsi': rsi,
                'reason': f"RSI Overbought ({rsi:.1f} > 70)"
            })
    
    return signals


def simulate_trades(signals: List[Dict], initial_balance: float = 1000.0) -> List[Dict]:
    """
    Simulate trade execution from signals.
    
    V22.1: Now handles TradingSymbol objects correctly.
    
    Simplified: Open position on signal, close on opposite signal or after 1h.
    
    Args:
        signals: List of signals (with TradingSymbol objects)
        initial_balance: Starting USDT balance
    
    Returns:
        List of trades with PnL (includes TradingSymbol objects)
    """
    trades = []
    open_positions = {}
    
    for signal in signals:
        # V22.1: Use symbol object, key by string for dict lookup
        symbol = signal['symbol']  # TradingSymbol object
        symbol_key = symbol.to_short()  # "BTC" for dict key
        
        if signal['type'] == 'BUY' and symbol_key not in open_positions:
            # Open long position
            open_positions[symbol_key] = {
                'symbol': symbol,  # V22.1: Store TradingSymbol object
                'entry_price': signal['price'],
                'entry_time': signal['timestamp'],
                'type': 'LONG'
            }
        
        elif signal['type'] == 'SELL':
            # Close long if exists, or open short
            if symbol_key in open_positions and open_positions[symbol_key]['type'] == 'LONG':
                # Close long
                position = open_positions[symbol_key]
                pnl = (signal['price'] - position['entry_price']) / position['entry_price'] * 100
                
                trades.append({
                    'symbol': symbol,  # V22.1: TradingSymbol object
                    'symbol_str': symbol_key,  # For display/reporting
                    'side': 'LONG',
                    'entry_price': position['entry_price'],
                    'exit_price': signal['price'],
                    'entry_time': position['entry_time'],
                    'exit_time': signal['timestamp'],
                    'pnl_pct': pnl,
                    'pnl': pnl * 10  # Assuming $1000 per trade
                })
                
                del open_positions[symbol_key]
    
    return trades


def main():
    parser = argparse.ArgumentParser(description='Hyper Simulation - Time Machine')
    parser.add_argument('--hours', type=int, default=24, help='Hours to simulate (default: 24)')
    parser.add_argument('--speed', type=int, default=60, help='Speed multiplier (default: 60x)')
    parser.add_argument('--symbols', default='BTC,ETH,SOL,ADA,DOGE', help='Comma-separated symbols')
    parser.add_argument('--output', default='SIMULATION_RESULT.md', help='Output report file')
    
    args = parser.parse_args()
    
    # Parse parameters
    symbols = [s.strip() for s in args.symbols.split(',')]
    hours = args.hours
    speed = args.speed
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    print_header("TIME MACHINE - HYPER SIMULATION")
    
    print(f"\nConfiguration:")
    print(f"  Period:       {start_time.strftime('%Y-%m-%d %H:%M')} → {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Duration:     {hours} hours")
    print(f"  Speed:        {speed}x real-time")
    print(f"  Symbols:      {', '.join(symbols)}")
    print(f"  Output:       {args.output}")
    
    expected_candles = hours * 60  # 1m interval
    simulation_time = expected_candles / speed
    
    print(f"\nExpected:")
    print(f"  Candles:      ~{expected_candles} per symbol")
    print(f"  Sim Time:     ~{simulation_time/60:.1f} minutes")
    
    # Step 1: Load historical data
    print_section("STEP 1/4: Loading Historical Data")
    
    loader = BinanceHistoricalLoader()
    
    try:
        symbols_data = loader.fetch_last_n_hours(
            symbols=symbols,
            hours=hours,
            interval="1m"
        )
    except Exception as e:
        logger.error(f"❌ Fatal error loading data: {e}")
        sys.exit(1)
    
    total_candles = sum(len(klines) for klines in symbols_data.values())
    print(f"✅ Loaded {total_candles} candles")
    
    # Step 2: Run simulation
    print_section("STEP 2/4: Running Strategy Simulation")
    
    all_signals = []
    
    for symbol_str, klines in symbols_data.items():
        if not klines:
            logger.warning(f"⚠️ No data for {symbol_str}, skipping")
            continue
        
        logger.info(f"   Simulating {symbol_str} ({len(klines)} candles)...")
        
        # V22.1: Convert string to TradingSymbol object
        try:
            symbol = TradingSymbol.from_str(symbol_str)
        except ValueError as e:
            logger.error(f"❌ Invalid symbol '{symbol_str}': {e}")
            continue
        
        signals = simulate_brain_strategy(klines, symbol)
        all_signals.extend(signals)
        
        print(f"   {symbol_str}: {len(signals)} signals generated")
    
    print(f"✅ Total signals generated: {len(all_signals)}")
    
    # Step 3: Simulate trades
    print_section("STEP 3/4: Simulating Trade Execution")
    
    trades = simulate_trades(all_signals)
    
    print(f"✅ Executed {len(trades)} trades")
    
    # Step 4: Calculate metrics
    print_section("STEP 4/4: Calculating Metrics")
    
    metrics = calculate_metrics(all_signals, trades)
    
    # Display results
    print_header("SIMULATION RESULTS")
    
    print(f"\n📊 Signal Generation:")
    print(f"  Total Signals:    {metrics['total_signals']}")
    print(f"  BUY signals:      {sum(1 for s in all_signals if s['type'] == 'BUY')}")
    print(f"  SELL signals:     {sum(1 for s in all_signals if s['type'] == 'SELL')}")
    
    print(f"\n💰 Trade Execution:")
    print(f"  Total Trades:     {metrics['total_trades']}")
    print(f"  Winning Trades:   {metrics['winning_trades']}")
    print(f"  Losing Trades:    {metrics['losing_trades']}")
    print(f"  Win Rate:         {metrics['win_rate']:.1f}%")
    
    print(f"\n📈 Performance:")
    print(f"  Total PnL:        ${metrics['total_pnl']:.2f}")
    print(f"  Avg PnL/Trade:    ${metrics['avg_pnl_per_trade']:.2f}")
    print(f"  Max Drawdown:     ${metrics['max_drawdown']:.2f}")
    
    # Verdict
    print(f"\n✅ VERDICT:")
    if metrics['total_pnl'] > 0:
        print(f"  ✅ PROFITABLE: Sistema habría ganado ${metrics['total_pnl']:.2f} ayer")
    else:
        print(f"  ⚠️ LOSS: Sistema habría perdido ${abs(metrics['total_pnl']):.2f} ayer")
    
    if metrics['win_rate'] >= 50:
        print(f"  ✅ WIN RATE GOOD: {metrics['win_rate']:.1f}% (>= 50% target)")
    else:
        print(f"  ⚠️ WIN RATE LOW: {metrics['win_rate']:.1f}% (< 50% target)")
    
    # Generate markdown report
    print_section("Generating Report")
    
    report_content = f"""# TIME MACHINE SIMULATION REPORT

**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Period:** {start_time.strftime('%Y-%m-%d %H:%M')} → {end_time.strftime('%Y-%m-%d %H:%M')}  
**Duration:** {hours} hours  
**Speed:** {speed}x real-time  
**Symbols:** {', '.join(symbols)}

---

## 📊 RESULTS SUMMARY

### Signal Generation
- **Total Signals:** {metrics['total_signals']}
- **BUY Signals:** {sum(1 for s in all_signals if s['type'] == 'BUY')}
- **SELL Signals:** {sum(1 for s in all_signals if s['type'] == 'SELL')}

### Trade Execution
- **Total Trades:** {metrics['total_trades']}
- **Winning Trades:** {metrics['winning_trades']}
- **Losing Trades:** {metrics['losing_trades']}
- **Win Rate:** {metrics['win_rate']:.1f}%

### Performance Metrics
- **Total PnL:** ${metrics['total_pnl']:.2f}
- **Avg PnL/Trade:** ${metrics['avg_pnl_per_trade']:.2f}
- **Max Drawdown:** ${metrics['max_drawdown']:.2f}

---

## ✅ VERDICT

"""
    
    if metrics['total_pnl'] > 0:
        report_content += f"✅ **PROFITABLE:** Sistema habría ganado **${metrics['total_pnl']:.2f}** en {hours}h.\n\n"
    else:
        report_content += f"⚠️ **LOSS:** Sistema habría perdido **${abs(metrics['total_pnl']):.2f}** en {hours}h.\n\n"
    
    if metrics['win_rate'] >= 50:
        report_content += f"✅ **WIN RATE:** {metrics['win_rate']:.1f}% (>= 50% target) - GOOD\n\n"
    else:
        report_content += f"⚠️ **WIN RATE:** {metrics['win_rate']:.1f}% (< 50% target) - NEEDS IMPROVEMENT\n\n"
    
    # Add detailed trades table
    report_content += "---\n\n## 📋 DETAILED TRADES\n\n"
    report_content += "| # | Symbol | Side | Entry | Exit | PnL % | PnL $ |\n"
    report_content += "|---|--------|------|-------|------|-------|-------|\n"
    
    for i, trade in enumerate(trades, 1):
        # V22.1: Use symbol_str for display
        symbol_display = trade.get('symbol_str', trade['symbol'].to_short() if hasattr(trade['symbol'], 'to_short') else str(trade['symbol']))
        report_content += f"| {i} | {symbol_display} | {trade['side']} | ${trade['entry_price']:.2f} | ${trade['exit_price']:.2f} | {trade['pnl_pct']:.2f}% | ${trade['pnl']:.2f} |\n"
    
    report_content += "\n---\n\n"
    report_content += f"**Report Generated:** {datetime.now().isoformat()}  \n"
    report_content += f"**System Version:** V22.1 (Type-Safe Persistence)  \n"
    
    # Save report
    with open(args.output, 'w') as f:
        f.write(report_content)
    
    print(f"✅ Report saved: {args.output}")
    
    # Also save JSON (V22.1: Serialize TradingSymbol objects to strings)
    json_output = args.output.replace('.md', '.json')
    
    # Convert TradingSymbol objects to strings for JSON serialization
    def serialize_for_json(obj):
        """Convert TradingSymbol objects to dicts for JSON."""
        if isinstance(obj, dict):
            return {k: serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [serialize_for_json(item) for item in obj]
        elif isinstance(obj, TradingSymbol):
            return obj.to_dict()  # Use built-in to_dict() method
        else:
            return obj
    
    with open(json_output, 'w') as f:
        json.dump({
            'config': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'hours': hours,
                'speed': speed,
                'symbols': symbols
            },
            'metrics': metrics,
            'signals': serialize_for_json(all_signals),
            'trades': serialize_for_json(trades)
        }, f, indent=2)
    
    print(f"✅ JSON data saved: {json_output}")
    
    print_header("SIMULATION COMPLETE")
    
    # Return exit code based on results
    if metrics['total_pnl'] > 0 and metrics['win_rate'] >= 45:
        print("\n✅ SIMULATION PASSED: System would be profitable\n")
        return 0
    else:
        print("\n⚠️ SIMULATION WARNING: System needs improvement\n")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Simulation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
