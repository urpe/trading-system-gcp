#!/bin/bash
###############################################################################
# MANUAL VALIDATION - V22.1.2 Production
# Más confiable que el health monitor automático
###############################################################################

echo "════════════════════════════════════════════════════════════════"
echo "  V22.1.2 MANUAL VALIDATION"
echo "════════════════════════════════════════════════════════════════"
echo ""

# 1. SERVICIOS CORRIENDO
echo ">>> 1. SERVICIOS CORRIENDO"
echo "────────────────────────────────────────────────────────────────"
RUNNING=$(docker compose ps --filter "status=running" --format json 2>/dev/null | jq -s 'length' 2>/dev/null || docker compose ps --filter "status=running" | grep -c "Up" || echo "0")
echo "Servicios corriendo: $RUNNING/10"
if [ "$RUNNING" -ge 9 ]; then
    echo "✅ PASS"
else
    echo "❌ FAIL - Solo $RUNNING servicios corriendo"
fi
echo ""

# 2. REDIS CONNECTIVITY
echo ">>> 2. REDIS CONNECTIVITY"
echo "────────────────────────────────────────────────────────────────"
REDIS_PING=$(docker compose exec -T redis redis-cli PING 2>/dev/null)
if [ "$REDIS_PING" = "PONG" ]; then
    echo "✅ Redis: CONNECTED"
else
    echo "❌ Redis: FAILED"
fi
echo ""

# 3. BRAIN WARM-UP
echo ">>> 3. BRAIN WARM-UP STATUS"
echo "────────────────────────────────────────────────────────────────"
WARMUP=$(docker compose logs brain 2>/dev/null | grep "WARM-UP COMPLETADO" | tail -1)
if [ ! -z "$WARMUP" ]; then
    echo "✅ Brain: WARM-UP COMPLETADO"
    echo "   $WARMUP"
else
    echo "⏳ Brain: Warm-up en progreso (espera 1-2 minutos más)"
fi
echo ""

# 4. ERRORES ACTIVOS (últimos 5 min)
echo ">>> 4. ERRORES ACTIVOS (últimos 5 minutos)"
echo "────────────────────────────────────────────────────────────────"

# Dashboard errors
DASH_ERRORS=$(docker compose logs dashboard --since 5m 2>/dev/null | grep -c "ERROR" || echo "0")
echo "Dashboard errors: $DASH_ERRORS"
if [ "$DASH_ERRORS" -lt 3 ]; then
    echo "✅ Dashboard: OK"
else
    echo "⚠️  Dashboard: Revisar logs"
fi

# Orders errors
ORDERS_ERRORS=$(docker compose logs orders --since 5m 2>/dev/null | grep -c "ERROR" || echo "0")
echo "Orders errors: $ORDERS_ERRORS"
if [ "$ORDERS_ERRORS" -lt 3 ]; then
    echo "✅ Orders: OK"
else
    echo "⚠️  Orders: Revisar logs"
fi

# Brain errors
BRAIN_ERRORS=$(docker compose logs brain --since 5m 2>/dev/null | grep -c "ERROR" || echo "0")
echo "Brain errors: $BRAIN_ERRORS"
if [ "$BRAIN_ERRORS" -lt 3 ]; then
    echo "✅ Brain: OK"
else
    echo "⚠️  Brain: Revisar logs"
fi
echo ""

# 5. COMMIT VERSION
echo ">>> 5. COMMIT VERSION"
echo "────────────────────────────────────────────────────────────────"
CURRENT_COMMIT=$(git log --oneline -1 2>/dev/null)
echo "$CURRENT_COMMIT"
if echo "$CURRENT_COMMIT" | grep -q "5a90c72\|d4be0d1"; then
    echo "✅ Version correcta (V22.1.2)"
else
    echo "⚠️  Commit no coincide con esperado (5a90c72 o d4be0d1)"
fi
echo ""

# 6. DATABASE ACCESSIBILITY
echo ">>> 6. DATABASE ACCESSIBILITY"
echo "────────────────────────────────────────────────────────────────"
docker compose exec -T dashboard python3 << 'PYEOF' 2>/dev/null
from src.shared.database import SessionLocal, Trade, Wallet
try:
    session = SessionLocal()
    trades_count = session.query(Trade).count()
    wallet = session.query(Wallet).order_by(Wallet.last_updated.desc()).first()
    session.close()
    print(f"✅ Database: ACCESSIBLE")
    print(f"   Trades: {trades_count}")
    if wallet:
        print(f"   Balance: ${wallet.usdt_balance:.2f} USDT")
except Exception as e:
    print(f"❌ Database: ERROR - {e}")
PYEOF
echo ""

# 7. REDIS DATA
echo ">>> 7. REDIS DATA"
echo "────────────────────────────────────────────────────────────────"
PRICE_KEYS=$(docker compose exec -T redis redis-cli --scan --pattern "price:*" 2>/dev/null | wc -l)
REGIME_KEYS=$(docker compose exec -T redis redis-cli --scan --pattern "market_regime:*" 2>/dev/null | wc -l)
echo "Price keys: $PRICE_KEYS"
echo "Regime keys: $REGIME_KEYS"
if [ "$PRICE_KEYS" -ge 3 ]; then
    echo "✅ Market Data: Publishing"
else
    echo "⏳ Market Data: Esperando datos (1-2 min)"
fi
echo ""

# 8. SIGNALS GENERADAS
echo ">>> 8. SIGNALS GENERADAS"
echo "────────────────────────────────────────────────────────────────"
SIGNALS=$(docker compose logs brain --since 10m 2>/dev/null | grep -c "🔔 SIGNAL" || echo "0")
echo "Signals (últimos 10 min): $SIGNALS"
if [ "$SIGNALS" -ge 1 ]; then
    echo "✅ Brain: Generando signals"
else
    echo "⏳ Brain: Sin opportunities o aún calentando"
fi
echo ""

# RESUMEN FINAL
echo "════════════════════════════════════════════════════════════════"
echo "  RESUMEN DE VALIDACIÓN"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Calcular score manual
SCORE=0
[ "$RUNNING" -ge 9 ] && SCORE=$((SCORE + 30))
[ "$REDIS_PING" = "PONG" ] && SCORE=$((SCORE + 20))
[ ! -z "$WARMUP" ] && SCORE=$((SCORE + 20))
[ "$DASH_ERRORS" -lt 3 ] && SCORE=$((SCORE + 10))
[ "$ORDERS_ERRORS" -lt 3 ] && SCORE=$((SCORE + 10))
[ "$PRICE_KEYS" -ge 3 ] && SCORE=$((SCORE + 10))

echo "Score estimado: $SCORE/100"
echo ""

if [ "$SCORE" -ge 80 ]; then
    echo "✅ ESTADO: SISTEMA OPERACIONAL"
    echo ""
    echo "Dashboard disponible en:"
    IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null)
    echo "  http://$IP:8050"
    echo ""
elif [ "$SCORE" -ge 50 ]; then
    echo "⚠️  ESTADO: SISTEMA EN WARM-UP"
    echo ""
    echo "Espera 2-3 minutos más y vuelve a ejecutar este script."
    echo ""
else
    echo "❌ ESTADO: PROBLEMAS DETECTADOS"
    echo ""
    echo "Revisa los logs con:"
    echo "  docker compose logs brain orders dashboard --tail 50"
    echo ""
fi

echo "════════════════════════════════════════════════════════════════"
