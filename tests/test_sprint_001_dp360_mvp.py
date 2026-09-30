import os
import json
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sprint_001_dp360_mvp.db")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")
os.environ.setdefault("PARDHA_CONNECTOR_MODE", "mock")

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.reasoning.context import build_business_context
from app.reasoning.gateway import reasoning_gateway


class Sprint001DP360MVPTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self.client.post("/demo/seed")

    def test_reasoning_gateway_runs_without_ollama(self):
        response = self.client.get("/ai/providers/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["active_provider"], "deterministic")
        providers = {item["provider"]: item for item in payload["providers"]}
        self.assertTrue(providers["deterministic"]["ready"])
        self.assertFalse(providers["ollama"]["ready"])

    def test_reasoning_gateway_falls_back_when_cloud_provider_is_unavailable(self):
        with patch.dict(os.environ, {"PARDHA_REASONING_PROVIDER": "openai", "PARDHA_REASONING_FALLBACK": "deterministic"}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            result = reasoning_gateway.generate("Recommend next step.", fallback="Use deterministic action plan.")

        self.assertEqual(result.provider, "deterministic")
        self.assertEqual(result.model, "pardha-deterministic-runtime")
        self.assertEqual(result.response, "Use deterministic action plan.")
        self.assertEqual(result.metadata["requested_provider"], "openai")
        self.assertEqual(result.metadata["fallback_provider"], "deterministic")

    def test_provider_status_honors_reasoning_provider_env(self):
        with patch.dict(os.environ, {"PARDHA_REASONING_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}, clear=False):
            response = self.client.get("/ai/providers/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["active_provider"], "openai")
        self.assertEqual(payload["provider_priority"][0], "openai")

    def test_reasoning_health_exposes_daily_budget_and_providers(self):
        reasoning_gateway.reset_usage()

        response = self.client.get("/reasoning/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["selected_provider"], "deterministic")
        self.assertEqual(payload["fallback_provider"], "deterministic")
        self.assertIn("daily_budget", payload)
        self.assertEqual(payload["daily_budget"]["requests_used"], 0)
        self.assertIn("deterministic", payload["providers"])

    def test_provider_status_includes_daily_usage_counters(self):
        reasoning_gateway.reset_usage()
        reasoning_gateway.generate("Track this usage.", fallback="Tracked.")

        response = self.client.get("/ai/providers/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("daily_budget", payload)
        self.assertGreaterEqual(payload["daily_budget"]["requests_used"], 1)
        self.assertIn("deterministic", payload["daily_budget"]["provider_usage"])

    def test_daily_budget_cap_forces_deterministic_fallback(self):
        reasoning_gateway.reset_usage()
        with patch.dict(os.environ, {"PARDHA_REASONING_PROVIDER": "openai", "PARDHA_REASONING_FALLBACK": "deterministic", "PARDHA_MAX_DAILY_REASONING_REQUESTS": "1"}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            first = reasoning_gateway.generate("First call.", fallback="First fallback.")
            second = reasoning_gateway.generate("Second call.", fallback="Budget fallback.")

        self.assertEqual(first.provider, "deterministic")
        self.assertEqual(second.provider, "deterministic")
        self.assertEqual(second.response, "Budget fallback.")
        self.assertTrue(second.metadata["daily_budget_exceeded"])
        self.assertEqual(second.metadata["fallback_reason"], "daily_reasoning_budget_exceeded")

    def test_agents_do_not_import_ollama_client_directly(self):
        agent_files = Path("app/agents").glob("*.py")
        offenders = [str(path) for path in agent_files if "app.reasoning.client" in path.read_text()]

        self.assertEqual(offenders, [])

    def test_dp360_command_center_is_populated(self):
        response = self.client.get("/commercial/dp360-command-center")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["workspace"]["business_name"], "DP360")
        self.assertFalse(payload["controls"]["ollama_required"])
        self.assertEqual(payload["controls"]["destructive_external_writes"], "blocked_without_founder_approval")
        self.assertGreater(payload["execution"]["counts"]["knowledge"], 0)
        self.assertIn("ceo", payload["departments"])
        self.assertIn("pm", payload["departments"])
        self.assertIn("cto", payload["departments"])
        self.assertIn("marketing", payload["departments"])
        self.assertIn("sales", payload["departments"])

    def test_dp360_knowledge_summary_exposes_source_and_version_metadata(self):
        response = self.client.get("/knowledge/summary?business_name=DP360")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["business_name"], "DP360")
        self.assertGreaterEqual(payload["total_records"], 5)
        self.assertTrue(payload["context_ready"])
        self.assertIn("product", payload["categories"])
        source_uris = {item["source_uri"] for item in payload["sources"]}
        self.assertIn("dp360/product_overview.json", source_uris)
        self.assertIn("dp360/architecture.json", source_uris)
        self.assertEqual(payload["missing_expected_sources"], [])

    def test_business_context_contains_dp360_knowledge_metadata(self):
        summary = self.client.get("/knowledge/summary?business_name=DP360").json()

        context = json.loads(build_business_context(business_id=summary["business_id"]))

        self.assertEqual(context["knowledge_context"]["business_name"], "DP360")
        self.assertEqual(context["knowledge_context"]["source"], "postgresql_knowledge_store")
        self.assertTrue(context["knowledge_context"]["context_ready"])
        self.assertIn("dp360/product_overview.json", context["knowledge_context"]["expected_sources"])
        self.assertTrue(any(item["source_uri"] == "dp360/roadmap.json" for item in context["business_knowledge"]))

    def test_agent_prompt_receives_dp360_context_metadata(self):
        summary = self.client.get("/knowledge/summary?business_name=DP360").json()
        captured = {}

        def capture(prompt, system_prompt=None, model=None, fallback=None, provider=None):
            captured["prompt"] = prompt
            return reasoning_gateway._provider("deterministic").generate(prompt, system_prompt, model, fallback)

        with patch("app.reasoning.service.reasoning_gateway.generate", side_effect=capture):
            self.client.post("/agents/ceo/reason", json={"business_id": summary["business_id"]})

        self.assertIn("knowledge_context", captured["prompt"])
        self.assertIn("postgresql_knowledge_store", captured["prompt"])
        self.assertIn("dp360/product_overview.json", captured["prompt"])

    def test_commercial_connectors_have_mock_or_real_data_paths(self):
        response = self.client.get("/commercial/connectors/status")

        self.assertEqual(response.status_code, 200)
        statuses = {item["provider"]: item for item in response.json()}
        for provider in ("hubspot", "meta", "instagram"):
            self.assertIn(provider, statuses)
            self.assertFalse(statuses[provider]["connected"])
            self.assertEqual(statuses[provider]["health"], "mock")
            self.assertEqual(statuses[provider]["authentication_status"], "mock_contract")

    def test_mcp_runtime_discovers_hubspot_meta_and_instagram_tools(self):
        response = self.client.get("/mcp/discovery")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        servers = {item["server_id"] for item in payload["servers"]}
        tools = {item["name"] for item in payload["tools"]}
        self.assertIn("hubspot", servers)
        self.assertIn("meta", servers)
        self.assertIn("contact.list", tools)
        self.assertIn("deal.list", tools)
        self.assertIn("campaign.list", tools)
        self.assertIn("instagram.media.list", tools)

    def test_mcp_read_calls_work_in_mock_contract_mode(self):
        self.client.post("/mcp/disconnect", json={"server_id": "meta"})
        self.client.post("/mcp/disconnect", json={"server_id": "hubspot"})
        meta = self.client.post("/mcp/execute", json={"server": "meta", "tool": "instagram.insights.summary", "params": {}})
        hubspot = self.client.post("/mcp/execute", json={"server": "hubspot", "tool": "deal.list", "params": {}})

        self.assertEqual(meta.status_code, 200)
        self.assertEqual(hubspot.status_code, 200)
        self.assertEqual(meta.json()["status"], "finished")
        self.assertEqual(hubspot.json()["status"], "finished")
        self.assertEqual(meta.json()["output"]["mode"], "mock_contract")
        self.assertEqual(hubspot.json()["output"]["mode"], "mock_contract")


if __name__ == "__main__":
    unittest.main()
