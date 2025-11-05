"""数据库配置模块"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from backend.core.conf import settings

# 数据库 URL - 需要根据实际情况配置
# 示例: postgresql+asyncpg://user:password@localhost/dbname
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/scheme_db"

# 创建异步引擎
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # 开发环境打印 SQL
    poolclass=NullPool,  # 使用 NullPool 避免连接池问题
)

# 创建会话工厂
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with async_session_factory() as session:
        yield session


async def init_db():
    """初始化数据库表"""
    from backend.common.model import Base
    from backend.app.agent.model.agent import Agent  # 导入所有模型

    async with async_engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("数据库表创建成功")


async def drop_db():
    """删除所有数据库表（慎用）"""
    from backend.common.model import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("数据库表已删除")
