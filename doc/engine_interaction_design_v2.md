# Engine 交互模块设计方案 V2.0

## 1. 概述

基于多用户并发使用场景，Backend采用定时同步机制：
- 通过APScheduler定期从Engine同步状态和日志到数据库
- 前端所有查询都基于数据库，不直接访问Engine
- 支持多用户同时查看完整的状态和日志信息

## 2. 架构设计

### 2.1 整体架构

```
多个Frontend实例 <--查询--> Backend <--定时同步--> Engine
                              |                      |
                              v                      v
                        PostgreSQL            Redis + RabbitMQ
                         (存储所有状态和日志)        (临时数据)
```

### 2.2 数据流设计

```
1. 任务下发流程：
   Frontend → Backend → Engine (一次性下发)
   Backend → Database (保存任务映射关系)

2. 状态同步流程（定时）：
   APScheduler触发 → Backend从Engine拉取状态 → 更新Database
   APScheduler触发 → Backend从RabbitMQ消费日志 → 存储到Database

3. 前端查询流程：
   Frontend → Backend → Database (所有查询都走数据库)
```

## 3. 模块设计

### 3.1 文件结构

```
backend/
├── app/
│   └── engine/                    # Engine交互模块
│       ├── __init__.py
│       ├── client/                # Engine客户端
│       │   ├── __init__.py
│       │   ├── engine_client.py  # Engine HTTP客户端
│       │   └── mq_consumer.py    # RabbitMQ消费者
│       ├── scheduler/             # 定时任务
│       │   ├── __init__.py
│       │   ├── jobs.py           # 定时任务定义
│       │   └── manager.py        # 调度器管理
│       ├── service/               # 业务逻辑
│       │   ├── __init__.py
│       │   ├── task_service.py   # 任务管理服务
│       │   ├── sync_service.py   # 同步服务
│       │   └── query_service.py  # 查询服务
│       ├── model/                 # 数据模型
│       │   ├── __init__.py
│       │   ├── task_execution.py # 任务执行记录
│       │   └── task_log.py       # 任务日志
│       ├── schema/                # Schema定义
│       │   ├── __init__.py
│       │   ├── task.py           # 任务相关schema
│       │   └── log.py            # 日志相关schema
│       └── api/                   # API路由
│           └── v1/
│               ├── __init__.py
│               ├── execute.py    # 执行相关API
│               └── query.py      # 查询相关API
```

### 3.2 数据库模型设计

#### 3.2.1 任务执行记录表

```python
# backend/app/engine/model/task_execution.py
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base

class TaskExecution(Base):
    """任务执行记录表 - 存储Engine中的任务信息"""

    __tablename__ = "task_execution"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联信息
    plan_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment="推演方案ID")
    engine_task_id: Mapped[str] = mapped_column(sa.String(128), unique=True, comment="Engine任务ID")

    # 任务信息
    agent_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=True, comment="智能体ID")
    agent_name: Mapped[str] = mapped_column(sa.String(128), comment="智能体名称")
    env_instance_id: Mapped[int] = mapped_column(sa.BigInteger, comment="环境实例ID")

    # 状态信息
    status: Mapped[str] = mapped_column(sa.String(32), comment="任务状态")
    progress: Mapped[int] = mapped_column(sa.Integer, default=0, comment="执行进度")

    # 配置信息
    task_config: Mapped[dict] = mapped_column(sa.JSON, comment="任务配置")
    result: Mapped[dict] = mapped_column(sa.JSON, nullable=True, comment="执行结果")

    # 时间信息
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True, comment="结束时间")
    last_sync_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True, comment="最后同步时间")

    # 索引
    __table_args__ = (
        sa.Index('idx_plan_agent', 'plan_id', 'agent_id'),
        sa.Index('idx_status', 'status'),
        sa.Index('idx_sync', 'last_sync_at'),
    )
```

#### 3.2.2 任务日志表

```python
# backend/app/engine/model/task_log.py
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base

class TaskLog(Base):
    """任务日志表 - 存储从RabbitMQ消费的日志"""

    __tablename__ = "task_log"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联信息
    execution_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("task_execution.id", ondelete="CASCADE"),
        index=True,
        comment="执行记录ID"
    )
    plan_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment="推演方案ID")
    agent_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=True, comment="智能体ID")

    # 日志内容
    log_type: Mapped[str] = mapped_column(
        sa.String(16),
        comment="日志类型: log/event/echart"
    )
    log_level: Mapped[str] = mapped_column(
        sa.String(16),
        comment="日志级别: info/warning/error/critical"
    )
    message: Mapped[str] = mapped_column(sa.Text, comment="日志消息")
    data: Mapped[dict] = mapped_column(sa.JSON, nullable=True, comment="附加数据")

    # 时间信息
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime, index=True, comment="日志时间")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        default=datetime.now,
        comment="入库时间"
    )

    # 索引优化查询
    __table_args__ = (
        sa.Index('idx_plan_time', 'plan_id', 'timestamp'),
        sa.Index('idx_agent_time', 'agent_id', 'timestamp'),
        sa.Index('idx_type_level', 'log_type', 'log_level'),
    )
```

### 3.3 定时任务设计

#### 3.3.1 调度器管理

```python
# backend/app/engine/scheduler/manager.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from backend.core.conf import settings
from backend.common.log import log

class SchedulerManager:
    """调度器管理器"""

    def __init__(self):
        self.scheduler = None

    def init_scheduler(self):
        """初始化调度器"""
        # 配置任务存储
        jobstores = {
            'default': SQLAlchemyJobStore(url=str(settings.DATABASE_URL))
        }

        # 配置执行器
        job_defaults = {
            'coalesce': True,  # 积压的任务只执行一次
            'max_instances': 3,  # 同一任务最多同时运行3个实例
            'misfire_grace_time': 30  # 任务错过执行时间30秒内仍会执行
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone=settings.DATETIME_TIMEZONE
        )

    async def start(self):
        """启动调度器"""
        if not self.scheduler:
            self.init_scheduler()

        # 注册定时任务
        from backend.app.engine.scheduler.jobs import (
            sync_task_status,
            consume_task_logs,
            clean_old_logs
        )

        # 每5秒同步一次任务状态
        self.scheduler.add_job(
            sync_task_status,
            'interval',
            seconds=5,
            id='sync_task_status',
            replace_existing=True
        )

        # 每2秒消费一次日志
        self.scheduler.add_job(
            consume_task_logs,
            'interval',
            seconds=2,
            id='consume_task_logs',
            replace_existing=True
        )

        # 每天凌晨2点清理旧日志
        self.scheduler.add_job(
            clean_old_logs,
            'cron',
            hour=2,
            minute=0,
            id='clean_old_logs',
            replace_existing=True
        )

        self.scheduler.start()
        log.info("定时任务调度器已启动")

    async def shutdown(self):
        """关闭调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            log.info("定时任务调度器已关闭")

scheduler_manager = SchedulerManager()
```

#### 3.3.2 定时任务实现

```python
# backend/app/engine/scheduler/jobs.py
from datetime import datetime, timedelta
from sqlalchemy import select, delete, and_
from backend.database.db import async_db_session
from backend.app.engine.client.engine_client import engine_client
from backend.app.engine.client.mq_consumer import mq_consumer
from backend.app.engine.model.task_execution import TaskExecution
from backend.app.engine.model.task_log import TaskLog
from backend.common.log import log

async def sync_task_status():
    """同步任务状态 - 定时任务"""
    try:
        async with async_db_session() as db:
            # 获取所有运行中的任务
            stmt = select(TaskExecution).where(
                TaskExecution.status.in_(['running', 'pending'])
            )
            result = await db.execute(stmt)
            running_tasks = result.scalars().all()

            if not running_tasks:
                return

            # 批量查询Engine状态
            task_ids = [task.engine_task_id for task in running_tasks]
            statuses = await engine_client.batch_query_status(task_ids)

            # 更新数据库
            for task in running_tasks:
                if task.engine_task_id in statuses:
                    engine_status = statuses[task.engine_task_id]
                    task.status = engine_status.get('status')
                    task.progress = engine_status.get('progress', 0)
                    task.last_sync_at = datetime.now()

                    if engine_status.get('result'):
                        task.result = engine_status['result']

                    if task.status == 'finished':
                        task.finished_at = datetime.now()

            await db.commit()
            log.debug(f"同步了 {len(running_tasks)} 个任务的状态")

    except Exception as e:
        log.error(f"同步任务状态失败: {e}")

async def consume_task_logs():
    """消费任务日志 - 定时任务"""
    try:
        async with async_db_session() as db:
            # 获取所有活跃的任务
            stmt = select(TaskExecution).where(
                TaskExecution.status.in_(['running', 'pending'])
            )
            result = await db.execute(stmt)
            active_tasks = result.scalars().all()

            if not active_tasks:
                return

            # 为每个任务消费日志
            for task in active_tasks:
                queue_name = f"task_logs_{task.engine_task_id}"

                # 批量消费日志（最多100条）
                logs = await mq_consumer.consume_messages(
                    queue_name=queue_name,
                    max_messages=100,
                    timeout=1.0
                )

                # 批量插入日志
                if logs:
                    log_entries = []
                    for log_data in logs:
                        log_entry = TaskLog(
                            execution_id=task.id,
                            plan_id=task.plan_id,
                            agent_id=task.agent_id,
                            log_type=log_data.get('type', 'log'),
                            log_level=log_data.get('level', 'info'),
                            message=log_data.get('message', ''),
                            data=log_data.get('data'),
                            timestamp=datetime.fromisoformat(
                                log_data.get('timestamp', datetime.now().isoformat())
                            )
                        )
                        log_entries.append(log_entry)

                    db.add_all(log_entries)
                    await db.commit()
                    log.debug(f"任务 {task.engine_task_id} 消费了 {len(logs)} 条日志")

    except Exception as e:
        log.error(f"消费任务日志失败: {e}")

async def clean_old_logs():
    """清理旧日志 - 定时任务"""
    try:
        async with async_db_session() as db:
            # 删除30天前的日志
            cutoff_date = datetime.now() - timedelta(days=30)

            stmt = delete(TaskLog).where(
                TaskLog.created_at < cutoff_date
            )
            result = await db.execute(stmt)

            # 删除已完成60天的任务记录
            task_cutoff = datetime.now() - timedelta(days=60)
            task_stmt = delete(TaskExecution).where(
                and_(
                    TaskExecution.status == 'finished',
                    TaskExecution.finished_at < task_cutoff
                )
            )
            task_result = await db.execute(task_stmt)

            await db.commit()
            log.info(f"清理了 {result.rowcount} 条旧日志, {task_result.rowcount} 个旧任务")

    except Exception as e:
        log.error(f"清理旧日志失败: {e}")
```

### 3.4 客户端实现

#### 3.4.1 Engine客户端

```python
# backend/app/engine/client/engine_client.py
import httpx
from typing import Dict, Any, List
from backend.core.conf import settings
from backend.common.log import log

class EngineClient:
    """Engine HTTP客户端"""

    def __init__(self):
        self.base_url = settings.ENGINE_BASE_URL
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )

    async def create_task(self, task_config: Dict[str, Any]) -> str:
        """创建任务"""
        try:
            response = await self.client.post(
                "/api/v1/task/create",
                json=task_config
            )
            response.raise_for_status()
            data = response.json()
            return data.get("task_id")
        except Exception as e:
            log.error(f"创建Engine任务失败: {e}")
            raise

    async def batch_query_status(self, task_ids: List[str]) -> Dict[str, Any]:
        """批量查询任务状态"""
        try:
            response = await self.client.post(
                "/api/v1/task/status/batch",
                json={"task_ids": task_ids}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.error(f"查询Engine任务状态失败: {e}")
            return {}

    async def stop_tasks(self, task_ids: List[str]) -> bool:
        """停止任务"""
        try:
            response = await self.client.post(
                "/api/v1/task/stop",
                json={"task_ids": task_ids}
            )
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            log.error(f"停止Engine任务失败: {e}")
            return False

    async def test_environment(self, env_config: Dict[str, Any]) -> Dict[str, Any]:
        """测试环境连接"""
        try:
            response = await self.client.post(
                "/api/v1/env/test",
                json=env_config
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.error(f"测试环境连接失败: {e}")
            raise

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self.client.get("/api/v1/health")
            return response.status_code == 200
        except Exception:
            return False

engine_client = EngineClient()
```

#### 3.4.2 RabbitMQ消费者

```python
# backend/app/engine/client/mq_consumer.py
import aio_pika
import asyncio
import json
from typing import List, Dict, Any, Optional
from backend.core.conf import settings
from backend.common.log import log

class MQConsumer:
    """RabbitMQ消费者"""

    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        """连接到RabbitMQ"""
        if not self.connection:
            self.connection = await aio_pika.connect_robust(
                f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@"
                f"{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
            )
            self.channel = await self.connection.channel()

    async def consume_messages(
        self,
        queue_name: str,
        max_messages: int = 100,
        timeout: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        批量消费消息
        Args:
            queue_name: 队列名称
            max_messages: 最大消费条数
            timeout: 超时时间
        Returns:
            消息列表
        """
        messages = []

        try:
            await self.connect()

            # 声明队列
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                arguments={'x-message-ttl': 86400000}  # 消息TTL 24小时
            )

            # 批量获取消息
            end_time = asyncio.get_event_loop().time() + timeout

            while len(messages) < max_messages:
                remaining_time = end_time - asyncio.get_event_loop().time()
                if remaining_time <= 0:
                    break

                try:
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=remaining_time
                    )

                    if message:
                        # 解析消息
                        data = json.loads(message.body.decode())
                        messages.append(data)

                        # 确认消息
                        await message.ack()
                    else:
                        break

                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    log.error(f"处理消息失败: {e}")
                    if message:
                        await message.nack(requeue=True)

        except Exception as e:
            log.error(f"消费消息失败: {e}")

        return messages

    async def close(self):
        """关闭连接"""
        if self.connection:
            await self.connection.close()

mq_consumer = MQConsumer()
```

### 3.5 服务层实现

#### 3.5.1 任务服务

```python
# backend/app/engine/service/task_service.py
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from backend.app.engine.client.engine_client import engine_client
from backend.app.engine.model.task_execution import TaskExecution
from backend.app.deduction.service.deduction_plan_service import deduction_plan_service
from backend.common.exception import errors

class TaskService:
    """任务管理服务 - 处理任务下发"""

    async def deploy_plan(
        self,
        db: AsyncSession,
        plan_id: int,
        env_instance_id: int
    ) -> Dict[str, Any]:
        """
        部署执行方案
        """
        # 1. 获取方案信息
        plan = await deduction_plan_service.get(db=db, pk=plan_id)
        if not plan:
            raise errors.NotFoundError(msg="推演方案不存在")

        # 2. 构建任务配置
        task_config = {
            "plan_id": plan_id,
            "plan_name": plan.name,
            "env_instance_id": env_instance_id,
            "task_config": plan.task_config,
        }

        # 3. 调用Engine创建任务
        engine_task_id = await engine_client.create_task(task_config)

        # 4. 保存任务执行记录到数据库
        agents = plan.task_config.get("agents", [])
        execution_records = []

        for agent_info in agents:
            execution = TaskExecution(
                plan_id=plan_id,
                engine_task_id=f"{engine_task_id}_{agent_info['agent_id']}",
                agent_id=agent_info.get("agent_id"),
                agent_name=agent_info.get("agent_name"),
                env_instance_id=env_instance_id,
                status="pending",
                task_config=agent_info,
                started_at=datetime.now()
            )
            execution_records.append(execution)

        db.add_all(execution_records)

        # 5. 更新方案状态
        plan.status = "running"
        plan.start_time = datetime.now()

        await db.commit()

        return {
            "success": True,
            "engine_task_id": engine_task_id,
            "task_count": len(execution_records)
        }

    async def stop_plan(
        self,
        db: AsyncSession,
        plan_id: int,
        agent_ids: Optional[List[int]] = None
    ) -> bool:
        """停止方案执行"""
        # 1. 查询任务执行记录
        query = select(TaskExecution).where(
            TaskExecution.plan_id == plan_id
        )

        if agent_ids:
            query = query.where(TaskExecution.agent_id.in_(agent_ids))

        result = await db.execute(query)
        executions = result.scalars().all()

        if not executions:
            return False

        # 2. 调用Engine停止任务
        task_ids = [exe.engine_task_id for exe in executions]
        success = await engine_client.stop_tasks(task_ids)

        # 3. 更新数据库状态
        if success:
            for exe in executions:
                exe.status = "stopped"
                exe.finished_at = datetime.now()

            # 如果停止了所有任务，更新方案状态
            if not agent_ids:
                plan = await deduction_plan_service.get(db=db, pk=plan_id)
                if plan:
                    plan.status = "stopped"

            await db.commit()

        return success

task_service = TaskService()
```

#### 3.5.2 查询服务

```python
# backend/app/engine/service/query_service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from backend.app.engine.model.task_execution import TaskExecution
from backend.app.engine.model.task_log import TaskLog

class QueryService:
    """查询服务 - 从数据库查询状态和日志"""

    async def get_plan_status(
        self,
        db: AsyncSession,
        plan_id: int
    ) -> Dict[str, Any]:
        """获取方案执行状态"""
        # 查询所有任务执行记录
        stmt = select(TaskExecution).where(
            TaskExecution.plan_id == plan_id
        )
        result = await db.execute(stmt)
        executions = result.scalars().all()

        if not executions:
            return {
                "plan_id": plan_id,
                "status": "not_started",
                "tasks": []
            }

        # 汇总状态
        tasks = []
        overall_status = "finished"
        total_progress = 0

        for exe in executions:
            tasks.append({
                "agent_id": exe.agent_id,
                "agent_name": exe.agent_name,
                "status": exe.status,
                "progress": exe.progress,
                "started_at": exe.started_at.isoformat() if exe.started_at else None,
                "finished_at": exe.finished_at.isoformat() if exe.finished_at else None,
                "result": exe.result
            })

            # 判断整体状态
            if exe.status in ["running", "pending"]:
                overall_status = "running"
            elif exe.status == "error" and overall_status != "running":
                overall_status = "error"

            total_progress += exe.progress

        avg_progress = total_progress // len(executions) if executions else 0

        return {
            "plan_id": plan_id,
            "status": overall_status,
            "progress": avg_progress,
            "task_count": len(tasks),
            "tasks": tasks
        }

    async def get_task_logs(
        self,
        db: AsyncSession,
        plan_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        execution_id: Optional[int] = None,
        log_type: Optional[str] = None,
        log_level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        查询任务日志
        支持多种过滤条件
        """
        # 构建查询
        query = select(TaskLog)
        conditions = []

        if plan_id:
            conditions.append(TaskLog.plan_id == plan_id)
        if agent_id:
            conditions.append(TaskLog.agent_id == agent_id)
        if execution_id:
            conditions.append(TaskLog.execution_id == execution_id)
        if log_type:
            conditions.append(TaskLog.log_type == log_type)
        if log_level:
            conditions.append(TaskLog.log_level == log_level)
        if start_time:
            conditions.append(TaskLog.timestamp >= start_time)
        if end_time:
            conditions.append(TaskLog.timestamp <= end_time)

        if conditions:
            query = query.where(and_(*conditions))

        # 排序和分页
        query = query.order_by(TaskLog.timestamp.desc())

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 获取数据
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        logs = result.scalars().all()

        # 格式化返回
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": [
                {
                    "id": log.id,
                    "agent_id": log.agent_id,
                    "type": log.log_type,
                    "level": log.log_level,
                    "message": log.message,
                    "data": log.data,
                    "timestamp": log.timestamp.isoformat()
                }
                for log in logs
            ]
        }

    async def get_latest_logs(
        self,
        db: AsyncSession,
        plan_id: int,
        last_log_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取最新日志（用于实时更新）
        Args:
            plan_id: 方案ID
            last_log_id: 上次获取的最后一条日志ID
        """
        query = select(TaskLog).where(TaskLog.plan_id == plan_id)

        if last_log_id:
            query = query.where(TaskLog.id > last_log_id)

        query = query.order_by(TaskLog.id).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": log.id,
                "agent_id": log.agent_id,
                "type": log.log_type,
                "level": log.log_level,
                "message": log.message,
                "data": log.data,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]

query_service = QueryService()
```

### 3.6 API路由实现

```python
# backend/app/engine/api/v1/execute.py
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from backend.app.engine.service.task_service import task_service
from backend.app.engine.client.engine_client import engine_client
from backend.database.db import CurrentSessionTransaction
from backend.common.response.response_schema import response_base

router = APIRouter()

@router.post("/deploy", summary="部署执行方案")
async def deploy_plan(
    db: CurrentSessionTransaction,
    plan_id: int,
    env_instance_id: int
):
    """部署方案到Engine执行"""
    result = await task_service.deploy_plan(
        db=db,
        plan_id=plan_id,
        env_instance_id=env_instance_id
    )
    return response_base.success(data=result)

@router.post("/stop", summary="停止方案执行")
async def stop_plan(
    db: CurrentSessionTransaction,
    plan_id: int,
    agent_ids: Optional[List[int]] = None
):
    """停止方案执行"""
    success = await task_service.stop_plan(
        db=db,
        plan_id=plan_id,
        agent_ids=agent_ids
    )
    return response_base.success(data={"success": success})

@router.post("/test-env", summary="测试环境连接")
async def test_environment(env_config: dict):
    """测试环境连接"""
    result = await engine_client.test_environment(env_config)
    return response_base.success(data=result)

@router.get("/health", summary="Engine健康检查")
async def health_check():
    """检查Engine服务状态"""
    is_healthy = await engine_client.health_check()
    return response_base.success(data={"healthy": is_healthy})
```

```python
# backend/app/engine/api/v1/query.py
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime
from backend.app.engine.service.query_service import query_service
from backend.database.db import CurrentSession
from backend.common.response.response_schema import response_base

router = APIRouter()

@router.get("/status/{plan_id}", summary="获取方案执行状态")
async def get_plan_status(
    db: CurrentSession,
    plan_id: int
):
    """从数据库获取方案执行状态"""
    status = await query_service.get_plan_status(db=db, plan_id=plan_id)
    return response_base.success(data=status)

@router.get("/logs", summary="查询任务日志")
async def get_logs(
    db: CurrentSession,
    plan_id: Optional[int] = Query(None),
    agent_id: Optional[int] = Query(None),
    log_type: Optional[str] = Query(None),
    log_level: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """从数据库查询任务日志"""
    logs = await query_service.get_task_logs(
        db=db,
        plan_id=plan_id,
        agent_id=agent_id,
        log_type=log_type,
        log_level=log_level,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )
    return response_base.success(data=logs)

@router.get("/logs/latest/{plan_id}", summary="获取最新日志")
async def get_latest_logs(
    db: CurrentSession,
    plan_id: int,
    last_log_id: Optional[int] = Query(None)
):
    """获取最新日志，用于前端轮询更新"""
    logs = await query_service.get_latest_logs(
        db=db,
        plan_id=plan_id,
        last_log_id=last_log_id
    )
    return response_base.success(data=logs)
```

### 3.7 集成到主应用

```python
# 在 backend/core/registrar.py 中添加

from backend.app.engine.scheduler.manager import scheduler_manager

@asynccontextmanager
async def register_init(app: FastAPI):
    """启动初始化"""

    # 创建数据库 & 连接db
    await create_tables()

    # 启动定时任务调度器
    await scheduler_manager.start()

    yield

    # 关闭调度器
    await scheduler_manager.shutdown()
```

## 4. 配置更新

```python
# backend/core/conf.py 添加

# Engine配置
ENGINE_BASE_URL: str = "http://localhost:8001"

# RabbitMQ配置
RABBITMQ_HOST: str = "localhost"
RABBITMQ_PORT: int = 5672
RABBITMQ_USER: str = "guest"
RABBITMQ_PASSWORD: str = "guest"

# 定时任务配置
SCHEDULER_STATUS_SYNC_INTERVAL: int = 5  # 状态同步间隔（秒）
SCHEDULER_LOG_SYNC_INTERVAL: int = 2     # 日志同步间隔（秒）
LOG_RETENTION_DAYS: int = 30             # 日志保留天数
```

## 5. 优势

1. **支持多用户并发**：所有前端查询数据库，不会互相影响
2. **完整日志保存**：日志持久化存储，所有用户都能看到完整日志
3. **减少Engine负载**：定时批量同步，而非每次查询都访问Engine
4. **历史数据查询**：支持查询历史执行记录和日志
5. **灵活的查询接口**：支持多维度过滤和分页
6. **自动清理机制**：定期清理旧数据，控制存储空间

## 6. 依赖包更新

```toml
dependencies = [
    # ... 现有依赖
    "httpx>=0.24.0",
    "aio-pika>=9.0.0",
    # apscheduler已经在依赖中
]
```