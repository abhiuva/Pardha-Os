"""PE0OM-75 Codex QA: a retry can never execute twice (immediate + queued paths), concurrent
run/retry/queue processing executes each node once, and high-risk nodes stay fail-closed.

Capability execution is replaced by a counting fake, so these tests count executions directly.
No adapter, connector or network is used.
"""
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import ExecutionPlanNode as ExecutionPlanNodeModel
from app.db.models import RuntimeExecution as RuntimeExecutionModel
from app.db.models import RuntimeQueueItem as RuntimeQueueItemModel
from app.main import app
from app.runtime import service as runtime_service

LOW_RISK_REQUEST = "Summarize weekly status"


class CountingCapability:
    def __init__(self, delay: float = 0.0):
        self.calls: list[str] = []
        self.delay = delay
        self.lock = threading.Lock()

    def __call__(self, request):
        if self.delay:
            time.sleep(self.delay)
        with self.lock:
            self.calls.append(request.payload.get("node_id"))
        return SimpleNamespace(status="succeeded", output={"fake": True}, error=None, runtime_ms=1, execution_id=f"fake-{len(self.calls)}")


class RetryIdempotencyTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        businesses = cls.client.get("/businesses").json()
        cls.business = next(item for item in businesses if item["business_name"] == "DP360")["business_id"]

    def tearDown(self):
        # Leave no queued work behind for other test modules sharing this disposable database.
        with SessionLocal() as session:
            for row in session.query(RuntimeQueueItemModel).filter(RuntimeQueueItemModel.execution_id.in_(self._executions)).all():
                if row.status in {"queued", "processing"}:
                    row.status = "cancelled"
            session.commit()

    def setUp(self):
        self._executions: list[str] = []

    # -- helpers -------------------------------------------------------------------------------
    def _plan_and_execution(self) -> tuple[str, str, list[str]]:
        plan = self.client.post("/planning/plan", json={"business_id": self.business, "request": LOW_RISK_REQUEST, "owner": "Founder"})
        self.assertEqual(plan.status_code, 201)
        plan_id = plan.json()["plan"]["plan_id"]
        started = self.client.post("/runtime/executions", json={"business_id": self.business, "plan_id": plan_id, "priority": 99})
        self.assertEqual(started.status_code, 201)
        execution_id = started.json()["execution_id"]
        self._executions.append(execution_id)
        with SessionLocal() as session:
            nodes = session.query(ExecutionPlanNodeModel).filter(ExecutionPlanNodeModel.plan_id == plan_id).all()
            capability_nodes = [node.node_id for node in nodes if node.capability_id and not node.approval_required]
        self.assertTrue(capability_nodes, "test plan needs at least one executable capability node")
        return plan_id, execution_id, capability_nodes

    def _set_status(self, execution_id: str, status: str) -> None:
        with SessionLocal() as session:
            session.get(RuntimeExecutionModel, execution_id).status = status
            session.commit()

    def _queue_rows(self, execution_id: str) -> list[RuntimeQueueItemModel]:
        with SessionLocal() as session:
            return session.query(RuntimeQueueItemModel).filter(RuntimeQueueItemModel.execution_id == execution_id).all()

    def _cancel_initial_queue_row(self, execution_id: str) -> None:
        with SessionLocal() as session:
            for row in session.query(RuntimeQueueItemModel).filter(RuntimeQueueItemModel.execution_id == execution_id).all():
                row.status = "cancelled"
            session.commit()

    # -- tests ---------------------------------------------------------------------------------
    def test_retry_executes_once_and_only_through_the_queue(self):
        _, execution_id, nodes = self._plan_and_execution()
        self._cancel_initial_queue_row(execution_id)
        self._set_status(execution_id, "failed")
        fake = CountingCapability()
        with patch.object(runtime_service, "execute_capability", fake):
            retried = self.client.post(f"/runtime/executions/{execution_id}/retry")
            self.assertEqual(retried.status_code, 200)
            self.assertEqual(retried.json()["status"], "queued")
            self.assertEqual(fake.calls, [], "retry must not also execute immediately")

            runtime_service.process_queue(self.business)
            self.assertEqual(sorted(fake.calls), sorted(nodes))

            runtime_service.process_queue(self.business)
            self.assertEqual(self.client.post(f"/runtime/executions/{execution_id}/retry").status_code, 409)
            runtime_service.process_queue(self.business)
        self.assertEqual(sorted(fake.calls), sorted(nodes), "a completed retry must never run again")

    def test_concurrent_retry_requests_queue_a_single_retry(self):
        _, execution_id, nodes = self._plan_and_execution()
        self._cancel_initial_queue_row(execution_id)
        self._set_status(execution_id, "failed")
        errors: list[BaseException] = []

        def retry():
            try:
                runtime_service.retry_execution(execution_id)
            except BaseException as exc:  # pragma: no cover - surfaced by the assertion below
                errors.append(exc)

        threads = [threading.Thread(target=retry) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        retry_rows = [row for row in self._queue_rows(execution_id) if (row.payload or {}).get("type") == "retry"]
        self.assertEqual(len(retry_rows), 1)
        with SessionLocal() as session:
            self.assertEqual(session.get(RuntimeExecutionModel, execution_id).retries, 1)

        fake = CountingCapability()
        with patch.object(runtime_service, "execute_capability", fake):
            runtime_service.process_queue(self.business)
        self.assertEqual(sorted(fake.calls), sorted(nodes))

    def test_concurrent_direct_runs_and_queue_processing_execute_each_node_once(self):
        _, execution_id, nodes = self._plan_and_execution()
        fake = CountingCapability(delay=0.05)
        errors: list[BaseException] = []

        def guarded(target):
            def run():
                try:
                    target()
                except BaseException as exc:  # pragma: no cover
                    errors.append(exc)
            return run

        with patch.object(runtime_service, "execute_capability", fake):
            threads = [threading.Thread(target=guarded(lambda: runtime_service.run_execution(execution_id))) for _ in range(4)]
            threads += [threading.Thread(target=guarded(lambda: runtime_service.process_queue(self.business))) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(sorted(fake.calls), sorted(nodes), "each node must execute exactly once")
        statuses = {row.status for row in self._queue_rows(execution_id)}
        self.assertTrue(statuses <= {"completed", "superseded"}, statuses)

    def test_rerun_after_completion_or_approval_follow_up_never_repeats_finished_nodes(self):
        _, execution_id, nodes = self._plan_and_execution()
        self._cancel_initial_queue_row(execution_id)
        fake = CountingCapability()
        with patch.object(runtime_service, "execute_capability", fake):
            self.assertEqual(runtime_service.run_execution(execution_id).status, "completed")
            self.assertEqual(runtime_service.run_execution(execution_id).status, "completed")  # not runnable: no-op
            self._set_status(execution_id, "waiting")  # e.g. a follow-up run after an approval
            runtime_service.run_execution(execution_id)
        self.assertEqual(sorted(fake.calls), sorted(nodes))

    def test_high_risk_node_never_runs_even_with_a_stored_approved_status(self):
        plan_id, execution_id, nodes = self._plan_and_execution()
        self._cancel_initial_queue_row(execution_id)
        high_risk = nodes[0]
        with SessionLocal() as session:
            node = session.get(ExecutionPlanNodeModel, high_risk)
            node.approval_required = 1
            node.status = "approved"  # no verified node-approval path exists; this must not unlock it
            session.commit()
        fake = CountingCapability()
        with patch.object(runtime_service, "execute_capability", fake):
            result = runtime_service.run_execution(execution_id)
        self.assertNotIn(high_risk, fake.calls)
        self.assertEqual(result.status, "waiting")


if __name__ == "__main__":
    unittest.main()
