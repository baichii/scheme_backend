from enum import Enum
from typing import Protocol, runtime_checkable

from backend.engine.schemas import (
    EngineCreateRequest,
    EngineEventRecord,
    EngineQueryRequest,
    EngineResponse,
    EngineStopRequest,
    EngineTaskState,
)


class EngineClientMode(str, Enum):
    FAKE = "fake"
    MATRIX = "matrix"


@runtime_checkable
class EngineClient(Protocol):
    mode: EngineClientMode

    async def create(self, request: EngineCreateRequest) -> EngineResponse[str]: ...

    async def query(
        self,
        request: EngineQueryRequest,
    ) -> EngineResponse[dict[str, EngineTaskState]]: ...

    async def stop(self, request: EngineStopRequest) -> EngineResponse[dict]: ...

    async def get_events(
        self,
        *,
        after_sequence: int = 0,
        task_ids: set[str] | None = None,
    ) -> list[EngineEventRecord]: ...

    async def aclose(self) -> None: ...
