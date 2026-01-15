import os
import subprocess

OUTPUT_FILE = "REPORTE_INGENIERIA.txt"

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)

def read_file(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return "[Error leyendo archivo]"
    return "[Archivo no encontrado]"

def generar_radiografia():
    print("🔬 Iniciando Escáner de Ingeniería Profunda...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("=== RADIOGRAFÍA DEL SISTEMA V8 (Estado Actual) ===\n\n")
        
        # 1. ESTADO DE DOCKER
        f.write("--- 1. ESTADO DE CONTENEDORES ---\n")
        f.write(run_command("docker ps -a"))
        f.write("\n\n")
        
        # 2. LOGS DE LOS CAÍDOS (Simulador y Pares)
        f.write("--- 2. LOGS DEL SIMULADOR (Últimas 50 líneas) ---\n")
        # Intentamos obtener logs del contenedor de simulador, buscando por nombre de imagen si el nombre cambio
        f.write(run_command("docker logs $(docker ps -a -q --filter ancestor=mi-bot-trading_simulator | head -n 1)"))
        f.write("\n\n")

        # 3. ARCHIVOS CRÍTICOS DE CONFIGURACIÓN
        f.write("--- 3. DOCKER-COMPOSE.YML (Redes y Puertos) ---\n")
        f.write(read_file("docker-compose.yml"))
        f.write("\n\n")
        
        # 4. CÓDIGO DEL SIMULADOR (Donde hiciste los cambios)
        f.write("--- 4. CÓDIGO SIMULADOR (services/backtesting-simulator/main.py) ---\n")
        f.write(read_file("services/backtesting-simulator/main.py"))
        f.write("\n\n")

        # 5. CÓDIGO DEL DASHBOARD (Para ver cómo llama al simulador)
        f.write("--- 5. CÓDIGO DASHBOARD (dashboard/main.py) ---\n")
        f.write(read_file("dashboard/main.py"))
        f.write("\n\n")

        # 6. ESTRUCTURA DE CARPETAS
        f.write("--- 6. ÁRBOL DE DIRECTORIOS ---\n")
        for root, dirs, files in os.walk("."):
            level = root.replace(".", "").count(os.sep)
            indent = " " * 4 * (level)
            f.write(f"{indent}{os.path.basename(root)}/\n")
            subindent = " " * 4 * (level + 1)
            for file in files:
                if file not in [OUTPUT_FILE, ".git", "__pycache__"]:
                    f.write(f"{subindent}{file}\n")

    print(f"✅ Reporte generado: {OUTPUT_FILE}")
    print("👉 Por favor, abre este archivo, copia su contenido o súbelo al chat.")

if __name__ == "__main__":
    generar_radiografia()