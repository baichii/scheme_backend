import json
from typing import Annotated

from fastapi import APIRouter, File, UploadFile, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.schema.agent_meta import AgentUploadRequest
from backend.app.agent.service.agent_service import agent_service
from backend.common.response.response_schema import ResponseModel, ResponseBase

router = APIRouter()

from backend.database import get_db


@router.post("/agent/upload", summary="智能体文件上传")
async def upload_agent(
    file: UploadFile = File(..., description="上传的 zip 文件"),
    metadata: str = Form(..., description="智能体元数据的 JSON 字符串"),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel:
    """
    接受上传的 zip 文件和元数据，解压并处理智能体文件

    Args:
        file: 上传的 zip 文件
        metadata: 包含智能体元数据的 JSON 字符串，格式:
            {
                "agent_name": "测试智能体1",
                "agent_desc": "这是一个测试的智能体",
                "side": "red",
                "params_schema": {...},
                "supported_env_templates": [1001, 1002],
                "agent_file": "智能体文件名"
            }
        db: 数据库会话

    Returns:
        ResponseModel: 包含上传结果的响应
    """
    # 验证文件格式
    if not file.filename or not file.filename.endswith(".zip"):
        return ResponseModel(
            code=400,
            msg="文件格式错误，仅支持 zip 文件",
            data=None
        )

    try:
        # 解析元数据
        metadata_dict = json.loads(metadata)
        agent_metadata = AgentUploadRequest(**metadata_dict)

        # 调用服务层处理上传
        result = await agent_service.upload(db, file, agent_metadata)

        return ResponseModel(
            code=200,
            msg="智能体上传成功",
            data=result
        )

    except json.JSONDecodeError:
        return ResponseModel(
            code=400,
            msg="元数据格式错误，无法解析 JSON",
            data=None
        )
    except ValueError as e:
        return ResponseModel(
            code=400,
            msg=str(e),
            data=None
        )
    except Exception as e:
        return ResponseModel(
            code=500,
            msg=f"上传失败: {str(e)}",
            data=None
        )


@router.get("/agent/{agent_id}", summary="获取智能体详情")
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel:
    """获取智能体详情"""
    try:
        agent = await agent_service.get(db, agent_id)
        if not agent:
            return ResponseModel(
                code=404,
                msg="智能体不存在",
                data=None
            )

        return ResponseModel(
            code=200,
            msg="获取成功",
            data={
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "agent_load": agent.agent_load,
                "agent_desc": agent.agent_desc,
                "agent_url": agent.agent_url,
                "side": agent.side,
                "param_schema": agent.param_schema,
                "supported_env_templates": agent.supported_env_templates,
                "create_at": agent.create_at.isoformat(),
                "update_at": agent.update_at.isoformat()
            }
        )
    except Exception as e:
        return ResponseModel(
            code=500,
            msg=f"获取失败: {str(e)}",
            data=None
        )


@router.get("/agents", summary="获取所有智能体")
async def list_agents(
    db: AsyncSession = Depends(get_db)
) -> ResponseModel:
    """获取所有智能体列表"""
    try:
        agents = await agent_service.list_all(db)

        data = [
            {
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "agent_load": agent.agent_load,
                "agent_desc": agent.agent_desc,
                "agent_url": agent.agent_url,
                "side": agent.side,
                "param_schema": agent.param_schema,
                "supported_env_templates": agent.supported_env_templates,
                "create_at": agent.create_at.isoformat(),
                "update_at": agent.update_at.isoformat()
            }
            for agent in agents
        ]

        return ResponseModel(
            code=200,
            msg="获取成功",
            data=data
        )
    except Exception as e:
        return ResponseModel(
            code=500,
            msg=f"获取失败: {str(e)}",
            data=None
        )


@router.delete("/agent/{agent_id}", summary="删除智能体")
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel:
    """删除智能体"""
    try:
        result = await agent_service.delete(db, agent_id)

        if not result:
            return ResponseModel(
                code=404,
                msg="智能体不存在",
                data=None
            )

        return ResponseModel(
            code=200,
            msg="删除成功",
            data=None
        )
    except Exception as e:
        return ResponseModel(
            code=500,
            msg=f"删除失败: {str(e)}",
            data=None
        )
