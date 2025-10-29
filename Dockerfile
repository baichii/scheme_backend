FROM python:3.13-slim AS builder
WORKDIR /app

# 配置清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install uv

# 只复制依赖文件
COPY pyproject.toml ./

RUN uv pip install --system --no-cache-dir  \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple


# 运行阶段 \
FROM python:3.13-slim
WORKDIR /app

