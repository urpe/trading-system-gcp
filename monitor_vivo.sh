#!/bin/bash
# MONITOR EN VIVO V15 (REDIS ENTERPRISE)
# Herramienta interactiva para ver el funcionamiento en tiempo real

show_menu() {
    clear
    echo "========================================================"
    echo "📺 MONITOR DE SISTEMA EN VIVO - HFT V15 ENTERPRISE"
    echo "========================================================"
    echo "Selecciona qué parte del sistema quieres observar:"
    echo ""
    echo "1. 🧠 CEREBRO (Brain)    - Ver generación de señales (Redis Listener)"
    echo "2. 👐 MANOS (Orders)     - Ver ejecución de órdenes"
    echo "3. 💼 CARTERA (Portfolio)- Ver balance y posiciones"
    echo "4. 👁️ MERCADO (Market)   - Ver ingestión de precios (Redis Publisher)"
    echo "5. 💾 PERSISTENCIA       - Ver guardado asíncrono en Firestore"
    echo "6. 📉 PAIRS (Strategy)   - Ver análisis de pares"
    echo "7. ⚡ REDIS MONITOR      - Ver comandos de Redis en tiempo real"
    echo "8. 🚨 ERRORES (Global)   - Ver solo errores recientes"
    echo "9. 💰 ACTIVIDAD (Resumen)- Ver solo Compras/Ventas recientes"
    echo "0. Salir"
    echo "========================================================"
    echo -n "Opción: "
}

while true; do
    show_menu
    read option
    
    case $option in
        1)
            echo "Conectando al CEREBRO... (Ctrl+C para salir)"
            docker compose logs -f brain
            ;;
        2)
            echo "Conectando a las MANOS... (Ctrl+C para salir)"
            docker compose logs -f orders
            ;;
        3)
            echo "Conectando al PORTFOLIO... (Ctrl+C para salir)"
            docker compose logs -f portfolio
            ;;
        4)
            echo "Conectando a MARKET DATA... (Ctrl+C para salir)"
            docker compose logs -f market-data
            ;;
        5)
            echo "Conectando a PERSISTENCE WORKER... (Ctrl+C para salir)"
            docker compose logs -f persistence
            ;;
        6)
            echo "Conectando a PAIRS TRADING... (Ctrl+C para salir)"
            docker compose logs -f pairs
            ;;
        7)
            echo "Conectando a REDIS MONITOR... (Ctrl+C para salir)"
            docker compose exec redis redis-cli monitor
            ;;
        8)
            echo "Buscando ERRORES en los últimos 500 logs de todo el sistema..."
            echo "------------------------------------------------------------"
            docker compose logs --tail 500 | grep -i -E "ERROR|CRITICAL|EXCEPTION|TRACEBACK|FAIL"
            echo "------------------------------------------------------------"
            echo "Presiona ENTER para volver al menú..."
            read
            ;;
        9)
            echo "Buscando ACTIVIDAD FINANCIERA reciente..."
            echo "------------------------------------------------------------"
            # Busca palabras clave de negocio: BUY, SELL, ORDER, FILLED, PROFIT
            docker compose logs --tail 1000 | grep -i -E "BUY|SELL|ORDER|FILLED|PROFIT|SIGNAL"
            echo "------------------------------------------------------------"
            echo "Presiona ENTER para volver al menú..."
            read
            ;;
        0)
            echo "Saliendo..."
            exit 0
            ;;
        *)
            echo "Opción no válida."
            sleep 1
            ;;
    esac
done
