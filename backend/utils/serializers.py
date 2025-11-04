from typing import Any

from msgspec import json
from starlette.responses import JSONResponse


class MsgSpecJsonResponse(JSONResponse):
    """使用 MsgSpec 进行 JSON 序列化的响应类"""

    def render(self, content: Any) -> bytes:
        return json.encode(content)