#!/bin/bash
# ============================================================================
# deploy_prod.sh - Deployment Script para GCP VM
# ============================================================================
# Uso: ./deploy_prod.sh [--full-rebuild]
#
# Workflow:
#   1. Pull latest code from GitHub
#   2. Restart services con Docker Compose
#   3. Optional: --full-rebuild para recrear imágenes (más lento)
#
# ⚠️ IMPORTANTE: Este script debe ejecutarse EN LA VM de GCP, NO en local
# ============================================================================

set -e  # Exit on error

echo "🚀 HFT Bot V21 - Production Deployment"
echo "======================================="
echo ""

# --- Validación de Entorno ---
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ ERROR: docker-compose.yml no encontrado"
    echo "   Este script debe ejecutarse en el directorio raíz del proyecto"
    exit 1
fi

# --- Pull Latest Code ---
echo "📥 Pulling latest code from GitHub..."
git fetch --all
git pull origin main || {
    echo "⚠️ Git pull failed. Posible conflicto o cambios no commiteados."
    echo "   Intentando reset forzado (cuidado)..."
    git reset --hard origin/main
}

echo "✅ Code updated to latest version"
echo ""

# --- Docker Deployment Strategy ---
if [ "$1" == "--full-rebuild" ]; then
    echo "🔨 Full rebuild mode: Recreando imágenes Docker..."
    docker compose down
    docker compose build --no-cache
    docker compose up -d
    echo "✅ Full rebuild completed"
else
    echo "⚡ Fast deployment: Restart services (sin rebuild)..."
    docker compose restart
    echo "✅ Services restarted"
fi

echo ""

# --- Verificación Post-Deployment ---
echo "🔍 Verificando servicios..."
sleep 5  # Dar tiempo a que los containers inicien

docker compose ps

echo ""
echo "📊 Dashboard URL: http://$(hostname -I | awk '{print $1}'):8050"
echo ""

# --- Health Check ---
RUNNING_COUNT=$(docker compose ps --format json | jq -s 'map(select(.State == "running")) | length')
TOTAL_COUNT=$(docker compose ps --format json | jq -s 'length')

if [ "$RUNNING_COUNT" -eq "$TOTAL_COUNT" ]; then
    echo "✅ DEPLOYMENT EXITOSO: $RUNNING_COUNT/$TOTAL_COUNT servicios corriendo"
else
    echo "⚠️ ADVERTENCIA: Solo $RUNNING_COUNT/$TOTAL_COUNT servicios corriendo"
    echo "   Revisa los logs: docker compose logs --tail=50"
fi

echo ""
echo "🎯 Next Steps:"
echo "   - Ver logs en vivo: docker compose logs -f"
echo "   - Verificar Dashboard: curl http://localhost:8050/api/dashboard-data"
echo "   - Ver regímenes: docker compose exec redis redis-cli KEYS 'market_regime:*'"
echo ""
echo "✨ Deployment completado"
