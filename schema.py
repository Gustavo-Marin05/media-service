# schema.py
import strawberry
from typing import List

@strawberry.type
class MediaType:
    id: strawberry.ID
    post_id: str
    filename: str
    file_url: str
    uploaded_at: str

@strawberry.type
class Query:
    @strawberry.field
    def all_media(self) -> List[MediaType]:
        # Importar aquí para evitar circular import
        from app import MediaFile
        
        files = MediaFile.query.all()
        return [
            MediaType(
                id=f.id,
                post_id=f.post_id,
                filename=f.filename,
                file_url=f.file_url,
                uploaded_at=f.uploaded_at.isoformat()
            ) for f in files
        ]

schema = strawberry.Schema(query=Query)