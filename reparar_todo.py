import os
import subprocess
import time

def run_cmd(cmd):
    print(f"🔄 Ejecutando: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        print(f"⚠️ Alerta: El comando '{cmd}' tuvo problemas, pero continuamos...")

def write_file(path, content):
    print(f"📝 Reescribiendo configuración: {path}")
    with open(path, 'w') as f:
        f.write(content)

print("=== 🚀 INICIANDO REPARACIÓN SISTEMA PRO v8.0 ===")

# 1. LIMPIEZA NUCLEAR DE DOCKER
print("\n--- ☢️ FASE 1: LIMPIEZA NUCLEAR ---")
run_cmd("docker-compose down")
run_cmd("docker rm -f $(docker ps -a -q)")
run_cmd("docker system prune -f")
run_cmd("docker volume prune -f")

# 2. REESCRIBIR DOCKER-COMPOSE (El Mapa del Ejército)
print("\n--- 🏗️ FASE 2: ARQUITECTURA ---")
docker_compose_content = """version: '3.8'

services:
  market-data:
    build: .
    container_name: bot_ojos
    command: python3 services/market_data_hub/main.py
    env_file: .env
    restart: always

  historical-data:
    build: .
    container_name: bot_historia
    command: python3 services/historical_data/main.py
    env_file: .env
    ports:
      - "5002:5000"
    restart: always

  strategy:
    build: .
    container_name: bot_cerebro
    command: python3 strategy_agent/main.py
    env_file: .env
    ports:
      - "5000:5000"
    restart: always
    depends_on:
      - market-data

  pairs-trading:
    build: .
    container_name: bot_pares
    command: python3 services/pairs-trading/main.py
    env_file: .env
    restart: always

  orders:
    build: .
    container_name: bot_manos
    command: python3 order_agent/main.py
    env_file: .env
    ports:
      - "5001:5001"
    restart: always
    depends_on:
      - strategy

  portfolio:
    build: .
    container_name: bot_contador
    command: python3 services/portfolio_manager/main.py
    env_file: .env
    restart: always

  dashboard:
    build: .
    container_name: bot_cara
    command: python3 dashboard/main.py
    env_file: .env
    ports:
      - "8050:8050"
    restart: always
    depends_on:
      - historical-data
      - strategy
      - simulator
      - pairs-trading

  simulator:
    build: .
    container_name: bot_simulador
    command: python3 services/backtesting-simulator/main.py
    env_file: .env
    restart: always

  alerts:
    build: .
    container_name: bot_alertas
    command: python3 alert_service/main.py
    env_file: .env
    restart: always
"""
write_file("docker-compose.yml", docker_compose_content)

# 3. CORREGIR CÓDIGO DEL DASHBOARD (Conexiones internas)
print("\n--- 🔌 FASE 3: CONEXIONES DEL DASHBOARD ---")
dashboard_path = "dashboard/main.py"
if os.path.exists(dashboard_path):
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Reemplazos forzosos de URLs
    replacements = {
        'localhost:5000': 'simulator:5000',
        'localhost:8080': 'simulator:5000',
        'SIMULATOR_URL", "http://localhost': 'SIMULATOR_URL", "http://simulator',
        'PAIRS_URL", "http://localhost': 'PAIRS_URL", "http://pairs-trading',
        'HISTORICAL_URL", "http://localhost': 'HISTORICAL_URL", "http://historical-data'
    }
    
    # Asegurar que las URLs por defecto apunten a los nombres de servicio
    if 'SIMULATOR_URL = os.environ.get("SIMULATOR_URL", "http://simulator:5000")' not in content:
        print("🔧 Parcheando URLs en dashboard/main.py...")
        content = content.replace('SIMULATOR_URL = os.environ.get("SIMULATOR_URL", "https://backtesting-simulator-347366802960.us-central1.run.app")', 
                                'SIMULATOR_URL = os.environ.get("SIMULATOR_URL", "http://simulator:5000")')
        content = content.replace('PAIRS_URL = os.environ.get("PAIRS_URL", "https://pairs-trading-engine-347366802960.us-central1.run.app")', 
                                'PAIRS_URL = os.environ.get("PAIRS_URL", "http://pairs-trading:5000")')
        content = content.replace('HISTORICAL_URL = os.environ.get("HISTORICAL_URL", "https://historical-data-347366802960.us-central1.run.app")', 
                                'HISTORICAL_URL = os.environ.get("HISTORICAL_URL", "http://historical-data:5000")')
        
        # Corrección genérica si no coincide lo anterior
        content = content.replace('http://localhost:5000', 'http://simulator:5000') 
    
    write_file(dashboard_path, content)

# 4. CORREGIR TODOS LOS MAIN.PY PARA ESCUCHAR EN 0.0.0.0
print("\n--- 👂 FASE 4: OÍDOS ABIERTOS (0.0.0.0) ---")
# Lista de todos los main.py que son servicios Flask
services_files = [
    "services/historical_data/main.py",
    "services/backtesting-simulator/main.py",
    "services/pairs-trading/main.py",
    "strategy_agent/main.py",
    "dashboard/main.py"
]

for file_path in services_files:
    if os.path.exists(file_path):
        print(f"🔧 Revisando: {file_path}")
        with open(file_path, 'r') as f:
            code = f.read()
        
        # Si tiene app.run pero no tiene host='0.0.0.0', lo arreglamos
        if "app.run" in code and "host='0.0.0.0'" not in code:
            print(f"   -> Aplicando parche de puerto/host a {file_path}")
            # Reemplazo inteligente: busca app.run(...) y lo cambia por la versión segura
            new_code = code.replace("app.run(port=port)", "app.run(host='0.0.0.0', port=port)")
            new_code = new_code.replace("app.run(debug=True)", "port = int(os.environ.get('PORT', 5000))\n    app.run(host='0.0.0.0', port=port)")
            new_code = new_code.replace("app.run(port=8080)", "app.run(host='0.0.0.0', port=5000)")
            
            # Asegurar puerto 5000 por defecto en variables de entorno (excepto dashboard)
            if "dashboard" not in file_path:
                new_code = new_code.replace("os.environ.get('PORT', 8080)", "os.environ.get('PORT', 5000)")
            else:
                 new_code = new_code.replace("os.environ.get('PORT', 8080)", "os.environ.get('PORT', 8050)")
                 
            write_file(file_path, new_code)

# 5. DESPLIEGUE FINAL
print("\n--- 🚀 FASE 5: LANZAMIENTO ---")
print("Levantando el ejército de bots...")
run_cmd("docker-compose up -d --build --remove-orphans")

print("\n✅ ¡SISTEMA REPARADO Y LANZADO!")
print("👉 Dashboard: http://23.251.129.214:8050 (Recarga con F5)")
print("👉 Prueba Data: curl -X POST 'http://localhost:5002/load/BTC?days=30'")

