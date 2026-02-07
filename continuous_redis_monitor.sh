#!/bin/bash
# =============================================================================
# continuous_redis_monitor.sh - Monitoreo Continuo de Redis Keys (V21.2)
# =============================================================================
# Ejecuta audit_redis_keys.py cada 1 hora y envía alertas si detecta issues.
#
# USO:
#   ./continuous_redis_monitor.sh
#
# DESPLIEGUE EN PRODUCCIÓN:
#   # Opción 1: systemd service (recomendado)
#   sudo systemctl start redis-monitor
#   
#   # Opción 2: screen/tmux
#   screen -dmS redis-monitor ./continuous_redis_monitor.sh
#   
#   # Opción 3: nohup
#   nohup ./continuous_redis_monitor.sh > monitor.log 2>&1 &
#
# ALERTAS:
#   - Si detecta discrepancias, escribe en alerts.log
#   - Integración con Telegram/Email (opcional, ver sección ALERTING)
# =============================================================================

set -e

# --- CONFIGURACIÓN ---
AUDIT_SCRIPT="audit_redis_keys.py"
CHECK_INTERVAL=3600  # 1 hora en segundos
ALERT_LOG="redis_alerts.log"
REPORT_DIR="redis_audit_reports"
MAX_REPORTS=168  # Guardar 1 semana de reportes (7 días * 24 horas)

# Colores para logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- FUNCIONES ---

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ℹ️ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

send_alert() {
    local message="$1"
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    
    # Guardar en log de alertas
    echo "[$timestamp] $message" >> "$ALERT_LOG"
    
    # TODO: Integrar con Telegram Bot API
    # curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    #      -d chat_id="${TELEGRAM_CHAT_ID}" \
    #      -d text="🚨 Redis Monitor Alert: $message"
    
    # TODO: Integrar con SendGrid/Mailgun
    # curl -s -X POST "https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/messages" \
    #      -u "api:${MAILGUN_API_KEY}" \
    #      -F from="alerts@trading-bot.com" \
    #      -F to="${ALERT_EMAIL}" \
    #      -F subject="Redis Monitor Alert" \
    #      -F text="$message"
    
    log_error "ALERT SENT: $message"
}

run_audit() {
    local report_file="$REPORT_DIR/audit_$(date +'%Y%m%d_%H%M%S').txt"
    
    log_info "Ejecutando auditoría de Redis..."
    
    # Ejecutar audit script dentro del contenedor Dashboard
    if docker compose ps dashboard | grep -q "Up"; then
        docker compose exec -T dashboard python "$AUDIT_SCRIPT" > "$report_file" 2>&1
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            # Analizar resultados
            if grep -q "⚠️ DISCREPANCIA" "$report_file"; then
                log_warning "Discrepancias detectadas en Redis"
                send_alert "Redis audit encontró DISCREPANCIAS. Ver: $report_file"
            elif grep -q "⚠️ BRAIN ISSUE" "$report_file"; then
                log_warning "Brain no está generando regímenes para todos los símbolos"
                send_alert "Brain issue detectado. Ver: $report_file"
            elif grep -q "🎉 ¡SISTEMA PERFECTO!" "$report_file"; then
                log_info "Auditoría exitosa - Sistema en estado óptimo ✅"
            else
                log_warning "Auditoría completada con advertencias menores"
            fi
        else
            log_error "Error ejecutando audit script (exit code: $exit_code)"
            send_alert "Audit script falló con código: $exit_code"
        fi
    else
        log_error "Contenedor Dashboard no está corriendo"
        send_alert "Dashboard container DOWN - No se puede ejecutar auditoría"
    fi
    
    # Limpiar reportes antiguos (mantener solo últimos MAX_REPORTS)
    cleanup_old_reports
}

cleanup_old_reports() {
    local report_count=$(ls -1 "$REPORT_DIR"/audit_*.txt 2>/dev/null | wc -l)
    
    if [ "$report_count" -gt "$MAX_REPORTS" ]; then
        log_info "Limpiando reportes antiguos (manteniendo últimos $MAX_REPORTS)..."
        ls -1t "$REPORT_DIR"/audit_*.txt | tail -n +$((MAX_REPORTS + 1)) | xargs rm -f
    fi
}

check_system_health() {
    log_info "Verificando salud del sistema..."
    
    # Verificar que Docker Compose esté corriendo
    if ! docker compose ps | grep -q "Up"; then
        log_error "Algunos contenedores NO están corriendo"
        send_alert "Docker Compose health check FAILED - Algunos servicios DOWN"
        return 1
    fi
    
    # Verificar Redis
    if ! docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_error "Redis NO responde"
        send_alert "Redis health check FAILED - No responde a PING"
        return 1
    fi
    
    log_info "Sistema saludable ✅"
    return 0
}

# --- INICIALIZACIÓN ---

log_info "🔍 Iniciando Redis Continuous Monitor V21.2"
log_info "   Check Interval: ${CHECK_INTERVAL}s ($(($CHECK_INTERVAL / 3600))h)"
log_info "   Alert Log: $ALERT_LOG"
log_info "   Reports Dir: $REPORT_DIR"
log_info ""

# Crear directorio de reportes si no existe
mkdir -p "$REPORT_DIR"

# Verificar que el script de auditoría existe
if [ ! -f "$AUDIT_SCRIPT" ]; then
    log_error "Script $AUDIT_SCRIPT no encontrado en el directorio actual"
    exit 1
fi

# --- LOOP PRINCIPAL ---

iteration=0

while true; do
    iteration=$((iteration + 1))
    log_info "═══════════════════════════════════════════════════════════"
    log_info "Iteración #$iteration - $(date +'%Y-%m-%d %H:%M:%S')"
    log_info "═══════════════════════════════════════════════════════════"
    
    # 1. Verificar salud del sistema
    if check_system_health; then
        # 2. Ejecutar auditoría
        run_audit
    else
        log_warning "Saltando auditoría debido a health check fallido"
    fi
    
    # 3. Esperar hasta la próxima iteración
    log_info ""
    log_info "⏳ Próxima auditoría en $(($CHECK_INTERVAL / 3600))h..."
    log_info "   Hora actual: $(date +'%Y-%m-%d %H:%M:%S')"
    log_info "   Próxima: $(date -d "+$CHECK_INTERVAL seconds" +'%Y-%m-%d %H:%M:%S')"
    log_info ""
    
    sleep "$CHECK_INTERVAL"
done
