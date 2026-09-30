import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_mcp_runtime.db")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")
os.environ.setdefault("PARDHA_CONNECTOR_MODE", "mock")

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


class MCPRuntimeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_meta_lifecycle_discovery_health_permissions_and_execution(self):
        servers = self.client.get("/mcp/servers")
        self.assertEqual(servers.status_code, 200)
        self.assertTrue(any(item["server_id"] == "meta" for item in servers.json()))

        discovery = self.client.get("/mcp/discovery")
        self.assertEqual(discovery.status_code, 200)
        tools = {item["name"] for item in discovery.json()["tools"]}
        self.assertIn("campaign.list", tools)
        self.assertIn("analytics.summary", tools)
        self.assertIn("instagram.insights.summary", tools)
        self.assertIn("contact.list", tools)
        self.assertIn("meta.campaigns.read", discovery.json()["permissions"]["meta"])
        self.assertIn("hubspot.contacts.read", discovery.json()["permissions"]["hubspot"])

        self.client.post("/mcp/disconnect", json={"server_id": "meta"})
        disconnected_execution = self.client.post("/mcp/execute", json={"server": "meta", "tool": "campaign.list", "params": {}})
        self.assertEqual(disconnected_execution.status_code, 200)
        self.assertEqual(disconnected_execution.json()["status"], "finished")
        self.assertEqual(disconnected_execution.json()["output"]["mode"], "mock_contract")

        connected = self.client.post(
            "/mcp/connect",
            json={
                "server_id": "meta",
                "auth_type": "bearer",
                "credentials": {"access_token": "test-token", "ad_account_id": "act_123", "business_account_id": "biz_123"},
            },
        )
        self.assertEqual(connected.status_code, 200)
        self.assertTrue(connected.json()["connected"])

        health = self.client.get("/mcp/health?server_id=meta")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()[0]["authentication_status"], "configured")

        execution = self.client.post("/mcp/execute", json={"server": "meta", "tool": "campaign.list", "params": {}})
        self.assertEqual(execution.status_code, 200)
        self.assertEqual(execution.json()["status"], "finished")

        logs = self.client.get("/mcp/logs?server_id=meta")
        events = self.client.get("/mcp/events?server_id=meta")
        self.assertEqual(logs.status_code, 200)
        self.assertEqual(events.status_code, 200)
        self.assertTrue(logs.json())
        self.assertTrue(events.json())

        disconnected = self.client.post("/mcp/disconnect", json={"server_id": "meta"})
        self.assertEqual(disconnected.status_code, 200)
        self.assertEqual(disconnected.json()["status"], "disconnected")

        reconnected = self.client.post(
            "/mcp/connect",
            json={"server_id": "meta", "credentials": {"access_token": "test-token", "ad_account_id": "act_123"}},
        )
        self.assertEqual(reconnected.status_code, 200)
        self.assertTrue(reconnected.json()["connected"])


if __name__ == "__main__":
    unittest.main()
