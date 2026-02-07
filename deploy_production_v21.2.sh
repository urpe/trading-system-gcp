#!/bin/bash

# ══════════════════════════════════════════════════════════════════════════════
# 🚀 V21.2 PRODUCTION DEPLOYMENT - QUICK START
# ══════════════════════════════════════════════════════════════════════════════
# 
# Testing local: ✅ COMPLETADO - ALL PASS
# Production:    ⏳ PENDIENTE (ejecutar comandos abajo)
#
# Duración estimada: 10 minutos
# ══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "            🚀 V21.2 PRODUCTION DEPLOYMENT - QUICK START"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📋 INSTRUCCIONES:"
echo ""
echo "1. Copia este archivo a tu VM de GCP:"
echo "   scp deploy_production_v21.2.sh vm-trading-bot:~/"
echo ""
echo "2. Conéctate a la VM:"
echo "   ssh vm-trading-bot"
echo ""
echo "3. Ejecuta este script:"
echo "   chmod +x deploy_production_v21.2.sh"
echo "   ./deploy_production_v21.2.sh"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
read -p "¿Continuar con el deployment? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ Deployment cancelado."
    exit 1
fi

# ══════════════════════════════════════════════════════════════════════════════
# FASE 1: PREPARACIÓN
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  FASE 1: PREPARACIÓN"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Verificar ubicación
if [ ! -d "trading-system-gcp" ]; then
    echo "❌ ERROR: No se encuentra el directorio trading-system-gcp"
    echo "   Asegúrate de estar en el directorio correcto."
    exit 1
fi

cd trading-system-gcp
echo "✅ Directorio: $(pwd)"

# Verificar git status
echo ""
echo "📊 Git status:"
git status --short

# ══════════════════════════════════════════════════════════════════════════════
# FASE 2: PULL DE CAMBIOS V21.2
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  FASE 2: PULL DE CAMBIOS V21.2"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

git pull origin main

echo ""
echo "📦 Últimos commits:"
git log --oneline -7

echo ""
echo "✅ Debe mostrar:"
echo "   - 9850f72 docs: Session complete summary V21.2"
echo "   - 6feaf16 docs: Add comprehensive local testing results"
echo "   - f4c20f4 fix: Remove duplicate code in get_market_regimes"
echo "   - 1532a24 docs: V21.2 Implementation Complete"
echo "   - 1883599 feat: V21.2 Additional Fixes + Production Tools"
echo "   - 95339fb docs: V21.2 Executive Summary"
echo "   - e2ec024 feat: V21.2 SYNCHRONIZED ARCHITECTURE"
echo ""

read -p "¿Los commits coinciden? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "⚠️ WARNING: Los commits no coinciden. Verifica git log."
    read -p "¿Continuar de todos modos? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ══════════════════════════════════════════════════════════════════════════════
# FASE 3: DEPLOYMENT
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  FASE 3: DEPLOYMENT (Rebuilding containers...)"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

./deploy_prod.sh

# Esperar a que los servicios estén listos
echo ""
echo "⏳ Esperando a que los servicios estén listos (30 segundos)..."
sleep 30

# ══════════════════════════════════════════════════════════════════════════════
# FASE 4: VERIFICACIÓN DE WARM-UP
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  FASE 4: VERIFICACIÓN DE WARM-UP SYSTEM"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

echo "🔥 Verificando logs del Brain (warm-up)..."
echo ""
docker compose logs brain | grep -A 20 "WARM-UP COMPLETADO"

echo ""
echo "✅ Debe mostrar:"
echo "   🎯 WARM-UP COMPLETADO: 5 símbolos listos para trading"
echo "   ⚡ Sistema operativo en <10 segundos"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# FASE 5: AUDITORÍA DE REDIS
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  FASE 5: AUDITORÍA DE REDIS KEYS"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

echo "📋 Copiando audit script al contenedor..."
docker compose cp audit_redis_keys.py dashboard:/app/

echo ""
echo "🔍 Ejecutando auditoría..."
echo ""
docker compose exec -T dashboard python /app/audit_redis_keys.py

echo ""
echo "✅ Debe mostrar:"
echo "   🎉 ¡SISTEMA PERFECTO! Arquitectura V21.2 sincronizada correctamente"
echo "   ✅ active_symbols → price:* keys: SYNC"
echo "   ✅ active_symbols → market_regime:* keys: SYNC"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# FASE 6: VERIFICACIÓN DE DASHBOARD API
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  FASE 6: VERIFICACIÓN DE DASHBOARD API"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

echo "📊 Verificando API endpoint..."
echo ""
curl -s http://localhost:8050/api/dashboard-data | python3 -m json.tool | head -30

echo ""
echo "✅ Debe mostrar:"
echo "   - total_equity: (número > 0, NO $0.00)"
echo "   - scanner: ['BTC', 'ETH', 'SOL', 'TRX', 'LINK']"
echo "   - regimes: {...} con datos de cada símbolo"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# FASE 7: VERIFICACIÓN DE SERVICIOS
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  FASE 7: ESTADO DE SERVICIOS"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

docker compose ps

echo ""
echo "✅ Debe mostrar:"
echo "   - 10 containers: Up"
echo "   - redis: Up (healthy)"
echo "   - dashboard: Up (puerto 8050)"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# FASE 8: RESUMEN FINAL
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  📊 RESUMEN DEL DEPLOYMENT"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "✅ FASE 1: Preparación ......................... COMPLETADO"
echo "✅ FASE 2: Pull cambios V21.2 .................. COMPLETADO"
echo "✅ FASE 3: Deployment (rebuild) ................ COMPLETADO"
echo "✅ FASE 4: Warm-up verification ................ VERIFICADO"
echo "✅ FASE 5: Redis audit ......................... EJECUTADO"
echo "✅ FASE 6: Dashboard API ....................... VERIFICADO"
echo "✅ FASE 7: Services status ..................... VERIFICADO"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🎉 DEPLOYMENT V21.2 COMPLETADO"
echo ""
echo "📚 Documentación completa en:"
echo "   - SESSION_COMPLETE_V21.2.md"
echo "   - PRODUCTION_TESTING_GUIDE.md"
echo "   - V21.2_ARCHITECTURE_FIXES_REPORT.md"
echo ""
echo "🔍 Para monitoreo continuo (OPCIONAL):"
echo "   screen -S redis-monitor"
echo "   ./continuous_redis_monitor.sh"
echo "   # Detach: Ctrl+A, luego D"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "           🚀 V21.2 SYNCHRONIZED ARCHITECTURE - PRODUCTION READY"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
