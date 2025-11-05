#!/usr/bin/env python3
"""
快速启动脚本

自动检查并启动所需服务和测试界面
"""
import subprocess
import sys
import time
from pathlib import Path


def check_docker():
    """检查 Docker 是否安装"""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_container(name):
    """检查容器是否运行"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        return name in result.stdout
    except subprocess.CalledProcessError:
        return False


def start_minio():
    """启动 MinIO 容器"""
    print("🚀 启动 MinIO...")
    try:
        subprocess.run([
            "docker", "run", "-d",
            "-p", "9000:9000",
            "-p", "9001:9001",
            "--name", "minio",
            "-e", "MINIO_ROOT_USER=admin",
            "-e", "MINIO_ROOT_PASSWORD=admin",
            "minio/minio", "server", "/data", "--console-address", ":9001"
        ], check=True)
        print("✅ MinIO 启动成功")
        print("   控制台: http://localhost:9001")
        print("   用户名: admin")
        print("   密码: admin")
        time.sleep(3)  # 等待启动
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ MinIO 启动失败: {e}")
        return False


def start_postgres():
    """启动 PostgreSQL 容器"""
    print("🚀 启动 PostgreSQL...")
    try:
        subprocess.run([
            "docker", "run", "-d",
            "-p", "5432:5432",
            "--name", "postgres",
            "-e", "POSTGRES_PASSWORD=postgres",
            "-e", "POSTGRES_DB=scheme_db",
            "postgres:latest"
        ], check=True)
        print("✅ PostgreSQL 启动成功")
        time.sleep(5)  # 等待启动
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ PostgreSQL 启动失败: {e}")
        return False


def start_gradio():
    """启动 Gradio 测试界面"""
    print("🚀 启动 Gradio 测试界面...")
    script_path = Path(__file__).parent / "gradio_test.py"

    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
    except KeyboardInterrupt:
        print("\n👋 测试界面已关闭")
    except subprocess.CalledProcessError as e:
        print(f"❌ Gradio 启动失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 智能体测试平台启动脚本")
    print("=" * 60)

    # 1. 检查 Docker
    if not check_docker():
        print("❌ 未检测到 Docker，请先安装 Docker")
        print("   下载地址: https://www.docker.com/get-started")
        return

    # 2. 检查并启动 MinIO
    if check_container("minio"):
        print("✅ MinIO 已在运行")
    else:
        if not start_minio():
            print("⚠️  MinIO 启动失败，请手动启动")

    # 3. 检查并启动 PostgreSQL
    if check_container("postgres"):
        print("✅ PostgreSQL 已在运行")
    else:
        if not start_postgres():
            print("⚠️  PostgreSQL 启动失败，请手动启动")

    print("\n" + "=" * 60)
    print("✅ 所有服务已就绪")
    print("=" * 60)

    # 4. 启动 Gradio
    start_gradio()


if __name__ == "__main__":
    main()
