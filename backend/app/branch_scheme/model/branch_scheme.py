import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base


class BranchScheme(Base):
    """分支方案聚合与修订指针。"""

    __tablename__ = "branch_scheme"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, comment="分支方案 ID")
    normalized_name: Mapped[str] = mapped_column(
        sa.String(160), unique=True, index=True, comment="规范化名称"
    )
    head_revision_id: Mapped[int] = mapped_column(sa.BigInteger, comment="当前修订 ID")
    head_revision_number: Mapped[int] = mapped_column(sa.Integer, comment="当前修订号")
    created_by: Mapped[str] = mapped_column(sa.String(80), comment="创建人")
    published_revision_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, default=None, comment="已发布修订 ID"
    )
    published_revision_number: Mapped[int | None] = mapped_column(
        sa.Integer, default=None, comment="已发布修订号"
    )


class BranchSchemeRevision(Base):
    """不可变分支方案修订。"""

    __tablename__ = "branch_scheme_revision"
    __table_args__ = (
        sa.UniqueConstraint("branch_scheme_id", "revision_number", name="uq_branch_scheme_revision_number"),
        sa.CheckConstraint("status IN ('draft', 'configured')", name="ck_branch_scheme_revision_status"),
        {"comment": "分支方案不可变修订。"},
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, comment="修订 ID")
    branch_scheme_id: Mapped[int] = mapped_column(
        sa.ForeignKey("branch_scheme.id", ondelete="CASCADE"), index=True, comment="分支方案 ID"
    )
    revision_number: Mapped[int] = mapped_column(sa.Integer, comment="修订号")
    name: Mapped[str] = mapped_column(sa.String(80), comment="方案名称")
    description: Mapped[str] = mapped_column(sa.String(500), comment="方案描述")
    scenario_type_key: Mapped[str] = mapped_column(sa.String(128), comment="想定类型")
    side_key: Mapped[str] = mapped_column(sa.String(64), comment="阵营")
    status: Mapped[str] = mapped_column(sa.String(16), comment="draft/configured")
    graph: Mapped[dict] = mapped_column(sa.JSON, comment="分支流程图")
    created_by: Mapped[str] = mapped_column(sa.String(80), comment="创建人")
    parent_revision_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment="父修订 ID")
    origin: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment="AI 迭代来源")
