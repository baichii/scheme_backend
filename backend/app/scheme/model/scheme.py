import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, snowflake_id_key


class Scheme(Base):
    """方案配置"""

    __tablename__ = "scheme"

    id: Mapped[snowflake_id_key] = mapped_column(sa.Integer, comment="方案ID")
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment="方案实例名称")
    description: Mapped[str] = mapped_column(sa.String(512), comment="方案实例描述")
    side: Mapped[str] = mapped_column(sa.String(64), comment="方案所属阵营")
    agent_schemes: Mapped[list] = mapped_column(sa.JSON, comment="方案实例参数")
