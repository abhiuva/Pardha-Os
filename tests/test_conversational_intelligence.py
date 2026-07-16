import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_conversational_intelligence.db")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import CapabilityExecution, ConversationMessage, ConversationSession, ConversationTimelineEvent
from app.main import app


class ConversationalIntelligenceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.business = next(item for item in cls.client.get("/businesses").json() if item["business_name"] == "DP360")

    def test_conversation_flows_through_kernel_and_persists_timeline(self):
        response = self.client.post(
            "/conversations/messages",
            json={"business_id": self.business["business_id"], "message": "Review backend architecture"},
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        conversation_id = payload["conversation"]["conversation_id"]
        self.assertEqual(payload["assistant_message"]["capability_ids"], ["cto.technical_brief"])
        self.assertEqual(payload["response"]["execution"]["status"], "succeeded")
        self.assertGreaterEqual(payload["response"]["confidence"], 50)
        self.assertTrue(payload["response"]["next_recommended_actions"])
        self.assertIn("business.context", payload["assistant_message"]["context_snapshot"]["context_sources"])
        self.assertIn("knowledge.search", payload["assistant_message"]["context_snapshot"]["context_sources"])

        detail = self.client.get(f"/conversations/{conversation_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.json()["messages"]), 2)
        timeline_types = {item["event_type"] for item in detail.json()["timeline"]}
        self.assertTrue({"question", "intent", "capability_selection", "execution", "verification", "result"}.issubset(timeline_types))

        with SessionLocal() as session:
            self.assertIsNotNone(session.get(ConversationSession, conversation_id))
            self.assertEqual(session.query(ConversationMessage).filter(ConversationMessage.conversation_id == conversation_id).count(), 2)
            self.assertGreaterEqual(session.query(ConversationTimelineEvent).filter(ConversationTimelineEvent.conversation_id == conversation_id).count(), 6)
            self.assertGreaterEqual(session.query(CapabilityExecution).count(), 1)

    def test_history_search_pin_archive_restore_and_export(self):
        created = self.client.post("/conversations", json={"title": "Pinned strategy review", "business_id": self.business["business_id"], "pinned": True})
        self.assertEqual(created.status_code, 201)
        conversation_id = created.json()["conversation_id"]

        message = self.client.post(
            f"/conversations/{conversation_id}/messages",
            json={"business_id": self.business["business_id"], "message": "Generate executive summary"},
        )
        self.assertEqual(message.status_code, 201)
        self.assertEqual(message.json()["assistant_message"]["capability_ids"], ["ceo.daily_brief"])

        listed = self.client.get("/conversations?search=strategy")
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(item["conversation_id"] == conversation_id for item in listed.json()))

        archived = self.client.patch(f"/conversations/{conversation_id}", json={"archived": True})
        self.assertEqual(archived.status_code, 200)
        self.assertTrue(archived.json()["archived"])

        restored = self.client.post(f"/conversations/{conversation_id}/restore")
        self.assertEqual(restored.status_code, 200)
        self.assertFalse(restored.json()["archived"])

        exported = self.client.get(f"/conversations/{conversation_id}/export")
        self.assertEqual(exported.status_code, 200)
        self.assertTrue(exported.json()["messages"])
        self.assertTrue(exported.json()["timeline"])

    def test_streaming_returns_expected_phases(self):
        response = self.client.post(
            "/conversations/stream",
            json={"business_id": self.business["business_id"], "message": "Check system health"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.text
        for phase in ("thinking", "planning", "executing", "verifying", "completed"):
            self.assertIn(f'"phase": "{phase}"', body)

    def test_ambiguous_business_asks_clarification_without_execution(self):
        response = self.client.post("/conversations/messages", json={"message": "Create roadmap"})
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn("which business should i use", payload["assistant_message"]["content"].lower())
        self.assertEqual(payload["response"]["verification"]["status"], "needs_clarification")
        self.assertEqual(payload["assistant_message"]["capability_ids"], [])


if __name__ == "__main__":
    unittest.main()
