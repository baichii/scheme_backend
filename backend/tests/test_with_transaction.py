"""
基于数据库事务的测试 - 测试后自动回滚，不留痕迹
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.db import async_engine, get_db
from backend.core.conf import settings


# ==================== 数据库事务 Fixtures ====================

@pytest.fixture(scope="session")
def db_engine():
    """创建测试数据库引擎"""
    # 可以使用单独的测试数据库
    # test_db_url = settings.DB_URL.replace("/scheme", "/scheme_test")
    # engine = create_engine(test_db_url)

    # 或者使用同一个数据库（通过事务回滚隔离）
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(settings.DB_URL, echo=False)
    return engine


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """
    为每个测试创建独立的数据库会话
    测试完成后自动回滚所有更改
    """
    async with db_engine.connect() as connection:
        # 开始事务
        async with connection.begin() as transaction:
            # 创建会话
            async_session = sessionmaker(
                connection, class_=Session, expire_on_commit=False
            )
            session = async_session()

            yield session  # 测试运行

            # 测试完成后回滚事务
            await transaction.rollback()


@pytest.fixture(scope="function")
async def override_get_db(db_session):
    """
    覆盖 FastAPI 的数据库依赖
    使测试使用事务会话
    """
    async def _get_db_override():
        yield db_session

    from backend.main import app
    app.dependency_overrides[get_db] = _get_db_override

    yield

    # 清理
    app.dependency_overrides.clear()


# ==================== 使用示例 ====================

class TestWithTransaction:
    """使用事务回滚的测试"""

    async def test_create_and_rollback(self, db_session, override_get_db):
        """
        测试创建数据，测试后会自动回滚
        数据库不会留下任何痕迹
        """
        from backend.app.env.model.env_template import EnvTemplate

        # 创建测试数据
        template = EnvTemplate(
            name="测试模版-会被回滚",
            param_schema=[{"name": "test", "type": "str"}]
        )
        db_session.add(template)
        await db_session.commit()

        # 验证数据已创建
        result = await db_session.execute(
            "SELECT * FROM env_template WHERE name = '测试模版-会被回滚'"
        )
        assert result.rowcount == 1

        # 测试结束后，事务会自动回滚
        # 数据库中不会留下这条记录


# ==================== 说明 ====================
"""
这种方式的优点：
1. 数据库完全干净，测试后不留任何痕迹
2. 测试之间完全隔离
3. 可以并行运行测试

注意事项：
1. 需要配置异步数据库连接
2. 与你的 ORM（Tortoise/SQLAlchemy）集成
3. 可能需要调整 FastAPI 的依赖注入
"""
