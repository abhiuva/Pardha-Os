import unittest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import AgentReasoning as AgentReasoningModel
from app.main import app
from app.reasoning.client import OllamaUnavailable, ensure_ollama_running, generate_response, switch_model
from app.reasoning.gateway import ReasoningGatewayResult
from app.reasoning.service import get_reasoning, reason_for_agent


class ReasoningTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        switch_model("qwen3:8b")
        with SessionLocal() as session:
            session.query(AgentReasoningModel).delete()
            session.commit()

    def tearDown(self):
        with SessionLocal() as session:
            session.query(AgentReasoningModel).delete()
            session.commit()

    @patch("app.reasoning.service.build_business_context", return_value='{"active_objectives": []}')
    @patch("app.reasoning.service.reasoning_gateway.generate", return_value=ReasoningGatewayResult(response="Use a three-school pilot with measurable targets.", provider="ollama", model="qwen3:8b", source="ollama", metadata={"provider": "ollama", "fallback_used": False}))
    def test_persists_local_ollama_reasoning(self, gateway_generate, _context):
        reasoning = reason_for_agent("ceo", "fallback")

        self.assertEqual(reasoning.source, "ollama")
        self.assertEqual(reasoning.model, "qwen3:8b")
        self.assertEqual(reasoning.provider_metadata["provider"], "ollama")
        self.assertIn("three-school pilot", reasoning.response)
        self.assertIn("strategic analysis", reasoning.prompt)
        gateway_generate.assert_called_once()

    @patch("app.reasoning.service.build_business_context", return_value='{"active_objectives": []}')
    @patch("app.reasoning.service.reasoning_gateway.generate", return_value=ReasoningGatewayResult(response="Review architecture boundaries.", provider="deterministic", model="pardha-deterministic-runtime", source="deterministic_fallback", metadata={"requested_provider": "ollama", "fallback_provider": "deterministic", "fallback_reason": "offline"}))
    def test_persists_deterministic_fallback_when_ollama_is_unavailable(self, _generate, _context):
        reasoning = reason_for_agent("cto", "Review architecture boundaries.")

        self.assertEqual(reasoning.source, "deterministic_fallback")
        self.assertEqual(reasoning.model, "pardha-deterministic-runtime")
        self.assertEqual(reasoning.response, "Review architecture boundaries.")
        self.assertEqual(reasoning.provider_metadata["fallback_provider"], "deterministic")

    @patch("app.reasoning.service.build_business_context", return_value='{"active_objectives": []}')
    @patch("app.reasoning.service.reasoning_gateway.generate", return_value=ReasoningGatewayResult(response="Prioritize the pilot backlog.", provider="ollama", model="qwen3:8b", source="ollama", metadata={"provider": "ollama"}))
    def test_agent_reasoning_endpoints_return_filtered_history(self, _generate, _context):
        reason_for_agent("pm", "fallback")
        reason_for_agent("ceo", "fallback")

        pm_response = self.client.get("/agents/pm/reasoning")
        ceo_response = self.client.get("/agents/ceo/reasoning")

        self.assertEqual(pm_response.status_code, 200)
        self.assertEqual(ceo_response.status_code, 200)
        self.assertEqual([item["agent_name"] for item in pm_response.json()], ["pm"])
        self.assertEqual([item["agent_name"] for item in ceo_response.json()], ["ceo"])
        self.assertEqual(len(get_reasoning("pm")), 1)

    @patch("app.reasoning.service.build_business_context", return_value='{"active_objectives": []}')
    @patch("app.reasoning.service.reasoning_gateway.generate", return_value=ReasoningGatewayResult(response="Manual CEO recommendation.", provider="ollama", model="llama3.2:3b", source="ollama", metadata={"provider": "ollama"}))
    def test_manual_reasoning_endpoint_invokes_default_model(self, generate, _context):
        response = self.client.post("/agents/ceo/reason")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "llama3.2:3b")
        self.assertEqual(response.json()["source"], "ollama")
        self.assertEqual(generate.call_args.args[2], "llama3.2:3b")

    @patch("app.reasoning.service.build_business_context", return_value='{"active_objectives": []}')
    @patch("app.reasoning.service.reasoning_gateway.generate", return_value=ReasoningGatewayResult(response="Advanced CTO recommendation.", provider="ollama", model="qwen3:8b", source="ollama", metadata={"provider": "ollama"}))
    def test_advanced_model_requires_explicit_request(self, generate, _context):
        response = self.client.post("/agents/cto/reason", json={"model": "qwen3:8b"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "qwen3:8b")
        self.assertEqual(generate.call_args.args[2], "qwen3:8b")

    @patch("app.reasoning.service.reasoning_gateway.generate")
    def test_briefs_and_objectives_never_invoke_ollama(self, generate):
        self.client.get("/agents/ceo/brief")
        self.client.get("/agents/cto/brief")
        self.client.get("/agents/pm/brief")
        response = self.client.post(
            "/objectives",
            json={
                "title": "Run deterministic objective",
                "description": "Verify automatic workflows remain deterministic.",
                "business_name": "DP360",
                "priority": "medium",
            },
        )

        self.assertEqual(response.status_code, 201)
        generate.assert_not_called()

    @patch("app.reasoning.client._enabled", return_value=True)
    @patch("app.reasoning.client._request", return_value={"response": "Resource controlled."})
    def test_client_unloads_model_after_manual_response(self, request, _enabled):
        response = generate_response("Analyze this.")

        self.assertEqual(response, "Resource controlled.")
        payload = request.call_args.args[1]
        self.assertEqual(payload["model"], "qwen3:8b")
        self.assertEqual(payload["keep_alive"], "90s")
        self.assertEqual(payload["options"]["num_ctx"], 4096)

    @patch("app.reasoning.client._enabled", return_value=True)
    def test_only_one_reasoning_request_runs_at_a_time(self, _enabled):
        state_lock = threading.Lock()
        active = 0
        maximum = 0

        def request(path, payload=None):
            nonlocal active, maximum
            if path != "/api/generate":
                return {"models": []}
            with state_lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.05)
            with state_lock:
                active -= 1
            return {"response": "done"}

        with patch("app.reasoning.client._request", side_effect=request):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(generate_response, ["first", "second"]))

        self.assertEqual(results, ["done", "done"])
        self.assertEqual(maximum, 1)

    @patch("app.reasoning.client.time.sleep")
    @patch("app.reasoning.client.subprocess.Popen")
    @patch("app.reasoning.client.shutil.which", return_value="/opt/homebrew/bin/ollama")
    @patch("app.reasoning.client._enabled", return_value=True)
    def test_manual_reasoning_starts_local_ollama_on_demand(self, _enabled, _which, popen, _sleep):
        calls = [
            OllamaUnavailable("offline"),
            OllamaUnavailable("offline"),
            {"models": []},
        ]
        with patch("app.reasoning.client._request", side_effect=calls):
            ensure_ollama_running()

        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ["/opt/homebrew/bin/ollama", "serve"])

    def test_ollama_status_endpoint_is_available(self):
        response = self.client.get("/system/ollama/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "qwen3:8b")
        self.assertIn(response.json()["state"], {"Running", "Idle", "Disabled"})
        self.assertEqual(response.json()["max_concurrent_reasoning"], 1)
        self.assertIn("connected", response.json())
        self.assertIn("latency_ms", response.json())
        self.assertEqual(response.json()["context_size"], 4096)

    @patch("app.reasoning.client._enabled", return_value=True)
    @patch("app.reasoning.client._request", return_value={"models": [{"name": "qwen3:8b"}]})
    def test_model_manager_switch_endpoint(self, _request, _enabled):
        response = self.client.post("/system/ollama/switch", json={"model": "llama3.2:3b"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "llama3.2:3b")

    def test_voice_runtime_validation_runs_100_scenarios(self):
        response = self.client.get("/conversations/voice-validation")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scenarios_run"], 100)
        self.assertIn("microphone", response.json()["categories"])


if __name__ == "__main__":
    unittest.main()
