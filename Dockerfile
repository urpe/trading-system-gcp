FROM python:3.11-slim

WORKDIR /app

# Optimización: Instalar dependencias del sistema primero
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Optimización: Capa de caché para pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . .

# Variable de entorno para Python path
ENV PYTHONPATH=/app
