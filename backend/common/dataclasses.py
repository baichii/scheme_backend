import dataclasses

from datetime import datetime

from fastapi import Response

@dataclasses.dataclass
class UploadUrl:
    url: str


@dataclasses.dataclass
class SnowflakeInfo:
    timestamp: int
    datetime: str
    cluster_id: int
    node_id: int
    sequence: int
