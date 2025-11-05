# 🚀 快速开始指南

## 一键启动测试

```bash
# 1. 进入项目目录
cd /Users/jiangzhenjie/Documents/Github/scheme_backend

# 2. 创建测试智能体 ZIP 文件
python local/agent/create_test_agent.py

# 3. 启动测试平台（会自动启动 Docker 服务）
python local/agent/start.py
```

访问: http://localhost:7860

## 手动启动（不使用 Docker）

如果你已有 MinIO 和 PostgreSQL 服务，可以直接启动：

```bash
python local/agent/gradio_test.py
```

## 测试流程

### 1. 生成测试文件

```bash
python local/agent/create_test_agent.py
```

这将生成 `test_agent.zip` 文件。

### 2. 上传测试

1. 打开浏览器访问 http://localhost:7860
2. 进入 "📤 上传智能体" 标签页
3. 填写表单：
   - 选择文件: `test_agent.zip`
   - 智能体名称: `测试智能体1`
   - 智能体描述: `这是一个测试的智能体`
   - 智能体文件名: `agent.py`
   - 阵营: `red`
   - 参数声明: `{"timeout": 30, "max_steps": 1000}`
   - 支持的环境模板: `1001,1002`
4. 点击 "🚀 上传"

### 3. 查询测试

1. 进入 "📋 查询智能体" 标签页
2. 点击 "🔍 查询所有智能体"
3. 查看上传的智能体列表

### 4. 详情测试

1. 进入 "🔍 查看详情" 标签页
2. 输入智能体 ID（从查询结果获取）
3. 点击 "📄 查看详情"

### 5. 删除测试

1. 进入 "🗑️ 删除智能体" 标签页
2. 输入智能体 ID
3. 点击 "🗑️ 删除"

## 故障排查

### 问题 1: 导入错误

```bash
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**:
```bash
pip install gradio minio sqlalchemy[asyncio] asyncpg
```

### 问题 2: 数据库连接失败

```bash
could not connect to server
```

**解决方案**:
1. 检查 PostgreSQL 是否运行: `docker ps | grep postgres`
2. 检查 `backend/database.py` 中的连接配置
3. 确保数据库已创建: `scheme_db`

### 问题 3: MinIO 连接失败

```bash
Connection refused
```

**解决方案**:
1. 检查 MinIO 是否运行: `docker ps | grep minio`
2. 检查 `.env` 文件配置
3. 访问 http://localhost:9001 验证 MinIO 控制台

### 问题 4: 端口被占用

```bash
Address already in use
```

**解决方案**: 修改 `gradio_test.py` 中的端口：
```python
demo.launch(server_port=8888)  # 改为其他端口
```

## 配置说明

### 数据库配置 (backend/database.py)

```python
DATABASE_URL = "postgresql+asyncpg://user:password@host:port/dbname"
```

### MinIO 配置 (.env)

```env
AGENT_MINIO_HOST=localhost
AGENT_MINIO_PORT=9000
AGENT_MINIO_USER=admin
AGENT_MINIO_PASSWORD=admin
AGENT_BUCKET=agent
```

## Docker 命令速查

```bash
# 启动 MinIO
docker start minio

# 停止 MinIO
docker stop minio

# 删除 MinIO 容器
docker rm minio

# 启动 PostgreSQL
docker start postgres

# 停止 PostgreSQL
docker stop postgres

# 查看日志
docker logs minio
docker logs postgres
```

## 生产环境部署建议

1. **数据库**: 使用独立的 PostgreSQL 服务器
2. **MinIO**: 配置持久化存储和 SSL
3. **认证**: 添加用户认证和权限控制
4. **监控**: 添加日志和监控
5. **备份**: 定期备份数据库和 MinIO 数据

## 更多信息

详细文档请查看: [README.md](README.md)
