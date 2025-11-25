# scheme backend


## 简介

 基于[fastapi](https://github.com/fastapi/fastapi)实现的scheme-backend



## 本地部署

1. 安装uv

2. 创建环境

   ```
   uv sync
   
   source .venv/bin/activate
   ```

3. 配置.env文件

   ```
   cd /backend
   
   # 生成本地.env文件
   cp .env.example .env
   ```

4. 启动容器依赖环境

   ```
   # 启动依赖容器
   docker compose up -d
   
   # 关闭依赖容器
   docker compose down -v
   ```

5. 服务启动

   ```
   PYTHONPATH=. fastapi dev backend/main.py
   ```



## todo

1. 功能测试、验证

   + 模块级，pytest
   + 联合调试，模拟matrix后端

2. 设计持续获取engine rabbitmq中的数据方案

   暂定队列订阅



## 参考
- [fastapi_tortoise_mysql](https://github.com/fastapi-practices/fastapi_tortoise_mysql/tree/master])

+ [fastapi_best_architecture](https://github.com/fastapi-practices/fastapi_best_architecture/tree/master)