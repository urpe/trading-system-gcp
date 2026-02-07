#!/bin/bash
# ============================================================================
# cleanup_legacy_v21.sh - Deep Clean: Eliminar código zombie de versiones antiguas
# ============================================================================
# Uso: ./cleanup_legacy_v21.sh [--dry-run]
#
# PRECAUCIÓN: Este script elimina archivos permanentemente.
# Ejecuta primero con --dry-run para ver qué se borrará.
# ============================================================================

set -e

DRY_RUN=false
if [ "$1" == "--dry-run" ]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No se eliminará nada"
fi

echo "🧹 V21 Deep Clean - Eliminando código legacy"
echo "============================================="
echo ""

# --- FUNCIÓN DE ELIMINACIÓN SEGURA ---
safe_delete() {
    local target=$1
    local reason=$2
    
    if [ -e "$target" ]; then
        echo "❌ $target"
        echo "   Razón: $reason"
        
        if [ "$DRY_RUN" = false ]; then
            rm -rf "$target"
            echo "   ✅ Eliminado"
        else
            echo "   [DRY RUN - No eliminado]"
        fi
        echo ""
    fi
}

# --- CATEGORÍA 1: SERVICIOS OBSOLETOS ---
echo "📦 1. SERVICIOS OBSOLETOS (Comentados en docker-compose.yml)"
echo "---"

safe_delete "src/services/portfolio" \
    "DISABLED V17: Orders service maneja wallet/portfolio management (ver docker-compose.yml línea 14)"

safe_delete "src/services/pairs" \
    "DISABLED V19.1: Reduce ruido del sistema, enfoque en Mean Reversion (ver docker-compose.yml línea 54)"

# --- CATEGORÍA 2: DEPENDENCIAS DE FIRESTORE (V13-V16) ---
echo "📦 2. CÓDIGO FIRESTORE LEGACY (V13-V16)"
echo "---"

# Verificar si existen archivos con firestore
FIRESTORE_FILES=$(grep -rl "firestore" src/ 2>/dev/null | grep -v "__pycache__" || true)

if [ -n "$FIRESTORE_FILES" ]; then
    echo "⚠️ Archivos con referencias a Firestore detectados:"
    echo "$FIRESTORE_FILES"
    echo ""
    echo "   RECOMENDACIÓN: No se eliminan automáticamente (pueden tener lógica útil)."
    echo "   Acción manual: Refactorizar para usar SQLite/Redis únicamente."
else
    echo "✅ No hay referencias a Firestore en el código activo"
fi
echo ""

# --- CATEGORÍA 3: ARCHIVOS DE BACKTESTING LEGACY ---
echo "📦 3. BACKTESTING STRATEGIES LEGACY"
echo "---"

safe_delete "src/services/simulator/strategy_v19_1.py" \
    "V19.1 strategy específica (V21 usa brain/strategies/)"

safe_delete "src/services/simulator/__pycache__/strategy_v19_1.cpython-310.pyc" \
    "Cache de strategy_v19_1.py"

safe_delete "src/services/simulator/__pycache__/high_fidelity_backtester.cpython-310.pyc" \
    "Cache de backtester"

safe_delete "src/services/brain/backtesting/__pycache__" \
    "Cache Python del backtesting"

# --- CATEGORÍA 4: ARCHIVOS DE CONFIGURACIÓN OBSOLETOS ---
echo "📦 4. ARCHIVOS DE CONFIGURACIÓN LEGACY"
echo "---"

safe_delete "secrets.json" \
    "Credenciales Firestore obsoletas (V21 usa SQLite/Redis local)"

safe_delete "credentials.json" \
    "Service account GCP (no usado en V21)"

# --- CATEGORÍA 5: LOGS Y BACKUPS ANTIGUOS ---
echo "📦 5. LOGS Y BACKUPS ANTIGUOS"
echo "---"

safe_delete "simulation_output.log" \
    "Log de simulación antigua (logs deben estar en Docker)"

# Buscar backups viejos (más de 7 días)
if [ -d "backups/" ]; then
    OLD_BACKUPS=$(find backups/ -name "*.db" -mtime +7 2>/dev/null || true)
    if [ -n "$OLD_BACKUPS" ]; then
        echo "⚠️ Backups > 7 días detectados:"
        echo "$OLD_BACKUPS"
        echo "   No se eliminan automáticamente. Revisión manual recomendada."
    fi
fi
echo ""

# --- CATEGORÍA 6: __pycache__ GLOBAL ---
echo "📦 6. LIMPIEZA DE CACHE PYTHON"
echo "---"

PYCACHE_DIRS=$(find src -type d -name "__pycache__" 2>/dev/null || true)
PYCACHE_COUNT=$(echo "$PYCACHE_DIRS" | grep -c "__pycache__" || echo "0")

if [ "$PYCACHE_COUNT" -gt 0 ]; then
    echo "🗑️ Eliminando $PYCACHE_COUNT directorios __pycache__"
    
    if [ "$DRY_RUN" = false ]; then
        find src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        echo "   ✅ Cache Python limpiado"
    else
        echo "   [DRY RUN - No eliminado]"
    fi
else
    echo "✅ No hay cache Python obsoleto"
fi
echo ""

# --- RESUMEN ---
echo "============================================="
echo "📋 RESUMEN DE LIMPIEZA"
echo "============================================="

if [ "$DRY_RUN" = true ]; then
    echo "⚠️ DRY RUN MODE - Ningún archivo fue eliminado"
    echo ""
    echo "Para ejecutar la limpieza real:"
    echo "  ./cleanup_legacy_v21.sh"
else
    echo "✅ Limpieza completada"
    echo ""
    echo "📊 Espacio liberado (estimado):"
    du -sh src/ 2>/dev/null || echo "N/A"
fi

echo ""
echo "🎯 PRÓXIMOS PASOS:"
echo "  1. Verificar que el sistema sigue funcionando: ./verify_system.sh"
echo "  2. Commit de los cambios: git add -A && git commit -m 'cleanup: Remove legacy V13-V19 code'"
echo "  3. Si algo falla, restaurar con: git checkout HEAD -- <archivo>"
echo ""
echo "✨ Deep Clean V21 completado"
