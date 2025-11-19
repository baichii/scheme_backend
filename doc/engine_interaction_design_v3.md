# Engine 交互模块设计方案 V3.0 - 基于现有数据模型

## 1. 现有数据模型评估

### 1.1 现有表结构分析

#### TaskStatus 表（任务状态表）
```python
# 文件：backend/app/deduction/model/task_status.py
class TaskStatus(Base):
    """推演任务状态"""
    __tablename__ = "task_status"

    task_id: Mapped[snowflake_id_key]  # 任务运行唯一ID
    suffix: Mapped[int]                 # 合成ID后缀
    deduce_id: Mapped[int]              # 推演方案ID
    status: Mapped[TaskStatus]          # 推演任务状态
```

**评估：需要扩展字段**
- ✅ 基本字段满足需求
- ❌ 缺少：engine_task_id（Engine中的任务ID）
- ❌ 缺少：agent_id（智能体ID）
- ❌ 缺少：env_instance_id（环境实例ID）
- ❌ 缺少：progress（执行进度）
- ❌ 缺少：task_config（任务配置）
- ❌ 缺少：result（执行结果）
- ❌ 缺少：时间戳字段（started_at, finished_at, last_sync_at）

#### TaskLog 表（任务日志表）
```python
# 文件：backend/app/deduction/model/task_log.py
class TaskLog(Base):
    """推演任务执行日志"""
    __tablename__ = "task_log"

    id: Mapped[snowflake_id_key]        # 日志记录ID
    task_id: Mapped[snowflake_id_key]   # 任务运行唯一ID
    suffix: Mapped[int]                 # 合成ID后缀
    deduce_id: Mapped[snowflake_id_key] # 推演方案ID
    content: Mapped[str]                 # 任务执行日志（512字符）
    type: Mapped[MessageType]            # 消息类型
    level: Mapped[MessageLevel]          # 消息等级
```

**评估：需要扩展字段**
- ✅ 基本字段满足需求
- ❌ content字段长度可能不够（建议改为Text）
- ❌ 缺少：agent_id（智能体ID）
- ❌ 缺少：data（附加数据，JSON字段）
- ❌ 缺少：timestamp（日志时间戳）
- ❌ 缺少：created_at（入库时间）

### 1.2 建议的模型扩展

```python
# 扩展 TaskStatus 模型
# backend/app/deduction/model/task_status_ext.py
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base, snowflake_id_key
from backend.common.enums import TaskStatus

class TaskStatusExt(Base):
    """扩展的任务状态表"""
    __tablename__ = "task_status_ext"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联字段
    task_id: Mapped[snowflake_id_key] = mapped_column(index=True, comment="任务运行唯一ID")
    deduce_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment="推演方案ID")
    engine_task_id: Mapped[str] = mapped_column(sa.String(128), unique=True, comment="Engine任务ID")
    agent_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=True, comment="智能体ID")
    env_instance_id: Mapped[int] = mapped_column(sa.BigInteger, comment="环境实例ID")

    # 状态字段
    status: Mapped[str] = mapped_column(sa.String(32), comment="任务状态")
    progress: Mapped[int] = mapped_column(sa.Integer, default=0, comment="执行进度")

    # 配置和结果
    task_config: Mapped[dict] = mapped_column(sa.JSON, comment="任务配置")
    result: Mapped[dict] = mapped_column(sa.JSON, nullable=True, comment="执行结果")

    # 时间戳
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True)
    last_sync_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True)
```

## 2. 基于现有模型的实现方案

### 2.1 文件结构（调整版）

```
backend/
├── app/
│   ├── deduction/          # 使用现有的deduction模块
│   │   ├── model/
│   │   │   ├── task_status.py      # 现有
│   │   │   ├── task_log.py         # 现有
│   │   │   └── task_status_ext.py  # 新增扩展表
│   │   └── service/
│   │       ├── task_status_service.py  # 现有
│   │       └── engine_sync_service.py  # 新增同步服务
│   └── engine/             # Engine交互模块
│       ├── __init__.py
│       ├── client/         # Engine客户端
│       │   ├── __init__.py
│       │   ├── engine_client.py
│       │   └── mq_consumer.py
│       ├── scheduler/      # 定时任务
│       │   ├── __init__.py
│       │   ├── jobs.py
│       │   └── manager.py
│       └── api/           # API路由
│           └── v1/
│               ├── __init__.py
│               ├── execute.py
│               └── query.py
```

### 2.2 定时任务实现

```python
# backend/app/engine/scheduler/jobs.py
from datetime import datetime, timedelta
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload
from backend.database.db import async_db_session
from backend.app.engine.client.engine_client import engine_client
from backend.app.engine.client.mq_consumer import mq_consumer
from backend.app.deduction.model.task_status import TaskStatus
from backend.app.deduction.model.task_log import TaskLog
from backend.app.deduction.crud.crud_task_status import task_status_dao
from backend.app.deduction.crud.crud_task_log import task_log_dao
from backend.common.log import log
from backend.utils.snowflake import SnowflakeIdGenerator

# 初始化雪花ID生成器
id_generator = SnowflakeIdGenerator()

async def sync_task_status():
    """同步任务状态 - 定时任务"""
    try:
        async with async_db_session() as db:
            # 查询所有运行中的任务
            stmt = select(TaskStatus).where(
                TaskStatus.status.in_(['normal', 'unknown'])  # 根据枚举调整
            )
            result = await db.execute(stmt)
            running_tasks = result.scalars().all()

            if not running_tasks:
                return

            # 构建task_id到engine_task_id的映射
            # 注意：需要从扩展表或其他地方获取engine_task_id
            task_mapping = {}
            for task in running_tasks:
                # 使用task_id和suffix构建engine_task_id
                engine_task_id = f"{task.task_id}_{task.suffix}"
                task_mapping[engine_task_id] = task

            # 批量查询Engine状态
            engine_task_ids = list(task_mapping.keys())
            statuses = await engine_client.batch_query_status(engine_task_ids)

            # 更新数据库状态
            for engine_task_id, engine_status in statuses.items():
                if engine_task_id in task_mapping:
                    task = task_mapping[engine_task_id]

                    # 映射Engine状态到本地枚举
                    status_map = {
                        'running': 'normal',
                        'finished': 'terminal',
                        'error': 'abnormal',
                        'pending': 'unknown'
                    }

                    new_status = status_map.get(
                        engine_status.get('status', 'unknown'),
                        'unknown'
                    )

                    # 更新状态
                    task.status = new_status

            await db.commit()
            log.debug(f"同步了 {len(running_tasks)} 个任务的状态")

    except Exception as e:
        log.error(f"同步任务状态失败: {e}")

async def consume_task_logs():
    """消费任务日志 - 定时任务"""
    try:
        async with async_db_session() as db:
            # 获取所有活跃的任务
            stmt = select(TaskStatus).where(
                TaskStatus.status.in_(['normal', 'unknown'])
            )
            result = await db.execute(stmt)
            active_tasks = result.scalars().all()

            if not active_tasks:
                return

            # 为每个任务消费日志
            for task in active_tasks:
                queue_name = f"task_logs_{task.task_id}_{task.suffix}"

                # 批量消费日志
                logs = await mq_consumer.consume_messages(
                    queue_name=queue_name,
                    max_messages=100,
                    timeout=1.0
                )

                # 批量插入日志
                if logs:
                    for log_data in logs:
                        # 生成雪花ID
                        log_id = id_generator.generate()

                        # 创建日志记录
                        new_log = TaskLog(
                            id=log_id,
                            task_id=task.task_id,
                            suffix=task.suffix,
                            deduce_id=task.deduce_id,
                            content=log_data.get('message', '')[:512],  # 截断到512字符
                            type=log_data.get('type', 'log'),
                            level=log_data.get('level', 'info')
                        )
                        db.add(new_log)

                    await db.commit()
                    log.debug(f"任务 {task.task_id} 消费了 {len(logs)} 条日志")

    except Exception as e:
        log.error(f"消费任务日志失败: {e}")

async def clean_old_data():
    """清理旧数据 - 定时任务"""
    try:
        async with async_db_session() as db:
            # 删除30天前的日志
            cutoff_date = datetime.now() - timedelta(days=30)

            # 这里需要添加时间戳字段到TaskLog表
            # 暂时使用ID作为排序依据

            log.info("清理旧数据任务执行完成")

    except Exception as e:
        log.error(f"清理旧数据失败: {e}")
```

### 2.3 Engine客户端实现

```python
# backend/app/engine/client/engine_client.py
import httpx
from typing import Dict, Any, List
from backend.core.conf import settings
from backend.common.log import log

class EngineClient:
    """Engine HTTP客户端"""

    def __init__(self):
        self.base_url = settings.ENGINE_BASE_URL if hasattr(settings, 'ENGINE_BASE_URL') else "http://localhost:8001"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )

    async def create_task(self, task_config: Dict[str, Any]) -> str:
        """
        创建任务
        Args:
            task_config: 任务配置
        Returns:
            engine_task_id: Engine返回的任务ID
        """
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
        """
        批量查询任务状态
        Args:
            task_ids: Engine任务ID列表
        Returns:
            状态字典 {task_id: {status, progress, ...}}
        """
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
        """
        停止任务
        Args:
            task_ids: Engine任务ID列表
        Returns:
            是否成功
        """
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
        """
        测试环境连接
        Args:
            env_config: 环境配置
        Returns:
            测试结果
        """
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

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

# 单例
engine_client = EngineClient()
```

### 2.4 RabbitMQ消费者实现

```python
# backend/app/engine/client/mq_consumer.py
import aio_pika
import asyncio
import json
from typing import List, Dict, Any
from backend.core.conf import settings
from backend.common.log import log

class MQConsumer:
    """RabbitMQ消费者"""

    def __init__(self):
        self.connection = None
        self.channel = None
        self._connect_lock = asyncio.Lock()

    async def connect(self):
        """连接到RabbitMQ"""
        async with self._connect_lock:
            if not self.connection or self.connection.is_closed:
                # 从配置获取连接参数，提供默认值
                host = getattr(settings, 'RABBITMQ_HOST', 'localhost')
                port = getattr(settings, 'RABBITMQ_PORT', 5672)
                user = getattr(settings, 'RABBITMQ_USER', 'guest')
                password = getattr(settings, 'RABBITMQ_PASSWORD', 'guest')

                self.connection = await aio_pika.connect_robust(
                    f"amqp://{user}:{password}@{host}:{port}/"
                )
                self.channel = await self.connection.channel()
                log.info("成功连接到RabbitMQ")

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
            timeout: 超时时间（秒）
        Returns:
            消息列表
        """
        messages = []

        try:
            # 确保连接
            await self.connect()

            # 声明队列
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                arguments={'x-message-ttl': 86400000}  # 消息TTL 24小时
            )

            # 设置预取数量
            await self.channel.set_qos(prefetch_count=max_messages)

            # 批量获取消息
            start_time = asyncio.get_event_loop().time()

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    try:
                        # 解析消息
                        data = json.loads(message.body.decode())
                        messages.append(data)

                        # 确认消息
                        await message.ack()

                        # 检查是否达到限制
                        if len(messages) >= max_messages:
                            break

                        # 检查超时
                        if asyncio.get_event_loop().time() - start_time > timeout:
                            break

                    except json.JSONDecodeError as e:
                        log.error(f"解析消息失败: {e}")
                        await message.nack(requeue=False)  # 丢弃无效消息
                    except Exception as e:
                        log.error(f"处理消息失败: {e}")
                        await message.nack(requeue=True)   # 重新入队

        except asyncio.TimeoutError:
            pass  # 正常超时
        except Exception as e:
            log.error(f"消费消息失败: {e}")

        return messages

    async def close(self):
        """关闭连接"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            log.info("关闭RabbitMQ连接")

# 单例
mq_consumer = MQConsumer()
```

### 2.5 调度器管理实现

```python
# backend/app/engine/scheduler/manager.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from backend.core.conf import settings
from backend.common.log import log

class SchedulerManager:
    """调度器管理器"""

    def __init__(self):
        self.scheduler = None

    def init_scheduler(self):
        """初始化调度器"""
        # 使用内存存储，避免数据库依赖
        jobstores = {
            'default': MemoryJobStore()
        }

        # 配置执行器
        job_defaults = {
            'coalesce': True,      # 积压的任务只执行一次
            'max_instances': 3,    # 同一任务最多同时运行3个实例
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
            clean_old_data
        )

        # 状态同步间隔
        sync_interval = getattr(settings, 'SCHEDULER_STATUS_SYNC_INTERVAL', 5)
        self.scheduler.add_job(
            sync_task_status,
            'interval',
            seconds=sync_interval,
            id='sync_task_status',
            replace_existing=True
        )

        # 日志消费间隔
        log_interval = getattr(settings, 'SCHEDULER_LOG_SYNC_INTERVAL', 2)
        self.scheduler.add_job(
            consume_task_logs,
            'interval',
            seconds=log_interval,
            id='consume_task_logs',
            replace_existing=True
        )

        # 每天凌晨2点清理旧数据
        self.scheduler.add_job(
            clean_old_data,
            'cron',
            hour=2,
            minute=0,
            id='clean_old_data',
            replace_existing=True
        )

        self.scheduler.start()
        log.info("定时任务调度器已启动")

    async def shutdown(self):
        """关闭调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            log.info("定时任务调度器已关闭")

# 单例
scheduler_manager = SchedulerManager()
```

### 2.6 服务层实现

```python
# backend/app/deduction/service/engine_sync_service.py
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.app.engine.client.engine_client import engine_client
from backend.app.deduction.model.task_status import TaskStatus
from backend.app.deduction.model.task_log import TaskLog
from backend.app.deduction.service.deduction_plan_service import deduction_plan_service
from backend.app.deduction.crud.crud_task_status import task_status_dao
from backend.app.deduction.crud.crud_task_log import task_log_dao
from backend.app.env.service.env_instance_service import env_instance_service
from backend.common.exception import errors
from backend.utils.snowflake import SnowflakeIdGenerator

# 初始化雪花ID生成器
id_generator = SnowflakeIdGenerator()

class EngineSyncService:
    """Engine同步服务"""

    async def deploy_plan(
        self,
        db: AsyncSession,
        plan_id: int,
        env_instance_id: int
    ) -> Dict[str, Any]:
        """
        部署执行方案到Engine
        Args:
            db: 数据库会话
            plan_id: 推演方案ID
            env_instance_id: 环境实例ID
        Returns:
            部署结果
        """
        # 1. 获取方案信息
        plan = await deduction_plan_service.get(db=db, pk=plan_id)
        if not plan:
            raise errors.NotFoundError(msg="推演方案不存在")

        # 2. 获取环境信息
        env_instance = await env_instance_service.get(db=db, pk=env_instance_id)
        if not env_instance:
            raise errors.NotFoundError(msg="环境实例不存在")

        # 3. 构建任务配置
        task_config = {
            "plan_id": plan_id,
            "plan_name": plan.name,
            "env_instance_id": env_instance_id,
            "env_config": env_instance.params,
            "task_config": plan.task_config,
        }

        # 4. 调用Engine创建任务
        engine_task_id = await engine_client.create_task(task_config)

        # 5. 创建任务状态记录
        agents = plan.task_config.get("agents", [])
        for idx, agent_info in enumerate(agents):
            # 生成任务ID
            task_id = id_generator.generate()

            # 创建任务状态记录
            task_status = TaskStatus(
                task_id=task_id,
                suffix=idx,
                deduce_id=plan_id,
                status='unknown'  # 初始状态
            )
            db.add(task_status)

        # 6. 更新方案状态
        plan.status = "running"
        plan.start_time = datetime.now()

        await db.commit()

        return {
            "success": True,
            "engine_task_id": engine_task_id,
            "task_count": len(agents)
        }

    async def stop_plan(
        self,
        db: AsyncSession,
        plan_id: int,
        task_ids: Optional[List[int]] = None
    ) -> bool:
        """
        停止方案执行
        Args:
            db: 数据库会话
            plan_id: 推演方案ID
            task_ids: 要停止的任务ID列表，None表示停止所有
        Returns:
            是否成功
        """
        # 1. 查询任务状态记录
        query = select(TaskStatus).where(TaskStatus.deduce_id == plan_id)

        if task_ids:
            query = query.where(TaskStatus.task_id.in_(task_ids))

        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            return False

        # 2. 构建Engine任务ID列表
        engine_task_ids = [f"{task.task_id}_{task.suffix}" for task in tasks]

        # 3. 调用Engine停止任务
        success = await engine_client.stop_tasks(engine_task_ids)

        # 4. 更新数据库状态
        if success:
            for task in tasks:
                task.status = 'terminal'  # 终止状态

            # 如果停止了所有任务，更新方案状态
            if not task_ids:
                plan = await deduction_plan_service.get(db=db, pk=plan_id)
                if plan:
                    plan.status = "stopped"

            await db.commit()

        return success

    async def get_plan_status(
        self,
        db: AsyncSession,
        plan_id: int
    ) -> Dict[str, Any]:
        """
        获取方案执行状态（从数据库）
        Args:
            db: 数据库会话
            plan_id: 推演方案ID
        Returns:
            状态信息
        """
        # 查询所有任务状态
        stmt = select(TaskStatus).where(TaskStatus.deduce_id == plan_id)
        result = await db.execute(stmt)
        tasks = result.scalars().all()

        if not tasks:
            return {
                "plan_id": plan_id,
                "status": "not_started",
                "tasks": []
            }

        # 汇总状态
        task_list = []
        overall_status = "finished"

        for task in tasks:
            task_list.append({
                "task_id": task.task_id,
                "suffix": task.suffix,
                "status": task.status.value if hasattr(task.status, 'value') else task.status
            })

            # 判断整体状态
            if task.status in ['normal', 'unknown']:
                overall_status = "running"
            elif task.status == 'abnormal' and overall_status != "running":
                overall_status = "error"

        return {
            "plan_id": plan_id,
            "status": overall_status,
            "task_count": len(tasks),
            "tasks": task_list
        }

    async def get_task_logs(
        self,
        db: AsyncSession,
        plan_id: Optional[int] = None,
        task_id: Optional[int] = None,
        log_type: Optional[str] = None,
        log_level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        查询任务日志（从数据库）
        Args:
            db: 数据库会话
            plan_id: 推演方案ID
            task_id: 任务ID
            log_type: 日志类型
            log_level: 日志级别
            limit: 返回条数
            offset: 偏移量
        Returns:
            日志列表
        """
        # 构建查询
        query = select(TaskLog)
        conditions = []

        if plan_id:
            conditions.append(TaskLog.deduce_id == plan_id)
        if task_id:
            conditions.append(TaskLog.task_id == task_id)
        if log_type:
            conditions.append(TaskLog.type == log_type)
        if log_level:
            conditions.append(TaskLog.level == log_level)

        if conditions:
            query = query.where(and_(*conditions))

        # 排序和分页
        query = query.order_by(TaskLog.id.desc())
        query = query.limit(limit).offset(offset)

        # 执行查询
        result = await db.execute(query)
        logs = result.scalars().all()

        # 格式化返回
        return {
            "total": len(logs),
            "limit": limit,
            "offset": offset,
            "logs": [
                {
                    "id": log.id,
                    "task_id": log.task_id,
                    "suffix": log.suffix,
                    "content": log.content,
                    "type": log.type.value if hasattr(log.type, 'value') else log.type,
                    "level": log.level.value if hasattr(log.level, 'value') else log.level
                }
                for log in logs
            ]
        }

# 单例
engine_sync_service = EngineSyncService()
```

### 2.7 API路由实现

```python
# backend/app/engine/api/v1/execute.py
from fastapi import APIRouter, HTTPException
from typing import Optional, List

from backend.app.deduction.service.engine_sync_service import engine_sync_service
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
    """
    部署方案到Engine执行
    """
    try:
        result = await engine_sync_service.deploy_plan(
            db=db,
            plan_id=plan_id,
            env_instance_id=env_instance_id
        )
        return response_base.success(data=result)
    except Exception as e:
        return response_base.fail(msg=str(e))

@router.post("/stop", summary="停止方案执行")
async def stop_plan(
    db: CurrentSessionTransaction,
    plan_id: int,
    task_ids: Optional[List[int]] = None
):
    """
    停止方案执行
    """
    try:
        success = await engine_sync_service.stop_plan(
            db=db,
            plan_id=plan_id,
            task_ids=task_ids
        )
        return response_base.success(data={"success": success})
    except Exception as e:
        return response_base.fail(msg=str(e))

@router.post("/test-env", summary="测试环境连接")
async def test_environment(env_config: dict):
    """
    测试环境连接
    """
    try:
        result = await engine_client.test_environment(env_config)
        return response_base.success(data=result)
    except Exception as e:
        return response_base.fail(msg=str(e))

@router.get("/health", summary="Engine健康检查")
async def health_check():
    """
    检查Engine服务状态
    """
    is_healthy = await engine_client.health_check()
    return response_base.success(data={
        "healthy": is_healthy,
        "engine_url": engine_client.base_url
    })
```

```python
# backend/app/engine/api/v1/query.py
from fastapi import APIRouter, Query
from typing import Optional

from backend.app.deduction.service.engine_sync_service import engine_sync_service
from backend.database.db import CurrentSession
from backend.common.response.response_schema import response_base

router = APIRouter()

@router.get("/status/{plan_id}", summary="获取方案执行状态")
async def get_plan_status(
    db: CurrentSession,
    plan_id: int
):
    """
    从数据库获取方案执行状态
    """
    try:
        status = await engine_sync_service.get_plan_status(
            db=db,
            plan_id=plan_id
        )
        return response_base.success(data=status)
    except Exception as e:
        return response_base.fail(msg=str(e))

@router.get("/logs", summary="查询任务日志")
async def get_logs(
    db: CurrentSession,
    plan_id: Optional[int] = Query(None),
    task_id: Optional[int] = Query(None),
    log_type: Optional[str] = Query(None),
    log_level: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    从数据库查询任务日志
    """
    try:
        logs = await engine_sync_service.get_task_logs(
            db=db,
            plan_id=plan_id,
            task_id=task_id,
            log_type=log_type,
            log_level=log_level,
            limit=limit,
            offset=offset
        )
        return response_base.success(data=logs)
    except Exception as e:
        return response_base.fail(msg=str(e))

@router.get("/logs/latest/{plan_id}", summary="获取最新日志")
async def get_latest_logs(
    db: CurrentSession,
    plan_id: int,
    last_log_id: Optional[int] = Query(None)
):
    """
    获取最新日志，用于前端轮询更新
    """
    try:
        # 如果提供了last_log_id，只返回比它新的日志
        logs = await engine_sync_service.get_task_logs(
            db=db,
            plan_id=plan_id,
            limit=50,
            offset=0
        )

        # 过滤出新日志
        if last_log_id:
            logs['logs'] = [
                log for log in logs['logs']
                if log['id'] > last_log_id
            ]

        return response_base.success(data=logs)
    except Exception as e:
        return response_base.fail(msg=str(e))
```

### 2.8 注册路由和调度器

```python
# backend/app/engine/api/v1/router.py
from fastapi import APIRouter
from backend.app.engine.api.v1 import execute, query
from backend.core.conf import settings

v1 = APIRouter(prefix=f"{settings.FAST_API_V1_PATH}/engine", tags=["Engine交互"])

v1.include_router(execute.router, prefix="/execute")
v1.include_router(query.router, prefix="/query")
```

```python
# 在 backend/app/router.py 中添加
from backend.app.engine.api.router import v1 as engine_v1

route = APIRouter()
route.include_router(env_v1)
route.include_router(engine_v1)  # 添加Engine路由
```

```python
# 在 backend/core/registrar.py 中更新
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.app.engine.scheduler.manager import scheduler_manager
from backend.app.engine.client.mq_consumer import mq_consumer
from backend.app.engine.client.engine_client import engine_client

@asynccontextmanager
async def register_init(app: FastAPI):
    """启动初始化"""

    # 创建数据库 & 连接db
    await create_tables()

    # 启动定时任务调度器
    await scheduler_manager.start()

    yield

    # 清理资源
    await scheduler_manager.shutdown()
    await mq_consumer.close()
    await engine_client.close()
```

## 3. 现有表结构的局限性和建议

### 3.1 必要的表结构调整

由于现有表结构缺少一些关键字段，建议进行以下最小化调整：

```sql
-- 为TaskStatus表添加扩展字段（可选）
ALTER TABLE task_status
ADD COLUMN engine_task_id VARCHAR(128),
ADD COLUMN agent_id BIGINT,
ADD COLUMN progress INTEGER DEFAULT 0,
ADD COLUMN last_sync_at TIMESTAMP;

-- 为TaskLog表添加时间戳（推荐）
ALTER TABLE task_log
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN agent_id BIGINT;

-- 创建索引优化查询
CREATE INDEX idx_task_status_deduce ON task_status(deduce_id);
CREATE INDEX idx_task_log_deduce ON task_log(deduce_id);
CREATE INDEX idx_task_log_created ON task_log(created_at);
```

### 3.2 或者创建扩展表（推荐）

如果不想修改现有表，可以创建扩展表存储额外信息：

```python
# backend/app/deduction/model/task_execution_ext.py
class TaskExecutionExt(Base):
    """任务执行扩展信息表"""
    __tablename__ = "task_execution_ext"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(sa.BigInteger, unique=True, comment="关联task_status表")
    engine_task_id: Mapped[str] = mapped_column(sa.String(128), comment="Engine任务ID")
    agent_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=True)
    agent_name: Mapped[str] = mapped_column(sa.String(128), nullable=True)
    env_instance_id: Mapped[int] = mapped_column(sa.BigInteger)
    progress: Mapped[int] = mapped_column(sa.Integer, default=0)
    task_config: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    result: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True)
    last_sync_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True)
```

## 4. 配置文件更新

```python
# backend/core/conf.py 添加
class Settings(BaseSettings):
    # ... 现有配置

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
    LOG_RETENTION_DAYS: int = 30            # 日志保留天数
```

## 5. 依赖包更新

```toml
# pyproject.toml
dependencies = [
    # ... 现有依赖
    "httpx>=0.24.0",        # HTTP客户端
    "aio-pika>=9.0.0",      # RabbitMQ客户端
    # apscheduler 已经在现有依赖中
]
```

## 6. 实现总结

基于现有的 `TaskStatus` 和 `TaskLog` 表，我们可以：

1. **直接使用现有表**：通过映射和适配层处理字段差异
2. **最小化调整**：只添加必要的字段（如engine_task_id、progress等）
3. **创建扩展表**：保持现有表不变，用扩展表存储额外信息

推荐采用第3种方案，既不破坏现有结构，又能满足新需求。

## 7. 下一步行动

1. 确认是否可以修改现有表结构
2. 如果不能修改，实现扩展表方案
3. 部署定时任务调度器
4. 实现Engine客户端和RabbitMQ消费者
5. 测试端到端流程