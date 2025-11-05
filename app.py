from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from minio import Minio
import os
import uuid
import pika
import json
from strawberry.flask.views import GraphQLView

app = Flask(__name__)
app.config.from_object(Config)

# === Validación ===
try:
    Config.validate()
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)

# === Base de datos ===
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class MediaFile(db.Model):
    __tablename__ = 'media_files'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    uploaded_by = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "filename": self.filename,
            "file_url": self.file_url,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at.isoformat()
        }

# === MINIO ===
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
except Exception as e:
    print(f"Error con MinIO: {e}")
    exit(1)

# === RabbitMQ ===
def publish_media_event(event_type: str, data: dict):
    try:
        connection = pika.BlockingConnection(pika.URLParameters(Config.RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue='media.events', durable=True)
        message = json.dumps({"event": event_type, "data": data})
        channel.basic_publish(
            exchange='',
            routing_key='media.events',
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
    except Exception as e:
        print(f"Error RabbitMQ: {e}")

# === RUTAS ===
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/media", methods=["POST"])
def upload_file():
    username = request.headers.get('X-User')
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    post_id = request.form.get("post_id")
    if not post_id:
        return jsonify({"error": "post_id required"}), 400

    ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else ''
    unique_filename = f"{uuid.uuid4()}.{ext}"
    temp_path = f"/tmp/{unique_filename}"
    file.save(temp_path)

    try:
        minio_client.fput_object(Config.MINIO_BUCKET, unique_filename, temp_path)
        file_url = f"http://{Config.MINIO_ENDPOINT}/{Config.MINIO_BUCKET}/{unique_filename}"
    except Exception as e:
        os.remove(temp_path)
        return jsonify({"error": "MinIO upload failed"}), 500

    media = MediaFile(
        post_id=post_id,
        filename=unique_filename,
        file_url=file_url,
        uploaded_by=username
    )
    db.session.add(media)
    db.session.commit()

    publish_media_event("media.uploaded", media.to_dict())
    os.remove(temp_path)
    return jsonify(media.to_dict()), 201

@app.route("/media", methods=["GET"])
def list_files():
    username = request.headers.get('X-User')
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    media_files = MediaFile.query.filter_by(uploaded_by=username).all()
    return jsonify({
        "user": username,
        "media": [m.to_dict() for m in media_files]
    })

# === GraphQL ===
from schema import schema
app.add_url_rule("/graphql", view_func=GraphQLView.as_view("graphql_view", schema=schema, graphiql=True))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000, debug=True)
