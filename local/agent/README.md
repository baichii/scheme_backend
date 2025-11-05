# 智能体上传测试工具

基于 Gradio 的智能体上传测试界面，提供可视化的上传、查询和管理功能。

## 功能特性

- 📤 **智能体上传**: 上传 ZIP 格式的智能体文件
- 📋 **智能体查询**: 查看所有已上传的智能体列表
- 🔍 **详情查看**: 查看单个智能体的详细信息
- 🗑️ **智能体删除**: 删除指定的智能体

## 安装依赖

```bash
pip install gradio
pip install sqlalchemy[asyncio]
pip install asyncpg  # PostgreSQL 驱动
pip install minio
```

## 配置数据库

编辑 `backend/database.py` 中的数据库连接配置：

```python
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/dbname"
```

## 配置 MinIO

在项目根目录创建 `.env` 文件，配置 MinIO 连接信息：

```env
AGENT_MINIO_HOST=localhost
AGENT_MINIO_PORT=9000
AGENT_MINIO_USER=admin
AGENT_MINIO_PASSWORD=admin
AGENT_BUCKET=agent
```

## 启动服务

### 1. 启动 MinIO（使用 Docker）

```bash
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=admin" \
  minio/minio server /data --console-address ":9001"
```

访问 MinIO 控制台: http://localhost:9001

### 2. 启动数据库（使用 Docker）

```bash
docker run -d \
  -p 5432:5432 \
  --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=scheme_db \
  postgres:latest
```

### 3. 启动 Gradio 测试界面

```bash
cd /path/to/scheme_backend
python local/agent/gradio_test.py
```

界面将在 http://localhost:7860 启动。

## 使用指南

### 上传智能体

1. 选择 "📤 上传智能体" 标签页
2. 点击 "选择 ZIP 文件" 上传 ZIP 文件
3. 填写必填字段：
   - **智能体名称**: 唯一标识，不能重复
   - **智能体描述**: 简短描述
   - **智能体文件名**: ZIP 中的主文件名（如 `agent.py`）
4. 填写可选字段：
   - **阵营**: 如 `red`、`blue`
   - **参数声明**: JSON 格式，如 `{"timeout": 30}`
   - **支持的环境模板**: 逗号分隔的数字，如 `1001,1002`
5. 点击 "🚀 上传" 按钮

### 查询智能体

1. 选择 "📋 查询智能体" 标签页
2. 点击 "🔍 查询所有智能体" 按钮
3. 查看所有智能体的列表信息

### 查看详情

1. 选择 "🔍 查看详情" 标签页
2. 输入智能体 ID
3. 点击 "📄 查看详情" 按钮
4. 查看智能体的完整信息

### 删除智能体

1. 选择 "🗑️ 删除智能体" 标签页
2. 输入要删除的智能体 ID
3. 点击 "🗑️ 删除" 按钮
4. ⚠️ 注意：删除操作不可恢复

## 创建测试用 ZIP 文件

可以使用 `create_test_agent.py` 脚本快速创建测试用的智能体 ZIP 文件：

```bash
python local/agent/create_test_agent.py
```

这将在当前目录生成 `test_agent.zip` 文件。

## 故障排查

### 连接数据库失败

- 检查数据库是否启动: `docker ps`
- 检查数据库连接配置是否正确
- 确认数据库用户名和密码

### MinIO 上传失败

- 检查 MinIO 是否启动
- 检查 `.env` 文件中的配置
- 访问 MinIO 控制台验证连接

### 端口被占用

如果 7860 端口被占用，可以修改 `gradio_test.py` 中的端口号：

```python
demo.launch(
    server_port=8888,  # 修改为其他端口
    ...
)
```

## 项目结构

```
scheme_backend/
├── backend/
│   ├── app/agent/
│   │   ├── model/agent.py          # 数据模型
│   │   ├── schema/agent_meta.py    # Schema 定义
│   │   ├── crud/crud_agent.py      # 数据库操作
│   │   ├── services/agent_service.py # 业务逻辑
│   │   └── api/v1/upload.py        # API 路由
│   ├── database.py                  # 数据库配置
│   └── utils/upload.py             # MinIO 上传工具
└── local/agent/
    ├── gradio_test.py              # Gradio 测试界面
    ├── create_test_agent.py        # 测试文件生成脚本
    └── README.md                   # 本文档
```

## API 文档

如果需要通过 API 而非界面进行测试，参考以下端点：

### 上传智能体

```bash
POST /agent/upload
Content-Type: multipart/form-data

file: <zip文件>
metadata: {
  "agent_name": "测试智能体",
  "agent_desc": "描述",
  "side": "red",
  "params_schema": {},
  "supported_env_templates": [1001],
  "agent_file": "agent.py"
}
```

### 查询智能体

```bash
GET /agents
```

### 获取详情

```bash
GET /agent/{agent_id}
```

### 删除智能体

```bash
DELETE /agent/{agent_id}
```

## 许可证

MIT
