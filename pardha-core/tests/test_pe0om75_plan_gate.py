"""PE0OM-75 (PE0OM-56 1/5): plans run only after an explicit, recorded founder approval.

Covers both execution paths: POST /planning/plans/{id}/execute and the runtime queue
(POST /runtime/executions + POST /runtime/queue/process).
"""
import unittest

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import ExecutionPlanNode as ExecutionPlanNodeModel
from app.db.models import PlanApproval as PlanApprovalModel
from app.main import app

MEDIUM_RISK_REQUEST = "Acquire 5 pilot customers"  # "acquire" is a medium-risk term
LOW_RISK_REQUEST = "Summarize weekly status"


class PlanExecutionGateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        businesses = cls.client.get("/businesses").json()
        cls.business_id = next(item for item in businesses if item["business_name"] == "DP360")["business_id"]

    def _create(self, request: str, approve: bool = False) -> dict:
        response = self.client.post(
            "/planning/plan",
            json={"business_id": self.business_id, "request": request, "owner": "Founder", "approve": approve},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["plan"]

    def _node_snapshot(self, plan_id: str) -> list[tuple[str, str, object]]:
        with SessionLocal() as session:
            nodes = session.query(ExecutionPlanNodeModel).filter(ExecutionPlanNodeModel.plan_id == plan_id).order_by(ExecutionPlanNodeModel.node_id).all()
            return [(node.node_id, node.status, node.output) for node in nodes]

    def _decide(self, plan_id: str, decision: str):
        return self.client.post(f"/planning/plans/{plan_id}/{decision}", json={"decided_by": "Founder", "comment": decision})

    # --- Rejected plans (Codex PR #1 QA finding D2) ---------------------------------

    def test_rejected_plan_executes_no_nodes_via_planning_api(self):
        plan = self._create(MEDIUM_RISK_REQUEST)
        self.assertEqual(plan["risk_level"], "medium")
        self.assertEqual(self._decide(plan["plan_id"], "reject").status_code, 200)
        before = self._node_snapshot(plan["plan_id"])

        response = self.client.post(f"/planning/plans/{plan['plan_id']}/execute")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self._node_snapshot(plan["plan_id"]), before)
        refreshed = self.client.get(f"/planning/plans/{plan['plan_id']}").json()["plan"]
        self.assertEqual(refreshed["status"], "rejected")
        self.assertEqual(refreshed["progress"], 0)

    def test_rejected_plan_executes_no_nodes_via_runtime_queue(self):
        plan = self._create(MEDIUM_RISK_REQUEST)
        self._decide(plan["plan_id"], "reject")
        before = self._node_snapshot(plan["plan_id"])

        started = self.client.post("/runtime/executions", json={"business_id": self.business_id, "plan_id": plan["plan_id"], "priority": 99})
        self.assertEqual(started.status_code, 201)
        processed = self.client.post(f"/runtime/queue/process?business_id={self.business_id}")
        self.assertEqual(processed.status_code, 200)
        execution = next(item for item in processed.json() if item["execution_id"] == started.json()["execution_id"])

        self.assertEqual(execution["status"], "blocked")
        self.assertEqual(execution["progress"], 0)
        self.assertEqual(self._node_snapshot(plan["plan_id"]), before)
        self.assertEqual(self.client.get(f"/planning/plans/{plan['plan_id']}").json()["plan"]["status"], "rejected")

    def test_rejected_plan_cannot_be_reapproved(self):
        plan = self._create(MEDIUM_RISK_REQUEST)
        self._decide(plan["plan_id"], "reject")

        self.assertEqual(self._decide(plan["plan_id"], "approve").status_code, 409)
        self.assertEqual(self.client.post(f"/planning/plans/{plan['plan_id']}/execute").status_code, 409)

    # --- Approval cannot be skipped at creation time ---------------------------------

    def test_create_time_approve_flag_does_not_authorize_execution(self):
        plan = self._create(MEDIUM_RISK_REQUEST, approve=True)
        before = self._node_snapshot(plan["plan_id"])

        response = self.client.post(f"/planning/plans/{plan['plan_id']}/execute")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "waiting_approval")
        self.assertEqual(response.json()["progress"], 0)
        self.assertEqual(self._node_snapshot(plan["plan_id"]), before)

    def test_create_time_approve_flag_does_not_authorize_runtime_execution(self):
        plan = self._create(MEDIUM_RISK_REQUEST, approve=True)
        before = self._node_snapshot(plan["plan_id"])

        started = self.client.post("/runtime/executions", json={"business_id": self.business_id, "plan_id": plan["plan_id"], "priority": 99}).json()
        processed = self.client.post(f"/runtime/queue/process?business_id={self.business_id}").json()
        execution = next(item for item in processed if item["execution_id"] == started["execution_id"])

        self.assertEqual(execution["status"], "waiting")
        self.assertEqual(execution["progress"], 0)
        self.assertEqual(self._node_snapshot(plan["plan_id"]), before)

    # --- Positive paths stay working ---------------------------------------------------

    def test_explicitly_approved_plan_executes_and_decision_is_recorded(self):
        plan = self._create(MEDIUM_RISK_REQUEST, approve=True)
        self.assertEqual(self._decide(plan["plan_id"], "approve").status_code, 200)

        with SessionLocal() as session:
            decisions = session.query(PlanApprovalModel).filter(PlanApprovalModel.plan_id == plan["plan_id"]).all()
            self.assertEqual([row.status for row in decisions], ["approved"])
            self.assertIsNotNone(decisions[0].decided_at)

        response = self.client.post(f"/planning/plans/{plan['plan_id']}/execute")
        self.assertEqual(response.status_code, 201)
        self.assertGreater(response.json()["progress"], 0)

    def test_low_risk_plan_without_approval_still_executes(self):
        plan = self._create(LOW_RISK_REQUEST)
        self.assertEqual(plan["risk_level"], "low")

        response = self.client.post(f"/planning/plans/{plan['plan_id']}/execute")

        self.assertEqual(response.status_code, 201)
        self.assertGreater(response.json()["progress"], 0)


if __name__ == "__main__":
    unittest.main()
