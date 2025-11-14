from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, snowflake_id_key
from backend.common.enums import TaskStatus


class TaskStatus(Base):
    """推演任务状态"""

    __tablename__ = "task_status"

    task_id: Mapped[snowflake_id_key] = mapped_column(comment="任务运行唯一ID")
    suffix: Mapped[int] = mapped_column(sa.Integer, comment="合成ID后缀")
    status: Mapped[TaskStatus] = mapped_column(sa.Enum(TaskStatus), comment="推演任务状态")
