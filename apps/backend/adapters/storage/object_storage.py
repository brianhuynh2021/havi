"""Object storage adapter — MinIO ở local, S3-compatible ở production.

Dùng **presigned POST** (không phải presigned PUT): chỉ POST cho phép đặt
condition `content-length-range`, nên giới hạn dung lượng được enforce ở tầng
storage. Với PUT thì client có thể gửi file bao nhiêu cũng được và API chỉ biết
sau khi đã tốn băng thông.

boto3 sync là đủ ở đây: `generate_presigned_post` chỉ ký HMAC local, không gọi
network nên không block event loop. Các hàm có I/O thật (`head_object`) được
đẩy qua thread pool.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from core.config import Settings


@dataclass
class UploadTicket:
    upload_url: str
    fields: dict[str, str] = field(default_factory=dict)
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class StoredObject:
    size_bytes: int
    content_type: str


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.media_endpoint_url,
            aws_access_key_id=settings.media_access_key,
            aws_secret_access_key=settings.media_secret_key,
            region_name=settings.media_region,
            # SigV4 + path-style: MinIO không hỗ trợ virtual-host style theo mặc định.
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def create_upload_ticket(self, *, object_key: str, content_type: str) -> UploadTicket:
        ttl = self._settings.media_upload_ttl_seconds
        response = self._client.generate_presigned_post(
            Bucket=self._settings.media_bucket,
            Key=object_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, self._settings.media_max_upload_bytes],
            ],
            ExpiresIn=ttl,
        )
        return UploadTicket(
            upload_url=response["url"],
            fields=response["fields"],
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
        )

    async def head_object(self, object_key: str) -> StoredObject | None:
        """None nếu object chưa tồn tại — dùng để xác nhận client upload xong thật."""

        def _head() -> StoredObject | None:
            try:
                response = self._client.head_object(
                    Bucket=self._settings.media_bucket, Key=object_key
                )
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                    return None
                raise
            return StoredObject(
                size_bytes=response["ContentLength"],
                content_type=response.get("ContentType", ""),
            )

        return await asyncio.to_thread(_head)

    async def read_prefix(self, object_key: str, *, num_bytes: int) -> bytes:
        """Đọc `num_bytes` đầu tiên — để kiểm magic bytes mà không tải cả file."""

        def _read() -> bytes:
            response = self._client.get_object(
                Bucket=self._settings.media_bucket,
                Key=object_key,
                Range=f"bytes=0-{num_bytes - 1}",
            )
            return response["Body"].read()

        return await asyncio.to_thread(_read)

    async def delete_object(self, object_key: str) -> None:
        def _delete() -> None:
            self._client.delete_object(Bucket=self._settings.media_bucket, Key=object_key)

        await asyncio.to_thread(_delete)

    def public_url(self, object_key: str) -> str:
        return f"{self._settings.media_public_url.rstrip('/')}/{object_key}"
