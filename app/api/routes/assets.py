import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.models import Asset
from app.db.session import get_db
from app.schemas.assets import AssetResponse
from app.services.hashing import sha256_etag
from app.services.storage import ObjectStorage

router = APIRouter(prefix="/assets", tags=["assets"])
storage = ObjectStorage()


@router.post("/upload", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: UploadFile = File(...),
    is_private: bool = Form(default=False),
    db: Session = Depends(get_db),
) -> Asset:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    etag = sha256_etag(content)
    asset_id = uuid.uuid4()
    extension = file.filename.rsplit(".", maxsplit=1)[-1] if "." in file.filename else "bin"
    key = f"assets/{asset_id}/current/content.{extension}"

    storage.ensure_bucket()
    storage.put_bytes(key=key, data=content, mime_type=file.content_type or "application/octet-stream")

    asset = Asset(
        id=asset_id,
        object_storage_key=key,
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        etag=etag,
        is_private=is_private,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
