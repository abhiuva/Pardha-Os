import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chief_of_staff.db")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import ChiefConversation, ChiefMessage, FounderGoal
from app.main import app


class ChiefOfStaffTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        businesses = cls.client.get("/businesses")
        cls.business = businesses.json()[0]

    def test_persistent_conversation_routes_to_existing_sales_workflow(self):
        response = self.client.post(
            "/chief/chat",
            json={
                "business_id": self.business["business_id"],
                "message": "We need five eCommerce pilot customers.",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["assistant_message"]["intent"], "sales_prospects")
        self.assertIn("prospect", payload["assistant_message"]["content"].lower())
        conversation_id = payload["conversation"]["conversation_id"]

        conversations = self.client.get(f"/chief/conversations?business_id={self.business['business_id']}")
        self.assertEqual(conversations.status_code, 200)
        self.assertTrue(any(item["conversation_id"] == conversation_id for item in conversations.json()))

        messages = self.client.get(f"/chief/conversations/{conversation_id}?business_id={self.business['business_id']}")
        self.assertEqual(messages.status_code, 200)
        self.assertEqual([message["role"] for message in messages.json()], ["user", "assistant"])

        with SessionLocal() as session:
            self.assertIsNotNone(session.get(ChiefConversation, conversation_id))
            self.assertEqual(
                session.query(ChiefMessage).filter(ChiefMessage.conversation_id == conversation_id).count(),
                2,
            )

    def test_founder_goal_creates_objective_plans_and_followups(self):
        response = self.client.post(
            "/chief/goals",
            json={
                "business_id": self.business["business_id"],
                "title": "Acquire 5 eCommerce Pilot Customers",
                "priority": "high",
                "owner": "Founder",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["title"], "Acquire 5 eCommerce Pilot Customers")
        self.assertTrue(payload["objective_id"])
        self.assertGreaterEqual(payload["plans"]["task_count"], 1)
        self.assertTrue(payload["timeline"])
        self.assertTrue(payload["daily_followups"])

        goals = self.client.get(f"/chief/goals?business_id={self.business['business_id']}")
        self.assertEqual(goals.status_code, 200)
        self.assertTrue(any(goal["goal_id"] == payload["goal_id"] for goal in goals.json()))

        with SessionLocal() as session:
            self.assertIsNotNone(session.get(FounderGoal, payload["goal_id"]))

    def test_executive_command_center_and_help_are_available(self):
        command = self.client.get(f"/chief/executive-command?business_id={self.business['business_id']}")
        self.assertEqual(command.status_code, 200)
        command_payload = command.json()
        departments = {department["name"] for department in command_payload["departments"]}
        self.assertTrue({"CEO", "PM", "CTO", "Sales", "Marketing", "Operations"}.issubset(departments))
        self.assertTrue(command_payload["quick_actions"])

        help_response = self.client.get("/chief/help?question=How%20do%20I%20upload%20knowledge")
        self.assertEqual(help_response.status_code, 200)
        help_payload = help_response.json()
        self.assertIn("Knowledge", " ".join(help_payload["related_actions"]))
        self.assertIn("upload", help_payload["answer"].lower())


if __name__ == "__main__":
    unittest.main()
