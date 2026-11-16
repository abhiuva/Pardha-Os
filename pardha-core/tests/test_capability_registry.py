import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_capability_registry.db")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import Capability, CapabilityExecution
from app.main import app


class CapabilityRegistryTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.business = cls.client.get("/businesses").json()[0]

    def test_default_capabilities_register_and_health_is_available(self):
        response = self.client.get("/capabilities")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        capability_ids = {item["capability_id"] for item in payload}
        self.assertIn("ceo.daily_brief", capability_ids)
        self.assertIn("pm.daily_brief", capability_ids)
        self.assertIn("cto.technical_brief", capability_ids)
        self.assertIn("knowledge.search", capability_ids)
        self.assertIn("diagnostics.system_health", capability_ids)

        health = self.client.get("/capabilities/health")
        self.assertEqual(health.status_code, 200)
        self.assertGreaterEqual(health.json()["total"], 10)

        with SessionLocal() as session:
            self.assertGreaterEqual(session.query(Capability).count(), 10)

    def test_kernel_ranks_capabilities_without_concrete_agent_routes(self):
        response = self.client.get("/capabilities/search?intent=architecture_review&query=Review%20backend&business_domain=engineering")
        self.assertEqual(response.status_code, 200)
        candidates = response.json()["candidates"]
        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["capability"]["capability_id"], "cto.technical_brief")
        self.assertGreater(candidates[0]["confidence"], 0)
        self.assertIn("exact_intent_match", candidates[0]["reasons"])

    def test_kernel_executes_selected_capability_and_records_history(self):
        response = self.client.post(
            "/kernel/execute",
            json={
                "intent": "system_health",
                "capability_id": "diagnostics.system_health",
                "business_id": self.business["business_id"],
                "payload": {},
            },
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["capability_id"], "diagnostics.system_health")
        self.assertEqual(payload["status"], "succeeded")
        self.assertIn("backend", payload["output"])

        with SessionLocal() as session:
            self.assertIsNotNone(session.get(CapabilityExecution, payload["execution_id"]))
            capability = session.get(Capability, "diagnostics.system_health")
            self.assertGreaterEqual(capability.execution_count, 1)

    def test_developer_can_register_search_and_unregister_future_capability(self):
        registration = {
            "capability_id": "future.plugin.demo",
            "name": "Future Plugin Demo",
            "version": "0.1.0",
            "description": "External plugin capability used to prove dynamic registration.",
            "supported_intents": ["future_plugin_test"],
            "business_domains": ["all"],
            "required_inputs": ["business_id"],
            "outputs": ["demo_result"],
            "dependencies": ["external_plugin"],
            "permissions": ["read:business"],
            "health": "healthy",
            "supports_hitl": True,
            "supports_streaming": False,
            "supports_learning": False,
            "priority": 99,
            "estimated_runtime_ms": 25,
            "registration_method": "manual",
            "current_status": "registered",
            "planner_interface": {"input_schema": "business_id", "output_schema": "demo_result"},
        }
        created = self.client.post("/capabilities/register", json=registration)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["capability_id"], "future.plugin.demo")

        search = self.client.post("/kernel/resolve", json={"intent": "future_plugin_test", "query": "future plugin", "max_results": 3})
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.json()["candidates"][0]["capability"]["capability_id"], "future.plugin.demo")

        unregister = self.client.post("/capabilities/unregister?capability_id=future.plugin.demo")
        self.assertEqual(unregister.status_code, 200)
        self.assertTrue(unregister.json()["unregistered"])

    def test_graph_and_validation_report_are_available(self):
        graph = self.client.get("/capabilities/graph")
        self.assertEqual(graph.status_code, 200)
        self.assertTrue(graph.json()["nodes"])
        self.assertTrue(graph.json()["edges"])

        validation = self.client.get("/capabilities/validation")
        self.assertEqual(validation.status_code, 200)
        payload = validation.json()
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["missing_required_fields"], [])


if __name__ == "__main__":
    unittest.main()
