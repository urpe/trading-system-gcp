#!/bin/bash
# ============================================================================
# CLEANUP V19 - Limpieza estructural del sistema
# ============================================================================
# Elimina archivos temporales, __pycache__, y verifica estructura
# Autor: Sistema Autónomo V19
# Fecha: 2026-02-02
# ============================================================================

set -e  # Exit on error

echo "============================================================================"
echo "🧹 CLEANUP V19 - Limpieza Estructural"
echo "============================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📂 Directorio de trabajo: $SCRIPT_DIR"
echo ""

# ============================================================================
# FASE 1: Eliminar __pycache__ recursivamente
# ============================================================================
echo "🗑️  FASE 1: Eliminando directorios __pycache__..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
echo "   Encontrados: $PYCACHE_COUNT directorios"

if [ $PYCACHE_COUNT -gt 0 ]; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo "   ✅ Eliminados $PYCACHE_COUNT directorios __pycache__"
else
    echo "   ✅ No hay directorios __pycache__"
fi
echo ""

# ============================================================================
# FASE 2: Eliminar archivos .pyc individuales
# ============================================================================
echo "🗑️  FASE 2: Eliminando archivos .pyc..."
PYC_COUNT=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l)
echo "   Encontrados: $PYC_COUNT archivos"

if [ $PYC_COUNT -gt 0 ]; then
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo "   ✅ Eliminados $PYC_COUNT archivos .pyc"
else
    echo "   ✅ No hay archivos .pyc"
fi
echo ""

# ============================================================================
# FASE 3: Eliminar archivos .DS_Store (macOS)
# ============================================================================
echo "🗑️  FASE 3: Eliminando archivos .DS_Store..."
DS_COUNT=$(find . -type f -name ".DS_Store" 2>/dev/null | wc -l)

if [ $DS_COUNT -gt 0 ]; then
    find . -type f -name ".DS_Store" -delete 2>/dev/null || true
    echo "   ✅ Eliminados $DS_COUNT archivos .DS_Store"
else
    echo "   ✅ No hay archivos .DS_Store"
fi
echo ""

# ============================================================================
# FASE 4: Eliminar logs antiguos
# ============================================================================
echo "🗑️  FASE 4: Eliminando archivos .log antiguos..."
LOG_COUNT=$(find . -type f -name "*.log" 2>/dev/null | wc -l)

if [ $LOG_COUNT -gt 0 ]; then
    echo "   Encontrados: $LOG_COUNT archivos de log"
    echo "   ⚠️  Manteniendo logs (ejecutar manualmente si deseas borrarlos)"
else
    echo "   ✅ No hay archivos .log"
fi
echo ""

# ============================================================================
# FASE 5: Verificar estructura de código
# ============================================================================
echo "🔍 FASE 5: Verificando estructura del proyecto..."

# Verificar que src/services/ existe y tiene contenido
if [ -d "src/services" ]; then
    SERVICE_COUNT=$(find src/services -maxdepth 1 -type d | wc -l)
    echo "   ✅ src/services/ existe ($SERVICE_COUNT servicios)"
else
    echo "   ❌ ERROR: src/services/ no existe!"
    exit 1
fi

# Verificar que NO existe src/agents/ (legacy)
if [ -d "src/agents" ]; then
    echo "   ⚠️  WARNING: src/agents/ (legacy) existe"
    echo "   💡 Ejecutar: rm -rf src/agents/"
else
    echo "   ✅ src/agents/ (legacy) no existe"
fi

# Verificar docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    echo "   ✅ docker-compose.yml existe"
    
    # Verificar que todos los comandos apuntan a src/services/
    WRONG_PATHS=$(grep -E "command.*src/agents" docker-compose.yml 2>/dev/null | wc -l)
    if [ $WRONG_PATHS -gt 0 ]; then
        echo "   ⚠️  WARNING: docker-compose.yml tiene referencias a src/agents/"
    else
        echo "   ✅ docker-compose.yml apunta correctamente a src/services/"
    fi
else
    echo "   ❌ ERROR: docker-compose.yml no existe!"
    exit 1
fi
echo ""

# ============================================================================
# FASE 6: Resumen de limpieza
# ============================================================================
echo "============================================================================"
echo "✅ LIMPIEZA COMPLETADA"
echo "============================================================================"
echo ""
echo "📊 RESUMEN:"
echo "   - Directorios __pycache__ eliminados: $PYCACHE_COUNT"
echo "   - Archivos .pyc eliminados: $PYC_COUNT"
echo "   - Archivos .DS_Store eliminados: $DS_COUNT"
echo "   - Archivos .log encontrados: $LOG_COUNT (no eliminados)"
echo ""
echo "📂 ESTRUCTURA:"
echo "   - src/services/: ✅ OK"
echo "   - src/agents/: $([ -d 'src/agents' ] && echo '⚠️  Existe (legacy)' || echo '✅ No existe')"
echo "   - docker-compose.yml: ✅ OK"
echo ""
echo "💡 SIGUIENTE PASO:"
echo "   Ejecutar: ./reset_simulation.sh"
echo ""
echo "============================================================================"
