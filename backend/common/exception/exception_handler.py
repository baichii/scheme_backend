from fastapi import Request
from fastapi.responses import JSONResponse

from backend.common.exception.errors import BaseExceptionError


async def base_exception_handler(request: Request, exc: BaseExceptionError) -> JSONResponse:
    """将 service 业务异常映射为标准 HTTP 状态，不改变 V2 成功响应结构。"""
    return JSONResponse(
        status_code=exc.code,
        content={"detail": exc.msg},
        background=exc.background,
    )
