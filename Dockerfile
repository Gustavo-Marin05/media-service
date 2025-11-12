# Imagen base
FROM python:3.12-slim

# Directorio de trabajo en el contenedor
WORKDIR /app

# Copiar archivos necesarios
COPY app.py /app/
COPY requirements.txt /app/

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto del microservicio
EXPOSE 5001

# Comando para iniciar el servicio
CMD ["python", "app.py"]
