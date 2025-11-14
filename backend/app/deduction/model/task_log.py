import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enums import TaskLogType as MessageType, TaskLogLevel as MessageLevel
from backend.common.model import Base, snowflake_id_key


class TaskLog(Base):
    """推演任务执行日志"""

    __tablename__ = "task_log"

    id: Mapped[int] = mapped_column(comment="日志记录ID")
    task_id: Mapped[snowflake_id_key] = mapped_column(sa.Integer, comment="任务运行唯一ID")
    suffix: Mapped[int] = mapped_column(sa.Integer, comment="合成ID后缀")
    content: Mapped[str] = mapped_column(sa.String(512), comment="任务执行日志")
    type: Mapped[MessageType] = mapped_column(sa.Enum(MessageType), comment="消息类型")
    level: Mapped[MessageLevel] = mapped_column(sa.Enum(MessageLevel), comment="消息等级")

