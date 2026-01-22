#!/bin/bash
OUTPUT="AUDITORIA_V14_RESULTADOS.txt"

echo "========================================================" > $OUTPUT
echo "📊 REPORTE DE ESTADO V14 - $(date)" >> $OUTPUT
echo "========================================================" >> $OUTPUT
echo "" >> $OUTPUT

# 1. VERIFICACIÓN FÍSICA DE ARCHIVOS (¿Existen los cerebros?)
echo "1. VERIFICACIÓN DE ARCHIVOS CRÍTICOS (main.py):" >> $OUTPUT
echo "--------------------------------------------------------" >> $OUTPUT
# Lista de servicios que "resucitamos"
SERVICIOS=("pairs" "simulator" "brain" "market_data" "historical" "alerts")

for svc in "${SERVICIOS[@]}"; do
    FILE="src/services/$svc/main.py"
    if [ -f "$FILE" ]; then
        LINES=$(wc -l < "$FILE")
        echo "✅ $svc: ENCONTRADO ($LINES líneas)" >> $OUTPUT
    else
        echo "❌ $svc: FALTA main.py (CRÍTICO)" >> $OUTPUT
        # Listamos qué hay en la carpeta para ver si quedó basura
        if [ -d "src/services/$svc" ]; then
            echo "   Contenido de la carpeta:" >> $OUTPUT
            ls -F "src/services/$svc/" >> $OUTPUT
        else
            echo "   ⚠️ La carpeta src/services/$svc ni siquiera existe." >> $OUTPUT
        fi
    fi
done
echo "" >> $OUTPUT

# 2. SIGNOS VITALES DE LOS CONTENEDORES
echo "2. ESTADO DE LOS CONTENEDORES (DOCKER PS):" >> $OUTPUT
echo "--------------------------------------------------------" >> $OUTPUT
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.State}}" >> $OUTPUT
echo "" >> $OUTPUT

# 3. AUTOPSIA DE CONTENEDORES CAÍDOS O EN REINICIO
echo "3. LOGS DE ERROR (SOLO SERVICIOS CON PROBLEMAS):" >> $OUTPUT
echo "--------------------------------------------------------" >> $OUTPUT

# Obtenemos IDs de contenedores que no están 'running' o que están 'restarting'
FAILING_CONTAINERS=$(docker ps -a --filter "status=exited" --filter "status=restarting" --filter "status=dead" --format "{{.Names}}")

if [ -z "$FAILING_CONTAINERS" ]; then
    echo "✨ ¡INCREÍBLE! Todos los contenedores parecen estar sanos (Running)." >> $OUTPUT
else
    for container in $FAILING_CONTAINERS; do
        echo "🚨 ERROR EN: $container" >> $OUTPUT
        echo "--- ÚLTIMAS 20 LÍNEAS DE LOG ---" >> $OUTPUT
        docker logs --tail 20 "$container" 2>&1 >> $OUTPUT
        echo "--------------------------------" >> $OUTPUT
        echo "" >> $OUTPUT
    done
fi

echo "✅ Auditoría finalizada. Revisa el archivo $OUTPUT"