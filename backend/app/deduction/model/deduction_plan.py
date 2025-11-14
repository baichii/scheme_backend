from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, snowflake_id_key

from backend.common.enums import DeductionPlanStatus


class DeductionPlan(Base):
    """推演方案配置模型"""

    __tablename__ = "deduction_plan"

    id: Mapped[snowflake_id_key] = mapped_column(comment="推演方案ID")
    scheme_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("scheme.id"), comment="关联方案ID")
    env_instance_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("env_instance.id"), comment="关联环境实例ID")

    name: Mapped[str] = mapped_column(sa.String(128), unique=True, comment="推理计划名称")
    description: Mapped[str | None] = mapped_column(sa.String(512), nullable=True, comment="推理计划描述")
    status: Mapped[int] = mapped_column(sa.Integer, comment="推理方案状态")

    scheme_snapshot: Mapped[dict] = mapped_column(sa.JSON, comment="方案快照数据")
    start_time: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True, comment="推演开始时间")
    end_time: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True, comment="推演结束时间")

    # 智能体统计
    agent_num : Mapped[int] = mapped_column(sa.Integer, default=0, comment="总智能体数量")
    # agent_ids: Mapped[]
