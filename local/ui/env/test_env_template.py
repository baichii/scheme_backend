import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import gradio as gr
import requests


class EnvTemplateTestUI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = f"{self.base_url}/api/v1/env/template"

    def get_all_templates(self) -> tuple[str, str]:
        try:
            response = requests.get(f"{self.api_prefix}/all")
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200:
                templates = data.get("data", [])
                if not templates:
                    return "INFO", "No templates found"

                result_text = f"**Found {len(templates)} templates**\n\n"
                for template in templates:
                    result_text += f"""---
**ID**: {template.get('id')}
**Name**: {template.get('name')}
**Param Schema**:
```json
{json.dumps(template.get('param_schema', {}), indent=2, ensure_ascii=False)}
```

"""
                return "SUCCESS", result_text
            else:
                return "ERROR", f"Request failed: {data.get('msg', 'Unknown error')}"

        except requests.RequestException as e:
            return "ERROR", f"Request failed: {str(e)}"
        except Exception as e:
            return "ERROR", f"Error: {str(e)}"

    def get_template_by_id(self, pk: str) -> tuple[str, str]:
        try:
            if not pk:
                return "ERROR", "Please input template ID"

            try:
                pk_int = int(pk)
            except ValueError:
                return "ERROR", "Template ID must be a number"

            response = requests.get(f"{self.api_prefix}/{pk_int}")
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200:
                template = data.get("data")
                if not template:
                    return "ERROR", f"Template ID {pk} not found"

                result_text = f"""**Template Details**

**ID**: {template.get('id')}
**Name**: {template.get('name')}
**Param Schema**:
```json
{json.dumps(template.get('param_schema', {}), indent=2, ensure_ascii=False)}
```
"""
                return "SUCCESS", result_text
            else:
                return "ERROR", f"Request failed: {data.get('msg', 'Unknown error')}"

        except requests.RequestException as e:
            return "ERROR", f"Request failed: {str(e)}"
        except Exception as e:
            return "ERROR", f"Error: {str(e)}"

    def create_template(self, name: str, param_schema: str) -> tuple[str, str]:
        try:
            if not name:
                return "ERROR", "Please input template name"

            if not param_schema:
                return "ERROR", "Please input param schema"

            try:
                schema_dict = json.loads(param_schema)
            except json.JSONDecodeError:
                return "ERROR", "Invalid JSON format for param schema"

            payload = {"name": name, "param_schema": schema_dict}

            response = requests.post(f"{self.api_prefix}/create", json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200:
                return "SUCCESS", f"Template '{name}' created successfully"
            else:
                return "ERROR", f"Create failed: {data.get('msg', 'Unknown error')}"

        except requests.RequestException as e:
            return "ERROR", f"Request failed: {str(e)}"
        except Exception as e:
            return "ERROR", f"Error: {str(e)}"

    def delete_template(self, pk: str) -> tuple[str, str]:
        try:
            if not pk:
                return "ERROR", "Please input template ID"

            try:
                pk_int = int(pk)
            except ValueError:
                return "ERROR", "Template ID must be a number"

            response = requests.delete(f"{self.api_prefix}/{pk_int}")
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200:
                return "SUCCESS", f"Template ID {pk} deleted successfully"
            else:
                return "ERROR", f"Delete failed: {data.get('msg', 'Unknown error')}"

        except requests.RequestException as e:
            return "ERROR", f"Request failed: {str(e)}"
        except Exception as e:
            return "ERROR", f"Error: {str(e)}"

    def create_interface(self):
        with gr.Blocks(title="Env Template Test") as demo:
            gr.Markdown("# Env Template Test")

            with gr.Tabs():
                with gr.Tab("Get All"):
                    gr.Markdown("### Get All Templates")
                    list_btn = gr.Button("Get All", variant="primary")
                    list_status = gr.Textbox(label="Status", interactive=False)
                    list_result = gr.Markdown()
                    list_btn.click(fn=self.get_all_templates, outputs=[list_status, list_result])

                with gr.Tab("Get By ID"):
                    gr.Markdown("### Get Template By ID")
                    get_id = gr.Textbox(label="Template ID", placeholder="Input template ID")
                    get_btn = gr.Button("Get", variant="primary")
                    get_status = gr.Textbox(label="Status", interactive=False)
                    get_result = gr.Markdown()
                    get_btn.click(
                        fn=self.get_template_by_id, inputs=[get_id], outputs=[get_status, get_result]
                    )

                with gr.Tab("Create"):
                    gr.Markdown("### Create Template")
                    create_name = gr.Textbox(label="Template Name", placeholder="e.g: test_template")
                    create_schema = gr.Textbox(
                        label="Param Schema (JSON)",
                        placeholder='e.g: {"host": "localhost", "port": 8080}',
                        lines=5,
                    )
                    create_btn = gr.Button("Create", variant="primary")
                    create_status = gr.Textbox(label="Status", interactive=False)
                    create_result = gr.Markdown()
                    create_btn.click(
                        fn=self.create_template,
                        inputs=[create_name, create_schema],
                        outputs=[create_status, create_result],
                    )

                with gr.Tab("Delete"):
                    gr.Markdown("### Delete Template")
                    gr.Markdown("**WARNING**: Delete operation cannot be recovered")
                    delete_id = gr.Textbox(label="Template ID", placeholder="Input template ID to delete")
                    delete_btn = gr.Button("Delete", variant="stop")
                    delete_status = gr.Textbox(label="Status", interactive=False)
                    delete_result = gr.Markdown()
                    delete_btn.click(
                        fn=self.delete_template, inputs=[delete_id], outputs=[delete_status, delete_result]
                    )

        return demo


def main():
    print("Starting Env Template Test Platform...")

    ui = EnvTemplateTestUI(base_url="http://localhost:8000")
    demo = ui.create_interface()

    print("Test platform started")
    print("Access at: http://localhost:7861")

    demo.launch(server_name="0.0.0.0", server_port=7861, share=False, show_error=True)


if __name__ == "__main__":
    main()
