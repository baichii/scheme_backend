"""
Gradio 智能体上传测试界面

提供智能体的上传、查询、查看详情和删除功能
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import gradio as gr
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.services.agent_service import agent_service
from backend.app.agent.schema.agent_meta import AgentUploadRequest
from backend.database import async_session_factory, init_db


class AgentTestUI:
    """智能体测试界面"""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # 初始化数据库
        self.loop.run_until_complete(init_db())

    async def _upload_agent(
        self,
        file_path: str,
        agent_name: str,
        agent_desc: str,
        side: str,
        params_schema: str,
        supported_env_templates: str,
        agent_file: str
    ) -> tuple[str, str]:
        """上传智能体（内部异步方法）"""
        try:
            # 验证输入
            if not file_path:
                return "❌ 错误", "请选择要上传的 zip 文件"

            if not agent_name:
                return "❌ 错误", "请输入智能体名称"

            if not agent_file:
                return "❌ 错误", "请输入智能体文件名"

            # 解析参数
            try:
                params_schema_dict = json.loads(params_schema) if params_schema.strip() else {}
            except json.JSONDecodeError:
                return "❌ 错误", "参数声明格式错误，必须是有效的 JSON"

            try:
                env_templates = [int(x.strip()) for x in supported_env_templates.split(",")] if supported_env_templates.strip() else []
            except ValueError:
                return "❌ 错误", "环境模板格式错误，必须是逗号分隔的数字，如: 1001,1002"

            # 读取文件
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            # 创建模拟的 UploadFile 对象
            class MockUploadFile:
                def __init__(self, filename: str, content: bytes):
                    self.filename = filename
                    self._content = content

                async def read(self):
                    return self._content

            mock_file = MockUploadFile(Path(file_path).name, file_bytes)

            # 创建元数据
            metadata = AgentUploadRequest(
                agent_name=agent_name,
                agent_desc=agent_desc,
                side=side if side.strip() else None,
                params_schema=params_schema_dict,
                supported_env_templates=env_templates,
                agent_file=agent_file
            )

            # 上传
            async with async_session_factory() as db:
                result = await agent_service.upload(db, mock_file, metadata)

            return "✅ 成功", f"""智能体上传成功！

**智能体 ID**: {result['agent_id']}
**智能体名称**: {result['agent_name']}
**存储路径**: {result['agent_url']}
"""

        except ValueError as e:
            return "❌ 错误", f"验证失败: {str(e)}"
        except Exception as e:
            return "❌ 错误", f"上传失败: {str(e)}"

    def upload_agent(self, *args):
        """上传智能体（同步包装）"""
        return self.loop.run_until_complete(self._upload_agent(*args))

    async def _list_agents(self) -> tuple[str, str]:
        """查询所有智能体（内部异步方法）"""
        try:
            async with async_session_factory() as db:
                agents = await agent_service.list_all(db)

            if not agents:
                return "ℹ️ 提示", "暂无智能体数据"

            result_text = f"📋 **共找到 {len(agents)} 个智能体**\n\n"
            for agent in agents:
                result_text += f"""---
**ID**: {agent.agent_id}
**名称**: {agent.agent_name}
**描述**: {agent.agent_desc}
**阵营**: {agent.side}
**加载名**: {agent.agent_load}
**存储路径**: {agent.agent_url}
**支持环境**: {', '.join(agent.supported_env_templates)}
**创建时间**: {agent.create_at}

"""
            return "✅ 成功", result_text

        except Exception as e:
            return "❌ 错误", f"查询失败: {str(e)}"

    def list_agents(self):
        """查询所有智能体（同步包装）"""
        return self.loop.run_until_complete(self._list_agents())

    async def _get_agent_detail(self, agent_id: str) -> tuple[str, str]:
        """获取智能体详情（内部异步方法）"""
        try:
            if not agent_id:
                return "❌ 错误", "请输入智能体 ID"

            try:
                agent_id_int = int(agent_id)
            except ValueError:
                return "❌ 错误", "智能体 ID 必须是数字"

            async with async_session_factory() as db:
                agent = await agent_service.get(db, agent_id_int)

            if not agent:
                return "❌ 错误", f"未找到 ID 为 {agent_id} 的智能体"

            result_text = f"""📄 **智能体详情**

**ID**: {agent.agent_id}
**名称**: {agent.agent_name}
**描述**: {agent.agent_desc}
**阵营**: {agent.side}
**加载名**: {agent.agent_load}
**存储路径**: {agent.agent_url}
**支持环境**: {', '.join(agent.supported_env_templates)}
**创建时间**: {agent.create_at}
**更新时间**: {agent.update_at}

**参数声明**:
```json
{json.dumps(agent.param_schema, indent=2, ensure_ascii=False)}
```
"""
            return "✅ 成功", result_text

        except Exception as e:
            return "❌ 错误", f"查询失败: {str(e)}"

    def get_agent_detail(self, agent_id: str):
        """获取智能体详情（同步包装）"""
        return self.loop.run_until_complete(self._get_agent_detail(agent_id))

    async def _delete_agent(self, agent_id: str) -> tuple[str, str]:
        """删除智能体（内部异步方法）"""
        try:
            if not agent_id:
                return "❌ 错误", "请输入智能体 ID"

            try:
                agent_id_int = int(agent_id)
            except ValueError:
                return "❌ 错误", "智能体 ID 必须是数字"

            async with async_session_factory() as db:
                result = await agent_service.delete(db, agent_id_int)

            if result:
                return "✅ 成功", f"智能体 ID {agent_id} 已成功删除"
            else:
                return "❌ 错误", f"未找到 ID 为 {agent_id} 的智能体"

        except Exception as e:
            return "❌ 错误", f"删除失败: {str(e)}"

    def delete_agent(self, agent_id: str):
        """删除智能体（同步包装）"""
        return self.loop.run_until_complete(self._delete_agent(agent_id))

    def create_interface(self):
        """创建 Gradio 界面"""
        with gr.Blocks(title="智能体测试平台", theme=gr.themes.Soft()) as demo:
            gr.Markdown("""
# 🤖 智能体测试平台

测试智能体的上传、查询和管理功能
""")

            with gr.Tabs():
                # 上传标签页
                with gr.Tab("📤 上传智能体"):
                    gr.Markdown("### 上传智能体 ZIP 文件")

                    with gr.Row():
                        with gr.Column():
                            upload_file = gr.File(
                                label="选择 ZIP 文件",
                                file_types=[".zip"],
                                type="filepath"
                            )
                            upload_name = gr.Textbox(
                                label="智能体名称 *",
                                placeholder="例如: 测试智能体1"
                            )
                            upload_desc = gr.Textbox(
                                label="智能体描述 *",
                                placeholder="例如: 这是一个测试的智能体",
                                lines=3
                            )
                            upload_side = gr.Textbox(
                                label="阵营（可选）",
                                placeholder="例如: red"
                            )
                            upload_file_name = gr.Textbox(
                                label="智能体文件名 *",
                                placeholder="例如: agent.py"
                            )
                            upload_params = gr.Textbox(
                                label="参数声明（JSON 格式，可选）",
                                placeholder='例如: {"param1": "value1"}',
                                lines=3
                            )
                            upload_env = gr.Textbox(
                                label="支持的环境模板（逗号分隔的数字，可选）",
                                placeholder="例如: 1001,1002"
                            )

                            upload_btn = gr.Button("🚀 上传", variant="primary", size="lg")

                        with gr.Column():
                            upload_status = gr.Textbox(label="状态", interactive=False)
                            upload_result = gr.Markdown()

                    upload_btn.click(
                        fn=self.upload_agent,
                        inputs=[
                            upload_file,
                            upload_name,
                            upload_desc,
                            upload_side,
                            upload_params,
                            upload_env,
                            upload_file_name
                        ],
                        outputs=[upload_status, upload_result]
                    )

                # 查询标签页
                with gr.Tab("📋 查询智能体"):
                    gr.Markdown("### 查看所有已上传的智能体")

                    with gr.Row():
                        list_btn = gr.Button("🔍 查询所有智能体", variant="primary", size="lg")

                    with gr.Row():
                        list_status = gr.Textbox(label="状态", interactive=False)

                    list_result = gr.Markdown()

                    list_btn.click(
                        fn=self.list_agents,
                        outputs=[list_status, list_result]
                    )

                # 详情标签页
                with gr.Tab("🔍 查看详情"):
                    gr.Markdown("### 查看智能体详细信息")

                    with gr.Row():
                        with gr.Column(scale=3):
                            detail_id = gr.Textbox(
                                label="智能体 ID",
                                placeholder="输入智能体 ID"
                            )
                        with gr.Column(scale=1):
                            detail_btn = gr.Button("📄 查看详情", variant="primary", size="lg")

                    with gr.Row():
                        detail_status = gr.Textbox(label="状态", interactive=False)

                    detail_result = gr.Markdown()

                    detail_btn.click(
                        fn=self.get_agent_detail,
                        inputs=[detail_id],
                        outputs=[detail_status, detail_result]
                    )

                # 删除标签页
                with gr.Tab("🗑️ 删除智能体"):
                    gr.Markdown("### 删除智能体")
                    gr.Markdown("⚠️ **警告**: 删除操作不可恢复！")

                    with gr.Row():
                        with gr.Column(scale=3):
                            delete_id = gr.Textbox(
                                label="智能体 ID",
                                placeholder="输入要删除的智能体 ID"
                            )
                        with gr.Column(scale=1):
                            delete_btn = gr.Button("🗑️ 删除", variant="stop", size="lg")

                    with gr.Row():
                        delete_status = gr.Textbox(label="状态", interactive=False)

                    delete_result = gr.Markdown()

                    delete_btn.click(
                        fn=self.delete_agent,
                        inputs=[delete_id],
                        outputs=[delete_status, delete_result]
                    )

            gr.Markdown("""
---
💡 **使用提示**:
- 上传前请确保 ZIP 文件包含指定的智能体文件
- 参数声明必须是有效的 JSON 格式
- 环境模板 ID 使用逗号分隔，例如: 1001,1002
- 删除操作会同时删除数据库记录和 MinIO 中的文件
""")

        return demo


def main():
    """启动测试界面"""
    print("🚀 启动智能体测试平台...")

    ui = AgentTestUI()
    demo = ui.create_interface()

    print("✅ 测试平台已启动")
    print("📍 访问地址: http://localhost:7860")

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
