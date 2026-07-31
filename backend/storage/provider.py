from functools import lru_cache

from backend.core.conf import settings
from backend.storage.client import ObjectStorageClient
from backend.storage.minio import MinioObjectStorage


@lru_cache
def get_object_storage() -> ObjectStorageClient:
    return MinioObjectStorage(
        settings.MINIO_ENDPOINT,
        settings.MINIO_ROOT_USER,
        settings.MINIO_ROOT_PASSWORD,
        settings.RESOURCE_BUCKET,
    )
