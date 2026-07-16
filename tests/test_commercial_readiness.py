import os
import unittest

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import AgentCollaboration as AgentCollaborationModel
from app.db.models import Event as EventModel
from app.db.models import JiraIssue as JiraIssueModel
from app.db.models import JiraProject as JiraProjectModel
from app.db.models import Knowledge as KnowledgeModel
from app.db.models import Objective as ObjectiveModel
from app.db.models import Project as ProjectModel
from app.db.models import Task as TaskModel
from app.main import app


class CommercialReadinessTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self.client.post("/demo/seed")

    def test_connector_statuses_are_honest_about_missing_auth(self):
        for key in [
            "GMAIL_CLIENT_ID",
            "GMAIL_CLIENT_SECRET",
            "GMAIL_REFRESH_TOKEN",
            "OUTLOOK_CLIENT_ID",
            "OUTLOOK_CLIENT_SECRET",
            "OUTLOOK_TENANT_ID",
            "OUTLOOK_REFRESH_TOKEN",
            "PARDHA_WHATSAPP_ACCESS_TOKEN",
            "PARDHA_WHATSAPP_PHONE_NUMBER_ID",
            "JIRA_URL",
            "JIRA_EMAIL",
            "JIRA_API_TOKEN",
            "JIRA_PROJECT_KEY",
            "GOOGLE_CALENDAR_CLIENT_ID",
            "GOOGLE_CALENDAR_CLIENT_SECRET",
            "GOOGLE_CALENDAR_REFRESH_TOKEN",
            "GITHUB_TOKEN",
            "VSCODE_PID",
            "PARDHA_OLLAMA_ENABLED",
        ]:
            os.environ.pop(key, None)

        response = self.client.get("/commercial/connectors/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        providers = {item["provider"] for item in payload}
        self.assertEqual(providers, {"gmail", "outlook", "whatsapp", "jira", "google_calendar", "github", "vscode", "ollama"})
        self.assertTrue(all(item["connected"] is False for item in payload))
        for provider in ("gmail", "outlook", "whatsapp", "jira", "google_calendar", "github", "vscode", "ollama"):
            self.assertIn(provider, providers)

    def test_dp360_demo_load_populates_customer_demo_surfaces(self):
        response = self.client.post("/commercial/demo/dp360")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["business_name"], "DP360")
        self.assertGreater(payload["counts"]["knowledge"], 0)
        self.assertGreater(payload["counts"]["objectives"], 0)
        self.assertGreater(payload["counts"]["tasks"], 0)
        self.assertTrue(payload["ceo_brief_generated"])
        self.assertTrue(payload["pm_roadmap_generated"])
        self.assertTrue(payload["cto_plan_generated"])
        self.assertTrue(payload["journey"]["ready"])

    def test_founder_dashboard_and_journey_are_available(self):
        demo = self.client.post("/commercial/demo/dp360").json()
        business_id = demo["business_id"]

        founder = self.client.get(f"/commercial/founder-dashboard?business_id={business_id}")
        journey = self.client.get(f"/commercial/demo/journey?business_id={business_id}")

        self.assertEqual(founder.status_code, 200)
        self.assertEqual(journey.status_code, 200)
        self.assertEqual(founder.json()["business_name"], "DP360")
        self.assertTrue(founder.json()["todays_priorities"])
        self.assertEqual(len(journey.json()["steps"]), 8)
        self.assertTrue(journey.json()["ready"])

    def test_system_health_exposes_commercial_diagnostics(self):
        response = self.client.get("/commercial/system/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["backend"]["status"], "healthy")
        self.assertIn("database_type", payload["database"])
        self.assertIn("memory_mb", payload["resources"])
        self.assertIn("environment", payload["runtime"])
        self.assertIn("connectors", payload["communications"])


if __name__ == "__main__":
    unittest.main()
