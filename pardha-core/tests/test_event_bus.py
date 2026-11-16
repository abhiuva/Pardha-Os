import unittest

from fastapi.testclient import TestClient

from app.events.bus import clear_events
from app.main import app


class EventBusTestCase(unittest.TestCase):
    def setUp(self):
        clear_events()
        self.client = TestClient(app)

    def tearDown(self):
        clear_events()

    def test_publish_event_and_get_events(self):
        event_data = {
            "source_agent": "agent-alpha",
            "target_agent": "agent-beta",
            "event_type": "agent.triggered",
            "payload": {"message": "hello"},
        }

        response = self.client.post("/events", json=event_data)
        self.assertEqual(response.status_code, 200)

        event = response.json()
        self.assertEqual(event["source_agent"], event_data["source_agent"])
        self.assertEqual(event["target_agent"], event_data["target_agent"])
        self.assertEqual(event["event_type"], event_data["event_type"])
        self.assertEqual(event["payload"], event_data["payload"])
        self.assertIn("event_id", event)
        self.assertIn("timestamp", event)

        response = self.client.get("/events")
        self.assertEqual(response.status_code, 200)

        events = response.json()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], event["event_id"])
        self.assertEqual(events[0]["event_type"], event["event_type"])

    def test_get_events_by_agent_returns_related_events(self):
        event_a = {
            "source_agent": "agent-alpha",
            "target_agent": "agent-beta",
            "event_type": "agent.started",
            "payload": {"step": 1},
        }
        event_b = {
            "source_agent": "agent-gamma",
            "target_agent": "agent-alpha",
            "event_type": "agent.responded",
            "payload": {"status": "ok"},
        }

        self.client.post("/events", json=event_a)
        self.client.post("/events", json=event_b)

        response = self.client.get("/events/agent-alpha")
        self.assertEqual(response.status_code, 200)

        events = response.json()
        self.assertEqual(len(events), 2)
        self.assertTrue(any(item["event_type"] == "agent.started" for item in events))
        self.assertTrue(any(item["event_type"] == "agent.responded" for item in events))

    def test_publish_event_validates_required_fields(self):
        response = self.client.post("/events", json={"source_agent": "agent-alpha"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
