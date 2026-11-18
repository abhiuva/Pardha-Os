"""PE0OM-75 (PE0OM-56 1/5): direct capability policy, plan/business consistency, queue
lifecycle and approval-decision integrity.

The "write-capable" capability used here is TEST-ONLY: it is registered with a mock
adapter injected into the server's adapter map, and deliberately declares a misleading
read-only permission, to prove the policy keys on server-side adapter code rather than
client-supplied registration metadata. No network or live connector is involved.
"""
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.capabilities.policy import VERIFIED_READ_ONLY_ADAPTERS
from app.db import SessionLocal, init_db
from app.db.models import CapabilityExecution as CapabilityExecutionModel
from app.db.models import ExecutionPlanNode as ExecutionPlanNodeModel
from app.db.models import PlanApproval as PlanApprovalModel
from app.db.models import RuntimeExecution as RuntimeExecutionModel
from app.db.models import RuntimeQueueItem as RuntimeQueueItemModel
from app.main import app

WRITE_PROBE = "test.write_probe"
MEDIUM_RISK_REQUEST = "Acquire 5 pilot customers"
LOW_RISK_REQUEST = "Summarize weekly status"


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        businesses = cls.client.get("/businesses").json()
        cls.dp360 = next(item for item in businesses if item["business_name"] == "DP360")["business_id"]
        cls.eatontime = next(item for item in businesses if item["business_name"] == "EatOnTime")["business_id"]

    def _plan(self, request: str, business_id: str | None = None, approve: bool = False) -> str:
        response = self.client.post("/planning/plan", json={"business_id": business_id or self.dp360, "request": request, "owner": "Founder", "approve": approve})
        self.assertEqual(response.status_code, 201)
        return response.json()["plan"]["plan_id"]

    def _decide(self, plan_id: str, decision: str, decided_by: str = "Founder"):
        return self.client.post(f"/planning/plans/{plan_id}/{decision}", json={"decided_by": decided_by, "comment": decision})

    def _queue_items(self) -> dict[str, dict]:
        return {item["queue_id"]: item for item in self.client.get(f"/runtime/queue?business_id={self.dp360}").json()}

    def _process(self) -> list[dict]:
        response = self.client.post(f"/runtime/queue/process?business_id={self.dp360}")
        self.assertEqual(response.status_code, 200)
        return response.json()


class DirectCapabilityPolicyTestCase(_Base):
    def setUp(self):
        self.write_adapter = MagicMock(return_value={"wrote": True})
        self.adapters = patch.dict("app.capabilities.executors.ADAPTERS", {WRITE_PROBE: self.write_adapter})
        self.adapters.start()
        registered = self.client.post(
            "/capabilities/register",
            json={
                "capability_id": WRITE_PROBE,
                "name": "Write probe (test only)",
                "description": "Test-only write-capable capability with a misleading read-only permission.",
                "supported_intents": ["write_probe"],
                "permissions": ["read:business"],
                "execution_adapter": WRITE_PROBE,
            },
        )
        self.assertEqual(registered.status_code, 201)

    def tearDown(self):
        self.adapters.stop()

    def test_write_probe_is_not_classified_read_only(self):
        self.assertNotIn(WRITE_PROBE, VERIFIED_READ_ONLY_ADAPTERS)

    def test_direct_queue_item_for_unclassified_capability_is_blocked_and_adapter_never_runs(self):
        queued = self.client.post("/runtime/queue", json={"business_id": self.dp360, "capability_id": WRITE_PROBE, "payload": {"x": 1}})
        self.assertEqual(queued.status_code, 201)

        processed = self._process()

        self.write_adapter.assert_not_called()
        execution = next(item for item in processed if item["current_capability"] == WRITE_PROBE)
        self.assertEqual(execution["status"], "blocked")
        self.assertEqual(execution["progress"], 0)
        self.assertEqual(self._queue_items()[queued.json()["queue_id"]]["status"], "blocked")
        with SessionLocal() as session:
            audit = session.query(CapabilityExecutionModel).filter(CapabilityExecutionModel.capability_id == WRITE_PROBE).all()
        self.assertTrue(audit and all(row.status == "denied" for row in audit))

    def test_kernel_endpoint_cannot_bypass_policy(self):
        response = self.client.post("/kernel/execute", json={"intent": "write_probe", "capability_id": WRITE_PROBE, "business_id": self.dp360})
        self.assertEqual(response.status_code, 403)
        self.write_adapter.assert_not_called()

    def test_intent_search_cannot_bypass_policy(self):
        response = self.client.post("/kernel/execute", json={"intent": "write_probe", "business_id": self.dp360, "payload": {"query": "write probe"}})
        self.assertIn(response.status_code, {403, 404})
        self.write_adapter.assert_not_called()

    def test_verified_read_only_capability_still_runs_from_the_queue(self):
        queued = self.client.post("/runtime/queue", json={"business_id": self.dp360, "capability_id": "projects.catalog"}).json()
        processed = self._process()
        execution = next(item for item in processed if item["current_capability"] == "projects.catalog")
        self.assertEqual(execution["status"], "completed")
        self.assertEqual(self._queue_items()[queued["queue_id"]]["status"], "completed")


class PlanBusinessConsistencyTestCase(_Base):
    def test_runtime_rejects_plan_from_another_business(self):
        plan_id = self._plan(LOW_RISK_REQUEST, business_id=self.eatontime)
        with SessionLocal() as session:
            before = session.query(RuntimeExecutionModel).filter(RuntimeExecutionModel.plan_id == plan_id).count()

        response = self.client.post("/runtime/executions", json={"business_id": self.dp360, "plan_id": plan_id, "priority": 90})

        self.assertEqual(response.status_code, 404)
        with SessionLocal() as session:
            self.assertEqual(session.query(RuntimeExecutionModel).filter(RuntimeExecutionModel.plan_id == plan_id).count(), before)

    def test_tampered_execution_business_is_blocked_at_run_time(self):
        plan_id = self._plan(LOW_RISK_REQUEST)
        started = self.client.post("/runtime/executions", json={"business_id": self.dp360, "plan_id": plan_id, "priority": 90}).json()
        with SessionLocal() as session:
            session.get(RuntimeExecutionModel, started["execution_id"]).business_id = self.eatontime
            session.commit()
        try:
            response = self.client.post(f"/runtime/executions/{started['execution_id']}/run")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "blocked")
            with SessionLocal() as session:
                outputs = [node.output for node in session.query(ExecutionPlanNodeModel).filter(ExecutionPlanNodeModel.plan_id == plan_id).all()]
            self.assertTrue(all(output is None for output in outputs))
        finally:
            # Remove only the deliberately tampered rows this test created (execution and its
            # queue item), so the shared test database keeps its invariants for other modules.
            with SessionLocal() as session:
                session.query(RuntimeQueueItemModel).filter(RuntimeQueueItemModel.execution_id == started["execution_id"]).delete()
                session.delete(session.get(RuntimeExecutionModel, started["execution_id"]))
                session.commit()


class QueueLifecycleTestCase(_Base):
    def test_queue_reports_blocked_waiting_failed_and_completed_without_reprocessing(self):
        rejected = self._plan(MEDIUM_RISK_REQUEST)
        self._decide(rejected, "reject")
        unapproved = self._plan(MEDIUM_RISK_REQUEST, approve=True)
        approved = self._plan(MEDIUM_RISK_REQUEST)
        self._decide(approved, "approve")

        def start(plan_id: str) -> str:
            response = self.client.post("/runtime/executions", json={"business_id": self.dp360, "plan_id": plan_id, "priority": 95})
            self.assertEqual(response.status_code, 201)
            return response.json()["execution_id"]

        executions = {"blocked": start(rejected), "waiting": start(unapproved), "completed": start(approved)}
        failing = MagicMock(side_effect=RuntimeError("adapter failure (test)"))
        with patch.dict("app.capabilities.executors.ADAPTERS", {"projects.catalog": failing}):
            failed_item = self.client.post("/runtime/queue", json={"business_id": self.dp360, "capability_id": "projects.catalog"}).json()
            self._process()

        by_execution = {item["execution_id"]: item for item in self._queue_items().values() if item["execution_id"]}
        for expected, execution_id in executions.items():
            with self.subTest(expected=expected):
                self.assertEqual(by_execution[execution_id]["status"], expected)
        self.assertEqual(self._queue_items()[failed_item["queue_id"]]["status"], "failed")

        # A second pass must not pick these items up again (no retry loop, no silent re-execution).
        failing.reset_mock()
        second_pass_ids = {item["execution_id"] for item in self._process()}
        self.assertFalse(second_pass_ids & set(executions.values()))
        failing.assert_not_called()


class QueueRobustnessTestCase(_Base):
    def test_orphaned_queue_item_is_marked_failed_and_does_not_jam_the_queue(self):
        orphan = self.client.post("/runtime/queue", json={"business_id": self.dp360, "capability_id": "projects.catalog"}).json()
        with SessionLocal() as session:
            row = session.get(RuntimeQueueItemModel, orphan["queue_id"])
            row.capability_id = None
            row.execution_id = "00000000-0000-0000-0000-000000000000"  # points at no execution
            session.commit()
        healthy = self.client.post("/runtime/queue", json={"business_id": self.dp360, "capability_id": "projects.catalog"}).json()

        processed = self.client.post(f"/runtime/queue/process?business_id={self.dp360}")

        self.assertEqual(processed.status_code, 200)
        items = self._queue_items()
        self.assertEqual(items[orphan["queue_id"]]["status"], "failed")
        self.assertEqual(items[healthy["queue_id"]]["status"], "completed")
        self.assertEqual(self.client.post(f"/runtime/queue/process?business_id={self.dp360}").status_code, 200)


class ApprovalDecisionIntegrityTestCase(_Base):
    def test_decisions_are_marked_unverified_and_not_write_authorizing(self):
        plan_id = self._plan(MEDIUM_RISK_REQUEST)
        approvals = self._decide(plan_id, "approve", decided_by="Someone claiming to be the founder").json()["approvals"]
        self.assertTrue(approvals)
        for approval in approvals:
            self.assertFalse(approval["decision_identity_verified"])
            self.assertFalse(approval["authorizes_external_writes"])

    def test_repeated_approval_records_a_single_decision(self):
        plan_id = self._plan(MEDIUM_RISK_REQUEST, approve=True)
        self._decide(plan_id, "approve")
        self._decide(plan_id, "approve")
        with SessionLocal() as session:
            statuses = [row.status for row in session.query(PlanApprovalModel).filter(PlanApprovalModel.plan_id == plan_id).all()]
        self.assertEqual(statuses, ["approved"])

    def test_rejection_after_approval_revokes_execution_permanently(self):
        plan_id = self._plan(MEDIUM_RISK_REQUEST)
        self.assertEqual(self._decide(plan_id, "approve").status_code, 200)
        self.assertEqual(self._decide(plan_id, "reject").status_code, 200)

        self.assertEqual(self.client.post(f"/planning/plans/{plan_id}/execute").status_code, 409)
        self.assertEqual(self._decide(plan_id, "approve").status_code, 409)
        self.assertEqual(self.client.post(f"/planning/plans/{plan_id}/execute").status_code, 409)

    def test_pending_medium_risk_plan_runs_no_capability(self):
        plan_id = self._plan(MEDIUM_RISK_REQUEST)
        with patch("app.planning.service.execute_capability") as planning_capability, patch("app.runtime.service.execute_capability") as runtime_capability:
            via_api = self.client.post(f"/planning/plans/{plan_id}/execute").json()
            started = self.client.post("/runtime/executions", json={"business_id": self.dp360, "plan_id": plan_id, "priority": 95}).json()
            self.client.post(f"/runtime/executions/{started['execution_id']}/run")
        self.assertEqual(via_api["status"], "waiting_approval")
        planning_capability.assert_not_called()
        runtime_capability.assert_not_called()


if __name__ == "__main__":
    unittest.main()
