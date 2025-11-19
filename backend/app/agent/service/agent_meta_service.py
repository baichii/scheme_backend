import zipfile
from collections.abc import Sequence
from io import BytesIO

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.crud.crud_agent_meta import agent_meta_dao
from backend.app.agent.model.agent_meta import AgentMeta
from backend.app.agent.schema.agent_meta import CreateAgentInternal, CreateAgentParam, DeleteAgentParam
from backend.common.exception import errors
from backend.utils.snowflake import snowflake
from backend.utils.upload import minio_uploader
from backend.common.log import log


class AgentMetaService:

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> AgentMeta:
        """获取智能体"""
        agent_meta = await agent_meta_dao.get(db, pk)
        if not agent_meta:
            raise errors.NotFoundError(msg="智能体不存在")
        return agent_meta

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[AgentMeta]:
        """获取所有智能体"""
        agent_metas = await agent_meta_dao.get_all(db)
        return agent_metas

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateAgentParam, file: UploadFile) -> AgentMeta:
        """创建智能体

        1. 文件校验，上传
        2. 结果写入数据库
        """
        # 1. 文件校验，上传
        if not file.filename or not file.filename.endswith(".zip"):
            raise errors.ZipError(msg="智能体文件必须为 zip 格式")

        contents = await file.read()
        filename = file.filename.rsplit(".", 1)[0]
        try:
            with zipfile.ZipFile(BytesIO(contents)) as zf:
                if zf.testzip():
                    raise errors.ZipError(msg="智能体文件压缩包损坏")
        except zipfile.BadZipFile:
            raise errors.ZipError(msg="智能体文件压缩包损坏")

        # 上传文件到 minio
        unique_id = snowflake.generate()
        file_load_name = f"{unique_id}_{filename}.zip"
        url = minio_uploader.upload_file(
            file_data=contents,
            object_name=file_load_name,
            content_type="application/zip",
        )
        # 2. 结果写入数据库
        agent = CreateAgentInternal(
            id=unique_id,
            name=obj.name,
            load=filename,
            side=obj.side,
            param_schema=obj.param_schema,
            description=obj.description,
            supported_env_templates=obj.supported_env_templates,
            url=url,
        )
        return await agent_meta_dao.create(db, agent)

    @staticmethod
    async def delete(*, db: AsyncSession, obj: DeleteAgentParam) -> int:
        """删除智能体"""
        # 获取删除智能体列表
        delete_agent_metas = []
        for pk in obj.pks:
            agent_meta = await agent_meta_dao.get(db, pk)
            if agent_meta:
                delete_agent_metas.append(agent_meta)

        # 删除数据库记录
        count = await agent_meta_dao.delete(db, obj.pks)

        # 删除minio文件
        if count > 0:
            for agent_meta in delete_agent_metas:
                try:
                    object_name = agent_meta.url.split("/")[-1]
                    minio_uploader.delete_file(object_name=object_name)
                except Exception as e:
                    log.info(f"删除minio文件{agent_meta}失败: {e}")

        return count


agent_meta_service: AgentMetaService = AgentMetaService()
