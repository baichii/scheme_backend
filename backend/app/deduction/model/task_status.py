import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, snowflake_id_key
from backend.common.enums import TaskStatus as DeductionTaskStatus


class TaskStatus(Base):
    """推演任务状态"""

    __tablename__ = "task_status"

    id: Mapped[snowflake_id_key] = mapped_column(sa.Integer, comment="任务运行ID")

    suffix: Mapped[int] = mapped_column(sa.Integer, comment="合成ID后缀")
    deduce_id: Mapped[int] = mapped_column(sa.Integer, comment="推演ID")
    status: Mapped[DeductionTaskStatus] = mapped_column(sa.Enum(DeductionTaskStatus), comment="推演状态")
