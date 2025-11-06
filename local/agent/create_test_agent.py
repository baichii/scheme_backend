"""
创建测试用的智能体 ZIP 文件

生成一个包含示例智能体代码的 ZIP 文件，用于测试上传功能
"""
import json
import zipfile
from pathlib import Path


def create_test_agent():
    """创建测试用的智能体 ZIP 文件"""

    # 创建临时目录
    temp_dir = Path("temp_agent")
    temp_dir.mkdir(exist_ok=True)

    # 1. 创建智能体主文件
    agent_code = '''"""
测试智能体

这是一个用于测试上传功能的示例智能体
"""

class TestAgent:
    """测试智能体类"""

    def __init__(self, config=None):
        """
        初始化智能体

        Args:
            config: 配置参数字典
        """
        self.config = config or {}
        self.name = "TestAgent"
        self.version = "1.0.0"

    def run(self, observation):
        """
        智能体主逻辑

        Args:
            observation: 观察到的环境状态

        Returns:
            action: 智能体的动作
        """
        # 这里是智能体的决策逻辑
        action = self.make_decision(observation)
        return action

    def make_decision(self, observation):
        """
        决策函数

        Args:
            observation: 观察值

        Returns:
            决策结果
        """
        # 简单的决策逻辑示例
        return {"action": "move", "direction": "forward"}

    def reset(self):
        """重置智能体状态"""
        print(f"{self.name} has been reset")


if __name__ == "__main__":
    agent = TestAgent()
    print(f"智能体 {agent.name} v{agent.version} 已创建")
'''

    agent_file = temp_dir / "agent.py"
    agent_file.write_text(agent_code, encoding="utf-8")

    # 2. 创建配置文件
    config = {
        "name": "TestAgent",
        "version": "1.0.0",
        "description": "这是一个测试智能体",
        "author": "Test User",
        "parameters": {
            "timeout": {
                "type": "int",
                "default": 30,
                "description": "执行超时时间（秒）"
            },
            "max_steps": {
                "type": "int",
                "default": 1000,
                "description": "最大执行步数"
            }
        }
    }

    config_file = temp_dir / "config.json"
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. 创建 README
    readme_content = """# 测试智能体

## 简介

这是一个用于测试上传功能的示例智能体。

## 文件说明

- `agent.py`: 智能体主程序
- `config.json`: 配置文件
- `README.md`: 说明文档

## 使用方法

```python
from agent import TestAgent

# 创建智能体实例
agent = TestAgent(config={"timeout": 30})

# 运行智能体
observation = {"state": "initial"}
action = agent.run(observation)
```

## 参数说明

- `timeout`: 执行超时时间（秒），默认 30
- `max_steps`: 最大执行步数，默认 1000
"""

    readme_file = temp_dir / "README.md"
    readme_file.write_text(readme_content, encoding="utf-8")

    # 4. 创建 ZIP 文件
    zip_path = Path("test_agent.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in temp_dir.iterdir():
            zipf.write(file, file.name)

    # 5. 清理临时目录
    for file in temp_dir.iterdir():
        file.unlink()
    temp_dir.rmdir()

    print(f"✅ 测试智能体 ZIP 文件已创建: {zip_path.absolute()}")
    print(f"📦 文件大小: {zip_path.stat().st_size} 字节")
    print("\n📋 使用此文件测试上传时，请填写：")
    print("  - 智能体名称: 测试智能体1")
    print("  - 智能体描述: 这是一个测试的智能体")
    print("  - 智能体文件名: agent.py")
    print("  - 阵营: red")
    print('  - 参数声明: {"timeout": 30, "max_steps": 1000}')
    print("  - 支持的环境模板: 1001,1002")


if __name__ == "__main__":
    create_test_agent()
