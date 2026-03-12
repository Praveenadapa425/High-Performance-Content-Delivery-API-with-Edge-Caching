from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

settings = get_settings()


class ObjectStorage:
    def __init__(self) -> None:
        self.client = Minio(
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
        )
        self.bucket = settings.s3_bucket

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_bytes(self, key: str, data: bytes, mime_type: str) -> None:
        try:
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=key,
                data=BytesIO(data),
                length=len(data),
                content_type=mime_type,
            )
        except S3Error as exc:
            raise RuntimeError(f"Object storage upload failed: {exc}") from exc
