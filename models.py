# models.py (OPCIONAL - solo si quieres separar los modelos)
# Si usas este archivo, importa db desde app en lugar de definirlo aquí

from datetime import datetime
import uuid

# Este archivo es OPCIONAL
# Los modelos ya están en app.py y funcionan bien ahí
# Solo úsalo si quieres una estructura más modular

def create_models(db):
    """
    Factory para crear modelos con una instancia de db
    Uso en app.py:
        from models import create_models
        MediaFile = create_models(db)
    """
    
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
    
    return MediaFile