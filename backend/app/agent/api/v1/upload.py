from fastapi import APIRouter, File, UploadFile
import zipfile
import io

from backend.app.agent.schema.agent_meta import AgentMeta
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseModel, ResponseBase

router = APIRouter()

@router.post("/upload", summary="智能体文件上传")
async def upload_agent(file: UploadFile = File(...)) -> ResponseModel:
    """接受上传的zip文件，解压并处理智能体文件"""
    if not file.filename.endswith(".zip"):
        return r
    file_bytes = await file.read()
    zip_bytes = io.BytesIO(file_bytes)

    with zipfile.ZipFile(zip_bytes, "r") as zf:
        file_list = zf.namelist()
        result =