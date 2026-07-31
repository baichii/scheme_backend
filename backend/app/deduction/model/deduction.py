import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, snowflake_id_key


class Deduction(Base):
    """推演定义；运行状态与环境绑定不在此表持久化。"""

    __tablename__ = "deduction"
    __table_args__ = (
        sa.CheckConstraint("status IN ('draft', 'ready')", name="ck_deduction_status"),
        {"comment": "推演定义；运行状态与环境绑定不在此表持久化。"},
    )

    id: Mapped[snowflake_id_key] = mapped_column(init=False, comment="推演方案 ID")
    name: Mapped[str] = mapped_column(sa.String(80), comment="推演名称")
    normalized_name: Mapped[str] = mapped_column(
        sa.String(160), unique=True, index=True, comment="用于大小写不敏感唯一约束的名称"
    )
    scenario_type_key: Mapped[str] = mapped_column(sa.String(128), comment="想定类型标识")
    graph: Mapped[dict] = mapped_column(sa.JSON, comment="推演画布")
    description: Mapped[str] = mapped_column(sa.String(500), default="", comment="推演描述")
    status: Mapped[str] = mapped_column(sa.String(16), default="draft", comment="定义状态：draft/ready")
    created_by: Mapped[str] = mapped_column(sa.String(80), default="当前用户", comment="创建人")
