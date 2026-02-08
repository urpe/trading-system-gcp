#!/bin/bash
###############################################################################
# V22.1.2 PRODUCTION DEPLOYMENT - COPY/PASTE COMMANDS
#
# INSTRUCCIONES:
# 1. Abre una terminal LOCAL en tu PC
# 2. Copia y pega estos comandos UNO POR UNO
# 3. Verifica el resultado de cada comando antes de continuar
#
# Autor: HFT Trading Bot Team
# Versión: V22.1.2
# Fecha: 2026-02-08
###############################################################################

echo "════════════════════════════════════════════════════════════════"
echo "  V22.1.2 PRODUCTION DEPLOYMENT - STEP BY STEP GUIDE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  IMPORTANTE: Ejecuta estos comandos en tu TERMINAL LOCAL"
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASO 1: CONECTAR A GCP VM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║                        PASO 1: CONECTAR A GCP VM                         ║
╚══════════════════════════════════════════════════════════════════════════╝

Ejecuta este comando en tu terminal:

    ssh vm-trading-bot

Deberías ver el prompt de la VM. Verifica con:

    hostname

EOF

read -p "✅ ¿Conectado a la VM? (presiona Enter para continuar) "

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASO 2: NAVEGAR AL PROYECTO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║                   PASO 2: NAVEGAR AL PROYECTO                            ║
╚══════════════════════════════════════════════════════════════════════════╝

Ejecuta en la VM:

    cd ~/trading-system-gcp
    pwd

Deberías ver: /home/[tu-usuario]/trading-system-gcp

EOF

read -p "✅ ¿En el directorio correcto? (presiona Enter para continuar) "

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASO 3: VERIFICAR ESTADO ACTUAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║                  PASO 3: VERIFICAR ESTADO ACTUAL                         ║
╚══════════════════════════════════════════════════════════════════════════╝

Ejecuta estos comandos en la VM:

    # Ver commit actual
    git log --oneline -1

    # Ver servicios corriendo
    docker compose ps

EOF

read -p "✅ ¿Verificado estado? (presiona Enter para continuar) "

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASO 4: EJECUTAR DEPLOY AUTOMATIZADO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║              PASO 4: EJECUTAR DEPLOY AUTOMATIZADO                        ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️  ESTE ES EL COMANDO PRINCIPAL. Ejecuta en la VM:

    ./deploy_v22.1.1_prod.sh

El script hará:
  1. ✅ Backup automático de la base de datos
  2. ✅ Git pull (traerá V22.1.2 desde GitHub)
  3. ✅ Docker rebuild de todos los servicios
  4. ✅ Health checks automáticos
  5. ✅ Reporte final

⏱️  Tiempo estimado: 10-15 minutos

Cuando el script pregunte "Proceed with PRODUCTION deployment?", escribe:

    yes

EOF

read -p "✅ ¿Listo para ejecutar? (presiona Enter y ejecuta el script) "

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASO 5: VALIDACIÓN POST-DEPLOY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║                  PASO 5: VALIDACIÓN POST-DEPLOY                          ║
╚══════════════════════════════════════════════════════════════════════════╝

Una vez que el script termine, ejecuta estos comandos en la VM:

    # 1. Verificar servicios
    docker compose ps

    # 2. Verificar commit actual (debe ser d4be0d1)
    git log --oneline -1

    # 3. Health check completo
    docker compose exec dashboard python3 /app/monitor_v21.3_health.py

    # 4. Verificar Dashboard (sin errores)
    docker compose logs dashboard --since 5m | grep "ERROR"

    # 5. Verificar Orders (sin errores)
    docker compose logs orders --since 5m | grep "ERROR"

    # 6. Ver IP externa
    curl -s http://checkip.amazonaws.com

EOF

read -p "✅ ¿Validación completa? (presiona Enter para continuar) "

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PASO 6: ACCEDER AL DASHBOARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║                   PASO 6: ACCEDER AL DASHBOARD                           ║
╚══════════════════════════════════════════════════════════════════════════╝

Abre tu navegador en:

    http://[IP-EXTERNA]:5007

Deberías ver:
  ✅ Equity chart cargando
  ✅ Posiciones abiertas (si las hay)
  ✅ Historial de signals
  ✅ Sin errores 500

Prueba navegar a:
  - http://[IP-EXTERNA]:5007/asset/BTC
  - http://[IP-EXTERNA]:5007/asset/ETH

Ambos deben cargar sin errores.

EOF

read -p "✅ ¿Dashboard accesible? (presiona Enter para finalizar) "

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FINALIZACIÓN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║                   🎉 DEPLOYMENT COMPLETADO 🎉                            ║
╚══════════════════════════════════════════════════════════════════════════╝

✅ V22.1.2 "Post-Production Hardening" DEPLOYED TO PRODUCTION

Sistema:          ✅ Running
Health Score:     ✅ Expected 95-100/100
Errores:          ✅ Expected 0 activos
Dashboard:        ✅ Accessible
Commit:           ✅ d4be0d1

═══════════════════════════════════════════════════════════════════════════

📊 MONITOREO CONTINUO (Próximas 24-72 horas):

Ejecuta cada 6 horas en la VM:

    docker compose exec dashboard python3 /app/monitor_v21.3_health.py

Si Health Score < 90/100:
    docker compose logs brain orders dashboard --tail 100

═══════════════════════════════════════════════════════════════════════════

🚨 ROLLBACK (Si algo falla):

    docker compose down
    git reset --hard 62ade4c  # V21.3.1 (último estable)
    docker compose build --no-cache
    docker compose up -d

═══════════════════════════════════════════════════════════════════════════

📝 PARA CERRAR SESIÓN SSH:

    exit

═══════════════════════════════════════════════════════════════════════════

EOF

echo "Script completado. ¡Felicidades por el deploy exitoso! 🚀"
