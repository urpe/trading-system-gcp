#!/bin/bash
# ============================================================================
# RESET SIMULATION V19 - Reset financiero total
# ============================================================================
# Borra base de datos, limpia Redis, y reinicia sistema con $1000 limpios
# Autor: Sistema Autónomo V19
# Fecha: 2026-02-02
# ============================================================================

set -e  # Exit on error

echo "============================================================================"
echo "🔄 RESET SIMULATION V19 - Reset Financiero Total"
echo "============================================================================"
echo ""
echo "⚠️  WARNING: Esta operación es DESTRUCTIVA"
echo "   - Detendrá todos los contenedores"
echo "   - Borrará la base de datos SQLite (trades, wallet, etc.)"
echo "   - Limpiará todas las claves de Redis"
echo "   - Reiniciará el sistema desde $1000 limpios"
echo ""
read -p "¿Continuar? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Operación cancelada"
    exit 0
fi
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📂 Directorio de trabajo: $SCRIPT_DIR"
echo ""

# ============================================================================
# FASE 1: Detener contenedores
# ============================================================================
echo "🛑 FASE 1: Deteniendo contenedores..."
docker compose down || {
    echo "   ⚠️  Warning: docker compose down falló (contenedores ya estaban detenidos?)"
}
echo "   ✅ Contenedores detenidos"
echo ""

# ============================================================================
# FASE 2: Backup de base de datos
# ============================================================================
echo "💾 FASE 2: Backup de base de datos..."
DB_FILE="src/data/trading_bot_v16.db"

if [ -f "$DB_FILE" ]; then
    BACKUP_DIR="backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/trading_bot_v16_backup_$TIMESTAMP.db"
    
    cp "$DB_FILE" "$BACKUP_FILE"
    echo "   ✅ Backup creado: $BACKUP_FILE"
    
    # Mostrar tamaño
    DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
    echo "   📊 Tamaño actual: $DB_SIZE"
else
    echo "   ℹ️  No existe base de datos (primera ejecución)"
fi
echo ""

# ============================================================================
# FASE 3: Eliminar base de datos
# ============================================================================
echo "🗑️  FASE 3: Eliminando base de datos..."

if [ -f "$DB_FILE" ]; then
    rm -f "$DB_FILE"
    echo "   ✅ Base de datos eliminada: $DB_FILE"
else
    echo "   ℹ️  Base de datos no existe"
fi
echo ""

# ============================================================================
# FASE 4: Limpiar Redis
# ============================================================================
echo "🧹 FASE 4: Limpiando Redis..."
echo "   ⚠️  Levantando Redis temporalmente para limpiar..."

# Levantar solo Redis
docker compose up -d redis

# Esperar a que Redis esté listo
echo "   ⏳ Esperando a que Redis esté listo..."
sleep 5

# Ejecutar FLUSHALL
echo "   🗑️  Ejecutando FLUSHALL..."
docker compose exec -T redis redis-cli FLUSHALL || {
    echo "   ⚠️  Warning: FLUSHALL falló (Redis no disponible?)"
}

# Verificar limpieza
KEY_COUNT=$(docker compose exec -T redis redis-cli DBSIZE 2>/dev/null || echo "0")
echo "   📊 Keys en Redis: $KEY_COUNT"

if [ "$KEY_COUNT" == "0" ] || [ "$KEY_COUNT" == "(integer) 0" ]; then
    echo "   ✅ Redis limpiado exitosamente"
else
    echo "   ⚠️  Redis tiene $KEY_COUNT keys (esperado: 0)"
fi

# Detener Redis
docker compose down
echo ""

# ============================================================================
# FASE 5: Levantar sistema completo
# ============================================================================
echo "🚀 FASE 5: Levantando sistema completo..."
echo "   🔨 Building images..."
docker compose up --build -d

echo "   ⏳ Esperando inicialización de servicios..."
sleep 10

# Verificar servicios
echo ""
echo "   📊 Estado de servicios:"
docker compose ps
echo ""

# ============================================================================
# FASE 6: Verificar inicialización
# ============================================================================
echo "🔍 FASE 6: Verificando inicialización..."

echo "   ⏳ Esperando 20s adicionales para inicialización completa..."
sleep 20

# Verificar que Brain está corriendo
BRAIN_STATUS=$(docker compose ps brain --format "{{.State}}" 2>/dev/null || echo "unknown")
if [ "$BRAIN_STATUS" == "running" ]; then
    echo "   ✅ Brain: Running"
else
    echo "   ⚠️  Brain: $BRAIN_STATUS"
fi

# Verificar que Optimizer está corriendo
OPTIMIZER_STATUS=$(docker compose ps strategy-optimizer --format "{{.State}}" 2>/dev/null || echo "unknown")
if [ "$OPTIMIZER_STATUS" == "running" ]; then
    echo "   ✅ Strategy Optimizer: Running"
else
    echo "   ⚠️  Strategy Optimizer: $OPTIMIZER_STATUS"
fi

# Verificar que Dashboard está corriendo
DASHBOARD_STATUS=$(docker compose ps dashboard --format "{{.State}}" 2>/dev/null || echo "unknown")
if [ "$DASHBOARD_STATUS" == "running" ]; then
    echo "   ✅ Dashboard: Running"
else
    echo "   ⚠️  Dashboard: $DASHBOARD_STATUS"
fi

echo ""

# ============================================================================
# FASE 7: Verificar torneo inicial
# ============================================================================
echo "🏆 FASE 7: Verificando ejecución de torneo inicial..."
echo "   ℹ️  El optimizer debería ejecutar un torneo inmediato si Redis está vacío"
echo "   📋 Últimas líneas del log del optimizer:"
echo ""
docker compose logs strategy-optimizer --tail 15 2>/dev/null || echo "   ⚠️  No se pueden leer logs"
echo ""

# ============================================================================
# FASE 8: Resumen final
# ============================================================================
echo "============================================================================"
echo "✅ RESET COMPLETADO"
echo "============================================================================"
echo ""
echo "📊 RESUMEN:"
echo "   - Base de datos: BORRADA (backup en backups/)"
echo "   - Redis: LIMPIADO (FLUSHALL ejecutado)"
echo "   - Servicios: REINICIADOS"
echo "   - Capital inicial: \$1000 (configurado en settings.py)"
echo ""
echo "🔍 VALIDACIÓN:"
echo "   1. Abrir Dashboard: http://localhost:8050"
echo "   2. Verificar Wallet muestra \$1000"
echo "   3. Verificar logs: docker compose logs brain -f"
echo "   4. Ejecutar diagnóstico: python check_brain_status.py"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   - El torneo inicial debería ejecutarse en ~30 segundos"
echo "   - Monitorear logs: docker compose logs strategy-optimizer -f"
echo "   - Si no se ejecuta, verificar que Redis estaba vacío"
echo ""
echo "💡 PRÓXIMOS PASOS:"
echo "   1. Verificar Dashboard en http://localhost:8050"
echo "   2. Esperar 30-60s para primer torneo"
echo "   3. Monitorear por 24h"
echo "   4. Verificar Win Rate > 55%"
echo ""
echo "============================================================================"
