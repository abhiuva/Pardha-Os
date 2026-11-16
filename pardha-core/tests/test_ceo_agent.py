import unittest

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.db.models import Agent as AgentModel
from app.events.bus import clear_events
from app.kernel.registry import register_agent
from app.memory.engine import clear_memories
from app.main import app


class CeoAgentTestCase(unittest.TestCase):
    def setUp(self):
        with SessionLocal() as session:
            session.query(AgentModel).delete()
            session.commit()

        clear_events()
        clear_memories()
        self.client = TestClient(app)

    def tearDown(self):
        with SessionLocal() as session:
            session.query(AgentModel).delete()
            session.commit()

        clear_events()
        clear_memories()

    def test_generate_daily_brief_with_data(self):
        agent_a = register_agent("Alpha", "research")
        agent_b = register_agent("Beta", "operations")

        self.client.post(
            "/events",
            json={
                "source_agent": agent_a["id"],
                "target_agent": agent_b["id"],
                "event_type": "agent.started",
                "payload": {"status": "ok"},
            },
        )

        self.client.post(
            "/memories",
            json={
                "agent_id": agent_a["id"],
                "content": "Observed agent startup behavior.",
                "metadata": {"stage": "init"},
            },
        )

        response = self.client.get("/agents/ceo/brief")
        self.assertEqual(response.status_code, 200)

        brief = response.json()
        self.assertIn("active_agents", brief)
        self.assertEqual(len(brief["active_agents"]), 2)
        self.assertIn("recent_events", brief)
        self.assertEqual(len(brief["recent_events"]), 1)
        self.assertIn("recent_memories", brief)
        self.assertEqual(len(brief["recent_memories"]), 1)
        self.assertIn("risks", brief)
        self.assertIn("recommendations", brief)

    def test_generate_daily_brief_without_data(self):
        response = self.client.get("/agents/ceo/brief")
        self.assertEqual(response.status_code, 200)

        brief = response.json()
        self.assertEqual(brief["active_agents"], [])
        self.assertEqual(brief["recent_events"], [])
        self.assertEqual(brief["recent_memories"], [])
        self.assertIn("No registered agents are available for execution.", brief["risks"])
        self.assertIn("No events have been recorded; agent activity is not observable.", brief["risks"])
        self.assertIn("No memories are stored; the system has limited recall.", brief["risks"])
        self.assertGreaterEqual(len(brief["recommendations"]), 1)


if __name__ == "__main__":
    unittest.main()
