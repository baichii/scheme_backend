from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, snowflake_id_key

ACTIVE_RUN_SQL = "status IN ('starting', 'running', 'stopping')"


class DeductionRun(Base):
    """推演的一次不可变输入快照及其运行状态。"""

    __tablename__ = "deduction_run"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('starting', 'running', 'stopping', 'finished', 'failed', 'stopped')",
            name="ck_deduction_run_status",
        ),
        sa.Index(
            "uq_deduction_run_active",
            "deduction_id",
            unique=True,
            postgresql_where=sa.text(ACTIVE_RUN_SQL),
            sqlite_where=sa.text(ACTIVE_RUN_SQL),
        ),
        {"comment": "推演运行及其输入快照。"},
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, comment="推演运行 ID")
    deduction_id: Mapped[int] = mapped_column(
        sa.ForeignKey("deduction.id", ondelete="CASCADE"), index=True, comment="推演定义 ID"
    )
    status: Mapped[str] = mapped_column(sa.String(16), index=True, comment="运行状态")
    environment_resource_id: Mapped[int] = mapped_column(sa.BigInteger, comment="环境资源 ID 快照引用")
    environment_name: Mapped[str] = mapped_column(sa.String(80), comment="环境名称快照")
    environment_snapshot: Mapped[dict] = mapped_column(sa.JSON, comment="环境连接配置快照")
    environment_runtime: Mapped[dict] = mapped_column(sa.JSON, comment="环境健康状态")
    branches: Mapped[list] = mapped_column(sa.JSON, comment="分支执行快照")
    engine_request: Mapped[dict] = mapped_column(sa.JSON, comment="已编译 Matrix create 请求")
    sim_time: Mapped[str] = mapped_column(sa.String(64), comment="当前仿真时间")
    started_at: Mapped[datetime] = mapped_column(TimeZone, comment="启动时间")
    sequence: Mapped[int] = mapped_column(sa.BigInteger, default=0, comment="最新 Runtime sequence")
    engine_cursor: Mapped[int] = mapped_column(sa.BigInteger, default=0, comment="Engine 消息游标")
    failure_reason: Mapped[str | None] = mapped_column(sa.String(500), default=None, comment="失败原因")
    ended_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment="结束时间")


class DeductionTask(Base):
    """推演运行中映射到 Matrix 的任务。"""

    __tablename__ = "deduction_task"
    __table_args__ = (
        sa.CheckConstraint("kind IN ('container', 'agent')", name="ck_deduction_task_kind"),
        sa.CheckConstraint(
            "status IN ('READY', 'PENDING', 'RUNNING', 'STOPPING', 'END', 'ERROR')",
            name="ck_deduction_task_status",
        ),
        {"comment": "推演运行中的 Matrix 任务。"},
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, comment="Matrix Task ID")
    run_id: Mapped[int] = mapped_column(
        sa.ForeignKey("deduction_run.id", ondelete="CASCADE"), index=True, comment="推演运行 ID"
    )
    kind: Mapped[str] = mapped_column(sa.String(16), comment="container/agent")
    branch_node_id: Mapped[str] = mapped_column(sa.String(128), index=True, comment="推演分支节点 ID")
    branch_scheme_id: Mapped[int] = mapped_column(sa.BigInteger, comment="分支方案 ID")
    branch_scheme_name: Mapped[str] = mapped_column(sa.String(80), comment="分支方案名称快照")
    name: Mapped[str] = mapped_column(sa.String(80), comment="任务名称")
    dependency_ids: Mapped[list] = mapped_column(sa.JSON, comment="依赖任务 ID")
    status: Mapped[str] = mapped_column(sa.String(16), index=True, comment="Matrix 状态")
    parent_task_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment="容器任务 ID")
    source_node_id: Mapped[str | None] = mapped_column(
        sa.String(128), default=None, comment="分支图节点 ID"
    )
    agent_resource_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, default=None, comment="智能体资源 ID"
    )
    agent_version_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, default=None, comment="智能体版本 ID"
    )
    agent_revision_number: Mapped[int | None] = mapped_column(
        sa.Integer, default=None, comment="平台修订号"
    )
    agent_checksum: Mapped[str | None] = mapped_column(
        sa.String(64), default=None, comment="智能体 checksum"
    )
    agent_name: Mapped[str | None] = mapped_column(sa.String(80), default=None, comment="智能体名称快照")
    agent_parameters: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment="实际运行参数")
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment="开始运行时间")
    ended_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment="任务结束时间")


class DeductionRuntimeMessage(Base):
    """可回放的推演运行增量消息。"""

    __tablename__ = "deduction_runtime_message"
    __table_args__ = (
        sa.UniqueConstraint("run_id", "sequence", name="uq_runtime_message_sequence"),
        sa.Index("ix_runtime_message_run_type_sequence", "run_id", "type", "sequence"),
        sa.Index("ix_runtime_message_run_task_sequence", "run_id", "task_id", "sequence"),
        {"comment": "推演运行 SSE 与历史查询的持久化消息。"},
    )

    id: Mapped[snowflake_id_key] = mapped_column(init=False, comment="消息 ID")
    run_id: Mapped[int] = mapped_column(
        sa.ForeignKey("deduction_run.id", ondelete="CASCADE"), index=True, comment="推演运行 ID"
    )
    sequence: Mapped[int] = mapped_column(sa.BigInteger, comment="Run 内严格递增序号")
    type: Mapped[str] = mapped_column(sa.String(16), comment="消息类型")
    payload: Mapped[dict] = mapped_column(sa.JSON, comment="Frontend Runtime 消息")
    emitted_at: Mapped[datetime] = mapped_column(TimeZone, comment="消息产生时间")
    task_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, index=True, comment="任务 ID")
    branch_node_id: Mapped[str | None] = mapped_column(
        sa.String(128), default=None, index=True, comment="分支节点 ID"
    )
