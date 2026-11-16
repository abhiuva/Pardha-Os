import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.executions import clear_executions, get_executions
from app.agents.scheduler import run_agent_cycle
from app.db import init_db
from app.main import app


class AgentSchedulerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        clear_executions()
        self.client = TestClient(app)

    def tearDown(self):
        clear_executions()

    @patch("app.agents.scheduler.AGENT_WORKFLOW")
    def test_cycle_runs_agents_in_order_and_persists_outputs(self, workflow):
        calls = []

        def output_for(agent_name):
            def generate():
                calls.append(agent_name)
                return _Output({"agent": agent_name})
            return generate

        workflow.__iter__.return_value = iter(
            [
                ("ceo", output_for("ceo")),
                ("cto", output_for("cto")),
                ("pm", output_for("pm")),
            ]
        )

        run_agent_cycle()

        executions = get_executions()
        self.assertEqual(calls, ["ceo", "cto", "pm"])
        self.assertEqual(len(executions), 3)
        self.assertEqual({execution.status for execution in executions}, {"succeeded"})
        self.assertEqual(len({execution.cycle_id for execution in executions}), 1)
        self.assertEqual({execution.output["agent"] for execution in executions}, {"ceo", "cto", "pm"})

    @patch("app.agents.scheduler.AGENT_WORKFLOW")
    def test_cycle_records_failure_and_continues(self, workflow):
        calls = []

        def fail():
            calls.append("ceo")
            raise RuntimeError("CEO failed")

        def succeed():
            calls.append("cto")
            return _Output({"agent": "cto"})

        workflow.__iter__.return_value = iter([("ceo", fail), ("cto", succeed)])

        run_agent_cycle()

        executions = get_executions()
        self.assertEqual(calls, ["ceo", "cto"])
        self.assertEqual(get_executions("ceo")[0].status, "failed")
        self.assertEqual(get_executions("ceo")[0].error, "CEO failed")
        self.assertEqual(get_executions("cto")[0].status, "succeeded")
        self.assertEqual(len(executions), 2)

    @patch("app.agents.scheduler.AGENT_WORKFLOW")
    def test_execution_endpoints_return_history_and_filter_by_agent(self, workflow):
        workflow.__iter__.return_value = iter(
            [("ceo", lambda: _Output({"agent": "ceo"})), ("pm", lambda: _Output({"agent": "pm"}))]
        )
        run_agent_cycle()

        all_response = self.client.get("/agents/executions")
        ceo_response = self.client.get("/agents/executions/CEO")

        self.assertEqual(all_response.status_code, 200)
        self.assertEqual(len(all_response.json()), 2)
        self.assertEqual(ceo_response.status_code, 200)
        self.assertEqual(len(ceo_response.json()), 1)
        self.assertEqual(ceo_response.json()[0]["agent_name"], "ceo")

    @patch("app.reasoning.gateway.generate_response")
    def test_normal_cycle_never_invokes_ollama(self, generate):
        run_agent_cycle()

        generate.assert_not_called()
        self.assertEqual(len(get_executions()), 3)


class _Output:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, mode):
        self.mode = mode
        return self.payload


if __name__ == "__main__":
    unittest.main()
