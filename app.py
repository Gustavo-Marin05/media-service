# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from minio import Minio
from flasgger import Swagger  # ← CORRECTO
import json 
import os
import uuid
from datetime import datetime

# === FLASK APP ===
app = Flask(__name__)
app.config.from_object(Config)

# === CORS ===
CORS(app, resources={r"/*": {"origins": "*"}})

# === VALIDACIÓN DE CONFIG ===
try:
    Config.validate()
except Exception as e:
    print(f"ERROR DE CONFIGURACIÓN: {e}")
    exit(1)

# === SWAGGER CONFIG (CORREGIDO) ===
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

template = {
    "info": {
        "title": "Media Service API",
        "version": "1.0.0",
        "description": "API para subir archivos multimedia. Usa MinIO para almacenamiento y PostgreSQL para metadatos."
    },
    "host": "localhost:5000",
    "basePath": "/",
    "schemes": ["http"]
}

swagger = Swagger(app, config=swagger_config, template=template)

# === DATABASE ===
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# === MODELO ===
class MediaFile(db.Model):
    __tablename__ = 'media_files'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = db.Column(db.String(50), nullable=False, default=lambda: str(uuid.uuid4())[:12])
    filename = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "filename": self.filename,
            "file_url": self.file_url,
            "uploaded_at": self.uploaded_at.isoformat()
        }

# === MINIO CLIENT ===
minio_client = Minio(
    Config.MINIO_ENDPOINT,
    access_key=Config.MINIO_ACCESS_KEY,
    secret_key=Config.MINIO_SECRET_KEY,
    secure=False
)

try:
    if not minio_client.bucket_exists(Config.MINIO_BUCKET):
        minio_client.make_bucket(Config.MINIO_BUCKET)
        print(f"Bucket creado: {Config.MINIO_BUCKET}")
    else:
        print(f"Bucket existe: {Config.MINIO_BUCKET}")
    
    # ADD THIS: Set bucket policy to public
    try:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{Config.MINIO_BUCKET}/*"]
                }
            ]
        }
        minio_client.set_bucket_policy(Config.MINIO_BUCKET, json.dumps(policy))
        print(f"Bucket policy set to public for: {Config.MINIO_BUCKET}")
    except Exception as e:
        print(f"Warning: Could not set bucket policy: {e}")
        
except Exception as e:
    print(f"ERROR con MinIO: {e}")
    exit(1)

# === RUTAS CON DOCUMENTACIÓN CORRECTA (OpenAPI 3) ===

@app.route("/api/health", methods=["GET"])
def health():
    """Health check del servicio
    ---
    responses:
      200:
        description: Servicio saludable
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                service:
                  type: string
                  example: media-service
            examples:
              default:
                status: ok
                service: media-service
    """
    print("Health check OK")
    return jsonify({"status": "ok", "service": "media-service"}), 200


@app.route("/api/media", methods=["POST"])
def upload_file():
    """Subir archivo multimedia
    ---
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: Archivo a subir (imagen, video, etc.)
    responses:
      201:
        description: Archivo subido exitosamente
        content:
          application/json:
            schema:
              type: object
              properties:
                id:
                  type: string
                  description: ID único del archivo
                post_id:
                  type: string
                  description: ID corto para relacionar con posts
                filename:
                  type: string
                  description: Nombre único en MinIO
                file_url:
                  type: string
                  description: URL pública del archivo
                uploaded_at:
                  type: string
                  format: date-time
                  description: Fecha de subida (UTC)
              required:
                - id
                - post_id
                - filename
                - file_url
                - uploaded_at
            example:
              id: "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8"
              post_id: "abc123def456"
              filename: "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8.jpg"
              file_url: "http://localhost:9000/micro-medios/a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8.jpg"
              uploaded_at: "2025-04-05T10:00:00"
      400:
        description: No se envió archivo
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: No file part
      500:
        description: Error interno del servidor
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
    """
    print("POST /media recibido")
    
    if "file" not in request.files:
        print("No file part en request")
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == '':
        print("Filename vacío")
        return jsonify({"error": "No selected file"}), 400

    print(f"Archivo recibido: {file.filename}")

    # Generar nombre único
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'bin'
    unique_filename = f"{uuid.uuid4()}.{ext}"
    temp_path = f"/tmp/{unique_filename}"
    
    try:
        file.save(temp_path)
        print(f"Guardado temporalmente: {temp_path}")
    except Exception as e:
        print(f"Error guardando archivo: {e}")
        return jsonify({"error": f"Error saving file: {str(e)}"}), 500

    # Subir a MinIO
    try:
        minio_client.fput_object(Config.MINIO_BUCKET, unique_filename, temp_path)
        file_url = f"{Config.MINIO_EXTERNAL_URL}/{Config.MINIO_BUCKET}/{unique_filename}"
        print(f"Subido a MinIO: {file_url}")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Error en MinIO: {e}")
        return jsonify({"error": f"MinIO upload failed: {str(e)}"}), 500

    # Guardar en DB
    try:
        media = MediaFile(filename=unique_filename, file_url=file_url)
        db.session.add(media)
        db.session.commit()
        print(f"Media guardado en DB: {media.id}")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Error en DB: {e}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    # Limpiar archivo temporal
    if os.path.exists(temp_path):
        os.remove(temp_path)

    return jsonify(media.to_dict()), 201

    
@app.route("/api/media/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    """Eliminar archivo multimedia
    ---
    parameters:
      - name: file_id
        in: path
        type: string
        required: true
        description: ID del archivo a eliminar
    responses:
      200:
        description: Archivo eliminado exitosamente
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: File deleted successfully
      404:
        description: Archivo no encontrado
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: File not found
      500:
        description: Error interno del servidor
    """
    print(f"DELETE /media/{file_id} recibido")
    
    try:
        # Find the file in database
        media_file = MediaFile.query.get(file_id)
        if not media_file:
            return jsonify({"error": "File not found"}), 404

        # Delete from MinIO
        try:
            minio_client.remove_object(Config.MINIO_BUCKET, media_file.filename)
            print(f"Archivo eliminado de MinIO: {media_file.filename}")
        except Exception as e:
            print(f"Error eliminando de MinIO: {e}")
            # Continue with DB deletion even if MinIO fails

        # Delete from database
        db.session.delete(media_file)
        db.session.commit()
        print(f"Media eliminado de DB: {file_id}")

        return jsonify({"message": "File deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error eliminando archivo: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# === CREAR TABLAS ===
with app.app_context():
    try:
        db.create_all()
        print("Tablas creadas/verificadas")
    except Exception as e:
        print(f"Error creando tablas: {e}")


# === GRAPHQL ===
def setup_graphql():
    from strawberry.flask.views import GraphQLView
    from schema import schema
    
    app.add_url_rule(
        "/graphql", 
        view_func=GraphQLView.as_view("graphql_view", schema=schema, graphiql=True)
    )

setup_graphql()


# === INICIO ===
if __name__ == "__main__":
    print("=" * 60)
    print("MEDIA SERVICE INICIANDO...")
    print(f"Swagger UI: http://localhost:5000/docs")
    print(f"GraphQL:     http://localhost:5000/graphql")
    print(f"Health:      http://localhost:5000/health")
    print(f"MinIO:       {Config.MINIO_ENDPOINT}")
    print(f"DB:          {Config.SQLALCHEMY_DATABASE_URI}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)