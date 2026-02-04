#!/usr/bin/env python3
"""
Time Machine V19.1/V20 - Main Simulation Runner
================================================
Script principal para ejecutar simulación comparativa V19 vs V19.1 vs V20.

Uso:
    python3 run_system_simulation.py [--hours 48] [--symbols BTC,ETH,SOL] [--include-v20]
"""

import sys
import os
import argparse
from datetime import datetime

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.simulator.binance_data_fetcher import fetch_1m_data, validate_data, get_data_summary
from src.services.simulator.high_fidelity_backtester import HighFidelityBacktester, SimulationConfig
from src.services.simulator.strategy_v19_1 import RsiMeanReversionV19, RsiMeanReversionV191
from src.services.simulator.strategy_v20 import RsiMeanReversionV20
from src.services.simulator.strategy_v20_hybrid import RsiMeanReversionV20Hybrid
from src.services.simulator.smart_exits import ExitConfig
from src.services.simulator.report_generator import generate_comparison_report, print_summary, generate_three_way_comparison

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
)
logger = logging.getLogger("TimeMachine")


def parse_args():
    """Parse argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Time Machine V19.1/V20 - Simulador de Alta Fidelidad'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=48,
        help='Horas de datos históricos a descargar (default: 48)'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        default='BTC,ETH,SOL,XRP,BNB',
        help='Símbolos separados por coma (default: BTC,ETH,SOL,XRP,BNB)'
    )
    parser.add_argument(
        '--capital',
        type=float,
        default=1000.0,
        help='Capital inicial (default: 1000)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='SIMULATION_REPORT_V19_vs_V19.1.md',
        help='Archivo de salida del reporte (default: SIMULATION_REPORT_V19_vs_V19.1.md)'
    )
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Omitir descarga (usar datos cacheados)'
    )
    parser.add_argument(
        '--include-v20',
        action='store_true',
        help='Incluir simulación V20 (Smart Exits + Sniper Mode)'
    )
    parser.add_argument(
        '--v20-only',
        action='store_true',
        help='Solo ejecutar V20 (skip V19 y V19.1)'
    )
    
    return parser.parse_args()


def main():
    """Función principal que orquesta toda la simulación"""
    args = parse_args()
    
    print("\n" + "="*80)
    print("⏰ TIME MACHINE V19.1/V20 - Simulador de Alta Fidelidad")
    print("="*80)
    print(f"\n📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Objetivo: Validar correcciones V19.1/V20 antes de deployment")
    print(f"💰 Capital: ${args.capital:,.2f}")
    print(f"⏱️  Período: Últimas {args.hours}h")
    
    symbols = args.symbols.split(',')
    print(f"🪙 Símbolos: {', '.join(symbols)}")
    print("="*80 + "\n")
    
    # FASE 1: DESCARGA DE DATOS
    logger.info("📥 FASE 1: Descargando datos históricos...")
    
    try:
        market_data = fetch_1m_data(symbols, hours_back=args.hours)
        
        if not validate_data(market_data):
            logger.error("❌ Validación de datos falló")
            return 1
        
        print("\n" + get_data_summary(market_data))
        print()
        
    except Exception as e:
        logger.error(f"❌ Error descargando datos: {e}")
        return 1
    
    # Inicializar resultados
    result_v19 = None
    result_v19_1 = None
    result_v20 = None
    
    # FASE 2: SIMULACIÓN V19 (Sin Restricciones)
    if not args.v20_only:
        logger.info("🔥 FASE 2: Simulando V19 (Sin Restricciones)...")
        print("\n" + "-"*80)
        print("🔥 SIMULACIÓN V19 - Sistema Original (Sin Restricciones)")
        print("-"*80)
        
        config_v19 = SimulationConfig(
            initial_capital=args.capital,
            trade_amount=200.0,
            max_positions=5,
            cooldown_minutes=0,
            global_throttle_seconds=0,
            stop_loss_pct=None,
            commission=0.001,
            slippage=0.0005
        )
        
        strategy_v19 = RsiMeanReversionV19(rsi_period=14, oversold=25, overbought=75)
        
        class StrategyWrapperV19:
            def __init__(self, strategy):
                self.strategy = strategy
            
            def evaluate(self, symbol, price, price_history, timestamp):
                return self.strategy.evaluate(symbol, price, price_history, timestamp, None)
        
        try:
            backtester_v19 = HighFidelityBacktester(config_v19)
            result_v19 = backtester_v19.run(market_data, StrategyWrapperV19(strategy_v19))
            
            print("\n✅ Simulación V19 completada")
            print(result_v19.summary())
            
        except Exception as e:
            logger.error(f"❌ Error en simulación V19: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # FASE 3: SIMULACIÓN V19.1 (Con Restricciones)
    if not args.v20_only:
        logger.info("✅ FASE 3: Simulando V19.1 (Con Restricciones)...")
        print("\n" + "-"*80)
        print("✅ SIMULACIÓN V19.1 - Sistema Mejorado (Con Restricciones)")
        print("-"*80)
        
        config_v19_1 = SimulationConfig(
            initial_capital=args.capital,
            trade_amount=50.0,
            max_positions=2,
            cooldown_minutes=10,
            global_throttle_seconds=60,
            stop_loss_pct=2.0,
            commission=0.001,
            slippage=0.0005
        )
        
        strategy_v19_1 = RsiMeanReversionV191(
            rsi_period=14,
            oversold=15,
            overbought=85,
            ema_fast=20,
            ema_slow=50,
            enable_trend_filter=True,
            min_profit_target_pct=1.0
        )
        
        class StrategyWrapperV191:
            def __init__(self, strategy, backtester):
                self.strategy = strategy
                self.backtester = backtester
            
            def evaluate(self, symbol, price, price_history, timestamp):
                open_position = None
                if symbol in self.backtester.open_positions:
                    pos = self.backtester.open_positions[symbol]
                    open_position = {
                        'entry_price': pos.entry_price,
                        'amount': pos.remaining_amount,
                        'timestamp': pos.entry_timestamp
                    }
                
                return self.strategy.evaluate(symbol, price, price_history, timestamp, open_position)
        
        try:
            backtester_v19_1 = HighFidelityBacktester(config_v19_1)
            result_v19_1 = backtester_v19_1.run(market_data, StrategyWrapperV191(strategy_v19_1, backtester_v19_1))
            
            print("\n✅ Simulación V19.1 completada")
            print(result_v19_1.summary())
            
        except Exception as e:
            logger.error(f"❌ Error en simulación V19.1: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # FASE 3.5: SIMULACIÓN V20 (Smart Exits + Sniper Mode)
    if args.include_v20 or args.v20_only:
        logger.info("🎯 FASE 3.5: Simulando V20 (Smart Exits + Sniper Mode)...")
        print("\n" + "-"*80)
        print("🎯 SIMULACIÓN V20 - ALPHA GENERATION (Smart Exits + Sniper)")
        print("-"*80)
        
        config_v20 = SimulationConfig(
            initial_capital=args.capital,
            trade_amount=50.0,
            max_positions=2,
            cooldown_minutes=10,
            global_throttle_seconds=60,
            stop_loss_pct=2.0,
            commission=0.001,
            slippage=0.0005,
            # V20 Smart Exits
            enable_trailing_stop=True,
            trailing_activation_pct=1.0,
            trailing_distance_pct=0.5,
            enable_atr_tp=True,
            atr_multiplier=2.0
        )
        
        exit_config = ExitConfig(
            trailing_stop_pct=0.5,
            trailing_activation_pct=0.8,  # Activar trailing más temprano
            atr_multiplier_tp=3.0,  # TP más ambicioso
            breakeven_activation_pct=0.3,  # Breakeven más temprano
            partial_profit_pct=50.0,
            partial_profit_target_multiplier=1.5
        )
        
        # V20 HYBRID: Entradas V19.1 + Exits Smart
        strategy_v20 = RsiMeanReversionV20Hybrid(
            rsi_period=14,
            oversold=15,  # V19.1 setting
            overbought=85,
            ema_fast=20,
            ema_slow=50,
            exit_config=exit_config
        )
        
        try:
            backtester_v20 = HighFidelityBacktester(config_v20)
            result_v20 = backtester_v20.run(market_data, strategy_v20)
            
            print("\n✅ Simulación V20 completada")
            print(result_v20.summary())
            
        except Exception as e:
            logger.error(f"❌ Error en simulación V20: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # FASE 4: GENERACIÓN DE REPORTE
    logger.info("📊 FASE 4: Generando reporte comparativo...")
    print("\n" + "-"*80)
    print("📊 GENERANDO REPORTE COMPARATIVO")
    print("-"*80 + "\n")
    
    try:
        output_path = os.path.join(
            os.path.dirname(__file__),
            'SIMULATION_REPORT_V20.md' if result_v20 else args.output
        )
        
        # Generar reporte según versiones disponibles
        if result_v20:
            if result_v19 and result_v19_1:
                # Reporte triple
                report_file = generate_three_way_comparison(result_v19, result_v19_1, result_v20, output_path)
            else:
                # Solo V20 vs baseline
                baseline = result_v19_1 if result_v19_1 else result_v19
                report_file = generate_three_way_comparison(baseline, baseline, result_v20, output_path)
        elif result_v19 and result_v19_1:
            report_file = generate_comparison_report(result_v19, result_v19_1, output_path)
        else:
            logger.error("❌ No hay resultados para generar reporte")
            return 1
        
        print(f"✅ Reporte guardado en: {report_file}\n")
        
        # Imprimir resumen en consola
        if result_v20:
            print_summary(result_v19_1 if result_v19_1 else result_v19, result_v20)
        elif result_v19_1:
            print_summary(result_v19, result_v19_1)
        
    except Exception as e:
        logger.error(f"❌ Error generando reporte: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # FINALIZACIÓN
    print("\n" + "="*80)
    print("🎉 SIMULACIÓN COMPLETADA CON ÉXITO")
    print("="*80)
    print(f"\n📄 Reporte detallado: {report_file}")
    print(f"📊 Revisa el reporte para decidir si desplegar\n")
    
    # Determinar resultado de salida
    result_to_evaluate = result_v20 if result_v20 else result_v19_1
    
    if result_to_evaluate:
        if result_v20:
            # Criterios V20
            rr_ratio = abs(result_v20.avg_win / result_v20.avg_loss) if result_v20.avg_loss != 0 else 0
            pf = (result_v20.winning_trades * result_v20.avg_win) / abs(result_v20.losing_trades * result_v20.avg_loss) if result_v20.losing_trades > 0 and result_v20.avg_loss != 0 else 0
            
            criteria = {
                'trades_per_day': result_v20.trades_per_day < 240,
                'win_rate': result_v20.win_rate >= 45,
                'pnl': result_v20.total_return_pct > -5,
                'rr_ratio': rr_ratio >= 1.5,
                'avg_win': result_v20.avg_win >= 1.0,
                'max_drawdown': result_v20.max_drawdown < 15,
                'profit_factor': pf > 1.0
            }
            
            if sum(criteria.values()) >= 6:
                print("✅ VEREDICTO: V20 APROBADO - Proceder con deployment\n")
                return 0
            else:
                print("⚠️  VEREDICTO: V20 requiere ajustes - Revisar parámetros\n")
                return 2
        else:
            # Criterios V19.1
            criteria = {
                'trades_per_day': result_to_evaluate.trades_per_day < 240,
                'win_rate': result_to_evaluate.win_rate > 45,
                'pnl': result_to_evaluate.total_return_pct > -5,
                'commissions': abs(result_to_evaluate.commission_pct_of_pnl) < 10 or result_to_evaluate.total_pnl > 0,
                'max_drawdown': result_to_evaluate.max_drawdown < 15
            }
            
            if sum(criteria.values()) >= 4:
                print("✅ VEREDICTO: V19.1 APROBADO - Proceder con deployment\n")
                return 0
            else:
                print("⚠️  VEREDICTO: V19.1 requiere ajustes - Revisar parámetros\n")
                return 2
    
    return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulación interrumpida por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
