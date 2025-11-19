from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, snowflake_id_key


class DeductionPlan(Base):
    """推演方案配置模型"""

    __tablename__ = "deduction_plan"

    id: Mapped[snowflake_id_key] = mapped_column(comment="推演方案ID")

    name: Mapped[str] = mapped_column(sa.String(128), unique=True, comment="推理方案名称")
    description: Mapped[str | None] = mapped_column(sa.String(512), nullable=True, comment="推理方案描述")
    status: Mapped[str] = mapped_column(sa.String(32), comment="推理方案状态")
    task_config: Mapped[list[dict]] = mapped_column(sa.JSON, comment="推演方案参数")
    env_instance_id: Mapped[int | None] = mapped_column(comment="环境实例ID")
    start_time: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="推演开始时间"
    )
