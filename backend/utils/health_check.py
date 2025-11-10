from math import ceil

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute

from backend.common.exception import errors


def ensure_unique_route_names(app: FastAPI):
    """
    检查路由名称唯一
    """
    temp_routes = set()
    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.name in temp_routes:
                raise ValueError(f"路由名称 {route.name} 重复")
            temp_routes.add(route.name)


async def http_limit_callback(request: Request, response: Response, expire: int):
    """
    HTTP 限流回调
    """
    expires = ceil(expire / 1000)
    raise errors.HTTPError(code=429, msg="请求频率过快，请稍后重试", headers={"Retry-After": str(expires)})
