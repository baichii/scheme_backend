import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class EnvInstance(Base):
    """环境配置实例"""

    __tablename__ = "env_instance"

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment="环境配置实例名称")
    template_id: Mapped[int] = mapped_column(comment="环境配置模版 ID")
    params: Mapped[dict] = mapped_column(sa.JSON, comment="环境配置实例参数")
