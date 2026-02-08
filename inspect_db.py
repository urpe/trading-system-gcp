#!/usr/bin/env python3
"""Quick DB inspection for migration planning."""
from src.shared.database import SessionLocal, Trade, Signal, MarketSnapshot

session = SessionLocal()

print("=== DATABASE INSPECTION ===\n")

# Check trades
trades_count = session.query(Trade).count()
print(f"Total Trades: {trades_count}")

if trades_count > 0:
    # Sample symbols
    sample_trades = session.query(Trade.symbol).distinct().limit(10).all()
    print(f"Sample Symbols: {[t[0] for t in sample_trades]}")
    
    # First trade
    first_trade = session.query(Trade).first()
    print(f"First Trade Symbol Format: '{first_trade.symbol}' (type: {type(first_trade.symbol).__name__})")

# Check signals
signals_count = session.query(Signal).count()
print(f"\nTotal Signals: {signals_count}")

# Check snapshots
snapshots_count = session.query(MarketSnapshot).count()
print(f"Total Snapshots: {snapshots_count}")

session.close()
