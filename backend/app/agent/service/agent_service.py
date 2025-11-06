import zipfile
from io import BytesIO

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.crud.crud_agent import crud_agent
from backend.app.agent.schema.agent_meta import AgentCreateRequest, AgentUploadRequest
from backend.utils.snowflake import snowflake
from backend.utils.upload import minio_uploader


class AgentService:

    @staticmethod
    async def upload(db: AsyncSession, file: UploadFile, metadata: AgentUploadRequest) -> dict:
        """
        智能体上传

        Args:
            db: 数据库会话
            file: 上传的 zip 文件
            metadata: 智能体元数据

        Returns:
            dict: 包含上传结果的字典

        """


        # 2. 读取文件内容
        file_bytes = await file.read()

        # 3. 验证是否为有效的 zip 文件
        try:
            zip_file = zipfile.ZipFile(BytesIO(file_bytes))
            file_list = zip_file.namelist()

            # 验证 agent_file 是否在 zip 中
            if metadata.agent_file not in file_list:
                raise ValueError(f"智能体文件 '{metadata.agent_file}' 不在上传的 zip 文件中")

        except zipfile.BadZipFile:
            raise ValueError("上传的文件不是有效的 zip 文件")

        # 4. 生成唯一的文件名和加载名
        unique_id = snowflake.generate()
        object_name = f"agents/{unique_id}_{metadata.agent_load}.zip"
        agent_load = metadata.agent_file.rsplit(".", 1)[0]  # 去除文件扩展名

        # 5. 上传文件到 MinIO
        try:
            agent_url = minio_uploader.upload_file(
                object_name=object_name,
                file_data=file_bytes,
                content_type="application/zip"
            )
        except Exception as e:
            raise Exception(f"文件上传到 MinIO 失败: {str(e)}")

        # 6. 创建数据库记录
        try:
            # 将 supported_env_templates 的 int 列表转换为 str 列表
            supported_env_templates = [str(t) for t in metadata.supported_env_templates]

            # 创建请求对象
            create_request = AgentCreateRequest(
                agent_name=metadata.agent_name,
                agent_load=agent_load,
                agent_desc=metadata.agent_desc,
                agent_url=agent_url,
                side=metadata.side or "unknown",  # 如果 side 为空，使用默认值
                param_schema=metadata.params_schema,
                supported_env_templates=supported_env_templates
            )

            agent = await crud_agent.create(db, create_request)

            return {
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "agent_url": agent.agent_url,
                "message": "智能体上传成功"
            }

        except Exception as e:
            # 如果数据库操作失败，删除已上传的文件
            try:
                minio_uploader.delete_file(object_name)
            except:
                pass
            raise Exception(f"数据库操作失败: {str(e)}")

    @staticmethod
    async def create(db: AsyncSession, agent_data: AgentCreateRequest):
        """创建智能体"""
        return await crud_agent.create(db, agent_data)

    @staticmethod
    async def delete(db: AsyncSession, agent_id: int) -> bool:
        """
        删除智能体

        Args:
            db: 数据库会话
            agent_id: 智能体 ID

        Returns:
            bool: 删除是否成功
        """
        # 先获取智能体信息，以便删除 MinIO 中的文件
        agent = await crud_agent.get(db, agent_id)
        if not agent:
            return False

        # 从 agent_url 中提取 object_name
        # agent_url 格式: "agent/agents/xxx.zip"
        object_name = agent.agent_url.replace(f"{minio_uploader.bucket_name}/", "")

        # 删除数据库记录
        deleted = await crud_agent.delete(db, agent_id)

        # 如果数据库删除成功，删除 MinIO 中的文件
        if deleted:
            try:
                minio_uploader.delete_file(object_name)
            except Exception as e:
                # 即使 MinIO 删除失败，也返回成功（因为数据库已删除）
                print(f"MinIO 文件删除失败: {str(e)}")

        return deleted

    @staticmethod
    async def get(db: AsyncSession, agent_id: int):
        """获取智能体详情"""
        return await crud_agent.get(db, agent_id)

    @staticmethod
    async def list_all(db: AsyncSession):
        """获取所有智能体"""
        return await crud_agent.list_all(db)


# 单例模式
agent_service = AgentService()
