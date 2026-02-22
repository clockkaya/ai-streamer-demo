"""
app.schemas.api_response
~~~~~~~~~~~~~~~~~~~~

全局统一应答体，所有 API 接口复用此结构返回一致的 JSON 格式。

独立于 ``core/`` 包，遵循 FastAPI 社区惯例：
schemas/ 存放请求/响应的 Pydantic 模型（类似 Java 中的 DTO 层）。
"""
from __future__ import annotations
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """统一 JSON 应答体。

    所有业务接口均通过此模型包装返回值，保证客户端收到的结构一致:

    .. code-block:: json

        {"code": 200, "data": {...}, "msg": "success"}

    Attributes:
        code: 业务状态码，200 表示成功。
        data: 实际业务数据。
        msg: 人类可读的状态消息。
    """

    code: int = Field(default=200, description="业务状态码")
    data: T = Field(..., description="业务数据")
    msg: str = Field(default="success", description="状态消息")

    @classmethod
    def ok(cls, data: T, msg: str = "success") -> ApiResponse[T]:
        """快捷构造成功响应。"""
        return cls(code=200, data=data, msg=msg)

    @classmethod
    def fail(cls, msg: str = "error", code: int = 500, data: Any = None) -> ApiResponse[Any]:
        """快捷构造失败响应。"""
        return cls(code=code, data=data, msg=msg)
