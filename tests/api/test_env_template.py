"""
Environment Template API Tests - Simplified Version
Focus on core functionality testing
"""

import pytest


class TestEnvTemplateBasic:
    """Basic CRUD Tests"""

    @pytest.mark.asyncio
    async def test_create_template(self, client, sample_env_template):
        """Test: Create template"""
        response = await client.post(
            "/api/v1/env/template/create",
            json=sample_env_template
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        print(f"✓ Template created successfully, ID: {data['data']}")

    @pytest.mark.asyncio
    async def test_get_all_templates(self, client):
        """Test: Get all templates"""
        response = await client.get("/api/v1/env/template/all")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        print(f"✓ Retrieved template list, count: {len(data['data'])}")

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, client, sample_env_template):
        """Test: Get template by ID"""
        # Create a template first
        create_resp = await client.post(
            "/api/v1/env/template/create",
            json=sample_env_template
        )
        template_id = create_resp.json()["data"]

        # Get the template
        response = await client.get(f"/api/v1/env/template/{template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == template_id
        print(f"✓ Retrieved template: {data['data']['name']}")

    @pytest.mark.asyncio
    async def test_get_template_by_name(self, client, sample_env_template):
        """Test: Get template by name"""
        # Create first
        await client.post("/api/v1/env/template/create", json=sample_env_template)

        # Get by name
        response = await client.get(
            f"/api/v1/env/template/by-name/{sample_env_template['name']}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == sample_env_template["name"]
        print(f"✓ Retrieved template by name successfully")

    @pytest.mark.asyncio
    async def test_delete_template(self, client, sample_env_template):
        """Test: Delete template"""
        # Create first
        create_resp = await client.post(
            "/api/v1/env/template/create",
            json=sample_env_template
        )
        template_id = create_resp.json()["data"]

        # Delete
        response = await client.delete(f"/api/v1/env/template/{template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        print(f"✓ Deleted template successfully, ID: {template_id}")


class TestEnvTemplateValidation:
    """Data Validation Tests"""

    @pytest.mark.asyncio
    async def test_create_with_missing_name(self, client):
        """Test: Missing required field"""
        invalid_data = {
            "param_schema": []
        }
        response = await client.post(
            "/api/v1/env/template/create",
            json=invalid_data
        )
        # Should return validation error
        assert response.status_code == 422
        print("✓ Required field validation passed")

    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, client, sample_env_template):
        """Test: Duplicate name"""
        # First creation
        await client.post("/api/v1/env/template/create", json=sample_env_template)

        # Second creation with same name
        response = await client.post(
            "/api/v1/env/template/create",
            json=sample_env_template
        )
        data = response.json()
        # Should return conflict error
        assert data["code"] != 200
        print("✓ Duplicate name validation passed")

    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, client):
        """Test: Get non-existent template"""
        response = await client.get("/api/v1/env/template/99999")
        # Should return error status code (not 200)
        assert response.status_code != 200
        print("✓ Non-existent resource handled correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
