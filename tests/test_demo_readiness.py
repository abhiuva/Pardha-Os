import unittest

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import (
    AgentCollaboration as AgentCollaborationModel,
    Agent as AgentModel,
    Event as EventModel,
    JiraIssue as JiraIssueModel,
    JiraProject as JiraProjectModel,
    Knowledge as KnowledgeModel,
    Objective as ObjectiveModel,
    Project as ProjectModel,
    Task as TaskModel,
)
from app.demo.service import ensure_demo_data, run_founder_copilot
from app.main import app


class DemoReadinessTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self._clear_demo_data()

    def tearDown(self):
        self._clear_demo_data()

    def _clear_demo_data(self):
        with SessionLocal() as session:
            session.query(JiraIssueModel).delete()
            session.query(JiraProjectModel).delete()
            session.query(AgentCollaborationModel).delete()
            session.query(TaskModel).delete()
            session.query(ObjectiveModel).delete()
            session.query(ProjectModel).delete()
            session.query(EventModel).delete()
            session.query(KnowledgeModel).delete()
            session.query(AgentModel).delete()
            session.commit()

    def test_seed_demo_data_creates_workspaces_objectives_tasks_knowledge_and_jira(self):
        result = ensure_demo_data()

        business_names = {business.business_name for business in result.businesses}
        self.assertTrue({"UVA", "DP360", "EatOnTime", "Trevia", "Cloud Kitchen Demo", "E-commerce Demo"}.issubset(business_names))
        self.assertGreaterEqual(result.objectives_created, 10)
        self.assertGreaterEqual(result.projects_created, 6)
        self.assertGreaterEqual(result.knowledge_created, 9)
        self.assertGreaterEqual(result.jira_issues_created, 1)

        with SessionLocal() as session:
            self.assertEqual(session.query(AgentModel).count(), 3)
            self.assertGreaterEqual(session.query(ProjectModel).count(), 6)
            self.assertGreaterEqual(session.query(TaskModel).count(), 54)
            self.assertGreaterEqual(session.query(JiraIssueModel).count(), 1)

    def test_seed_endpoint_is_idempotent(self):
        first = self.client.post("/demo/seed").json()
        second = self.client.post("/demo/seed").json()

        self.assertEqual(first["objectives_created"], 10)
        self.assertEqual(first["projects_created"], 6)
        self.assertEqual(second["objectives_created"], 0)
        self.assertEqual(second["projects_created"], 0)
        self.assertEqual(second["knowledge_created"], 0)
        self.assertEqual(second["jira_issues_created"], 0)

    def test_founder_copilot_generates_objective_roadmap_engineering_tasks(self):
        ensure_demo_data()

        result = run_founder_copilot("Launch EatOnTime in 3 schools")

        self.assertEqual(result.business_name, "EatOnTime")
        self.assertIn("CEO", " ".join(result.ceo_strategy))
        self.assertEqual(len(result.pm_roadmap), 3)
        self.assertEqual(len(result.cto_tasks), 3)
        self.assertEqual(result.workflow.objective.status, "IN_PROGRESS")
        self.assertEqual(len(result.workflow.collaborations), 14)

    def test_founder_copilot_endpoint_supports_retention_demo_scenario(self):
        ensure_demo_data()

        response = self.client.post(
            "/copilot/founder",
            json={"prompt": "Improve customer retention by 15%", "business_name": "DP360"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["business_name"], "DP360")
        self.assertIn("Improve customer retention by 15%", payload["workflow"]["objective"]["title"])
        self.assertEqual(len(payload["pm_roadmap"]), 3)
        self.assertEqual(len(payload["cto_tasks"]), 3)


if __name__ == "__main__":
    unittest.main()
