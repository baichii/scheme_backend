import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, snowflake_id_key


class EnvTemplate(Base):
    """环境配置模版"""

    __tablename__ = "env_template"

    id: Mapped[int] = mapped_column(snowflake_id_key, primary_key=True, comment="环境配置模版 ID")
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment="环境配置模版名称")
    param_schema: Mapped[dict] = mapped_column(sa.JSON, comment="环境配置模版参数 schema")
