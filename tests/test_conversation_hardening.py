import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_conversation_hardening.db")

from fastapi.testclient import TestClient

from app.capabilities.service import ensure_default_capabilities, get_capability
from app.db import SessionLocal, init_db
from app.db.models import FounderOperationalLearning
from app.main import app


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


if __name__ == "__main__":
    unittest.main()
