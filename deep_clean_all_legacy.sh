#!/bin/bash
# ============================================================================
# deep_clean_all_legacy.sh - LIMPIEZA PROFUNDA de archivos obsoletos
# ============================================================================
# Elimina TODOS los archivos de versiones antiguas (V13-V20)
# Mantiene SOLO documentación V21.1 actual
#
# SEGURO: Todo está respaldado en Git/GitHub
# ============================================================================

set -e

DRY_RUN=false
if [ "$1" == "--dry-run" ]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No se eliminará nada"
fi

echo "🧹 DEEP CLEAN - Eliminando TODA documentación legacy"
echo "===================================================="
echo ""

# --- FUNCIÓN DE ELIMINACIÓN ---
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

# --- CATEGORÍA 1: REPORTES DE VERSIONES ANTIGUAS (V13-V20) ---
echo "📦 1. REPORTES Y DOCUMENTACIÓN LEGACY"
echo "---"

safe_delete "ANÁLISIS_FINAL_V20.md" \
    "Reporte de V20 obsoleto (ahora en V21.1)"

safe_delete "AUDIT_REPORT_V19.md" \
    "Auditoría de V19 obsoleta"

safe_delete "DEPLOYMENT_V19.1_REPORT.md" \
    "Deployment V19.1 obsoleto"

safe_delete "ONBOARDING_NEW_ENGINEER.md" \
    "Onboarding antiguo (V21.1 tiene documentación actualizada)"

safe_delete "REGIME_DIAGNOSIS_REPORT.txt" \
    "Diagnóstico de régimen antiguo"

safe_delete "SIMULATION_REPORT_V19_vs_V19.1.md" \
    "Reporte de simulación V19 obsoleto"

safe_delete "SIMULATION_REPORT_V20.md" \
    "Reporte de simulación V20 obsoleto"

safe_delete "SYSTEM_ARCHITECTURE_MASTER.md" \
    "Arquitectura legacy (V21.1 tiene docs actualizadas)"

safe_delete "V18_5_UPGRADE_REPORT.md" \
    "Reporte V18.5 obsoleto"

safe_delete "V19_IMPLEMENTATION_REPORT.md" \
    "Implementación V19 obsoleta"

safe_delete "V19_REGIME_SWITCHING_RELEASE.md" \
    "Release notes V19 obsoleto"

safe_delete "V21_DEPLOYMENT_STATUS.md" \
    "Status V21 obsoleto (ahora tenemos V21.1_FINAL_STATUS_REPORT.md)"

safe_delete "VISUAL_SYSTEM_FLOW.txt" \
    "Diagrama de flujo antiguo"

# --- CATEGORÍA 2: SCRIPTS DE DEBUGGING ANTIGUOS ---
echo "📦 2. SCRIPTS DE DEBUGGING Y VERIFICACIÓN LEGACY"
echo "---"

safe_delete "check_brain_status.py" \
    "Script de debugging antiguo (ahora usamos verify_system.sh)"

safe_delete "debug_regime.py" \
    "Script de debugging V19/V20 obsoleto"

safe_delete "verify_adx_live.py" \
    "Script de verificación ADX antiguo (V21 resolvió el bug)"

safe_delete "auditoria_total.sh" \
    "Script de auditoría antiguo (reemplazado por verify_system.sh)"

safe_delete "cleanup_v19.sh" \
    "Script de limpieza V19 obsoleto (ahora usamos cleanup_legacy_v21.sh)"

safe_delete "monitor_vivo.sh" \
    "Script de monitoreo antiguo"

safe_delete "reset_simulation.sh" \
    "Script de reset antiguo"

safe_delete "run_system_simulation.py" \
    "Script de simulación antiguo"

safe_delete "exportar_todo_codigo.sh" \
    "Script de exportación legacy"

# --- CATEGORÍA 3: PLANES ANTIGUOS DE CURSOR ---
echo "📦 3. PLANES ANTIGUOS DE CURSOR (.cursor/plans/)"
echo "---"

if [ -d ".cursor/plans" ]; then
    echo "🗑️ Eliminando planes de Cursor antiguos..."
    
    # Listar planes antes de eliminar
    PLAN_COUNT=$(find .cursor/plans -name "*.plan.md" 2>/dev/null | wc -l || echo "0")
    
    if [ "$PLAN_COUNT" -gt 0 ]; then
        echo "   Encontrados: $PLAN_COUNT archivos .plan.md"
        
        if [ "$DRY_RUN" = false ]; then
            # Eliminar todos los planes
            find .cursor/plans -name "*.plan.md" -delete 2>/dev/null || true
            echo "   ✅ $PLAN_COUNT planes eliminados"
        else
            echo "   [DRY RUN - No eliminado]"
            find .cursor/plans -name "*.plan.md" 2>/dev/null | head -10
        fi
    else
        echo "   ✅ No hay planes antiguos"
    fi
else
    echo "   ✅ Directorio .cursor/plans no existe"
fi
echo ""

# --- CATEGORÍA 4: ARCHIVOS DE CONFIGURACIÓN ANTIGUOS ---
echo "📦 4. ARCHIVOS DE CONFIGURACIÓN OBSOLETOS"
echo "---"

safe_delete "install_v15_env.sh" \
    "Script de instalación V15 obsoleto"

# --- CATEGORÍA 5: BACKUPS ANTIGUOS ---
echo "📦 5. BACKUPS Y ARCHIVOS TEMPORALES"
echo "---"

if [ -d "backups/" ]; then
    echo "📁 Revisando backups..."
    
    # Contar backups
    BACKUP_COUNT=$(find backups/ -type f 2>/dev/null | wc -l || echo "0")
    
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        echo "   Encontrados: $BACKUP_COUNT archivos en backups/"
        echo "   ⚠️ RECOMENDACIÓN: Revisar manualmente si son necesarios"
        echo "   No se eliminan automáticamente por seguridad"
    else
        echo "   ✅ No hay backups"
    fi
fi
echo ""

# --- CATEGORÍA 6: DOCUMENTACIÓN DE AUDITORÍA ANTIGUA ---
echo "📦 6. DIRECTORIOS DE AUDITORÍA LEGACY"
echo "---"

safe_delete "audit/" \
    "Directorio de auditoría antiguo (V21.1 usa logs Docker)"

safe_delete "docs/" \
    "Documentación legacy (V21.1 tiene docs en root actualizados)"

# --- RESUMEN DE ARCHIVOS A MANTENER ---
echo "============================================="
echo "📋 ARCHIVOS QUE SE MANTIENEN (V21.1 ACTUAL)"
echo "============================================="
echo ""
echo "✅ Documentación V21.1:"
echo "   - ACTIONS_COMPLETED_REPORT.md"
echo "   - V21.1_FINAL_STATUS_REPORT.md"
echo "   - V21_BLACKOUT_POSTMORTEM.md"
echo "   - V21_DATA_CONSISTENCY_REPORT.md"
echo "   - DEV_WORKFLOW_GUIDE.md"
echo "   - FINOPS_OPTIMIZATION_REPORT.md"
echo "   - README.md"
echo ""
echo "✅ Scripts activos:"
echo "   - deploy_prod.sh"
echo "   - verify_system.sh"
echo "   - cleanup_legacy_v21.sh"
echo "   - git_commit_v21.1.sh"
echo ""
echo "✅ Configuración:"
echo "   - docker-compose.yml"
echo "   - Dockerfile"
echo "   - requirements.txt"
echo "   - .cursorrules"
echo "   - .gitignore"
echo ""

# --- RESUMEN FINAL ---
echo "============================================="
echo "📊 RESUMEN DE LIMPIEZA"
echo "============================================="

if [ "$DRY_RUN" = true ]; then
    echo "⚠️ DRY RUN MODE - Ningún archivo fue eliminado"
    echo ""
    echo "Para ejecutar la limpieza real:"
    echo "  ./deep_clean_all_legacy.sh"
else
    echo "✅ Limpieza completada"
    echo ""
    echo "📊 Espacio liberado:"
    du -sh . 2>/dev/null || echo "N/A"
    echo ""
    echo "📁 Archivos restantes:"
    find . -maxdepth 1 -type f -name "*.md" | wc -l && echo "documentos .md en root"
    find . -maxdepth 1 -type f -name "*.sh" | wc -l && echo "scripts .sh en root"
fi

echo ""
echo "🎯 PRÓXIMOS PASOS:"
echo "  1. Verificar sistema: ./verify_system.sh"
echo "  2. Commit: git add -A && git commit -m 'cleanup: Remove ALL legacy docs V13-V20'"
echo "  3. Push: git push origin main"
echo ""
echo "⚠️ NOTA: Todo está respaldado en Git. Si necesitas algo, usa:"
echo "   git checkout HEAD~2 -- <archivo>"
echo ""
echo "✨ Deep Clean completado"
