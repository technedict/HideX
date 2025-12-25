"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "HideX"
    
    def test_readiness_check(self, client):
        """Test readiness check."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "HideX"
        assert "disclaimers" in data
        assert len(data["disclaimers"]) > 0


class TestPlanEndpoints:
    """Tests for plan endpoints."""
    
    def test_create_simple_plan(self, client):
        """Test creating a simple plan."""
        # First initialize wallet (must pass empty JSON body)
        client.post("/wallets/initialize", json={})
        
        response = client.post("/plans", json={
            "source_address": "0x1234567890123456789012345678901234567890",
            "destination_address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "amount_wei": "1000000000000000000",
            "plan_type": "simple",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["source_address"] == "0x1234567890123456789012345678901234567890"
        assert data["is_dry_run"] is True
        assert len(data["steps"]) == 1
    
    def test_create_multi_hop_plan(self, client):
        """Test creating a multi-hop plan."""
        # First initialize wallet (must pass empty JSON body)
        client.post("/wallets/initialize", json={})
        
        response = client.post("/plans", json={
            "source_address": "0x1234567890123456789012345678901234567890",
            "destination_address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "amount_wei": "1000000000000000000",
            "plan_type": "multi_hop",
            "num_hops": 2,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["steps"]) == 3  # 2 hops + final
    
    def test_get_plan(self, client):
        """Test getting a plan by ID."""
        # First create a plan
        client.post("/wallets/initialize", json={})
        create_response = client.post("/plans", json={
            "source_address": "0x1234567890123456789012345678901234567890",
            "destination_address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "amount_wei": "1000000000000000000",
            "plan_type": "simple",
        })
        plan_id = create_response.json()["id"]
        
        # Get the plan
        response = client.get(f"/plans/{plan_id}")
        assert response.status_code == 200
        assert response.json()["id"] == plan_id
    
    def test_get_nonexistent_plan(self, client):
        """Test getting a plan that doesn't exist."""
        response = client.get("/plans/nonexistent_id")
        assert response.status_code == 404


class TestPolicyEndpoints:
    """Tests for policy endpoints."""
    
    def test_list_policies(self, client):
        """Test listing policies."""
        response = client.get("/policies")
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert data["total"] >= 1  # At least default policy
    
    def test_get_default_template(self, client):
        """Test getting default policy template."""
        response = client.get("/policies/default/template")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "default"
        assert "rules" in data
        assert len(data["rules"]) > 0


class TestAuditEndpoints:
    """Tests for audit endpoints."""
    
    def test_get_current_log(self, client):
        """Test getting current audit log."""
        response = client.get("/audit/current")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total_entries" in data
    
    def test_list_sessions(self, client):
        """Test listing audit sessions."""
        response = client.get("/audit/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data


class TestExecutionRequiresConfirmation:
    """Tests that execution requires proper confirmation."""
    
    def test_execute_without_confirmation_fails(self, client):
        """Test that execution without confirmation fails."""
        # Create a plan
        client.post("/wallets/initialize", json={})
        create_response = client.post("/plans", json={
            "source_address": "0x1234567890123456789012345678901234567890",
            "destination_address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "amount_wei": "1000000000000000000",
            "plan_type": "simple",
        })
        plan_id = create_response.json()["id"]
        
        # Try to execute without confirmation
        response = client.post(f"/plans/{plan_id}/execute", json={
            "plan_id": plan_id,
            "confirmation": False,
        })
        
        # Should fail because confirmation is required
        assert response.status_code == 400
        assert "confirmation" in response.json()["detail"].lower()
