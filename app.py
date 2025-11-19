# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from minio import Minio
from flasgger import Swagger
import json 
import os
import uuid
from datetime import datetime
from typing import List, Dict

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

# === SWAGGER CONFIG ===
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
        "version": "2.0.0",
        "description": "API para subir archivos multimedia con URLs públicas y soporte para posts"
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
    post_id = db.Column(db.String(50), nullable=False, unique=True)
    filename = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "filename": self.filename,
            "file_url": self.file_url,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None
        }

# === MINIO CLIENT ===
try:
    minio_client = Minio(
        Config.MINIO_ENDPOINT,
        access_key=Config.MINIO_ACCESS_KEY,
        secret_key=Config.MINIO_SECRET_KEY,
        secure=False
    )

    # Check/create bucket
    if not minio_client.bucket_exists(Config.MINIO_BUCKET):
        minio_client.make_bucket(Config.MINIO_BUCKET)
        print(f"Bucket creado: {Config.MINIO_BUCKET}")
    else:
        print(f"Bucket existe: {Config.MINIO_BUCKET}")
    
    # Set bucket policy to PUBLIC - This is the key change!
    try:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectVersion"
                    ],
                    "Resource": [f"arn:aws:s3:::{Config.MINIO_BUCKET}/*"]
                }
            ]
        }
        minio_client.set_bucket_policy(Config.MINIO_BUCKET, json.dumps(policy))
        print(f"Bucket policy set to PUBLIC for: {Config.MINIO_BUCKET}")
    except Exception as e:
        print(f"Warning: Could not set bucket policy: {e}")
        
except Exception as e:
    print(f"ERROR con MinIO: {e}")
    exit(1)

# === RUTAS ACTUALIZADAS ===

@app.route("/api/health", methods=["GET"])
def health():
    """Health check del servicio"""
    return jsonify({"status": "ok", "service": "media-service"}), 200

@app.route("/api/media/upload", methods=["POST"])
def upload_media_for_post():
    """Subir archivo multimedia para un post específico"""
    print("POST /api/media/upload recibido")
    
    # Validar post_id
    post_id = request.form.get('post_id')
    if not post_id:
        return jsonify({"error": "post_id is required"}), 400

    # Verificar si ya existe un archivo para este post_id
    existing_media = MediaFile.query.filter_by(post_id=post_id).first()
    if existing_media:
        return jsonify({"error": f"Media already exists for post_id: {post_id}"}), 409

    # Validar archivo
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    print(f"Subiendo archivo para post_id: {post_id}, archivo: {file.filename}")

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
        
        # Generate PUBLIC URL (no presigned, just the direct URL)
        file_url = f"{Config.MINIO_EXTERNAL_URL}/{Config.MINIO_BUCKET}/{unique_filename}"
        print(f"Subido a MinIO: {file_url}")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Error en MinIO: {e}")
        return jsonify({"error": f"MinIO upload failed: {str(e)}"}), 500

    # Guardar en DB
    try:
        media = MediaFile(
            post_id=post_id,
            filename=unique_filename,
            file_url=file_url
        )
        db.session.add(media)
        db.session.commit()
        print(f"Media guardado en DB: {media.id} para post_id: {post_id}")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Error en DB: {e}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    # Limpiar archivo temporal
    if os.path.exists(temp_path):
        os.remove(temp_path)

    return jsonify(media.to_dict()), 201

@app.route("/api/media/post/<post_id>", methods=["GET"])
def get_media_by_post_id(post_id):
    """Obtener información del media por post_id"""
    print(f"GET /api/media/post/{post_id}")
    
    media_file = MediaFile.query.filter_by(post_id=post_id).first()
    if not media_file:
        return jsonify({"error": "Media not found for this post_id"}), 404

    return jsonify(media_file.to_dict()), 200

@app.route("/api/media/batch", methods=["POST"])
def get_batch_media():
    """Obtener información de múltiples medias por post_ids"""
    print("POST /api/media/batch")
    
    data = request.get_json()
    if not data or 'post_ids' not in data:
        return jsonify({"error": "post_ids array is required"}), 400

    post_ids = data.get('post_ids', [])

    if not isinstance(post_ids, list):
        return jsonify({"error": "post_ids must be an array"}), 400

    print(f"Buscando {len(post_ids)} archivos")

    # Buscar todos los archivos en una sola consulta
    media_files = MediaFile.query.filter(MediaFile.post_id.in_(post_ids)).all()
    
    results = []
    for media in media_files:
        results.append(media.to_dict())

    # Identificar post_ids no encontrados
    found_post_ids = {media.post_id for media in media_files}
    not_found = [pid for pid in post_ids if pid not in found_post_ids]

    return jsonify({
        "found": results,
        "not_found": not_found,
        "total_requested": len(post_ids),
        "total_found": len(results)
    }), 200

@app.route("/api/media/post/<post_id>", methods=["DELETE"])
def delete_media_by_post_id(post_id):
    """Eliminar archivo multimedia por post_id"""
    print(f"DELETE /api/media/post/{post_id}")
    
    media_file = MediaFile.query.filter_by(post_id=post_id).first()
    if not media_file:
        return jsonify({"error": "Media not found for this post_id"}), 404

    try:
        # Eliminar de MinIO
        try:
            minio_client.remove_object(Config.MINIO_BUCKET, media_file.filename)
            print(f"Archivo eliminado de MinIO: {media_file.filename}")
        except Exception as e:
            print(f"Error eliminando de MinIO: {e}")

        # Eliminar de la base de datos
        db.session.delete(media_file)
        db.session.commit()
        print(f"Media eliminado de DB para post_id: {post_id}")

        return jsonify({"message": "File deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error eliminando archivo: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# Mantener endpoints legacy para compatibilidad
@app.route("/api/media", methods=["POST"])
def upload_file():
    """Subir archivo multimedia (endpoint legacy)"""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Generar un post_id automático para compatibilidad
    auto_post_id = str(uuid.uuid4())[:12]
    
    # Usar la nueva función de upload
    request.form = request.form.copy()
    request.form['post_id'] = auto_post_id
    
    return upload_media_for_post()

@app.route("/api/media/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    """Eliminar archivo multimedia por ID (endpoint legacy)"""
    media_file = MediaFile.query.get(file_id)
    if not media_file:
        return jsonify({"error": "File not found"}), 404

    try:
        minio_client.remove_object(Config.MINIO_BUCKET, media_file.filename)
        db.session.delete(media_file)
        db.session.commit()
        return jsonify({"message": "File deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
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
    print("MEDIA SERVICE v2.0 SIMPLIFICADO INICIANDO...")
    print("URLS PÚBLICAS - SIN PRESIGNED")
    print("ENDPOINTS:")
    print("  POST   /api/media/upload    - Subir archivo con post_id")
    print("  POST   /api/media/batch     - Obtener múltiples medias")
    print("  GET    /api/media/post/<id> - Obtener media por post_id")
    print("  DELETE /api/media/post/<id> - Eliminar media por post_id")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)