import asyncio
from io import BytesIO

from minio import Minio


class MinioObjectStorage:
    """Lazy MinIO adapter; construction performs no network I/O."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        self.bucket = bucket
        self._ready = False
        self._lock = asyncio.Lock()

    async def _ensure_bucket(self) -> None:
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            exists = await asyncio.to_thread(self.client.bucket_exists, self.bucket)
            if not exists:
                await asyncio.to_thread(self.client.make_bucket, self.bucket)
            self._ready = True

    async def put(self, object_name: str, data: bytes, content_type: str) -> None:
        await self._ensure_bucket()
        await asyncio.to_thread(
            self.client.put_object,
            self.bucket,
            object_name,
            BytesIO(data),
            len(data),
            content_type=content_type,
        )

    async def get(self, object_name: str) -> bytes:
        await self._ensure_bucket()
        response = await asyncio.to_thread(self.client.get_object, self.bucket, object_name)
        try:
            return await asyncio.to_thread(response.read)
        finally:
            response.close()
            response.release_conn()

    async def delete(self, object_name: str) -> None:
        await self._ensure_bucket()
        await asyncio.to_thread(self.client.remove_object, self.bucket, object_name)
