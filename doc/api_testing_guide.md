# 后端 API 测试指南

## 📋 测试方案对比

| 方案 | 批量测试 | 可复用 | 报告 | 学习成本 | 推荐度 |
|------|---------|--------|------|---------|--------|
| **Pytest** | ✅ | ✅ | ✅ | 低 | ⭐⭐⭐⭐⭐ |
| Postman | ❌ | 部分 | ✅ | 低 | ⭐⭐⭐ |
| Swagger UI | ❌ | ❌ | ❌ | 很低 | ⭐⭐ |
| Python脚本 | ✅ | ✅ | ❌ | 中 | ⭐⭐⭐⭐ |
| Gradio界面 | ❌ | ❌ | ❌ | 高 | ⭐⭐ |

## 🎯 推荐：Pytest + httpx

### 为什么选择 Pytest？

1. **批量测试** - 参数化测试，一次测试多组数据
2. **可复用** - 测试用例可保存、版本管理
3. **详细报告** - 自动生成测试报告，支持多种格式
4. **CI/CD** - 可集成到持续集成流程
5. **Fixtures** - 测试数据管理，自动清理
6. **断言丰富** - 各种断言方式，错误信息清晰

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install pytest httpx pytest-html
```

### 2. 运行测试

```bash
# 运行所有测试
pytest backend/tests/test_env_api.py -v

# 运行特定测试类
pytest backend/tests/test_env_api.py::TestEnvTemplate -v

# 运行特定测试
pytest backend/tests/test_env_api.py::TestEnvTemplate::test_create_template -v

# 显示打印输出
pytest backend/tests/test_env_api.py -v -s

# 生成 HTML 报告
pytest backend/tests/test_env_api.py -v --html=report.html --self-contained-html

# 失败时立即停止
pytest backend/tests/test_env_api.py -v -x

# 重新运行失败的测试
pytest backend/tests/test_env_api.py -v --lf

# 并行运行（需要 pytest-xdist）
pytest backend/tests/test_env_api.py -v -n auto
```

### 3. 查看测试报告

测试完成后会显示详细的测试结果：

```
================================ test session starts =================================
collected 15 items

backend/tests/test_env_api.py::TestEnvTemplate::test_create_template PASSED    [  6%]
backend/tests/test_env_api.py::TestEnvTemplate::test_get_all_templates PASSED  [ 13%]
backend/tests/test_env_api.py::TestEnvTemplate::test_delete_template PASSED    [ 20%]
...

================================ 15 passed in 5.42s ==================================
```

## 📝 测试脚本说明

### 测试文件结构

```
backend/tests/test_env_api.py
├── Fixtures（测试数据和清理）
│   ├── client - HTTP 客户端
│   ├── clean_templates - 清理模版
│   ├── clean_instances - 清理实例
│   ├── sample_template_data - 示例模版数据
│   └── sample_instance_data - 示例实例数据
│
├── TestEnvTemplate（环境模版测试）
│   ├── test_create_template - 创建模版
│   ├── test_get_all_templates - 获取所有模版
│   ├── test_get_template_by_id - 根据ID获取
│   ├── test_get_template_by_name - 根据名称获取
│   ├── test_delete_template - 删除模版
│   └── test_create_multiple_templates - 批量创建（参数化）
│
├── TestEnvInstance（环境实例测试）
│   ├── test_create_instance - 创建实例
│   ├── test_get_all_instances - 获取所有实例
│   ├── test_get_instance_by_id - 根据ID获取
│   ├── test_get_instance_by_template_id - 根据模版ID获取
│   ├── test_delete_instance - 删除实例
│   └── test_create_multiple_instances - 批量创建（参数化）
│
├── TestCompleteFlow（完整流程测试）
│   └── test_full_workflow - 测试完整业务流程
│
└── TestPerformance（性能测试）
    ├── test_batch_create_templates - 批量创建模版性能
    └── test_batch_create_instances - 批量创建实例性能
```

### 核心功能

#### 1. 参数化测试

```python
@pytest.mark.parametrize("instance_name,ip,port", [
    ("环境1", "192.168.1.100", 8080),
    ("环境2", "192.168.1.101", 8081),
    ("环境3", "192.168.1.102", 8082),
])
def test_create_multiple_instances(self, client, template_id, instance_name, ip, port):
    """一次运行测试多组数据"""
    # 测试逻辑
```

#### 2. Fixtures（自动清理）

```python
@pytest.fixture(scope="function")
def clean_templates(client):
    """每个测试后自动清理"""
    yield
    client.delete(f"{API_V1}/env/template/all")
```

#### 3. 完整流程测试

```python
def test_full_workflow(self, client):
    """测试完整业务流程"""
    # 1. 创建模版
    # 2. 获取模版
    # 3. 创建实例
    # 4. 查询实例
    # 5. 删除实例
    # 6. 验证结果
```

#### 4. 性能测试

```python
def test_batch_create_templates(self, client):
    """测试批量创建100个模版的性能"""
    import time
    start_time = time.time()
    # 批量创建
    elapsed = time.time() - start_time
    print(f"总耗时: {elapsed:.2f}秒")
```

## 💡 实用技巧

### 1. 只运行特定标记的测试

```python
# 添加标记
@pytest.mark.slow
def test_large_dataset():
    pass

@pytest.mark.fast
def test_simple_case():
    pass
```

```bash
# 只运行快速测试
pytest -v -m fast

# 跳过慢速测试
pytest -v -m "not slow"
```

### 2. 使用 conftest.py 共享 Fixtures

创建 `backend/tests/conftest.py`：

```python
import pytest
import httpx

@pytest.fixture(scope="session")
def api_client():
    """全局共享的 HTTP 客户端"""
    return httpx.Client(base_url="http://localhost:8000", timeout=30.0)
```

### 3. 生成测试数据

```python
@pytest.fixture
def generate_templates(client):
    """生成测试用的模版"""
    templates = []
    for i in range(10):
        data = {...}
        resp = client.post("/api/v1/env/template/create", json=data)
        templates.append(resp.json()["data"])
    return templates
```

### 4. 数据驱动测试

```python
# 从文件读取测试数据
import json

with open("test_data.json") as f:
    test_data = json.load(f)

@pytest.mark.parametrize("data", test_data)
def test_with_data(client, data):
    response = client.post("/api/endpoint", json=data)
    assert response.status_code == 200
```

## 📊 生成测试报告

### HTML 报告

```bash
# 生成 HTML 报告
pytest backend/tests/test_env_api.py --html=test_report.html --self-contained-html

# 在浏览器中打开
open test_report.html
```

### JUnit XML（用于 CI/CD）

```bash
pytest backend/tests/test_env_api.py --junitxml=test_report.xml
```

### Coverage 报告

```bash
# 安装 pytest-cov
pip install pytest-cov

# 生成覆盖率报告
pytest backend/tests/ --cov=backend --cov-report=html

# 查看报告
open htmlcov/index.html
```

## 🔄 与其他工具结合

### 1. 与 Postman 结合

- 用 Postman 进行快速手动测试
- 用 Pytest 进行自动化批量测试

### 2. 与 Swagger UI 结合

- 用 Swagger UI 查看 API 文档
- 用 Pytest 进行完整测试

### 3. 与 CI/CD 结合

```yaml
# GitHub Actions 示例
name: API Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest backend/tests/ -v --junitxml=test-results.xml
```

## 📖 扩展阅读

### 更多测试场景

```python
# 1. 测试错误场景
def test_create_template_with_invalid_data(client):
    """测试使用无效数据创建模版"""
    response = client.post("/api/v1/env/template/create", json={})
    assert response.status_code == 422  # 验证错误

# 2. 测试并发
import asyncio
async def test_concurrent_requests(client):
    """测试并发请求"""
    tasks = [create_template(i) for i in range(100)]
    await asyncio.gather(*tasks)

# 3. 测试数据库状态
def test_database_state(client, db_session):
    """直接验证数据库状态"""
    # 创建数据
    # 查询数据库
    # 验证结果
```

## 🎯 最佳实践

1. **测试隔离** - 每个测试独立，使用 fixtures 清理数据
2. **命名清晰** - 测试名称要表达测试意图
3. **单一职责** - 每个测试只测一个功能点
4. **参数化** - 使用参数化测试多组数据
5. **快速反馈** - 保持测试运行快速
6. **持续集成** - 将测试集成到 CI/CD 流程

## 💪 总结

使用 Pytest 进行后端测试的优势：

- ✅ **高效** - 批量测试，一次运行多个场景
- ✅ **可靠** - 自动化测试，减少人为错误
- ✅ **可复用** - 测试用例可保存和共享
- ✅ **专业** - 业界标准，功能强大
- ✅ **省时** - 比手动测试或写界面快得多

建议：
- **开发阶段** - 用 Pytest 进行自动化测试
- **快速验证** - 用 Swagger UI 手动测试
- **演示展示** - 用 Gradio 界面展示功能
