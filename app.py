from flask import Flask
import sqlite3
import os

app = Flask(__name__)

# --- Ruta donde se guardará la base de datos ---
DATABASE_DIR = "data"
DATABASE_PATH = os.path.join(DATABASE_DIR, "media.db")

# Crear carpeta si no existe
os.makedirs(DATABASE_DIR, exist_ok=True)

# --- Función para conectarse a la base de datos ---
def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print("❌ Error al conectar:", e)
        return None

# --- Health check ---
@app.route("/health")
def health_check():
    return {"status": "OK", "message": "Microservicio MEDIA funcionando 🚀"}

# --- Endpoint para probar conexión a la base de datos ---
@app.route("/test-db")
def test_db():
    conn = get_db_connection()
    if conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.close()
        return {"status": "OK", "message": "Conectado a la base de datos ✅"}
    else:
        return {"status": "ERROR", "message": "No se pudo conectar a la base de datos ❌"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
