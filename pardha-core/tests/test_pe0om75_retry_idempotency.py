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
from app.db.models import ToolRuntimeInvocation as ToolRuntimeInvocationModel
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


class _RuntimeTestBase(unittest.TestCase):
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


class RetryIdempotencyTestCase(_RuntimeTestBase):
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


class BlockingCapability:
    """The first call made by each thread named in `blockers` blocks until that thread is released;
    the blocked call can then fail. Every other call returns immediately. Outputs are tagged with the
    calling thread's name."""

    def __init__(self, blockers=("worker-A",), fail_after_release: bool = False):
        self.entered = {name: threading.Event() for name in blockers}
        self.release = {name: threading.Event() for name in blockers}
        self.fail_after_release = fail_after_release
        self.calls: list[tuple[str, str]] = []
        self.lock = threading.Lock()

    def __call__(self, request):
        name = threading.current_thread().name
        node_id = request.payload.get("node_id")
        with self.lock:
            first_block = name in self.entered and not self.entered[name].is_set()
            self.calls.append((name, node_id))
        if first_block:
            self.entered[name].set()
            self.release[name].wait(10)
            if self.fail_after_release:
                raise RuntimeError("stale worker failure (test)")
        return SimpleNamespace(status="succeeded", output={"by": name}, error=None, runtime_ms=1, execution_id=f"{name}-{node_id}")


class OwnershipRaceTestCase(_RuntimeTestBase):
    """Codex QA P1: rollback/retry while an attempt is running, and stale-worker fencing."""

    def _run_in_thread(self, execution_id: str, name: str = "worker-A"):
        outcome: dict = {}

        def target():
            try:
                outcome["result"] = runtime_service.run_execution(execution_id)
            except BaseException as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=target, name=name)
        thread.start()
        return thread, outcome

    def _simulate_ownership_transfer(self, execution_id: str) -> int:
        """What lease recovery must do: bump the attempt generation and make it runnable again."""
        with SessionLocal() as session:
            row = session.get(RuntimeExecutionModel, execution_id)
            self.assertEqual(row.status, "running")
            row.retries += 1
            row.status = "queued"
            session.commit()
            return row.retries

    def test_rollback_and_retry_of_a_running_execution_are_rejected(self):
        _, execution_id, nodes = self._plan_and_execution()
        self._cancel_initial_queue_row(execution_id)
        fake = BlockingCapability()
        with patch.object(runtime_service, "execute_capability", fake):
            thread, outcome = self._run_in_thread(execution_id)
            self.assertTrue(fake.entered["worker-A"].wait(10))
            rows_before = len(self._queue_rows(execution_id))

            self.assertEqual(self.client.post(f"/runtime/executions/{execution_id}/rollback").status_code, 409)
            retried = self.client.post(f"/runtime/executions/{execution_id}/retry")
            self.assertEqual((retried.status_code, retried.json()["status"]), (200, "running"))
            self.assertEqual(len(self._queue_rows(execution_id)), rows_before, "no retry may be queued while an attempt is active")
            runtime_service.process_queue(self.business)

            fake.release["worker-A"].set()
            thread.join(10)
        self.assertNotIn("error", outcome)
        self.assertEqual(outcome["result"].status, "completed")
        self.assertEqual(sorted(node for _, node in fake.calls), sorted(nodes), "each node exactly once")
        self.assertEqual(self.client.post(f"/runtime/executions/{execution_id}/rollback").json()["status"], "cancelled")
        self.assertEqual(self.client.post(f"/runtime/executions/{execution_id}/rollback").status_code, 200)  # idempotent

    def test_stale_worker_cannot_persist_results_after_ownership_changes(self):
        # Worst case: the stale attempt (A) and the new owner (B) are both inside capability calls,
        # and A tries to persist first, while the execution is still "running" (for B).
        _, execution_id, nodes = self._plan_and_execution()
        self._cancel_initial_queue_row(execution_id)
        fake = BlockingCapability(blockers=("worker-A", "worker-B"))
        with patch.object(runtime_service, "execute_capability", fake):
            thread_a, outcome_a = self._run_in_thread(execution_id, "worker-A")
            self.assertTrue(fake.entered["worker-A"].wait(10))
            new_generation = self._simulate_ownership_transfer(execution_id)
            thread_b, outcome_b = self._run_in_thread(execution_id, "worker-B")
            self.assertTrue(fake.entered["worker-B"].wait(10))
            fake.release["worker-A"].set()
            thread_a.join(10)
            fake.release["worker-B"].set()
            thread_b.join(10)
        self.assertNotIn("error", outcome_a)
        self.assertNotIn("error", outcome_b)
        self.assertEqual(outcome_b["result"].status, "completed")
        with SessionLocal() as session:
            execution = session.get(RuntimeExecutionModel, execution_id)
            self.assertEqual((execution.status, execution.retries), ("completed", new_generation))
            outputs = [session.get(ExecutionPlanNodeModel, node).output for node in nodes]
            invocations = session.query(ToolRuntimeInvocationModel).filter(ToolRuntimeInvocationModel.execution_id == execution_id).count()
        self.assertTrue(all(output["capability_execution_id"].startswith("worker-B-") for output in outputs), outputs)
        self.assertEqual(invocations, len(nodes), "the stale attempt's invocation records must be discarded")

    def test_stale_worker_failure_cannot_overwrite_a_newer_attempt(self):
        _, execution_id, _ = self._plan_and_execution()
        self._cancel_initial_queue_row(execution_id)
        fake = BlockingCapability(blockers=("worker-A", "worker-B"), fail_after_release=True)
        with patch.object(runtime_service, "execute_capability", fake):
            thread_a, outcome_a = self._run_in_thread(execution_id, "worker-A")
            self.assertTrue(fake.entered["worker-A"].wait(10))
            self._simulate_ownership_transfer(execution_id)
            thread_b, outcome_b = self._run_in_thread(execution_id, "worker-B")
            self.assertTrue(fake.entered["worker-B"].wait(10))
            fake.release["worker-A"].set()  # A fails while B still owns and runs the execution
            thread_a.join(10)
            with SessionLocal() as session:
                self.assertEqual(session.get(RuntimeExecutionModel, execution_id).status, "running", "stale failure overwrote the new owner")
            fake.fail_after_release = False
            fake.release["worker-B"].set()
            thread_b.join(10)
        self.assertIsInstance(outcome_a.get("error"), RuntimeError)
        self.assertNotIn("error", outcome_b)
        with SessionLocal() as session:
            self.assertEqual(session.get(RuntimeExecutionModel, execution_id).status, "completed")

    def test_worker_that_observed_an_old_generation_cannot_claim_after_a_retry(self):
        # Race window: a worker reads the execution (generation g), then a retry moves it to g+1
        # and queues it, then the worker tries to claim. The claim must fail, otherwise the stale
        # worker and the retry would both execute the capabilities.
        _, execution_id, nodes = self._plan_and_execution()
        self._cancel_initial_queue_row(execution_id)
        self._set_status(execution_id, "waiting")
        original_claim = runtime_service._claim_execution
        injected = {"done": False}

        def claim_after_concurrent_retry(exec_id, generation):
            if not injected["done"]:
                injected["done"] = True
                runtime_service.retry_execution(exec_id)  # ownership changes inside the window
            return original_claim(exec_id, generation)

        fake = CountingCapability()
        with patch.object(runtime_service, "execute_capability", fake), patch.object(runtime_service, "_claim_execution", claim_after_concurrent_retry):
            stale = runtime_service.run_execution(execution_id)
            self.assertEqual(stale.status, "queued")
            self.assertEqual(fake.calls, [], "the stale worker must not execute anything")
            runtime_service.process_queue(self.business)
        self.assertEqual(sorted(fake.calls), sorted(nodes))

    def test_no_capability_runs_twice_under_mixed_concurrent_run_retry_rollback_and_queue(self):
        _, execution_id, nodes = self._plan_and_execution()
        fake = CountingCapability(delay=0.02)
        errors: list[BaseException] = []
        actions = [
            lambda: runtime_service.run_execution(execution_id),
            lambda: runtime_service.process_queue(self.business),
            lambda: runtime_service.retry_execution(execution_id),
            lambda: runtime_service.rollback_execution(execution_id),
        ]

        def worker(index: int):
            for step in range(6):
                try:
                    actions[(index + step) % len(actions)]()
                except runtime_service.ExecutionStateConflict:
                    pass  # an expected, clean refusal
                except BaseException as exc:  # pragma: no cover
                    errors.append(exc)

        with patch.object(runtime_service, "execute_capability", fake):
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(30)
            runtime_service.process_queue(self.business)
        self.assertEqual(errors, [])
        duplicates = {node for node in fake.calls if fake.calls.count(node) > 1}
        self.assertEqual(duplicates, set(), "a capability node was executed more than once")
        with SessionLocal() as session:
            self.assertNotEqual(session.get(RuntimeExecutionModel, execution_id).status, "running")


if __name__ == "__main__":
    unittest.main()
