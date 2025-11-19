from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class AgentMeta(Base):
    __tablename__ = "agent_meta"

    id: Mapped[id_key] = mapped_column(init=False, comment="智能体ID")
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment="智能体名称")
    load: Mapped[str] = mapped_column(sa.String(128), unique=True, comment="智能体文件加载名称")
    side: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, comment="智能体默认阵营")
    param_schema: Mapped[dict] = mapped_column(sa.JSON, comment="智能体参数声明")
    description: Mapped[str] = mapped_column(sa.String(512), comment="智能体描述")
    supported_env_templates: Mapped[list[int]] = mapped_column(
        sa.ARRAY(sa.Integer), comment="支持的环境模板列表"
    )
    url: Mapped[str] = mapped_column(sa.String(128), comment="智能体下载路径")
