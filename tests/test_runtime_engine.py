import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_runtime_engine.db")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import RuntimeExecution, RuntimeNotification, RuntimeQueueItem, ToolRuntimeInvocation
from app.main import app


class RuntimeEngineTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        businesses = cls.client.get("/businesses").json()
        cls.dp360 = next(item for item in businesses if item["business_name"] == "DP360")
        cls.eot = next(item for item in businesses if item["business_name"] == "EatOnTime")

    def _approved_plan(self, business_id: str) -> str:
        plan = self.client.post(
            "/planning/plan",
            json={"business_id": business_id, "request": "Acquire 5 pilot customers", "owner": "Founder", "approve": True},
        )
        self.assertEqual(plan.status_code, 201)
        return plan.json()["plan"]["plan_id"]

    def test_universal_execution_queue_process_notifications_and_rollback(self):
        plan_id = self._approved_plan(self.dp360["business_id"])
        started = self.client.post("/runtime/executions", json={"business_id": self.dp360["business_id"], "plan_id": plan_id, "priority": 90})
        self.assertEqual(started.status_code, 201)
        execution_id = started.json()["execution_id"]
        self.assertEqual(started.json()["status"], "queued")

        queue = self.client.get(f"/runtime/queue?business_id={self.dp360['business_id']}")
        self.assertEqual(queue.status_code, 200)
        self.assertTrue(any(item["execution_id"] == execution_id for item in queue.json()))

        processed = self.client.post(f"/runtime/queue/process?business_id={self.dp360['business_id']}")
        self.assertEqual(processed.status_code, 200)
        execution = next(item for item in processed.json() if item["execution_id"] == execution_id)
        self.assertEqual(execution["status"], "completed")
        self.assertEqual(execution["progress"], 100)

        notifications = self.client.get(f"/runtime/notifications?business_id={self.dp360['business_id']}")
        self.assertEqual(notifications.status_code, 200)
        self.assertTrue(notifications.json())
        notification_id = notifications.json()[0]["notification_id"]
        read = self.client.post(f"/runtime/notifications/{notification_id}/read")
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()["status"], "read")

        rollback = self.client.post(f"/runtime/executions/{execution_id}/rollback")
        self.assertEqual(rollback.status_code, 200)
        self.assertEqual(rollback.json()["status"], "cancelled")
        self.assertTrue(rollback.json()["rollback"]["completed"])

        with SessionLocal() as session:
            self.assertIsNotNone(session.get(RuntimeExecution, execution_id))
            self.assertGreaterEqual(session.query(ToolRuntimeInvocation).filter(ToolRuntimeInvocation.business_id == self.dp360["business_id"]).count(), 1)
            self.assertGreaterEqual(session.query(RuntimeNotification).filter(RuntimeNotification.business_id == self.dp360["business_id"]).count(), 1)

    def test_departments_dashboard_automation_and_business_isolation(self):
        rule = self.client.post(
            "/runtime/automation/rules",
            json={"business_id": self.dp360["business_id"], "name": "Notify on Execution Completed", "trigger_event": "Execution Completed", "action": "notify_founder"},
        )
        self.assertEqual(rule.status_code, 201)

        plan_id = self._approved_plan(self.dp360["business_id"])
        started = self.client.post("/runtime/executions", json={"business_id": self.dp360["business_id"], "plan_id": plan_id, "priority": 80}).json()
        processed = self.client.post(f"/runtime/queue/process?business_id={self.dp360['business_id']}")
        self.assertEqual(processed.status_code, 200)

        departments = self.client.get(f"/runtime/departments?business_id={self.dp360['business_id']}")
        self.assertEqual(departments.status_code, 200)
        self.assertEqual(len(departments.json()), 9)
        self.assertTrue(any(item["name"] == "CEO" for item in departments.json()))

        dashboard = self.client.get(f"/runtime/dashboard?business_id={self.dp360['business_id']}")
        self.assertEqual(dashboard.status_code, 200)
        payload = dashboard.json()
        self.assertTrue(payload["executions"])
        self.assertIn("success_rate", payload["observability"])
        self.assertTrue(payload["business_timeline"])

        eot_dashboard = self.client.get(f"/runtime/dashboard?business_id={self.eot['business_id']}")
        self.assertEqual(eot_dashboard.status_code, 200)
        self.assertEqual(eot_dashboard.json()["executions"], [])
        self.assertNotEqual(self.dp360["business_id"], self.eot["business_id"])

        with SessionLocal() as session:
            self.assertEqual(
                session.query(RuntimeQueueItem).filter(RuntimeQueueItem.business_id == self.eot["business_id"]).count(),
                0,
            )

    def test_direct_tool_queue_uses_same_runtime_contract(self):
        queued = self.client.post(
            "/runtime/queue",
            json={"business_id": self.dp360["business_id"], "capability_id": "diagnostics.system_health", "priority": 75, "payload": {"query": "health"}},
        )
        self.assertEqual(queued.status_code, 201)
        self.assertEqual(queued.json()["capability_id"], "diagnostics.system_health")
        processed = self.client.post(f"/runtime/queue/process?business_id={self.dp360['business_id']}")
        self.assertEqual(processed.status_code, 200)
        self.assertTrue(any(item["status"] == "completed" for item in processed.json()))


if __name__ == "__main__":
    unittest.main()
