from typing import Any, TypeVar

from pydantic import BaseModel, Field

from backend.common.response.response_code import CustomResponse, CustomResponseCode

SchemaT = TypeVar("SchemaT")


class ResponseModel(BaseModel):
    """
    不包含返回数据的响应模型

    Examples
    --------
        @router.get("/test", response_model=ResponseSchema)
        def test():
            return ResponseModel(data={"test': "test"})

    """

    code: int = Field(CustomResponseCode.HTTP_200.code, description="返回状态码")
    msg: str = Field(CustomResponseCode.HTTP_200.msg, description="返回消息")
    data: Any | None = Field(None, description="返回数据")


class ResponseSchemaModel(ResponseModel):
    data: SchemaT


class ResponseBase:
    """统一返回方法"""

    @staticmethod
    def __response(
        *, res: CustomResponseCode | CustomResponse = None, data: Any | None = None
    ) -> ResponseModel | ResponseSchemaModel:
        """统一返回方法"""
        return ResponseModel(code=res.code, msg=res.msg, data=data)

    def success(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        data: Any | None = None,
    ) -> ResponseModel | ResponseSchemaModel:
        """成功响应"""
        return self.__response(res=res, data=data)

    def fail(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_400,
        data: Any | None = None,
    ) -> ResponseModel | ResponseSchemaModel:
        """失败响应"""
        return self.__response(res=res, data=data)


response_base: ResponseBase = ResponseBase()
