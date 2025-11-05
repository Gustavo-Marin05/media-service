# schema.py
import strawberry
from typing import List
from models import MediaFile

@strawberry.type
class MediaType:
    id: strawberry.ID
    filename: str
    fileUrl: str

@strawberry.type
class Query:
    @strawberry.field
    def all_media(self) -> List[MediaType]:
        files = MediaFile.query.all()
        return [MediaType(id=str(f.id), filename=f.filename, fileUrl=f.file_url) for f in files]

schema = strawberry.Schema(query=Query)