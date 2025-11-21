from backend.app.env.schema.env_template import CreateEnvTemplateParam
from backend.app.env.schema.env_instance import CreateEnvInstanceParam
from backend.common.enums import ParamType


def test_create_env_template_param():
    create_env_template_param = {
        "name": "test",
        "param_schema": [
            {
                "name": "param1",
                "type": ParamType.STR,
                "input_type": "字符串",
                "required": True,
                "description": "参数1",
            },
            {
                "name": "param2",
                "type": ParamType.INT,
                "input_type": "整数",
                "required": False,
                "description": "参数2",
                "default": 0,
            },
        ],
    }

    env_template = CreateEnvTemplateParam(
        **create_env_template_param
    )

    print(env_template.name)
    print(env_template.param_schema[0].name)


def test_create_env_instance_param():
    create_env_instance_param = {
        "name": "test",
        "template_id": 1234,
        "params": [
            {
                "name": "param1",
                "value": "value1",
            },
            {
                "name": "param2",
                "value": 1,
            },
        ],
    }

    env_instance = CreateEnvInstanceParam(
        **create_env_instance_param
    )

    print(env_instance.name)
    print(env_instance.params)


if __name__ == '__main__':
    test_create_env_template_param()
    test_create_env_instance_param()
