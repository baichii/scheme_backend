import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class EnvTemplate(Base):
    """环境配置模型"""

    __tablename__ = "env_template"

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment="环境配置模版名称")
    param_schema: Mapped[dict] = mapped_column(sa.JSON, comment="环境配置模版参数 schema")
