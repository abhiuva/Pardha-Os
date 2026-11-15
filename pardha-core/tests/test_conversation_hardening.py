import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_conversation_hardening.db")

from fastapi.testclient import TestClient

from app.capabilities.service import ensure_default_capabilities, get_capability
from app.db import SessionLocal, init_db
from app.db.models import FounderOperationalLearning
from app.main import app
from app.reasoning.gateway import ReasoningGatewayResult


class ConversationHardeningTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        ensure_default_capabilities()
        cls.client = TestClient(app)
        cls.business = next(item for item in cls.client.get("/businesses").json() if item["business_name"] == "DP360")

    def test_response_composer_hides_internal_language_and_exposes_transparency(self):
        response = self.client.post(
            "/conversations/messages",
            json={"business_id": self.business["business_id"], "message": "Review backend architecture"},
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        content = payload["assistant_message"]["content"].lower()
        self.assertNotIn("i routed", content)
        self.assertNotIn("capability executed", content)
        self.assertNotIn("capability_id", content)
        self.assertEqual(payload["response"]["response_style"], "executive")
        self.assertIn("transparency", payload["response"])
        self.assertTrue(payload["response"]["verification"]["founder_safe"])
        self.assertTrue(payload["response"]["verification"]["runtime_inspected"])

    def test_runtime_inspector_answers_what_can_you_do_from_live_state(self):
        response = self.client.post(
            "/conversations/messages",
            json={"message": "What can you do?"},
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        content = payload["assistant_message"]["content"]
        self.assertIn("Here is what I can do right now", content)
        self.assertIn("internal operating paths", content)
        self.assertIn("runtime_inspection", payload["response"])
        self.assertFalse(payload["response"]["verification"]["static_response"])

    def test_connector_diagnostic_returns_root_cause_and_fix(self):
        response = self.client.post(
            "/conversations/messages",
            json={"message": "How do I connect Gmail?"},
        )
        self.assertEqual(response.status_code, 201)
        content = response.json()["assistant_message"]["content"]
        self.assertIn("Gmail is not connected", content)
        self.assertIn("Root cause", content)
        self.assertIn("Set", content)

    def test_hardening_capabilities_are_registered_and_learning_persists(self):
        for capability_id in (
            "conversation.response_composer",
            "conversation.runtime_inspector",
            "conversation.operational_learning",
        ):
            self.assertIsNotNone(get_capability(capability_id))

        response = self.client.post(
            "/conversations/messages",
            json={"business_id": self.business["business_id"], "message": "Generate daily executive brief"},
        )
        self.assertEqual(response.status_code, 201)
        conversation_id = response.json()["conversation"]["conversation_id"]
        with SessionLocal() as session:
            signals = (
                session.query(FounderOperationalLearning)
                .filter(FounderOperationalLearning.source_conversation_id == conversation_id)
                .all()
            )
            self.assertTrue(signals)
            self.assertTrue(any(item.signal_type == "daily_workflow" for item in signals))

    def test_chat_boots_with_ollama_disabled_and_uses_deterministic_fallback(self):
        with patch.dict(os.environ, {"PARDHA_OLLAMA_ENABLED": "false", "PARDHA_REASONING_PROVIDER": "deterministic"}, clear=False):
            response = self.client.post(
                "/conversations/messages",
                json={"business_id": self.business["business_id"], "message": "Analyze retention risk for DP360"},
            )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["response"]
        self.assertFalse(payload["reasoning_used"])
        self.assertEqual(payload["reasoning_provider"], "deterministic")
        self.assertTrue(payload["reasoning_metadata"]["fallback_used"])

    @patch(
        "app.conversations.composer.reasoning_gateway.generate",
        return_value=ReasoningGatewayResult(
            response="Model-backed retention assessment.",
            provider="ollama",
            model="qwen3:8b",
            source="ollama",
            metadata={"provider": "ollama", "fallback_used": False},
        ),
    )
    def test_reasoning_required_prompt_uses_gateway_and_records_model_metadata(self, generate):
        response = self.client.post(
            "/conversations/messages",
            json={"business_id": self.business["business_id"], "message": "Analyze retention risk for DP360"},
        )

        self.assertEqual(response.status_code, 201)
        generate.assert_called_once()
        payload = response.json()["response"]
        self.assertEqual(response.json()["assistant_message"]["content"], "Model-backed retention assessment.")
        self.assertTrue(payload["reasoning_used"])
        self.assertEqual(payload["reasoning_provider"], "ollama")
        self.assertEqual(payload["reasoning_metadata"]["provider"], "ollama")
        self.assertEqual(payload["reasoning_metadata"]["model"], "qwen3:8b")
        self.assertFalse(payload["reasoning_metadata"]["fallback_used"])

    @patch(
        "app.conversations.composer.reasoning_gateway.generate",
        return_value=ReasoningGatewayResult(
            response="Qwen coding answer.",
            provider="ollama",
            model="qwen3:8b",
            source="ollama",
            metadata={"provider": "ollama", "fallback_used": False},
        ),
    )
    def test_ollama_qwen_route_requests_qwen_model_through_gateway(self, generate):
        response = self.client.post(
            "/conversations/messages",
            json={"message": "Write a Python function to retry an API call"},
        )

        self.assertEqual(response.status_code, 201)
        args, kwargs = generate.call_args
        self.assertEqual(args[2], "qwen3:8b")
        self.assertEqual(kwargs["provider"], "ollama")
        payload = response.json()["response"]
        self.assertTrue(payload["reasoning_used"])
        self.assertEqual(payload["reasoning_metadata"]["requested_provider"], "ollama")
        self.assertEqual(payload["reasoning_metadata"]["requested_model"], "qwen3:8b")

    @patch(
        "app.conversations.composer.reasoning_gateway.generate",
        return_value=ReasoningGatewayResult(
            response="I can help with the code question directly.",
            provider="deterministic",
            model="pardha-deterministic-runtime",
            source="deterministic_fallback",
            metadata={
                "requested_provider": "ollama",
                "fallback_provider": "deterministic",
                "fallback_reason": "offline",
                "fallback_used": True,
            },
        ),
    )
    def test_failed_qwen_call_falls_back_without_marking_reasoning_used(self, generate):
        response = self.client.post(
            "/conversations/messages",
            json={"message": "Write a Python function to retry an API call"},
        )

        self.assertEqual(response.status_code, 201)
        generate.assert_called_once()
        payload = response.json()["response"]
        self.assertFalse(payload["reasoning_used"])
        self.assertEqual(payload["reasoning_provider"], "deterministic")
        self.assertTrue(payload["reasoning_metadata"]["fallback_used"])
        self.assertEqual(payload["reasoning_metadata"]["fallback_reason"], "offline")


if __name__ == "__main__":
    unittest.main()
