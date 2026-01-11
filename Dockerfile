# Usamos una imagen ligera de Python oficial
FROM python:3.10-slim

# Evita que Python genere archivos .pyc y fuerza logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos dependencias del sistema (git, gcc, etc)
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiamos los requerimientos primero (para aprovechar caché)
# NOTA: Crearemos este archivo requirements.txt en un momento
COPY requirements.txt .

# Instalamos las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código del proyecto
COPY . .

# Variable de entorno para que Python encuentre los módulos
ENV PYTHONPATH=/app

