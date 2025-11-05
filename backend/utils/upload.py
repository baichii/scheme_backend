from io import BytesIO
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from backend.core.conf import settings


class MinIOUploader:
    """MinIO 文件上传工具类"""

    def __init__(self):
        """初始化 MinIO 客户端"""
        self.client = Minio(
            f"{settings.AGENT_MINIO_HOST}:{settings.AGENT_MINIO_PORT}",
            access_key=settings.AGENT_MINIO_USER,
            secret_key=settings.AGENT_MINIO_PASSWORD,
            secure=False  # 如果使用 HTTPS，设置为 True
        )
        self.bucket_name = settings.AGENT_BUCKET
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """确保 bucket 存在，不存在则创建"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise Exception(f"创建 bucket 失败: {str(e)}")

    def upload_file(
        self,
        object_name: str,
        file_data: bytes | BinaryIO,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        上传文件到 MinIO

        Args:
            object_name: 对象名称（文件路径）
            file_data: 文件数据（bytes 或文件对象）
            content_type: 文件类型

        Returns:
            str: 文件的下载路径

        Raises:
            Exception: 上传失败时抛出异常
        """
        try:
            # 如果是 bytes，转换为 BytesIO
            if isinstance(file_data, bytes):
                file_data = BytesIO(file_data)
                file_size = len(file_data.getvalue())
                file_data.seek(0)
            else:
                # 获取文件大小
                file_data.seek(0, 2)
                file_size = file_data.tell()
                file_data.seek(0)

            # 上传文件
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type
            )

            # 返回文件路径
            return f"{self.bucket_name}/{object_name}"

        except S3Error as e:
            raise Exception(f"文件上传失败: {str(e)}")

    def delete_file(self, object_name: str):
        """
        删除 MinIO 中的文件

        Args:
            object_name: 对象名称（文件路径）

        Raises:
            Exception: 删除失败时抛出异常
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
        except S3Error as e:
            raise Exception(f"文件删除失败: {str(e)}")

    def get_file_url(self, object_name: str) -> str:
        """
        获取文件的访问 URL

        Args:
            object_name: 对象名称（文件路径）

        Returns:
            str: 文件的访问 URL
        """
        return f"http://{settings.AGENT_MINIO_HOST}:{settings.AGENT_MINIO_PORT}/{self.bucket_name}/{object_name}"


# 单例模式
minio_uploader = MinIOUploader()
