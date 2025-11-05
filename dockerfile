FROM python:3.11-slim

WORKDIR /app

# Instalar cliente de PostgreSQL (si lo necesitas) y otras dependencias
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Exponer puerto
EXPOSE 6000

# Ejecutar Flask directamente
CMD ["flask", "run", "--host=0.0.0.0", "--port=6000"]
