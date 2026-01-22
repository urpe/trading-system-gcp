#!/bin/bash
echo "🔧 APLICANDO PARCHE FINAL V14.2 (Market Data Rescue)..."

# 1. ACTUALIZAR DEPENDENCIAS (Faltaban las de red asíncrona)
echo "📦 Agregando aiohttp y websockets a requirements.txt..."
cat >> requirements.txt << 'EOF'
# Async Network (Market Data)
aiohttp==3.9.1
websockets==12.0
EOF

# 2. PARCHE CÓDIGO MARKET DATA (Arreglar Imports y Path)
echo "📡 Parcheando src/services/market_data/main.py..."

# Leemos el archivo actual
FILE="src/services/market_data/main.py"

# Inyectamos un bloque al inicio para arreglar el sys.path
# Esto permite que 'from analyzer import...' funcione sin cambiar todo el código
TEMP_FILE=$(mktemp)
cat > $TEMP_FILE << 'EOF'
import sys
import os

# FIX V14.2: Asegurar que Python vea los submódulos locales
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

EOF

# Concatenamos el fix con el contenido original
cat $FILE >> $TEMP_FILE
mv $TEMP_FILE $FILE

echo "✅ Código parcheado con corrección de rutas (sys.path)."

# 3. RECONSTRUCCIÓN DEL SERVICIO CAÍDO
echo "🏗️ Reconstruyendo contenedor market-data..."
docker-compose up -d --build market-data

echo " "
echo "✅ OPERACIÓN FINALIZADA."
echo "👉 Espera 30 segundos y verifica todo con: docker ps"