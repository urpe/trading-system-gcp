#!/bin/bash

echo "🛑 DETENIENDO SISTEMA COMPLETO..."
docker-compose down --remove-orphans

echo "🧹 LIMPIEZA PROFUNDA..."
# Borramos contenedores zombies específicos si quedaron
docker rm -f bot_simulador bot_pares bot_dashboard 2>/dev/null

echo "🏗️ RECONSTRUYENDO CEREBROS (BUILD)..."
# Forzamos la reconstrucción del simulador para que tome el código nuevo
docker-compose build --no-cache simulator

echo "🚀 LANZANDO SISTEMA V9.0..."
docker-compose up -d

echo "⏳ ESPERANDO A QUE LOS SERVICIOS DESPIERTEN (15 seg)..."
sleep 15

echo "📊 ESTADO DEL SISTEMA:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "✅ LISTO. Prueba el Dashboard ahora."