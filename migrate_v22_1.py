#!/usr/bin/env python3
"""
V22.1 Database Migration Script
================================
Migra datos del formato viejo (strings) al nuevo formato (JSON con TradingSymbol).

Safety Features:
    - Dry-run mode (--dry-run) para preview sin modificar datos
    - Validación pre/post migración
    - Manejo de excepciones robusto
    - Logging detallado de cada cambio

Usage:
    # Preview (no changes)
    python3 migrate_v22_1.py --dry-run
    
    # Execute migration
    python3 migrate_v22_1.py
    
    # Validate only (after manual migration)
    python3 migrate_v22_1.py --validate-only

Author: HFT Trading Bot Team
Version: V22.1
Date: 2026-02-08
"""

import argparse
import sys
from datetime import datetime
from src.shared.database import SessionLocal, Trade, Signal, MarketSnapshot, PairsSignal
from src.shared.database_types import (
    validate_trading_symbol_column,
    convert_string_to_trading_symbol_json
)
from src.shared.utils import get_logger

logger = get_logger("MigrationV22.1")


def print_header(text: str):
    """Print styled header."""
    print("\n" + "=" * 80)
    print(f"{text:^80}")
    print("=" * 80)


def print_section(text: str):
    """Print section header."""
    print(f"\n>>> {text}")
    print("-" * 80)


def validate_pre_migration(session) -> dict:
    """
    Validate database state before migration.
    
    Returns:
        {
            'trades': {...validation result...},
            'signals': {...},
            'market_snapshots': {...},
            'pairs_signals_a': {...},
            'pairs_signals_b': {...}
        }
    """
    print_section("PRE-MIGRATION VALIDATION")
    
    results = {}
    
    # Validate Trade.symbol
    logger.info("Validating Trade.symbol...")
    results['trades'] = validate_trading_symbol_column(session, 'trades', 'symbol')
    print(f"  Trades: {results['trades']['total_rows']} rows")
    print(f"    - Valid JSON: {results['trades']['valid_json']}")
    print(f"    - Old format: {results['trades']['old_format']}")
    print(f"    - Invalid: {results['trades']['invalid']}")
    
    # Validate Signal.symbol
    logger.info("Validating Signal.symbol...")
    results['signals'] = validate_trading_symbol_column(session, 'signals', 'symbol')
    print(f"  Signals: {results['signals']['total_rows']} rows")
    print(f"    - Valid JSON: {results['signals']['valid_json']}")
    print(f"    - Old format: {results['signals']['old_format']}")
    print(f"    - Invalid: {results['signals']['invalid']}")
    
    # Validate MarketSnapshot.symbol
    logger.info("Validating MarketSnapshot.symbol...")
    results['market_snapshots'] = validate_trading_symbol_column(session, 'market_snapshots', 'symbol')
    print(f"  Market Snapshots: {results['market_snapshots']['total_rows']} rows")
    print(f"    - Valid JSON: {results['market_snapshots']['valid_json']}")
    print(f"    - Old format: {results['market_snapshots']['old_format']}")
    print(f"    - Invalid: {results['market_snapshots']['invalid']}")
    
    # Validate PairsSignal.asset_a
    logger.info("Validating PairsSignal.asset_a...")
    results['pairs_signals_a'] = validate_trading_symbol_column(session, 'pairs_signals', 'asset_a')
    print(f"  Pairs Signals (asset_a): {results['pairs_signals_a']['total_rows']} rows")
    print(f"    - Valid JSON: {results['pairs_signals_a']['valid_json']}")
    print(f"    - Old format: {results['pairs_signals_a']['old_format']}")
    print(f"    - Invalid: {results['pairs_signals_a']['invalid']}")
    
    # Validate PairsSignal.asset_b
    logger.info("Validating PairsSignal.asset_b...")
    results['pairs_signals_b'] = validate_trading_symbol_column(session, 'pairs_signals', 'asset_b')
    print(f"  Pairs Signals (asset_b): {results['pairs_signals_b']['total_rows']} rows")
    print(f"    - Valid JSON: {results['pairs_signals_b']['valid_json']}")
    print(f"    - Old format: {results['pairs_signals_b']['old_format']}")
    print(f"    - Invalid: {results['pairs_signals_b']['invalid']}")
    
    # Check for any errors
    total_invalid = sum(r['invalid'] for r in results.values())
    
    if total_invalid > 0:
        print(f"\n⚠️  WARNING: Found {total_invalid} invalid symbols")
        print("    These rows will be logged but not migrated")
        
        for table, result in results.items():
            if result['errors']:
                print(f"\n    Errors in {table}:")
                for error in result['errors'][:5]:  # Show first 5
                    print(f"      - Row {error['row_id']}: '{error['value']}' - {error['error']}")
    
    return results


def execute_migration(session, dry_run: bool = False) -> dict:
    """
    Execute migration for all tables.
    
    Args:
        session: SQLAlchemy session
        dry_run: If True, only preview changes without committing
    
    Returns:
        {
            'trades': migrated_count,
            'signals': migrated_count,
            'market_snapshots': migrated_count,
            'pairs_signals_a': migrated_count,
            'pairs_signals_b': migrated_count,
            'total': total_migrated
        }
    """
    print_section(f"{'DRY-RUN: ' if dry_run else ''}EXECUTING MIGRATION")
    
    results = {}
    
    # Migrate Trade.symbol
    logger.info("Migrating Trade.symbol...")
    results['trades'] = convert_string_to_trading_symbol_json(session, 'trades', 'symbol')
    print(f"  ✅ Trades: {results['trades']} rows migrated")
    
    # Migrate Signal.symbol
    logger.info("Migrating Signal.symbol...")
    results['signals'] = convert_string_to_trading_symbol_json(session, 'signals', 'symbol')
    print(f"  ✅ Signals: {results['signals']} rows migrated")
    
    # Migrate MarketSnapshot.symbol
    logger.info("Migrating MarketSnapshot.symbol...")
    results['market_snapshots'] = convert_string_to_trading_symbol_json(session, 'market_snapshots', 'symbol')
    print(f"  ✅ Market Snapshots: {results['market_snapshots']} rows migrated")
    
    # Migrate PairsSignal.asset_a
    logger.info("Migrating PairsSignal.asset_a...")
    results['pairs_signals_a'] = convert_string_to_trading_symbol_json(session, 'pairs_signals', 'asset_a')
    print(f"  ✅ Pairs Signals (asset_a): {results['pairs_signals_a']} rows migrated")
    
    # Migrate PairsSignal.asset_b
    logger.info("Migrating PairsSignal.asset_b...")
    results['pairs_signals_b'] = convert_string_to_trading_symbol_json(session, 'pairs_signals', 'asset_b')
    print(f"  ✅ Pairs Signals (asset_b): {results['pairs_signals_b']} rows migrated")
    
    results['total'] = sum(results.values())
    
    if dry_run:
        print(f"\n🔍 DRY-RUN: Would migrate {results['total']} total rows (no changes made)")
        session.rollback()
    else:
        print(f"\n✅ Migrated {results['total']} total rows")
        session.commit()
        logger.info(f"✅ Migration committed successfully")
    
    return results


def validate_post_migration(session) -> bool:
    """
    Validate database state after migration.
    
    Returns:
        True if all validations pass, False otherwise
    """
    print_section("POST-MIGRATION VALIDATION")
    
    results = validate_pre_migration(session)
    
    # Check that all rows are now in new format
    all_valid = True
    
    for table, result in results.items():
        old_format_count = result['old_format']
        invalid_count = result['invalid']
        
        if old_format_count > 0:
            print(f"  ⚠️  {table}: Still has {old_format_count} rows in old format")
            all_valid = False
        
        if invalid_count > 0:
            print(f"  ❌ {table}: Has {invalid_count} invalid rows")
            all_valid = False
    
    if all_valid:
        print("\n✅ POST-MIGRATION VALIDATION PASSED")
        print("   All symbols are in new JSON format")
    else:
        print("\n⚠️  POST-MIGRATION VALIDATION FAILED")
        print("   Some rows were not migrated successfully")
    
    return all_valid


def test_read_write(session):
    """
    Test that we can read and write TradingSymbol objects after migration.
    """
    print_section("FUNCTIONALITY TEST")
    
    from src.domain import TradingSymbol
    
    try:
        # Test 1: Read existing trade
        first_trade = session.query(Trade).first()
        
        if first_trade:
            print(f"  ✅ Read Trade #{first_trade.id}")
            print(f"     - symbol type: {type(first_trade.symbol).__name__}")
            print(f"     - symbol value: {first_trade.symbol.to_short()}")
            print(f"     - base: {first_trade.symbol.base}")
            print(f"     - quote: {first_trade.symbol.quote.value}")
        else:
            print("  ⚠️  No trades in database to test")
        
        # Test 2: Create new trade with TradingSymbol
        test_symbol = TradingSymbol.from_str("TEST")
        test_trade = Trade(
            symbol=test_symbol,
            side='LONG',
            amount=1.0,
            entry_price=100.0,
            status='TEST'
        )
        session.add(test_trade)
        session.flush()  # Don't commit, just test
        
        print(f"\n  ✅ Created test Trade")
        print(f"     - symbol type: {type(test_trade.symbol).__name__}")
        print(f"     - symbol value: {test_trade.symbol.to_short()}")
        
        # Rollback test trade
        session.rollback()
        print(f"  ✅ Test trade rolled back (not saved)")
        
        print("\n✅ FUNCTIONALITY TEST PASSED")
        return True
    
    except Exception as e:
        logger.error(f"❌ Functionality test failed: {e}", exc_info=True)
        print(f"\n❌ FUNCTIONALITY TEST FAILED: {e}")
        session.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description='V22.1 Database Migration')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without committing')
    parser.add_argument('--validate-only', action='store_true', help='Only run validation, no migration')
    args = parser.parse_args()
    
    print_header("V22.1 DATABASE MIGRATION")
    
    print(f"\nMode: {'DRY-RUN' if args.dry_run else 'VALIDATE-ONLY' if args.validate_only else 'LIVE MIGRATION'}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Backup: trading_bot_v16_PRE_V22.1.backup")
    
    session = SessionLocal()
    
    try:
        # Step 1: Pre-migration validation
        pre_results = validate_pre_migration(session)
        
        total_old_format = sum(r['old_format'] for r in pre_results.values())
        
        if total_old_format == 0:
            print("\n✅ No migration needed - all data already in new format")
            
            if not args.validate_only:
                # Still run functionality test
                test_read_write(session)
            
            return 0
        
        print(f"\n📊 Migration Plan:")
        print(f"   Rows to migrate: {total_old_format}")
        print(f"   Tables affected: 5 (trades, signals, market_snapshots, pairs_signals x2)")
        
        if args.validate_only:
            print("\n🔍 VALIDATE-ONLY mode: Skipping migration")
            return 0
        
        # Step 2: Execute migration
        if not args.dry_run:
            response = input("\n⚠️  Proceed with LIVE migration? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Migration cancelled by user")
                return 1
        
        migration_results = execute_migration(session, dry_run=args.dry_run)
        
        if args.dry_run:
            print("\n🔍 DRY-RUN complete - no changes made")
            return 0
        
        # Step 3: Post-migration validation
        validation_passed = validate_post_migration(session)
        
        if not validation_passed:
            print("\n⚠️  WARNING: Post-migration validation failed")
            print("   Check logs for details")
            return 1
        
        # Step 4: Functionality test
        test_passed = test_read_write(session)
        
        if not test_passed:
            print("\n❌ CRITICAL: Functionality test failed")
            print("   Database may be in inconsistent state")
            print("   Restore from backup: trading_bot_v16_PRE_V22.1.backup")
            return 1
        
        # Success
        print_header("MIGRATION COMPLETE ✅")
        
        print(f"\nMigration Summary:")
        print(f"  Total rows migrated: {migration_results['total']}")
        print(f"  - Trades: {migration_results['trades']}")
        print(f"  - Signals: {migration_results['signals']}")
        print(f"  - Market Snapshots: {migration_results['market_snapshots']}")
        print(f"  - Pairs Signals: {migration_results['pairs_signals_a'] + migration_results['pairs_signals_b']}")
        
        print(f"\nValidation: ✅ PASSED")
        print(f"Functionality: ✅ PASSED")
        print(f"\n✅ System ready for V22.1 operations")
        
        return 0
    
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        print(f"\n❌ MIGRATION FAILED: {e}")
        print(f"\nTo rollback:")
        print(f"  1. Stop all services: docker compose down")
        print(f"  2. Restore backup: cp src/data/trading_bot_v16_PRE_V22.1.backup src/data/trading_bot_v16.db")
        print(f"  3. Restart: docker compose up -d")
        session.rollback()
        return 1
    
    finally:
        session.close()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Migration cancelled by user")
        sys.exit(130)
