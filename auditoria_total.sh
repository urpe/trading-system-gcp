#!/bin/bash
# AUDITORIA TOTAL DEL SISTEMA V14
# Genera reportes detallados de Infraestructura, Código y Logs.

echo "=============================================================================="
echo "🚀 INICIANDO AUDITORÍA TOTAL - SISTEMA HFT V14"
echo "Fecha: $(date)"
echo "=============================================================================="
echo ""

# CREAR DIRECTORIO DE RESULTADOS
mkdir -p auditoria_resultados
cd auditoria_resultados || exit

echo "📂 Generando archivos en carpeta: auditoria_resultados/"

# ________________________________________________________________________________
# FASE 1: Auditoría de Infraestructura y Estructura
# ________________________________________________________________________________
echo "------------------------------------------------------------------------------"
echo "🔍 FASE 1: INFRAESTRUCTURA Y ESTRUCTURA"
echo "------------------------------------------------------------------------------"

echo "[1/4] Mapeando estructura del proyecto..."
find ../src -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g' > auditoria_estructura.txt
echo "   ✅ Estructura guardada en: auditoria_estructura.txt"

echo "[2/4] Calculando volumen de código..."
find ../src -name "*.py" | xargs wc -l > auditoria_volumen.txt
echo "   ✅ Volumen guardado en: auditoria_volumen.txt"

echo "[3/4] Inventariando librerías (Stack Tecnológico)..."
# Intentamos usar docker-compose para mayor compatibilidad
if docker-compose ps -q brain > /dev/null 2>&1; then
    docker-compose exec -T brain pip list > auditoria_librerias.txt
    echo "   ✅ Librerías del servicio 'brain' guardadas en: auditoria_librerias.txt"
else
    echo "   ⚠️ Servicio 'brain' no encontrado en ejecución. Intentando 'bot_cerebro'..."
    if docker ps | grep -q bot_cerebro; then
        docker exec bot_cerebro pip list > auditoria_librerias.txt
        echo "   ✅ Librerías de 'bot_cerebro' guardadas."
    else
        echo "   ❌ No se pudo conectar al contenedor para listar librerías." > auditoria_librerias.txt
    fi
fi

echo "[4/4] Verificando estado de contenedores..."
docker ps > auditoria_contenedores.txt
echo "   ✅ Estado guardado en: auditoria_contenedores.txt"


# ________________________________________________________________________________
# FASE 2: Auditoría de Código (Calidad y Seguridad)
# ________________________________________________________________________________
echo ""
echo "------------------------------------------------------------------------------"
echo "🕵️‍♂️ FASE 2: CALIDAD Y SEGURIDAD (Puede tardar unos minutos)"
echo "------------------------------------------------------------------------------"

echo "[5/6] Ejecutando análisis Pylint (Sintaxis y Bugs)..."
# Ejecutamos desde la raíz del proyecto (..)
docker run --rm -v "$(dirname $(pwd))":/app python:3.10-slim /bin/bash -c "pip install pylint && pylint --disable=C,R /app/src" > auditoria_calidad_pylint.txt 2>&1
echo "   ✅ Reporte Pylint guardado en: auditoria_calidad_pylint.txt"

echo "[6/6] Ejecutando análisis Bandit (Seguridad)..."
docker run --rm -v "$(dirname $(pwd))":/app python:3.10-slim /bin/bash -c "pip install bandit && bandit -r /app/src" > auditoria_seguridad_bandit.txt 2>&1
echo "   ✅ Reporte Bandit guardado en: auditoria_seguridad_bandit.txt"


# ________________________________________________________________________________
# FASE 3: Evidencia de Errores (Logs Recientes)
# ________________________________________________________________________________
echo ""
echo "------------------------------------------------------------------------------"
echo "🚑 FASE 3: EVIDENCIA DE ERRORES"
echo "------------------------------------------------------------------------------"

echo "[7/7] Extrayendo logs del sistema..."
cd .. # Volvemos a raíz para docker-compose
docker-compose logs --tail 200 > auditoria_resultados/auditoria_logs_sistema.txt 2>&1
cd auditoria_resultados || exit
echo "   ✅ Logs guardados en: auditoria_logs_sistema.txt"

# ________________________________________________________________________________
# FASE 4: Análisis de Lógica de Negocio (Resultados Operativos)
# ________________________________________________________________________________
echo ""
echo "------------------------------------------------------------------------------"
echo "🧠 FASE 4: ANÁLISIS DE FLUJO DE NEGOCIO (¿Qué está haciendo el bot?)"
echo "------------------------------------------------------------------------------"

echo "[Analizando] Últimas Señales Generadas (Cerebro)..."
docker-compose logs --tail 2000 brain | grep -i "SIGNAL" > auditoria_negocio_senales.txt
echo "   ✅ Señales guardadas en: auditoria_negocio_senales.txt"

echo "[Analizando] Ejecuciones de Órdenes (Manos)..."
docker-compose logs --tail 2000 orders | grep -i -E "ORDER|FILLED|EXECUTED" > auditoria_negocio_ordenes.txt
echo "   ✅ Ejecuciones guardadas en: auditoria_negocio_ordenes.txt"

echo "[Analizando] Movimientos de Cartera (Portfolio)..."
docker-compose logs --tail 2000 portfolio | grep -i -E "BALANCE|POSITION|EQUITY" > auditoria_negocio_cartera.txt
echo "   ✅ Movimientos guardados en: auditoria_negocio_cartera.txt"

echo "[Analizando] Errores Críticos Recientes..."
docker-compose logs --tail 2000 | grep -i -E "ERROR|CRITICAL|EXCEPTION" > auditoria_errores_criticos.txt
echo "   ✅ Errores filtrados en: auditoria_errores_criticos.txt"


echo ""
echo "=============================================================================="
echo "✨ AUDITORÍA COMPLETADA EXITOSAMENTE"
echo "Revisa la carpeta 'auditoria_resultados' para ver los informes."
echo "=============================================================================="
