#!/bin/bash
# ============================================================================
# verify_system.sh - Script de Verificación Post-Deployment V21.1
# ============================================================================
# Uso: ./verify_system.sh
# ============================================================================

set -e

echo "🔍 HFT Bot V21.1 - System Health Check"
echo "======================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- 1. Docker Services ---
echo "📦 1. Verificando Docker Services..."
RUNNING=$(docker compose ps --format json | jq -s 'map(select(.State == "running")) | length')
TOTAL=$(docker compose ps --format json | jq -s 'length')

if [ "$RUNNING" -eq "$TOTAL" ]; then
    echo -e "${GREEN}✅ Todos los servicios corriendo: $RUNNING/$TOTAL${NC}"
else
    echo -e "${RED}⚠️ Solo $RUNNING/$TOTAL servicios activos${NC}"
    echo "   Servicios inactivos:"
    docker compose ps --format json | jq -r '.[] | select(.State != "running") | .Name'
fi
echo ""

# --- 2. Dashboard API ---
echo "🌐 2. Verificando Dashboard API..."
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8050/api/dashboard-data)

if [ "$DASHBOARD_STATUS" == "200" ]; then
    echo -e "${GREEN}✅ Dashboard API: HTTP 200 OK${NC}"
else
    echo -e "${RED}❌ Dashboard API: HTTP $DASHBOARD_STATUS${NC}"
    exit 1
fi
echo ""

# --- 3. Market Regimes Endpoint ---
echo "🦅 3. Verificando Endpoint de Regímenes (V21 EAGLE EYE)..."
REGIMES=$(curl -s http://localhost:8050/api/market-regimes | jq -r 'keys | length')

if [ "$REGIMES" -gt 0 ]; then
    echo -e "${GREEN}✅ Regímenes detectados: $REGIMES símbolos${NC}"
    curl -s http://localhost:8050/api/market-regimes | jq -r 'to_entries[] | "   \(.key): \(.value.regime) (ADX: \(.value.adx | round))"'
else
    echo -e "${YELLOW}⚠️ No hay regímenes en Redis (esperando datos...)${NC}"
fi
echo ""

# --- 4. Redis Health ---
echo "💾 4. Verificando Redis..."
REDIS_PING=$(docker compose exec redis redis-cli PING 2>&1)

if [[ "$REDIS_PING" == *"PONG"* ]]; then
    echo -e "${GREEN}✅ Redis: PONG${NC}"
    
    # Verificar configuración FinOps
    APPENDFSYNC=$(docker compose exec redis redis-cli CONFIG GET appendfsync 2>&1 | grep -A1 appendfsync | tail -1)
    echo "   - appendfsync: $APPENDFSYNC"
    
    if [ "$APPENDFSYNC" == "no" ]; then
        echo -e "   ${GREEN}✅ FinOps optimizado (appendfsync no)${NC}"
    else
        echo -e "   ${YELLOW}⚠️ Redis con appendfsync: $APPENDFSYNC (no optimizado)${NC}"
    fi
else
    echo -e "${RED}❌ Redis: No responde${NC}"
    exit 1
fi
echo ""

# --- 5. OHLCV Data Stream ---
echo "📊 5. Verificando OHLCV Stream (Market Data)..."
LAST_OHLCV=$(docker compose logs market-data --tail=5 | grep "OHLCV" | tail -1)

if [ -n "$LAST_OHLCV" ]; then
    echo -e "${GREEN}✅ OHLCV Stream activo${NC}"
    echo "   Último update: $LAST_OHLCV"
else
    echo -e "${YELLOW}⚠️ No hay logs recientes de OHLCV${NC}"
fi
echo ""

# --- 6. Brain ADX Validation ---
echo "🧠 6. Verificando Brain (ADX > 0 fix)..."
BRAIN_LOGS=$(docker compose logs brain --tail=10 | grep -E "BULL|BEAR|SIDEWAYS" | tail -3)

if [ -n "$BRAIN_LOGS" ]; then
    echo -e "${GREEN}✅ Brain detectando regímenes${NC}"
    echo "$BRAIN_LOGS" | while IFS= read -r line; do
        echo "   $line"
    done
else
    echo -e "${YELLOW}⚠️ Sin detección de regímenes reciente${NC}"
fi
echo ""

# --- 7. Active Positions ---
echo "💼 7. Verificando Posiciones Activas..."
POSITIONS=$(curl -s http://localhost:8050/api/dashboard-data | jq -r '.positions | length')

if [ "$POSITIONS" -gt 0 ]; then
    echo -e "${GREEN}✅ Posiciones activas: $POSITIONS${NC}"
    curl -s http://localhost:8050/api/dashboard-data | jq -r '.positions[] | "   \(.symbol) \(.type): \(.amount) @ $\(.current_price) (PnL: $\(.pnl))"'
else
    echo -e "${YELLOW}⚠️ No hay posiciones abiertas (normal si es un fresh start)${NC}"
fi
echo ""

# --- 8. Docker Logs Rotation ---
echo "📝 8. Verificando Rotación de Logs (FinOps)..."
LOG_DRIVER=$(docker inspect trading-system-gcp-dashboard-1 2>/dev/null | jq -r '.[0].HostConfig.LogConfig.Type')

if [ "$LOG_DRIVER" == "json-file" ]; then
    MAX_SIZE=$(docker inspect trading-system-gcp-dashboard-1 | jq -r '.[0].HostConfig.LogConfig.Config."max-size"')
    MAX_FILE=$(docker inspect trading-system-gcp-dashboard-1 | jq -r '.[0].HostConfig.LogConfig.Config."max-file"')
    echo -e "${GREEN}✅ Rotación de logs configurada${NC}"
    echo "   - max-size: $MAX_SIZE"
    echo "   - max-file: $MAX_FILE"
else
    echo -e "${YELLOW}⚠️ Sin rotación de logs (puede crecer infinitamente)${NC}"
fi
echo ""

# --- 9. Disk Usage ---
echo "💽 9. Verificando Uso de Disco..."
PROJECT_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')
REDIS_SIZE=$(du -sh ~/redis_data 2>/dev/null | awk '{print $1}' || echo "N/A")

echo "   - Proyecto: $PROJECT_SIZE"
echo "   - Redis Data: $REDIS_SIZE"

if [[ "$PROJECT_SIZE" == *"G"* ]]; then
    echo -e "   ${RED}⚠️ Proyecto >1GB (revisar backups/logs)${NC}"
fi
echo ""

# --- 10. Recent Errors ---
echo "🚨 10. Buscando Errores Recientes..."
ERRORS=$(docker compose logs --since=10m 2>&1 | grep -i "error\|exception\|failed" | grep -v "grep" | wc -l)

if [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✅ Sin errores en los últimos 10 minutos${NC}"
else
    echo -e "${YELLOW}⚠️ $ERRORS errores detectados:${NC}"
    docker compose logs --since=10m 2>&1 | grep -i "error\|exception\|failed" | tail -5
fi
echo ""

# --- Summary ---
echo "======================================="
echo "📋 RESUMEN DE VERIFICACIÓN"
echo "======================================="

if [ "$DASHBOARD_STATUS" == "200" ] && [ "$RUNNING" -eq "$TOTAL" ]; then
    echo -e "${GREEN}✅ SISTEMA OPERATIVO Y SALUDABLE${NC}"
    echo ""
    echo "🎯 Dashboard: http://localhost:8050"
    echo "📊 Regímenes API: http://localhost:8050/api/market-regimes"
    echo ""
    echo "Próximos pasos:"
    echo "  1. Abrir Dashboard en tu navegador"
    echo "  2. Verificar que equity y posiciones cargan"
    echo "  3. Monitorear logs: docker compose logs -f"
else
    echo -e "${RED}⚠️ SISTEMA TIENE PROBLEMAS${NC}"
    echo "   Revisa los logs: docker compose logs --tail=50"
fi

echo ""
echo "✨ Verificación completada"
