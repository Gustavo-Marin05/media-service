# schema.py
import strawberry
from typing import List, Optional

@strawberry.type
class MediaType:
    id: strawberry.ID
    post_id: str
    filename: str
    file_url: str
    uploaded_at: str
    presigned_url: Optional[str]

@strawberry.input
class BatchPresignedInput:
    post_ids: List[str]
    expiry_hours: Optional[int] = 1

@strawberry.type
class BatchPresignedResult:
    post_id: str
    presigned_url: Optional[str]
    filename: str
    media_id: str

@strawberry.type
class BatchPresignedResponse:
    found: List[BatchPresignedResult]
    not_found: List[str]
    total_requested: int
    total_found: int

@strawberry.type
class Query:
    @strawberry.field
    def all_media(self) -> List[MediaType]:
        from app import MediaFile, generate_presigned_url
        
        files = MediaFile.query.all()
        result = []
        for f in files:
            presigned_url = generate_presigned_url(f.filename)
            result.append(
                MediaType(
                    id=f.id,
                    post_id=f.post_id,
                    filename=f.filename,
                    file_url=f.file_url,
                    uploaded_at=f.uploaded_at.isoformat(),
                    presigned_url=presigned_url
                )
            )
        return result

    @strawberry.field
    def media_by_post_id(self, post_id: str) -> Optional[MediaType]:
        from app import MediaFile, generate_presigned_url
        
        media = MediaFile.query.filter_by(post_id=post_id).first()
        if media:
            presigned_url = generate_presigned_url(media.filename)
            return MediaType(
                id=media.id,
                post_id=media.post_id,
                filename=media.filename,
                file_url=media.file_url,
                uploaded_at=media.uploaded_at.isoformat(),
                presigned_url=presigned_url
            )
        return None

@strawberry.type
class Mutation:
    @strawberry.mutation
    def generate_batch_presigned_urls(self, input: BatchPresignedInput) -> BatchPresignedResponse:
        from app import MediaFile, generate_presigned_url, db
        
        media_files = MediaFile.query.filter(MediaFile.post_id.in_(input.post_ids)).all()
        
        found_results = []
        for media in media_files:
            presigned_url = generate_presigned_url(media.filename, input.expiry_hours)
            found_results.append(
                BatchPresignedResult(
                    post_id=media.post_id,
                    presigned_url=presigned_url,
                    filename=media.filename,
                    media_id=media.id
                )
            )
        
        found_post_ids = {media.post_id for media in media_files}
        not_found = [pid for pid in input.post_ids if pid not in found_post_ids]
        
        return BatchPresignedResponse(
            found=found_results,
            not_found=not_found,
            total_requested=len(input.post_ids),
            total_found=len(found_results)
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)