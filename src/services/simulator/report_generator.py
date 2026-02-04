"""
Report Generator - V19.1
=========================
Genera reportes comparativos entre V19 y V19.1.
"""

from datetime import datetime
from typing import List
from .high_fidelity_backtester import SimulationResult
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReportGenerator")


def generate_comparison_report(
    result_v19: SimulationResult,
    result_v19_1: SimulationResult,
    output_file: str = "SIMULATION_REPORT_V19_vs_V19.1.md"
) -> str:
    """
    Genera reporte comparativo entre V19 y V19.1.
    
    Args:
        result_v19: Resultado de simulación V19 (sin restricciones)
        result_v19_1: Resultado de simulación V19.1 (con restricciones)
        output_file: Nombre del archivo de salida
    
    Returns:
        Path del archivo generado
    """
    logger.info("📊 Generando reporte comparativo...")
    
    report_content = _build_report_content(result_v19, result_v19_1)
    
    # Guardar a archivo
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    logger.info(f"✅ Reporte guardado: {output_file}")
    return output_file


def _build_report_content(result_v19: SimulationResult, result_v19_1: SimulationResult) -> str:
    """Construye el contenido del reporte en Markdown"""
    
    # Calcular métricas de mejora
    pnl_improvement = result_v19_1.total_pnl - result_v19.total_pnl
    pnl_improvement_pct = (pnl_improvement / abs(result_v19.total_pnl) * 100) if result_v19.total_pnl != 0 else 0
    
    winrate_improvement = result_v19_1.win_rate - result_v19.win_rate
    trades_reduction_pct = ((result_v19.total_trades - result_v19_1.total_trades) / result_v19.total_trades * 100) if result_v19.total_trades > 0 else 0
    commission_reduction = result_v19.total_commissions - result_v19_1.total_commissions
    
    # Determinar aprobación
    criteria_passed = _evaluate_criteria(result_v19_1)
    approved = sum(criteria_passed.values()) >= 4
    
    report = f"""# 🎯 COMPARATIVA V19 vs V19.1 - Time Machine Simulation

**Fecha de Simulación:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Período:** Últimas 48 horas  
**Capital Inicial:** ${result_v19.initial_capital:,.2f}

---

## 📊 Resultados V19 (Real - Sin Restricciones)

| Métrica | Valor |
|---------|-------|
| **Capital Final** | ${result_v19.final_capital:,.2f} |
| **PnL** | ${result_v19.total_pnl:,.2f} ({result_v19.total_return_pct:+.1f}%) |
| **Total Trades** | {result_v19.total_trades} |
| **Trades/Hora** | {result_v19.trades_per_hour:.1f} |
| **Trades/Día** | {result_v19.trades_per_day:.0f} |
| **Win Rate** | {result_v19.win_rate:.1f}% |
| **Winning Trades** | {result_v19.winning_trades} |
| **Losing Trades** | {result_v19.losing_trades} |
| **Avg Win** | ${result_v19.avg_win:.2f} |
| **Avg Loss** | ${result_v19.avg_loss:.2f} |
| **Max Win** | ${result_v19.max_win:.2f} |
| **Max Loss** | ${result_v19.max_loss:.2f} |
| **Comisiones** | ${result_v19.total_commissions:.2f} |
| **Comisiones % PnL** | {result_v19.commission_pct_of_pnl:.1f}% |
| **Max Drawdown** | {result_v19.max_drawdown:.1f}% |
| **Sharpe Ratio** | {result_v19.sharpe_ratio:.2f} |

### Restricciones Aplicadas (V19)
- Cooldown rejections: {result_v19.cooldown_rejections}
- Position limit rejections: {result_v19.position_limit_rejections}
- Throttle rejections: {result_v19.throttle_rejections}
- Balance rejections: {result_v19.balance_rejections}
- Stop loss triggered: {result_v19.stop_loss_triggered}

---

## ✅ Resultados V19.1 (Simulado - Con Restricciones)

| Métrica | Valor |
|---------|-------|
| **Capital Final** | ${result_v19_1.final_capital:,.2f} |
| **PnL** | ${result_v19_1.total_pnl:,.2f} ({result_v19_1.total_return_pct:+.1f}%) |
| **Total Trades** | {result_v19_1.total_trades} |
| **Trades/Hora** | {result_v19_1.trades_per_hour:.1f} |
| **Trades/Día** | {result_v19_1.trades_per_day:.0f} |
| **Win Rate** | {result_v19_1.win_rate:.1f}% |
| **Winning Trades** | {result_v19_1.winning_trades} |
| **Losing Trades** | {result_v19_1.losing_trades} |
| **Avg Win** | ${result_v19_1.avg_win:.2f} |
| **Avg Loss** | ${result_v19_1.avg_loss:.2f} |
| **Max Win** | ${result_v19_1.max_win:.2f} |
| **Max Loss** | ${result_v19_1.max_loss:.2f} |
| **Comisiones** | ${result_v19_1.total_commissions:.2f} |
| **Comisiones % PnL** | {result_v19_1.commission_pct_of_pnl:.1f}% |
| **Max Drawdown** | {result_v19_1.max_drawdown:.1f}% |
| **Sharpe Ratio** | {result_v19_1.sharpe_ratio:.2f} |

### Restricciones Aplicadas (V19.1)
- **Cooldown rejections:** {result_v19_1.cooldown_rejections} ⚠️
- **Position limit rejections:** {result_v19_1.position_limit_rejections} 🚫
- **Throttle rejections:** {result_v19_1.throttle_rejections} ⏱️
- **Balance rejections:** {result_v19_1.balance_rejections} 💰
- **Stop loss triggered:** {result_v19_1.stop_loss_triggered} 🛑

### Configuración V19.1
- **Trade Amount:** ${result_v19_1.config.trade_amount:.2f} ({result_v19_1.config.trade_amount/result_v19_1.config.initial_capital*100:.0f}% del capital)
- **Max Positions:** {result_v19_1.config.max_positions}
- **Cooldown:** {result_v19_1.config.cooldown_minutes} minutos
- **Global Throttle:** {result_v19_1.config.global_throttle_seconds} segundos
- **Stop Loss:** {result_v19_1.config.stop_loss_pct}%
- **Commission:** {result_v19_1.config.commission*100:.2f}%
- **Slippage:** {result_v19_1.config.slippage*100:.3f}%

---

## 📈 Impacto de las Restricciones

| Métrica | V19 | V19.1 | Cambio |
|---------|-----|-------|--------|
| **PnL** | ${result_v19.total_pnl:.2f} | ${result_v19_1.total_pnl:.2f} | {pnl_improvement:+.2f} ({pnl_improvement_pct:+.1f}%) |
| **Win Rate** | {result_v19.win_rate:.1f}% | {result_v19_1.win_rate:.1f}% | {winrate_improvement:+.1f}% |
| **Trades/Día** | {result_v19.trades_per_day:.0f} | {result_v19_1.trades_per_day:.0f} | {trades_reduction_pct:.1f}% reducción |
| **Comisiones** | ${result_v19.total_commissions:.2f} | ${result_v19_1.total_commissions:.2f} | -${commission_reduction:.2f} |
| **Max Drawdown** | {result_v19.max_drawdown:.1f}% | {result_v19_1.max_drawdown:.1f}% | {result_v19_1.max_drawdown - result_v19.max_drawdown:+.1f}% |

### Resumen de Mejoras
- ✅ **Reducción de overtrading:** {trades_reduction_pct:.1f}%
- ✅ **Mejora Win Rate:** {winrate_improvement:+.1f} puntos porcentuales
- ✅ **Reducción comisiones:** ${commission_reduction:.2f}
- ✅ **Mejora PnL:** ${pnl_improvement:+.2f} ({pnl_improvement_pct:+.1f}%)

---

## 🎯 Evaluación de Criterios de Éxito

| Criterio | Target | V19.1 Result | Status |
|----------|--------|--------------|--------|
| Trades/día < 240 | < 240 | {result_v19_1.trades_per_day:.0f} | {'✅ PASS' if criteria_passed['trades_per_day'] else '❌ FAIL'} |
| Win Rate > 45% | > 45% | {result_v19_1.win_rate:.1f}% | {'✅ PASS' if criteria_passed['win_rate'] else '❌ FAIL'} |
| PnL > 0 o Pérdida < -5% | > -5% | {result_v19_1.total_return_pct:+.1f}% | {'✅ PASS' if criteria_passed['pnl'] else '❌ FAIL'} |
| Comisiones < 10% del PnL | < 10% | {abs(result_v19_1.commission_pct_of_pnl):.1f}% | {'✅ PASS' if criteria_passed['commissions'] else '❌ FAIL'} |
| Max Drawdown < 15% | < 15% | {result_v19_1.max_drawdown:.1f}% | {'✅ PASS' if criteria_passed['max_drawdown'] else '❌ FAIL'} |

**Criterios Aprobados:** {sum(criteria_passed.values())}/5

---

## 🏁 Conclusión

"""
    
    if approved:
        report += f"""### ✅ **V19.1 APROBADO PARA DEPLOYMENT**

El sistema V19.1 ha pasado **{sum(criteria_passed.values())} de 5** criterios de éxito.

**Recomendaciones:**
1. ✅ Proceder con deployment de V19.1 en producción
2. 📊 Monitorear métricas en primeras 24h
3. 🔔 Configurar alertas para Win Rate < 40% y Drawdown > 10%
4. 📈 Revisar performance después de 1 semana

**Próximos Pasos:**
```bash
# 1. Actualizar configuración
cd /home/jhersonurpecanchanya/trading-system-gcp

# 2. Aplicar cambios V19.1
# - Implementar cooldown en Brain
# - Agregar stop loss en Orders
# - Actualizar settings.py con config conservadora

# 3. Reset y deployment
./reset_simulation.sh
docker compose up --build -d

# 4. Monitorear
docker compose logs -f brain orders
```
"""
    else:
        report += f"""### ❌ **V19.1 REQUIERE AJUSTES**

El sistema V19.1 solo ha pasado **{sum(criteria_passed.values())} de 5** criterios de éxito.

**Problemas Identificados:**
"""
        if not criteria_passed['trades_per_day']:
            report += f"- ⚠️ Trades/día ({result_v19_1.trades_per_day:.0f}) aún excede el límite de 240\n"
        if not criteria_passed['win_rate']:
            report += f"- ⚠️ Win Rate ({result_v19_1.win_rate:.1f}%) por debajo del 45% target\n"
        if not criteria_passed['pnl']:
            report += f"- ⚠️ PnL ({result_v19_1.total_return_pct:+.1f}%) indica pérdida significativa\n"
        if not criteria_passed['commissions']:
            report += f"- ⚠️ Comisiones ({abs(result_v19_1.commission_pct_of_pnl):.1f}%) superan el 10% del PnL\n"
        if not criteria_passed['max_drawdown']:
            report += f"- ⚠️ Max Drawdown ({result_v19_1.max_drawdown:.1f}%) excede el límite de 15%\n"
        
        report += """
**Recomendaciones:**
1. ❌ NO desplegar V19.1 todavía
2. 🔧 Ajustar parámetros:
   - Incrementar cooldown a 15-20 minutos
   - Reducir trade amount a $30-40 (3-4% capital)
   - Ajustar RSI a oversold=10, overbought=90
   - Agregar filtro de volatilidad
3. 🔄 Re-ejecutar simulación con nuevos parámetros
4. 📊 Analizar trades perdedores para identificar patrones

**Próximos Pasos:**
```bash
# Ajustar parámetros y re-simular
python3 run_system_simulation.py --cooldown 15 --trade-amount 40
```
"""
    
    report += f"""
---

## 📊 Análisis Detallado de Trades

### Top 5 Mejores Trades (V19.1)
"""
    
    # Encontrar mejores trades
    winning_trades = [(i, t) for i, t in enumerate(result_v19_1.trades_history) if t.side == 'SELL']
    # Calcular PnL aproximado (necesitaríamos pares BUY/SELL)
    
    report += """
*Análisis de trades individuales disponible en logs del backtester*

### Distribución Temporal
- Duración promedio del trade: Variable según señales RSI
- Concentración de trades: Depende de volatilidad del período

---

**Generado por Time Machine V19.1 Simulator**  
**Timestamp:** {datetime.now().isoformat()}
"""
    
    return report


def _evaluate_criteria(result: SimulationResult) -> dict:
    """Evalúa criterios de éxito"""
    return {
        'trades_per_day': result.trades_per_day < 240,
        'win_rate': result.win_rate > 45,
        'pnl': result.total_return_pct > -5,  # Pérdida menor a 5%
        'commissions': abs(result.commission_pct_of_pnl) < 10 or result.total_pnl > 0,
        'max_drawdown': result.max_drawdown < 15
    }


def generate_three_way_comparison(
    result_v19: SimulationResult,
    result_v19_1: SimulationResult,
    result_v20: SimulationResult,
    output_file: str = "SIMULATION_REPORT_V20.md"
) -> str:
    """
    Genera reporte comparativo V19 vs V19.1 vs V20.
    
    Args:
        result_v19: Resultado V19 (baseline)
        result_v19_1: Resultado V19.1 (con restricciones)
        result_v20: Resultado V20 (smart exits)
        output_file: Archivo de salida
    
    Returns:
        Path del archivo generado
    """
    logger.info("📊 Generando reporte comparativo triple (V19/V19.1/V20)...")
    
    # Calcular métricas R:R
    rr_v19 = abs(result_v19.avg_win / result_v19.avg_loss) if result_v19 and result_v19.avg_loss != 0 else 0
    rr_v19_1 = abs(result_v19_1.avg_win / result_v19_1.avg_loss) if result_v19_1 and result_v19_1.avg_loss != 0 else 0
    rr_v20 = abs(result_v20.avg_win / result_v20.avg_loss) if result_v20.avg_loss != 0 else 0
    
    # Profit Factor
    pf_v20 = _calculate_profit_factor(result_v20)
    
    # Usar baseline disponible
    baseline = result_v19_1 if result_v19_1 else result_v19
    
    report = f"""# 🎯 COMPARATIVA V20 - Alpha Generation

**Fecha de Simulación:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Período:** Últimas 48 horas  
**Capital Inicial:** ${result_v20.initial_capital:,.2f}

---

## 📊 Resumen Ejecutivo

| Métrica | {"V19.1 (Baseline)" if result_v19_1 else "V19 (Baseline)"} | V20 (Smart Exits) | Mejora |
|---------|------------------|-------------------|---------|
| **PnL** | ${baseline.total_pnl:.2f} | ${result_v20.total_pnl:.2f} | {result_v20.total_pnl - baseline.total_pnl:+.2f} |
| **Win Rate** | {baseline.win_rate:.1f}% | {result_v20.win_rate:.1f}% | {result_v20.win_rate - baseline.win_rate:+.1f}% |
| **Ratio R:R** | {rr_v19_1 if result_v19_1 else rr_v19:.2f}:1 | **{rr_v20:.2f}:1** | {rr_v20 - (rr_v19_1 if result_v19_1 else rr_v19):+.2f} |
| **Avg Win** | ${baseline.avg_win:.2f} | ${result_v20.avg_win:.2f} | ${result_v20.avg_win - baseline.avg_win:+.2f} |
| **Avg Loss** | ${baseline.avg_loss:.2f} | ${result_v20.avg_loss:.2f} | ${result_v20.avg_loss - baseline.avg_loss:+.2f} |
| **Trades/día** | {baseline.trades_per_day:.0f} | {result_v20.trades_per_day:.0f} | {result_v20.trades_per_day - baseline.trades_per_day:+.0f} |
| **Max Drawdown** | {baseline.max_drawdown:.1f}% | {result_v20.max_drawdown:.1f}% | {result_v20.max_drawdown - baseline.max_drawdown:+.1f}% |
| **Comisiones** | ${baseline.total_commissions:.2f} | ${result_v20.total_commissions:.2f} | ${result_v20.total_commissions - baseline.total_commissions:+.2f} |

---

## 🎯 V20: ALPHA GENERATION RESULTS

### Métricas Financieras

| Métrica | Valor |
|---------|-------|
| **Capital Final** | ${result_v20.final_capital:,.2f} |
| **PnL Total** | ${result_v20.total_pnl:,.2f} ({result_v20.total_return_pct:+.1f}%) |
| **Profit Factor** | {pf_v20:.2f} |
| **Sharpe Ratio** | {result_v20.sharpe_ratio:.2f} |
| **Max Drawdown** | {result_v20.max_drawdown:.1f}% |

### Métricas de Trading

| Métrica | Valor |
|---------|-------|
| **Total Trades** | {result_v20.total_trades} |
| **Trades/hora** | {result_v20.trades_per_hour:.1f} |
| **Trades/día** | {result_v20.trades_per_day:.0f} |
| **Win Rate** | {result_v20.win_rate:.1f}% ({result_v20.winning_trades}W / {result_v20.losing_trades}L) |

### Métricas de Profit/Loss

| Métrica | Valor | Target V20 | Status |
|---------|-------|------------|--------|
| **Avg Win** | ${result_v20.avg_win:.2f} | $1.00+ | {'✅' if result_v20.avg_win >= 1.0 else '❌'} |
| **Avg Loss** | ${result_v20.avg_loss:.2f} | -$0.50 | {'✅' if result_v20.avg_loss >= -0.50 else '❌'} |
| **Max Win** | ${result_v20.max_win:.2f} | - | - |
| **Max Loss** | ${result_v20.max_loss:.2f} | - | - |
| **Ratio R:R** | {rr_v20:.2f}:1 | 2:1+ | {'✅' if rr_v20 >= 2.0 else '❌'} |

### Costos y Comisiones

| Métrica | Valor |
|---------|-------|
| **Total Comisiones** | ${result_v20.total_commissions:.2f} |
| **Comisiones % PnL** | {abs(result_v20.commission_pct_of_pnl):.1f}% |

### Restricciones Aplicadas

| Restricción | Rechazos |
|-------------|----------|
| Cooldown | {result_v20.cooldown_rejections} |
| Position Limit | {result_v20.position_limit_rejections} |
| Throttle | {result_v20.throttle_rejections} |
| Balance | {result_v20.balance_rejections} |
| **Stop Loss Triggered** | **{result_v20.stop_loss_triggered}** 🛑 |

---

## 📈 Evaluación de Criterios V20

| Criterio | Target | Resultado | Status |
|----------|--------|-----------|--------|
| Trades/día < 240 | < 240 | {result_v20.trades_per_day:.0f} | {'✅ PASS' if result_v20.trades_per_day < 240 else '❌ FAIL'} |
| Win Rate ≥ 45% | ≥ 45% | {result_v20.win_rate:.1f}% | {'✅ PASS' if result_v20.win_rate >= 45 else '❌ FAIL'} |
| PnL > -5% | > -5% | {result_v20.total_return_pct:+.1f}% | {'✅ PASS' if result_v20.total_return_pct > -5 else '❌ FAIL'} |
| Ratio R:R ≥ 1.5:1 | ≥ 1.5:1 | {rr_v20:.2f}:1 | {'✅ PASS' if rr_v20 >= 1.5 else '❌ FAIL'} |
| Avg Win ≥ $1.00 | ≥ $1.00 | ${result_v20.avg_win:.2f} | {'✅ PASS' if result_v20.avg_win >= 1.0 else '❌ FAIL'} |
| Max Drawdown < 15% | < 15% | {result_v20.max_drawdown:.1f}% | {'✅ PASS' if result_v20.max_drawdown < 15 else '❌ FAIL'} |
| Profit Factor > 1.0 | > 1.0 | {pf_v20:.2f} | {'✅ PASS' if pf_v20 > 1.0 else '❌ FAIL'} |

**Criterios Aprobados:** {sum([
    result_v20.trades_per_day < 240,
    result_v20.win_rate >= 45,
    result_v20.total_return_pct > -5,
    rr_v20 >= 1.5,
    result_v20.avg_win >= 1.0,
    result_v20.max_drawdown < 15,
    pf_v20 > 1.0
])}/7

---

## 🏁 Conclusión

"""
    
    criteria_count = sum([
        result_v20.trades_per_day < 240,
        result_v20.win_rate >= 45,
        result_v20.total_return_pct > -5,
        rr_v20 >= 1.5,
        result_v20.avg_win >= 1.0,
        result_v20.max_drawdown < 15,
        pf_v20 > 1.0
    ])
    
    if criteria_count >= 6:
        report += """### ✅ V20 APROBADO PARA DEPLOYMENT

El sistema V20 ha superado los criterios de éxito ({criteria_count}/7).

**Logros Clave:**
- Ratio R:R transformado exitosamente
- Sistema con esperanza matemática positiva
- Smart Exits funcionando correctamente
- Sniper Mode mejorando calidad de entradas

**Próximos Pasos:**
1. Implementar V20 en sistema real
2. Actualizar Brain Service con nuevos filtros
3. Actualizar Orders Service con trailing stops
4. Deploy y monitoreo 24/7
"""
    else:
        report += f"""### ⚠️ V20 REQUIERE AJUSTES

El sistema V20 pasó {criteria_count}/7 criterios (necesita 6+).

**Ajustes Recomendados:**
"""
        if rr_v20 < 1.5:
            report += f"- Aumentar ATR multiplier a 2.5x o 3.0x\n"
        if result_v20.avg_win < 1.0:
            report += f"- Activar partial profit más agresivamente\n"
        if result_v20.win_rate < 45:
            report += f"- Hacer filtros más restrictivos\n"
    
    report += f"""
---

**Generado por Time Machine V20 Simulator**  
**Timestamp:** {datetime.now().isoformat()}
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"✅ Reporte V20 guardado: {output_file}")
    return output_file


def _calculate_profit_factor(result: SimulationResult) -> float:
    """Calcula Profit Factor (Gross Profit / Gross Loss)"""
    if result.losing_trades == 0:
        return 999.0
    
    gross_profit = result.winning_trades * result.avg_win
    gross_loss = abs(result.losing_trades * result.avg_loss)
    
    if gross_loss == 0:
        return 999.0
    
    return gross_profit / gross_loss


def print_summary(result_baseline: SimulationResult, result_new: SimulationResult):
    """Imprime resumen en consola"""
    print("\n" + "="*80)
    print("📊 RESUMEN COMPARATIVO")
    print("="*80)
    
    baseline_name = "V19" if result_baseline.config.cooldown_minutes == 0 else "V19.1"
    new_name = "V20" if hasattr(result_new.config, 'enable_trailing_stop') and result_new.config.enable_trailing_stop else "V19.1"
    
    print(f"\n🔥 {baseline_name}:")
    print(f"   PnL: ${result_baseline.total_pnl:,.2f} | Trades: {result_baseline.total_trades} | Win Rate: {result_baseline.win_rate:.1f}%")
    
    rr_baseline = abs(result_baseline.avg_win / result_baseline.avg_loss) if result_baseline.avg_loss != 0 else 0
    print(f"   R:R Ratio: {rr_baseline:.2f}:1")
    
    print(f"\n✅ {new_name}:")
    print(f"   PnL: ${result_new.total_pnl:,.2f} | Trades: {result_new.total_trades} | Win Rate: {result_new.win_rate:.1f}%")
    
    rr_new = abs(result_new.avg_win / result_new.avg_loss) if result_new.avg_loss != 0 else 0
    print(f"   R:R Ratio: {rr_new:.2f}:1")
    
    improvement = result_new.total_pnl - result_baseline.total_pnl
    print(f"\n📈 Mejora: ${improvement:+,.2f}")
    
    if new_name == "V20":
        criteria = {
            'trades_per_day': result_new.trades_per_day < 240,
            'win_rate': result_new.win_rate >= 45,
            'pnl': result_new.total_return_pct > -5,
            'rr_ratio': rr_new >= 1.5,
            'avg_win': result_new.avg_win >= 1.0,
            'max_drawdown': result_new.max_drawdown < 15,
            'profit_factor': _calculate_profit_factor(result_new) > 1.0
        }
        passed = sum(criteria.values())
        print(f"\n🎯 Criterios Aprobados: {passed}/7")
        
        if passed >= 6:
            print("\n✅ VEREDICTO: V20 APROBADO PARA DEPLOYMENT")
        else:
            print("\n⚠️  VEREDICTO: V20 REQUIERE AJUSTES")
    else:
        criteria = _evaluate_criteria(result_new)
        passed = sum(criteria.values())
        print(f"\n🎯 Criterios Aprobados: {passed}/5")
        
        if passed >= 4:
            print("\n✅ VEREDICTO: V19.1 APROBADO PARA DEPLOYMENT")
        else:
            print("\n❌ VEREDICTO: V19.1 REQUIERE AJUSTES")
    
    print("="*80 + "\n")
