import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, MappedBase

agent_resource_id_sequence = sa.Sequence("agent_resource_id_seq", start=10000, metadata=MappedBase.metadata)


class Resource(Base):
    """统一资源聚合。"""

    __tablename__ = "resource"
    __table_args__ = (
        sa.UniqueConstraint("type", "normalized_name", name="uq_resource_type_normalized_name"),
        sa.CheckConstraint(
            "type IN ('scenario', 'strategy', 'agent', 'environment')",
            name="ck_resource_type",
        ),
        {"comment": "想定、策略、智能体和环境的统一资源聚合。"},
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, comment="资源 ID")
    type: Mapped[str] = mapped_column(sa.String(16), index=True, comment="资源类型")
    name: Mapped[str] = mapped_column(sa.String(80), comment="资源名称")
    normalized_name: Mapped[str] = mapped_column(sa.String(160), comment="规范化名称")
    description: Mapped[str | None] = mapped_column(sa.String(500), default=None, comment="资源描述")
    current_version_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, default=None, comment="当前版本 ID"
    )
    archived: Mapped[bool] = mapped_column(sa.Boolean, default=False, index=True, comment="是否归档")
    environment: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment="环境连接配置")


class ResourceVersion(Base):
    """不可变资源版本。"""

    __tablename__ = "resource_version"
    __table_args__ = (
        sa.UniqueConstraint("resource_id", "version", name="uq_resource_version_name"),
        sa.UniqueConstraint("resource_id", "revision_number", name="uq_resource_revision_number"),
        {"comment": "资源的不可变文件或配置版本。"},
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, comment="资源版本 ID")
    resource_id: Mapped[int] = mapped_column(
        sa.ForeignKey("resource.id", ondelete="CASCADE"), index=True, comment="资源 ID"
    )
    version: Mapped[str] = mapped_column(sa.String(32), comment="展示版本")
    format: Mapped[str] = mapped_column(sa.String(16), comment="文件格式")
    validation: Mapped[dict] = mapped_column(sa.JSON, comment="校验报告")
    revision_number: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment="平台修订号")
    package_version: Mapped[str | None] = mapped_column(sa.String(64), default=None, comment="包内程序版本")
    file_name: Mapped[str | None] = mapped_column(sa.String(255), default=None, comment="原文件名")
    size: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment="文件字节数")
    checksum: Mapped[str | None] = mapped_column(sa.String(64), default=None, index=True, comment="SHA-256")
    object_key: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment="对象存储键")
    parsed_data: Mapped[dict | list | None] = mapped_column(
        sa.JSON, default=None, comment="解析后的协议数据"
    )
