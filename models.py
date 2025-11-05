# models.py
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# NO IMPORTES db DESDE app.py AQUÍ

class MediaFile:
    """Modelo temporal hasta que db esté listo"""
    pass

# db se asignará más tarde
db = None

def init_db(actual_db):
    global db
    db = actual_db

    class MediaFileActual(db.Model):
        id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        post_id = db.Column(db.String(50), nullable=False)
        filename = db.Column(db.String(255), nullable=False)
        file_url = db.Column(db.String(500), nullable=False)
        uploaded_by = db.Column(db.String(100), nullable=False)
        uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

        def to_dict(self):
            return {
                "id": str(self.id),
                "post_id": self.post_id,
                "filename": self.filename,
                "file_url": self.file_url,
                "uploaded_by": str(self.uploaded_by),
                "uploaded_at": self.uploaded_at.isoformat()
            }

    # Reasigna la clase
    globals()['MediaFile'] = MediaFileActual