from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    object_storage_key: str
    filename: str
    mime_type: str
    size_bytes: int
    etag: str
    current_version_id: UUID | None
    is_private: bool
    created_at: datetime
    updated_at: datetime
