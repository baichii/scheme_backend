# Engine 交互模块设计方案

## 1. 概述

根据开发计划，Backend需要与Engine进行交互，Engine负责：
- 执行智能体方案
- 与环境（env）交互
- 通过Redis处理内部状态
- 将日志、状态写入RabbitMQ供Backend查询

## 2. 架构设计

### 2.1 整体架构

```
Frontend <--> Backend <--> Engine (Celery + Redis + RabbitMQ)
                |             |
                v             v
           PostgreSQL      Environment
             MinIO
```

### 2.2 交互流程

```
1. Backend 下发任务 --> Engine (通过HTTP/gRPC)
2. Engine 执行任务 --> 更新状态到Redis
3. Engine 产生日志 --> 发送到RabbitMQ
4. Backend 查询状态 <-- 从Engine获取
5. Backend 订阅日志 <-- 从RabbitMQ消费
```

## 3. 模块设计

### 3.1 文件结构

```
backend/
├── app/
│   └── engine/           # Engine交互模块
│       ├── __init__.py
│       ├── api/          # Engine相关的API路由
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── task.py        # 任务管理API
│       │       ├── health.py      # 健康检查API
│       │       └── env_test.py    # 环境测试API
│       ├── client/       # Engine客户端
│       │   ├── __init__.py
│       │   ├── base.py           # 基础客户端类
│       │   ├── task_client.py    # 任务操作客户端
│       │   └── rabbitmq_client.py # RabbitMQ客户端
│       ├── schema/       # 数据模型
│       │   ├── __init__.py
│       │   ├── task.py           # 任务相关schema
│       │   └── log.py            # 日志相关schema
│       └── service/      # 业务逻辑
│           ├── __init__.py
│           ├── task_service.py   # 任务管理服务
│           ├── log_service.py    # 日志处理服务
│           └── health_service.py # 健康检查服务
```

### 3.2 核心组件设计

#### 3.2.1 Engine客户端基类

```python
# backend/app/engine/client/base.py
from typing import Any, Dict, Optional
import httpx
from pydantic import BaseModel
from backend.core.conf import settings

class EngineClientBase:
    """Engine客户端基类"""

    def __init__(self):
        self.base_url = settings.ENGINE_BASE_URL  # 需要在conf.py添加
        self.timeout = settings.ENGINE_TIMEOUT
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """统一的请求方法"""
        response = await self.client.request(
            method=method,
            url=endpoint,
            json=data,
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
```

#### 3.2.2 任务客户端

```python
# backend/app/engine/client/task_client.py
from typing import List, Dict, Any
from backend.app.engine.client.base import EngineClientBase

class TaskClient(EngineClientBase):
    """任务操作客户端"""

    async def create_task(self, task_config: Dict[str, Any]) -> str:
        """
        创建任务
        Args:
            task_config: 任务配置，包含方案ID、智能体列表、环境配置等
        Returns:
            task_id: 任务ID
        """
        result = await self._request(
            method="POST",
            endpoint="/api/v1/task/create",
            data=task_config
        )
        return result["task_id"]

    async def update_task(self, task_id: str, update_config: Dict[str, Any]) -> bool:
        """修改运行中的任务"""
        result = await self._request(
            method="PUT",
            endpoint=f"/api/v1/task/{task_id}",
            data=update_config
        )
        return result["success"]

    async def query_task_status(self, task_ids: List[str]) -> Dict[str, Any]:
        """
        查询任务状态
        Args:
            task_ids: 任务ID列表
        Returns:
            状态信息字典
        """
        result = await self._request(
            method="POST",
            endpoint="/api/v1/task/status",
            data={"task_ids": task_ids}
        )
        return result

    async def stop_task(self, task_ids: List[str]) -> bool:
        """停止任务"""
        result = await self._request(
            method="POST",
            endpoint="/api/v1/task/stop",
            data={"task_ids": task_ids}
        )
        return result["success"]

    async def test_environment(self, env_config: Dict[str, Any]) -> Dict[str, Any]:
        """测试环境连接"""
        result = await self._request(
            method="POST",
            endpoint="/api/v1/env/test",
            data=env_config
        )
        return result

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            result = await self._request(
                method="GET",
                endpoint="/api/v1/health"
            )
            return result.get("status") == "healthy"
        except Exception:
            return False

# 单例
task_client = TaskClient()
```

#### 3.2.3 RabbitMQ客户端

```python
# backend/app/engine/client/rabbitmq_client.py
import asyncio
import aio_pika
from typing import AsyncGenerator, Dict, Any
import json
from backend.core.conf import settings

class RabbitMQClient:
    """RabbitMQ客户端，用于订阅日志"""

    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        """连接到RabbitMQ"""
        self.connection = await aio_pika.connect_robust(
            f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@"
            f"{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
        )
        self.channel = await self.connection.channel()

    async def subscribe_logs(
        self,
        task_id: str,
        queue_name: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        订阅任务日志
        Args:
            task_id: 任务ID
            queue_name: 队列名称，如果为None则自动生成
        Yields:
            日志消息
        """
        if not self.channel:
            await self.connect()

        # 使用task_id构建队列名
        if not queue_name:
            queue_name = f"task_logs_{task_id}"

        queue = await self.channel.declare_queue(
            queue_name,
            durable=True
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    log_data = json.loads(message.body.decode())
                    yield log_data

    async def close(self):
        """关闭连接"""
        if self.connection:
            await self.connection.close()

rabbitmq_client = RabbitMQClient()
```

#### 3.2.4 任务服务层

```python
# backend/app/engine/service/task_service.py
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.engine.client.task_client import task_client
from backend.app.deduction.service.deduction_plan_service import deduction_plan_service
from backend.app.agent.service.agent_meta_service import agent_meta_service
from backend.common.exception import errors

class EngineTaskService:
    """Engine任务服务"""

    async def deploy_plan(
        self,
        db: AsyncSession,
        plan_id: int,
        env_instance_id: int
    ) -> str:
        """
        部署执行方案到Engine
        Args:
            db: 数据库会话
            plan_id: 方案ID
            env_instance_id: 环境实例ID
        Returns:
            task_id: Engine返回的任务ID
        """
        # 1. 获取方案配置
        plan = await deduction_plan_service.get(db=db, pk=plan_id)
        if not plan:
            raise errors.NotFoundError(msg="推演方案不存在")

        # 2. 构建任务配置
        task_config = {
            "plan_id": plan_id,
            "plan_name": plan.name,
            "env_instance_id": env_instance_id,
            "task_config": plan.task_config,
            "agents": await self._build_agent_configs(db, plan.task_config)
        }

        # 3. 调用Engine创建任务
        task_id = await task_client.create_task(task_config)

        # 4. 更新方案状态
        await deduction_plan_service.update_status(
            db=db,
            pk=plan_id,
            status="running"
        )

        return task_id

    async def _build_agent_configs(
        self,
        db: AsyncSession,
        task_config: Dict
    ) -> List[Dict]:
        """构建智能体配置列表"""
        agent_configs = []

        # 从task_config中提取智能体信息
        for agent_info in task_config.get("agents", []):
            agent_id = agent_info.get("agent_id")
            agent = await agent_meta_service.get(db=db, pk=agent_id)

            if not agent:
                raise errors.NotFoundError(f"智能体 {agent_id} 不存在")

            agent_configs.append({
                "agent_id": agent_id,
                "agent_name": agent.name,
                "agent_config": agent_info.get("config", {}),
                "position": agent_info.get("position"),
                "team": agent_info.get("team")
            })

        return agent_configs

    async def query_plan_status(
        self,
        db: AsyncSession,
        plan_id: int
    ) -> Dict[str, Any]:
        """
        查询方案执行状态
        """
        # 1. 获取方案对应的所有task_id
        task_ids = await self._get_plan_task_ids(db, plan_id)

        if not task_ids:
            return {"status": "not_started", "tasks": []}

        # 2. 查询Engine中的状态
        status_data = await task_client.query_task_status(task_ids)

        return status_data

    async def stop_plan(
        self,
        db: AsyncSession,
        plan_id: int,
        agent_ids: Optional[List[int]] = None
    ) -> bool:
        """
        停止方案执行
        Args:
            db: 数据库会话
            plan_id: 方案ID
            agent_ids: 要停止的智能体ID列表，如果为None则停止所有
        """
        # 获取要停止的task_ids
        task_ids = await self._get_plan_task_ids(db, plan_id, agent_ids)

        if not task_ids:
            return False

        # 调用Engine停止任务
        success = await task_client.stop_task(task_ids)

        if success:
            # 更新方案状态
            await deduction_plan_service.update_status(
                db=db,
                pk=plan_id,
                status="stopped"
            )

        return success

    async def _get_plan_task_ids(
        self,
        db: AsyncSession,
        plan_id: int,
        agent_ids: Optional[List[int]] = None
    ) -> List[str]:
        """获取方案的任务ID列表"""
        # TODO: 从数据库或缓存中获取plan_id对应的task_ids
        # 这需要在创建任务时保存映射关系
        pass

engine_task_service = EngineTaskService()
```

#### 3.2.5 日志服务

```python
# backend/app/engine/service/log_service.py
from typing import AsyncGenerator, Dict, Any
from backend.app.engine.client.rabbitmq_client import rabbitmq_client
import asyncio

class LogService:
    """日志服务"""

    async def stream_task_logs(
        self,
        task_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式获取任务日志
        Args:
            task_id: 任务ID
        Yields:
            日志数据
        """
        async for log_data in rabbitmq_client.subscribe_logs(task_id):
            # 处理日志格式
            processed_log = {
                "timestamp": log_data.get("timestamp"),
                "level": log_data.get("level", "info"),
                "message": log_data.get("message"),
                "type": log_data.get("type", "log"),  # log/event/echart
                "agent_id": log_data.get("agent_id"),
                "data": log_data.get("data")
            }
            yield processed_log

    async def get_recent_logs(
        self,
        task_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        # TODO: 从数据库或缓存获取历史日志
        pass

log_service = LogService()
```

### 3.3 API路由设计

```python
# backend/app/engine/api/v1/task.py
from fastapi import APIRouter, WebSocket
from backend.app.engine.service.task_service import engine_task_service
from backend.app.engine.service.log_service import log_service
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()

@router.post("/deploy", summary="部署执行方案")
async def deploy_plan(
    db: CurrentSessionTransaction,
    plan_id: int,
    env_instance_id: int
):
    """部署方案到Engine执行"""
    task_id = await engine_task_service.deploy_plan(
        db=db,
        plan_id=plan_id,
        env_instance_id=env_instance_id
    )
    return {"task_id": task_id}

@router.get("/status/{plan_id}", summary="查询方案执行状态")
async def get_plan_status(
    db: CurrentSession,
    plan_id: int
):
    """查询方案执行状态"""
    status = await engine_task_service.query_plan_status(
        db=db,
        plan_id=plan_id
    )
    return status

@router.post("/stop/{plan_id}", summary="停止方案执行")
async def stop_plan(
    db: CurrentSessionTransaction,
    plan_id: int,
    agent_ids: List[int] = None
):
    """停止方案执行"""
    success = await engine_task_service.stop_plan(
        db=db,
        plan_id=plan_id,
        agent_ids=agent_ids
    )
    return {"success": success}

@router.websocket("/logs/{task_id}")
async def stream_logs(websocket: WebSocket, task_id: str):
    """WebSocket流式传输日志"""
    await websocket.accept()
    try:
        async for log_data in log_service.stream_task_logs(task_id):
            await websocket.send_json(log_data)
    except Exception as e:
        await websocket.close(code=1000)
```

### 3.4 数据模型扩展

需要添加的表：

```python
# backend/app/engine/model/task_mapping.py
from sqlalchemy.orm import Mapped, mapped_column
import sqlalchemy as sa
from backend.common.model import Base

class TaskMapping(Base):
    """方案与Engine任务映射表"""

    __tablename__ = "task_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(sa.Integer, comment="方案ID")
    task_id: Mapped[str] = mapped_column(sa.String(64), comment="Engine任务ID")
    agent_id: Mapped[int] = mapped_column(sa.Integer, nullable=True, comment="智能体ID")
    status: Mapped[str] = mapped_column(sa.String(32), comment="任务状态")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=datetime.now)
```

## 4. 配置更新

在 `backend/core/conf.py` 中添加：

```python
# Engine配置
ENGINE_BASE_URL: str = "http://localhost:8001"  # Engine服务地址
ENGINE_TIMEOUT: float = 30.0  # 请求超时时间

# RabbitMQ配置
RABBITMQ_HOST: str = "localhost"
RABBITMQ_PORT: int = 5672
RABBITMQ_USER: str = "guest"
RABBITMQ_PASSWORD: str = "guest"
```

## 5. 实现步骤

1. **第一阶段：基础框架**
   - 创建engine模块目录结构
   - 实现Engine客户端基类
   - 实现配置管理

2. **第二阶段：核心功能**
   - 实现任务管理客户端
   - 实现任务服务层
   - 添加数据模型

3. **第三阶段：日志系统**
   - 实现RabbitMQ客户端
   - 实现日志服务
   - 添加WebSocket支持

4. **第四阶段：API集成**
   - 创建API路由
   - 集成到主路由
   - 测试接口

5. **第五阶段：优化**
   - 添加重试机制
   - 实现连接池
   - 添加缓存层
   - 错误处理优化

## 6. 关键点

1. **异步处理**：所有与Engine的交互都应该是异步的
2. **容错性**：需要处理Engine不可用的情况
3. **状态同步**：需要定期同步Engine中的任务状态到数据库
4. **日志流**：使用WebSocket实现实时日志推送
5. **事务一致性**：确保数据库操作和Engine操作的一致性

## 7. 测试方案

1. 单元测试：测试各个客户端方法
2. 集成测试：测试完整的任务生命周期
3. 性能测试：测试并发任务处理能力
4. 容错测试：测试Engine故障场景

## 8. 依赖包

需要添加到 `pyproject.toml`:

```toml
dependencies = [
    # ... 现有依赖
    "httpx>=0.24.0",           # 异步HTTP客户端
    "aio-pika>=9.0.0",         # RabbitMQ异步客户端
    "websockets>=11.0.0",      # WebSocket支持
]
```