import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_planning_engine.db")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import ExecutionPlan, ExecutionPlanNode, GoalKPI, PlanApproval, PlanExecution, PlanningGoal
from app.main import app


class PlanningEngineTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.business = next(item for item in cls.client.get("/businesses").json() if item["business_name"] == "DP360")

    def test_request_generates_goal_plan_graph_approvals_and_kpis(self):
        response = self.client.post(
            "/planning/plan",
            json={"business_id": self.business["business_id"], "request": "Acquire 5 pilot customers", "owner": "Founder"},
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        goal = payload["goal"]
        plan = payload["plan"]
        self.assertEqual(goal["business_id"], self.business["business_id"])
        self.assertEqual(goal["risk_level"], "medium")
        self.assertEqual(plan["status"], "waiting_approval")
        self.assertTrue(plan["approval_required"])
        self.assertGreaterEqual(len(plan["nodes"]), 5)
        self.assertTrue(plan["graph"]["nodes"])
        self.assertTrue(plan["graph"]["critical_path"])
        self.assertTrue(payload["approvals"])
        self.assertGreaterEqual(len(payload["kpis"]), 3)

        with SessionLocal() as session:
            self.assertIsNotNone(session.get(PlanningGoal, goal["goal_id"]))
            self.assertIsNotNone(session.get(ExecutionPlan, plan["plan_id"]))
            self.assertGreaterEqual(session.query(ExecutionPlanNode).filter(ExecutionPlanNode.plan_id == plan["plan_id"]).count(), 5)
            self.assertGreaterEqual(session.query(GoalKPI).filter(GoalKPI.goal_id == goal["goal_id"]).count(), 3)
            self.assertGreaterEqual(session.query(PlanApproval).filter(PlanApproval.plan_id == plan["plan_id"]).count(), 1)

    def test_approval_execution_timeline_and_daily_plan(self):
        created = self.client.post(
            "/planning/plan",
            json={"business_id": self.business["business_id"], "request": "Develop new EatOnTime feature", "owner": "Founder"},
        ).json()
        plan_id = created["plan"]["plan_id"]
        goal_id = created["goal"]["goal_id"]

        approvals = self.client.get(f"/planning/approvals?business_id={self.business['business_id']}")
        self.assertEqual(approvals.status_code, 200)
        self.assertTrue(any(item["plan_id"] == plan_id for item in approvals.json()))

        approved = self.client.post(f"/planning/plans/{plan_id}/approve", json={"decided_by": "Founder", "comment": "Proceed."})
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["plan"]["status"], "approved")

        execution = self.client.post(f"/planning/plans/{plan_id}/execute")
        self.assertEqual(execution.status_code, 201)
        self.assertIn(execution.json()["status"], {"completed", "waiting_approval"})

        timeline = self.client.get(f"/planning/goals/{goal_id}/timeline")
        self.assertEqual(timeline.status_code, 200)
        timeline_types = {item["event_type"] for item in timeline.json()}
        self.assertIn("plan_generated", timeline_types)
        self.assertIn("approval_approved", timeline_types)

        kpis = self.client.get(f"/planning/goals/{goal_id}/kpis")
        self.assertEqual(kpis.status_code, 200)
        self.assertTrue(kpis.json())

        daily = self.client.get(f"/planning/daily?business_id={self.business['business_id']}")
        self.assertEqual(daily.status_code, 200)
        self.assertTrue(daily.json()["ceo_priorities"])
        self.assertTrue(daily.json()["recommended_actions"])

        with SessionLocal() as session:
            self.assertGreaterEqual(session.query(PlanExecution).filter(PlanExecution.plan_id == plan_id).count(), 1)

    def test_conversation_turn_creates_executable_plan_not_text_only(self):
        response = self.client.post(
            "/conversations/messages",
            json={"business_id": self.business["business_id"], "message": "We need 5 eCommerce pilot customers."},
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn("Goal Created", payload["assistant_message"]["content"])
        self.assertIn("plan_id", payload["response"]["execution"])
        self.assertTrue(payload["response"]["execution"]["approval_required"])
        self.assertTrue(payload["response"]["next_recommended_actions"])
        timeline_types = {item["event_type"] for item in payload["timeline"]}
        self.assertIn("execution_plan", timeline_types)


if __name__ == "__main__":
    unittest.main()
