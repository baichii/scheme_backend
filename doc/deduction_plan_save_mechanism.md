# 推演方案保存机制改进方案

## 问题分析

当前存在的问题：
1. `create` 接口没有返回创建的方案ID
2. 前端无法知道创建的方案ID，导致后续保存会创建新方案
3. 缺少 `update` 接口来更新已存在的方案
4. 没有"草稿"和"正式保存"的区分

## 解决方案

### 方案一：创建时返回ID + 添加更新接口（推荐）

#### 1. 修改 create 接口返回ID

```python
# backend/app/deduction/api/v1/deduction_plan.py

@router.post("/create", summary="创建推演方案配置")
async def create_deduction_plan(
    db: CurrentSessionTransaction,
    param: CreateDeductionPlanParam
) -> ResponseSchemaModel[GetDeductionPlanParam]:  # 返回创建的方案
    """创建推演方案配置"""
    deduction_plan = await deduction_plan_service.create(db=db, obj=param)
    return response_base.success(data=deduction_plan)
```

```python
# backend/app/deduction/service/deduction_plan_service.py

@staticmethod
async def create(*, db: AsyncSession, obj: CreateDeductionPlanParam) -> DeductionPlan:
    """创建推理方案"""

    unique_id = snowflake.generate()
    obj_internal = CreateDeductionPlanInternal(
        id=unique_id,
        **obj.model_dump(),
        status=DeductionPlanStatus.INACTIVE,
    )
    deduction_plan = await deduction_plan_dao.create(db, obj_internal)

    # 返回创建的对象
    return await deduction_plan_dao.get(db, unique_id)
```

#### 2. 添加 update 接口

```python
# backend/app/deduction/schema/deduction_plan.py

class UpdateDeductionPlanParam(SchemaBase):
    """更新推演方案参数"""
    id: int = Field(description="推演方案ID")
    name: str | None = Field(None, description="推理方案名称")
    description: str | None = Field(None, description="推理方案描述")
    task_config: dict | None = Field(None, description="推演方案配置")
```

```python
# backend/app/deduction/api/v1/deduction_plan.py

@router.put("/update", summary="更新推演方案配置")
async def update_deduction_plan(
    db: CurrentSessionTransaction,
    param: UpdateDeductionPlanParam
) -> ResponseSchemaModel[GetDeductionPlanParam]:
    """更新推演方案配置"""
    deduction_plan = await deduction_plan_service.update(db=db, obj=param)
    return response_base.success(data=deduction_plan)
```

```python
# backend/app/deduction/service/deduction_plan_service.py

@staticmethod
async def update(*, db: AsyncSession, obj: UpdateDeductionPlanParam) -> DeductionPlan:
    """更新推理方案"""
    # 检查是否存在
    existing = await deduction_plan_dao.get(db, obj.id)
    if not existing:
        raise errors.NotFoundError(msg="推理方案不存在")

    # 只更新提供的字段
    update_data = obj.model_dump(exclude_unset=True, exclude={'id'})
    if update_data:
        await deduction_plan_dao.update(db, obj.id, update_data)

    # 返回更新后的对象
    return await deduction_plan_dao.get(db, obj.id)
```

#### 3. 前端使用流程

```javascript
// 前端伪代码
let planId = null;

// 第一次保存
async function savePlan(planData) {
    if (!planId) {
        // 创建新方案
        const response = await api.post('/deduction-plan/create', planData);
        planId = response.data.id;  // 保存返回的ID
    } else {
        // 更新已存在的方案
        await api.put('/deduction-plan/update', {
            id: planId,
            ...planData
        });
    }
}

// 用户操作流程
// 1. 创建方案，填写名称
savePlan({ name: '测试方案', description: '...', task_config: {} });
// 返回: { id: 123456, name: '测试方案', ... }

// 2. 添加第一个智能体
savePlan({
    id: 123456,
    task_config: { agents: [{ agent_id: 1, ... }] }
});

// 3. 添加第二个智能体
savePlan({
    id: 123456,
    task_config: { agents: [{ agent_id: 1, ... }, { agent_id: 2, ... }] }
});
```

### 方案二：统一的 save 接口（创建或更新）

```python
# backend/app/deduction/api/v1/deduction_plan.py

@router.post("/save", summary="保存推演方案（创建或更新）")
async def save_deduction_plan(
    db: CurrentSessionTransaction,
    param: SaveDeductionPlanParam
) -> ResponseSchemaModel[GetDeductionPlanParam]:
    """
    保存推演方案
    - 如果没有ID，创建新方案
    - 如果有ID，更新现有方案
    """
    deduction_plan = await deduction_plan_service.save(db=db, obj=param)
    return response_base.success(data=deduction_plan)
```

```python
# backend/app/deduction/schema/deduction_plan.py

class SaveDeductionPlanParam(SchemaBase):
    """保存推演方案参数"""
    id: int | None = Field(None, description="推演方案ID，为空时创建新方案")
    name: str = Field(description="推理方案名称")
    description: str | None = Field(None, description="推理方案描述")
    task_config: dict = Field(default_factory=dict, description="推演方案配置")
```

```python
# backend/app/deduction/service/deduction_plan_service.py

@staticmethod
async def save(*, db: AsyncSession, obj: SaveDeductionPlanParam) -> DeductionPlan:
    """保存推理方案（创建或更新）"""

    if obj.id:
        # 更新现有方案
        existing = await deduction_plan_dao.get(db, obj.id)
        if not existing:
            raise errors.NotFoundError(msg="推理方案不存在")

        update_data = obj.model_dump(exclude={'id'}, exclude_unset=True)
        await deduction_plan_dao.update(db, obj.id, update_data)
        return await deduction_plan_dao.get(db, obj.id)
    else:
        # 创建新方案
        unique_id = snowflake.generate()
        obj_internal = CreateDeductionPlanInternal(
            id=unique_id,
            **obj.model_dump(exclude={'id'}),
            status=DeductionPlanStatus.INACTIVE,
        )
        await deduction_plan_dao.create(db, obj_internal)
        return await deduction_plan_dao.get(db, unique_id)
```

### 方案三：自动保存草稿机制

```python
# backend/app/deduction/model/deduction_plan.py
# 添加草稿字段

class DeductionPlan(Base):
    """推演方案配置模型"""

    __tablename__ = "deduction_plan"

    id: Mapped[snowflake_id_key] = mapped_column(comment="推演方案ID")
    name: Mapped[str] = mapped_column(sa.String(128), unique=True, comment="推理方案名称")
    description: Mapped[str | None] = mapped_column(sa.String(512), nullable=True, comment="推理方案描述")
    status: Mapped[str] = mapped_column(sa.String(32), comment="推理方案状态")
    task_config: Mapped[dict] = mapped_column(sa.JSON, comment="推演方案参数")

    # 新增字段
    is_draft: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment="是否为草稿")
    auto_save_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True, comment="自动保存时间")
    published_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True, comment="发布时间")
```

```python
# backend/app/deduction/api/v1/deduction_plan.py

@router.post("/auto-save", summary="自动保存草稿")
async def auto_save_draft(
    db: CurrentSessionTransaction,
    param: AutoSaveParam
) -> ResponseSchemaModel[dict]:
    """
    自动保存草稿
    - 如果没有ID，创建草稿
    - 如果有ID，更新草稿
    """
    draft_id = await deduction_plan_service.auto_save(db=db, obj=param)
    return response_base.success(data={"id": draft_id, "saved_at": datetime.now()})

@router.post("/publish/{plan_id}", summary="发布方案")
async def publish_plan(
    db: CurrentSessionTransaction,
    plan_id: int
) -> ResponseModel:
    """将草稿发布为正式方案"""
    await deduction_plan_service.publish(db=db, plan_id=plan_id)
    return response_base.success()
```

## 实现建议

### 1. 立即修改（最小改动）

仅修改 create 接口返回值：

```python
# backend/app/deduction/api/v1/deduction_plan.py
# 修改第26-29行

@router.post("/create", summary="创建推演方案配置")
async def create_deduction_plan(
    db: CurrentSessionTransaction,
    param: CreateDeductionPlanParam
) -> ResponseSchemaModel[dict]:  # 改为返回包含ID的字典
    """创建推演方案配置"""
    plan_id = await deduction_plan_service.create_and_return_id(db=db, obj=param)
    return response_base.success(data={"id": plan_id})
```

```python
# backend/app/deduction/service/deduction_plan_service.py
# 添加新方法

@staticmethod
async def create_and_return_id(*, db: AsyncSession, obj: CreateDeductionPlanParam) -> int:
    """创建推理方案并返回ID"""

    unique_id = snowflake.generate()
    obj_internal = CreateDeductionPlanInternal(
        id=unique_id,
        **obj.model_dump(),
        status=DeductionPlanStatus.INACTIVE,
    )
    await deduction_plan_dao.create(db, obj_internal)
    return unique_id
```

### 2. 完整方案（推荐）

实现方案一：
- 修改 create 接口返回完整对象
- 添加 update 接口
- 前端保存第一次获得的ID

### 3. 前端适配

```typescript
// 前端 TypeScript 示例
interface DeductionPlan {
    id?: number;
    name: string;
    description?: string;
    task_config: {
        agents: Agent[];
    };
}

class PlanEditor {
    private planId: number | null = null;

    async save(plan: DeductionPlan): Promise<void> {
        if (this.planId) {
            // 更新
            await api.put('/deduction-plan/update', {
                ...plan,
                id: this.planId
            });
        } else {
            // 创建
            const response = await api.post('/deduction-plan/create', plan);
            this.planId = response.data.id;
        }
    }

    addAgent(agent: Agent): void {
        // 添加智能体到当前方案
        this.currentPlan.task_config.agents.push(agent);
        // 自动保存
        this.save(this.currentPlan);
    }
}
```

## 数据库兼容性

这些改动不需要修改数据库结构，完全向后兼容。

## 总结

推荐采用**方案一**：
1. 最小改动，风险低
2. 符合RESTful设计原则
3. 前后端职责清晰
4. 易于理解和维护

需要修改的文件：
1. `deduction_plan.py` (API层) - 修改返回值，添加update接口
2. `deduction_plan_service.py` (Service层) - 修改create返回值，添加update方法
3. `deduction_plan.py` (Schema层) - 添加UpdateDeductionPlanParam
4. `crud_deduction_plan.py` (CRUD层) - 添加update方法（如果还没有）