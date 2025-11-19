# models.py
from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class MediaFile(db.Model):
    __tablename__ = 'media_files'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = db.Column(db.String(50), nullable=False, unique=True)  # One-to-one with post
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