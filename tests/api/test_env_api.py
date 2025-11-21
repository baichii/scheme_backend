"""
环境模版和实例测试脚本
使用 pytest 进行批量测试
"""

import pytest
import httpx
from typing import List, Dict, Any


# ==================== 配置 ====================

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"


# ==================== Fixtures ====================

@pytest.fixture(scope="session")
def client():
    """创建 HTTP 客户端"""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


@pytest.fixture(scope="function")
def clean_templates(client):
    """每个测试前清理所有模版"""
    yield
    # 清理：删除所有模版
    response = client.delete(f"{API_V1}/env/template/all")
    print(f"清理模版: {response.status_code}")


@pytest.fixture(scope="function")
def clean_instances(client):
    """每个测试前清理所有实例"""
    yield
    # 清理：删除所有实例
    response = client.delete(f"{API_V1}/env/instance/all")
    print(f"清理实例: {response.status_code}")


@pytest.fixture
def sample_template_data():
    """示例模版数据"""
    return {
        "name": "测试环境模版",
        "param_schema": [
            {
                "name": "ip",
                "input_name": "仿真地址",
                "type": "str",
                "required": 1,
                "description": "环境的IP地址",
                "default_value": None,
            },
            {
                "name": "port",
                "input_name": "端口号",
                "type": "int",
                "required": 1,
                "description": "服务端口",
                "default_value": None,
            },
            {
                "name": "username",
                "input_name": "用户名",
                "type": "str",
                "required": 0,
                "description": "登录用户名",
                "default_value": "admin",
            },
        ],
    }


@pytest.fixture
def sample_instance_data():
    """示例实例数据"""
    return {
        "name": "测试环境1",
        "params": {
            "ip": "192.168.1.100",
            "port": 8080,
            "username": "testuser",
        },
    }


# ==================== 测试：环境模版 ====================

class TestEnvTemplate:
    """环境模版测试"""

    def test_create_template(self, client, sample_template_data, clean_templates):
        """测试创建模版"""
        response = client.post(f"{API_V1}/env/template/create", json=sample_template_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        template_id = data["data"]
        assert isinstance(template_id, int)
        print(f"✅ 创建模版成功，ID: {template_id}")

    def test_get_all_templates(self, client, sample_template_data, clean_templates):
        """测试获取所有模版"""
        # 先创建一个模版
        client.post(f"{API_V1}/env/template/create", json=sample_template_data)

        # 获取所有模版
        response = client.get(f"{API_V1}/env/template/all")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        templates = data["data"]
        assert len(templates) >= 1
        assert templates[0]["name"] == sample_template_data["name"]
        print(f"✅ 获取模版列表成功，共 {len(templates)} 个")

    def test_get_template_by_id(self, client, sample_template_data, clean_templates):
        """测试根据ID获取模版"""
        # 创建模版
        create_resp = client.post(f"{API_V1}/env/template/create", json=sample_template_data)
        template_id = create_resp.json()["data"]

        # 获取模版
        response = client.get(f"{API_V1}/env/template/{template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        template = data["data"]
        assert template["id"] == template_id
        assert template["name"] == sample_template_data["name"]
        print(f"✅ 获取模版 {template_id} 成功")

    def test_get_template_by_name(self, client, sample_template_data, clean_templates):
        """测试根据名称获取模版"""
        # 创建模版
        client.post(f"{API_V1}/env/template/create", json=sample_template_data)

        # 根据名称获取
        response = client.get(f"{API_V1}/env/template/by-name/{sample_template_data['name']}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        template = data["data"]
        assert template["name"] == sample_template_data["name"]
        print(f"✅ 根据名称获取模版成功")

    def test_delete_template(self, client, sample_template_data, clean_templates):
        """测试删除模版"""
        # 创建模版
        create_resp = client.post(f"{API_V1}/env/template/create", json=sample_template_data)
        template_id = create_resp.json()["data"]

        # 删除模版
        response = client.delete(f"{API_V1}/env/template/{template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        print(f"✅ 删除模版 {template_id} 成功")

        # 验证已删除
        get_resp = client.get(f"{API_V1}/env/template/{template_id}")
        assert get_resp.status_code != 200 or get_resp.json()["code"] != 200

    @pytest.mark.parametrize("template_name,expected", [
        ("模版A", "模版A"),
        ("模版B", "模版B"),
        ("测试模版C", "测试模版C"),
    ])
    def test_create_multiple_templates(self, client, sample_template_data, template_name, expected, clean_templates):
        """参数化测试：批量创建多个模版"""
        data = sample_template_data.copy()
        data["name"] = template_name

        response = client.post(f"{API_V1}/env/template/create", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        print(f"✅ 创建模版 {template_name} 成功")


# ==================== 测试：环境实例 ====================

class TestEnvInstance:
    """环境实例测试"""

    @pytest.fixture
    def template_id(self, client, sample_template_data, clean_templates):
        """创建一个模版并返回其ID"""
        response = client.post(f"{API_V1}/env/template/create", json=sample_template_data)
        return response.json()["data"]

    def test_create_instance(self, client, template_id, sample_instance_data, clean_instances):
        """测试创建实例"""
        data = sample_instance_data.copy()
        data["template_id"] = template_id

        response = client.post(f"{API_V1}/env/instance/create", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        instance_id = result["data"]
        assert isinstance(instance_id, int)
        print(f"✅ 创建实例成功，ID: {instance_id}")

    def test_get_all_instances(self, client, template_id, sample_instance_data, clean_instances):
        """测试获取所有实例"""
        # 创建实例
        data = sample_instance_data.copy()
        data["template_id"] = template_id
        client.post(f"{API_V1}/env/instance/create", json=data)

        # 获取所有实例
        response = client.get(f"{API_V1}/env/instance/all")
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        instances = result["data"]
        assert len(instances) >= 1
        print(f"✅ 获取实例列表成功，共 {len(instances)} 个")

    def test_get_instance_by_id(self, client, template_id, sample_instance_data, clean_instances):
        """测试根据ID获取实例"""
        # 创建实例
        data = sample_instance_data.copy()
        data["template_id"] = template_id
        create_resp = client.post(f"{API_V1}/env/instance/create", json=data)
        instance_id = create_resp.json()["data"]

        # 获取实例
        response = client.get(f"{API_V1}/env/instance/{instance_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        instance = result["data"]
        assert instance["id"] == instance_id
        print(f"✅ 获取实例 {instance_id} 成功")

    def test_get_instance_by_template_id(self, client, template_id, sample_instance_data, clean_instances):
        """测试根据模版ID获取实例"""
        # 创建实例
        data = sample_instance_data.copy()
        data["template_id"] = template_id
        client.post(f"{API_V1}/env/instance/create", json=data)

        # 根据模版ID获取
        response = client.get(f"{API_V1}/env/instance/by-template-id/{template_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        instances = result["data"]
        assert len(instances) >= 1
        assert all(inst["template_id"] == template_id for inst in instances)
        print(f"✅ 根据模版ID获取实例成功，共 {len(instances)} 个")

    def test_delete_instance(self, client, template_id, sample_instance_data, clean_instances):
        """测试删除实例"""
        # 创建实例
        data = sample_instance_data.copy()
        data["template_id"] = template_id
        create_resp = client.post(f"{API_V1}/env/instance/create", json=data)
        instance_id = create_resp.json()["data"]

        # 删除实例
        response = client.delete(f"{API_V1}/env/instance/{instance_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        print(f"✅ 删除实例 {instance_id} 成功")

    @pytest.mark.parametrize("instance_name,ip,port", [
        ("环境1", "192.168.1.100", 8080),
        ("环境2", "192.168.1.101", 8081),
        ("环境3", "192.168.1.102", 8082),
        ("环境4", "192.168.1.103", 8083),
        ("环境5", "192.168.1.104", 8084),
    ])
    def test_create_multiple_instances(
        self, client, template_id, instance_name, ip, port, clean_instances
    ):
        """参数化测试：批量创建多个实例"""
        data = {
            "template_id": template_id,
            "name": instance_name,
            "params": {
                "ip": ip,
                "port": port,
                "username": "admin",
            },
        }

        response = client.post(f"{API_V1}/env/instance/create", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        print(f"✅ 创建实例 {instance_name} ({ip}:{port}) 成功")


# ==================== 测试：完整流程 ====================

class TestCompleteFlow:
    """完整流程测试"""

    def test_full_workflow(self, client, clean_templates, clean_instances):
        """测试完整的工作流程"""
        # 1. 创建模版
        template_data = {
            "name": "完整流程测试模版",
            "param_schema": [
                {
                    "name": "ip",
                    "input_name": "IP地址",
                    "type": "str",
                    "required": 1,
                    "description": "服务器IP",
                    "default_value": None,
                }
            ],
        }
        resp = client.post(f"{API_V1}/env/template/create", json=template_data)
        template_id = resp.json()["data"]
        print(f"✅ 步骤1: 创建模版 {template_id}")

        # 2. 获取模版列表
        resp = client.get(f"{API_V1}/env/template/all")
        templates = resp.json()["data"]
        assert len(templates) >= 1
        print(f"✅ 步骤2: 获取模版列表，共 {len(templates)} 个")

        # 3. 创建多个实例
        for i in range(3):
            instance_data = {
                "template_id": template_id,
                "name": f"实例{i+1}",
                "params": {"ip": f"192.168.1.{100+i}"},
            }
            resp = client.post(f"{API_V1}/env/instance/create", json=instance_data)
            assert resp.json()["code"] == 200
        print(f"✅ 步骤3: 创建3个实例")

        # 4. 获取实例列表
        resp = client.get(f"{API_V1}/env/instance/all")
        instances = resp.json()["data"]
        assert len(instances) == 3
        print(f"✅ 步骤4: 获取实例列表，共 {len(instances)} 个")

        # 5. 根据模版ID获取实例
        resp = client.get(f"{API_V1}/env/instance/by-template-id/{template_id}")
        instances = resp.json()["data"]
        assert len(instances) == 3
        print(f"✅ 步骤5: 根据模版ID获取实例，共 {len(instances)} 个")

        # 6. 删除一个实例
        instance_id = instances[0]["id"]
        resp = client.delete(f"{API_V1}/env/instance/{instance_id}")
        assert resp.json()["code"] == 200
        print(f"✅ 步骤6: 删除实例 {instance_id}")

        # 7. 验证删除
        resp = client.get(f"{API_V1}/env/instance/all")
        remaining_instances = resp.json()["data"]
        assert len(remaining_instances) == 2
        print(f"✅ 步骤7: 验证删除后剩余 {len(remaining_instances)} 个实例")

        print("\n🎉 完整流程测试通过！")


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""

    def test_batch_create_templates(self, client, clean_templates):
        """性能测试：批量创建100个模版"""
        import time

        count = 100
        start_time = time.time()

        for i in range(count):
            data = {
                "name": f"性能测试模版{i}",
                "param_schema": [
                    {
                        "name": "param",
                        "input_name": "参数",
                        "type": "str",
                        "required": 1,
                        "description": "测试参数",
                        "default_value": None,
                    }
                ],
            }
            response = client.post(f"{API_V1}/env/template/create", json=data)
            assert response.status_code == 200

        elapsed = time.time() - start_time
        avg_time = elapsed / count
        print(f"✅ 批量创建 {count} 个模版")
        print(f"   总耗时: {elapsed:.2f}秒")
        print(f"   平均耗时: {avg_time*1000:.2f}毫秒/个")
        print(f"   吞吐量: {count/elapsed:.2f}个/秒")

    def test_batch_create_instances(self, client, sample_template_data, clean_templates, clean_instances):
        """性能测试：批量创建100个实例"""
        import time

        # 先创建模版
        resp = client.post(f"{API_V1}/env/template/create", json=sample_template_data)
        template_id = resp.json()["data"]

        count = 100
        start_time = time.time()

        for i in range(count):
            data = {
                "template_id": template_id,
                "name": f"性能测试实例{i}",
                "params": {
                    "ip": f"192.168.{i//256}.{i%256}",
                    "port": 8000 + i,
                },
            }
            response = client.post(f"{API_V1}/env/instance/create", json=data)
            assert response.status_code == 200

        elapsed = time.time() - start_time
        avg_time = elapsed / count
        print(f"✅ 批量创建 {count} 个实例")
        print(f"   总耗时: {elapsed:.2f}秒")
        print(f"   平均耗时: {avg_time*1000:.2f}毫秒/个")
        print(f"   吞吐量: {count/elapsed:.2f}个/秒")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
