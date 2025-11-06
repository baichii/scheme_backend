from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.common.model import Base, id_key, snowflake_id_key


class Agent(Base):

    __tablename__ = "agent"

    agent_id: Mapped[snowflake_id_key] = mapped_column(init=False)
    agent_name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment="智能体名称")
    agent_load: Mapped[str] = mapped_column(sa.String(64), unique=True, comment="智能体文件加载名称")
    agent_desc: Mapped[str] = mapped_column(sa.String(512), comment="智能体描述")
    agent_url: Mapped[str] = mapped_column(sa.String(64), comment="智能体下载路径")
    side: Mapped[str] = mapped_column(sa.String(64), comment="智能体默认阵营")
    param_schema: Mapped[dict] = mapped_column(sa.JSON, comment="智能体参数声明")
    supported_env_templates: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.String(64)), comment="支持的环境模板列表")
    create_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.now, comment="创建时间")
    update_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
