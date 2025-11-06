from typing import Any

from fastapi import HTTPException
from starlette.background import BackgroundTask


class BaseExceptionMixin(Exception):
    """基础异常混入类"""

    code: int

    def __init__(self, *, msg: str = None, data: Any = None, background: BackgroundTask | None = None):
        self.msg = msg
        self.data = data
        self.background = background


class HttpError(HTTPException):
    """http 异常"""
    def __init__(self, code:int , msg: Any = None, headers: dict[str, Any] | None = None):
        super().__init__(status_code=code, detail=msg, headers=headers)

    


